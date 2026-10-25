from itertools import groupby

import frappe
from frappe.utils import cint
from hrms.hr.doctype.employee_checkin.employee_checkin import handle_attendance_exception
from hrms.hr.doctype.shift_type.shift_type import ShiftType

from mtcpl.api.attendance_review import (
	create_draft_attendance,
	get_review_reason,
	get_settings,
	is_review_enabled,
)
from mtcpl.overrides.leave_application import get_approved_short_leave


class CustomShiftType(ShiftType):
	def _process(self, logs):
		"""With Attendance Review on, irregular days become draft Attendance for HR; everything
		else goes through the standard HRMS processing."""
		if not is_review_enabled():
			return super()._process(logs)

		key = lambda log: (log["employee"], log["shift_start"])  # noqa
		remaining = []
		for (employee, shift_start), group in groupby(sorted(logs, key=key), key=key):
			group = list(group)
			attendance_date = shift_start.date()
			reason = get_review_reason(group, self)

			if (
				not reason
				or not self.should_mark_attendance(employee, attendance_date)
				# leave, attendance requests and half day records are left to HRMS
				or frappe.db.exists(
					"Attendance",
					{"employee": employee, "attendance_date": attendance_date, "docstatus": ["<", 2]},
				)
			):
				remaining.extend(group)
				continue

			try:
				frappe.db.savepoint("attendance_creation")
				create_draft_attendance(self, group, reason)
			except frappe.ValidationError as e:
				handle_attendance_exception([log.name for log in group], e)

		frappe.db.commit()  # nosemgrep
		return super()._process(remaining)

	def get_attendance(self, logs):
		"""Count approved Short Leave hours as worked time before the Absent / Half Day / Present
		thresholds are applied. The recorded working hours stay the actual hours from check-ins.
		With Attendance Review on, the full-day tolerance also counts towards the Half Day threshold."""
		status, working_hours, late_entry, early_exit, in_time, out_time = super().get_attendance(logs)

		_short_leave, hours = get_approved_short_leave(logs[0].employee, logs[0].shift_start.date())
		tolerance = cint(get_settings().full_day_tolerance_minutes) / 60 if is_review_enabled() else 0
		if hours or tolerance:
			credited_hours = working_hours + hours
			if (
				self.working_hours_threshold_for_absent
				and credited_hours < self.working_hours_threshold_for_absent
			):
				status = "Absent"
			elif (
				self.working_hours_threshold_for_half_day
				and credited_hours + tolerance < self.working_hours_threshold_for_half_day
			):
				status = "Half Day"
			else:
				status = "Present"

		return status, working_hours, late_entry, early_exit, in_time, out_time
