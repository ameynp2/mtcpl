import frappe
from frappe import _
from frappe.utils import cint, flt, get_first_day, get_last_day, get_time, getdate
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication

SHORT_LEAVE = "Short Leave"
# unit of the Short Leave balance is hours: 2 hours per month, taken as 1 or 2 hours together
DEFAULT_MONTHLY_SHORT_LEAVE_HOURS = 2


def is_single_day(leave):
	return getdate(leave.from_date) == getdate(leave.to_date)


def is_short_leave(leave):
	return leave.leave_type == SHORT_LEAVE and is_single_day(leave)


def is_half_day_leave(leave):
	return leave.leave_type != SHORT_LEAVE and cint(leave.half_day) and is_single_day(leave)


def is_short_leave_half_day_pair(leave, other):
	"""Half Day Leave + Short Leave on the same date (either order) is the only allowed overlap."""
	if getdate(leave.from_date) != getdate(other.from_date):
		return False

	return (is_short_leave(leave) and is_half_day_leave(other)) or (
		is_half_day_leave(leave) and is_short_leave(other)
	)


def time_to_hours(value):
	value = get_time(value)
	return value.hour + value.minute / 60 + value.second / 3600


def get_monthly_short_leave_hours():
	return (
		flt(frappe.db.get_value("Leave Type", SHORT_LEAVE, "custom_number_of_leaves_per_month_"))
		or DEFAULT_MONTHLY_SHORT_LEAVE_HOURS
	)


def get_approved_short_leave(employee, date):
	"""(application name, hours) of the approved Short Leave of an employee on a date, if any."""
	leave = frappe.db.get_value(
		"Leave Application",
		{
			"employee": employee,
			"leave_type": SHORT_LEAVE,
			"from_date": date,
			"to_date": date,
			"docstatus": 1,
			"status": "Approved",
		},
		["name", "custom_short_leave_hours", "total_leave_days"],
		as_dict=True,
	)
	if not leave:
		return None, 0
	return leave.name, flt(leave.custom_short_leave_hours) or flt(leave.total_leave_days)


def get_status_for_hours(shift, working_hours):
	"""Same Absent / Half Day / Present thresholds Shift Type uses for auto attendance."""
	absent_threshold, half_day_threshold = frappe.db.get_value(
		"Shift Type",
		shift,
		["working_hours_threshold_for_absent", "working_hours_threshold_for_half_day"],
	)
	if absent_threshold and working_hours < absent_threshold:
		return "Absent"
	if half_day_threshold and working_hours < half_day_threshold:
		return "Half Day"
	return "Present"


def set_short_leave_on_attendance(attendance_name, short_leave, hours):
	"""Flag (or clear, when short_leave is empty) the Short Leave on an attendance.

	An attendance marked from biometric check-ins gets the Short Leave hours counted as worked
	time, so leaving an hour early on approved Short Leave does not turn the day into a Half Day.
	Attendance created from a leave application keeps its status.
	"""
	attendance = frappe.db.get_value(
		"Attendance",
		attendance_name,
		["status", "leave_application", "working_hours", "shift"],
		as_dict=True,
	)
	values = {
		"custom_short_leave_applied": 1 if short_leave else 0,
		"custom_short_leave_hours": flt(hours) if short_leave else 0,
		"custom_short_leave_source": "Manual" if short_leave else None,
		"custom_short_leave_application": short_leave,
	}

	if (
		not attendance.leave_application
		and attendance.shift
		and flt(attendance.working_hours) > 0
		and attendance.status in ("Present", "Half Day", "Absent")
	):
		values["status"] = get_status_for_hours(
			attendance.shift, flt(attendance.working_hours) + (flt(hours) if short_leave else 0)
		)

	frappe.db.set_value("Attendance", attendance_name, values)


class CustomLeaveApplication(LeaveApplication):
	def validate(self):
		self.validate_short_leave()
		super().validate()

	def validate_short_leave(self):
		if self.leave_type != SHORT_LEAVE:
			return

		if not is_single_day(self):
			frappe.throw(_("Short Leave can only be applied for a single day."))

		if cint(self.half_day):
			frappe.throw(_("Short Leave cannot be combined with Half Day in the same application."))

		if not (self.custom_short_leave_from_time and self.custom_short_leave_to_time):
			frappe.throw(_("Please enter the From Time and To Time of the Short Leave."))

		hours = round(
			time_to_hours(self.custom_short_leave_to_time) - time_to_hours(self.custom_short_leave_from_time),
			2,
		)
		if hours <= 0:
			frappe.throw(_("Short Leave To Time must be after From Time."))

		limit = get_monthly_short_leave_hours()
		if hours > limit:
			frappe.throw(_("A Short Leave cannot be longer than {0} hours.").format(limit))

		self.custom_short_leave_hours = hours
		self.validate_monthly_short_leave_hours(hours, limit)

	def validate_monthly_short_leave_hours(self, hours, limit):
		# rejected and cancelled applications don't count, so cancelling frees the hours again
		used = flt(
			frappe.db.sql(
				"""
				select sum(if(ifnull(custom_short_leave_hours, 0) > 0, custom_short_leave_hours, total_leave_days))
				from `tabLeave Application`
				where employee = %s and leave_type = %s and docstatus < 2
					and status not in ('Rejected', 'Cancelled')
					and from_date between %s and %s and name != %s
				""",
				(
					self.employee,
					SHORT_LEAVE,
					get_first_day(self.from_date),
					get_last_day(self.from_date),
					self.name or "",
				),
			)[0][0]
		)
		if used + hours > limit:
			frappe.throw(
				_("Only {0} hours of Short Leave are allowed per calendar month. Already applied: {1}").format(
					limit, used
				),
				title=_("Monthly Short Leave Limit Exceeded"),
			)

	def validate_balance_leaves(self):
		super().validate_balance_leaves()

		# the standard check counts the day; Short Leave consumes its hours from the balance instead
		if self.leave_type == SHORT_LEAVE and flt(self.custom_short_leave_hours):
			self.total_leave_days = flt(self.custom_short_leave_hours)

	def get_overlapping_leave_applications(self):
		return frappe.get_all(
			"Leave Application",
			filters={
				"employee": self.employee,
				"docstatus": ("<", 2),
				"status": ("in", ["Open", "Approved"]),
				"to_date": (">=", self.from_date),
				"from_date": ("<=", self.to_date),
				"name": ("!=", self.name or "New Leave Application"),
			},
			fields=["name", "leave_type", "from_date", "to_date", "half_day", "half_day_date"],
		)

	def validate_leave_overlap(self):
		overlapping_leaves = self.get_overlapping_leave_applications()
		if len(overlapping_leaves) == 1 and is_short_leave_half_day_pair(self, overlapping_leaves[0]):
			return

		super().validate_leave_overlap()

	def validate_attendance(self):
		# a Short Leave is taken on a working day, so the employee is usually already present
		if self.leave_type == SHORT_LEAVE:
			return

		super().validate_attendance()

	def create_or_update_attendance(self, attendance_name, date):
		if self.leave_type == SHORT_LEAVE:
			# a Short Leave never creates or changes the attendance status on its own: the employee
			# is present, and the hours count as worked time when attendance is marked
			if attendance_name:
				set_short_leave_on_attendance(attendance_name, self.name, self.custom_short_leave_hours)
			return

		super().create_or_update_attendance(attendance_name, date)

		short_leave, hours = get_approved_short_leave(self.employee, date)
		if short_leave:
			attendance_name = frappe.db.get_value(
				"Attendance",
				{"employee": self.employee, "attendance_date": date, "docstatus": ("!=", 2)},
				"name",
			)
			if attendance_name:
				set_short_leave_on_attendance(attendance_name, short_leave, hours)

	def cancel_attendance(self):
		if self.leave_type != SHORT_LEAVE:
			return super().cancel_attendance()

		# the standard handling cancels the day's attendance; a Short Leave only owns its flags
		attendance_name = frappe.db.get_value(
			"Attendance",
			{"employee": self.employee, "attendance_date": self.from_date, "docstatus": ("<", 2)},
			"name",
		)
		if attendance_name and frappe.db.get_value(
			"Attendance", attendance_name, "custom_short_leave_application"
		) == self.name:
			set_short_leave_on_attendance(attendance_name, None, 0)
