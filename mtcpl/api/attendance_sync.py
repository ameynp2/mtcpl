from datetime import timedelta

import frappe
from frappe.utils import add_days, cint, get_datetime, getdate, today
from hrms.hr.doctype.employee_checkin.employee_checkin import update_attendance_in_checkins

from mtcpl.api.attendance_review import get_review_reason, get_settings

STATUS_RANK = {"Absent": 0, "Half Day": 1, "Present": 2}


def set_attendance_cutoff():
	"""Only treat shifts that ended before today as complete.

	The biometric laptop can push the previous day's OUT punches the next morning, so
	HRMS must not finalise a day until the following afternoon. HRMS's own hourly job
	does the processing; this only moves the cut-off.
	"""
	if not cint(get_settings().hold_attendance_for_late_checkins):
		return

	cutoff = get_datetime(today()) - timedelta(minutes=1)
	for shift in frappe.get_all(
		"Shift Type", filters={"enable_auto_attendance": 1, "auto_update_last_sync": 0}, pluck="name"
	):
		frappe.db.set_value("Shift Type", shift, "last_sync_of_checkin", cutoff)


def reconcile_late_checkins(days=7, dry_run=False):
	"""Re-evaluate attendance when check-ins reach ERPNext after the attendance was created.

	HRMS never revisits a day once its Attendance exists: a late OUT punch gets
	skip_auto_attendance=1 and the Absent stays. This recomputes status and hours from all
	of the shift's logs. Only ever upgrades an Absent or Half Day record (Absent -> Half Day/Present,
	Half Day -> Present); Present, leave and Attendance Request records are left alone.

	A draft awaiting HR review is refreshed with the new punches, and submitted only if the
	late check-ins removed the reason for review and nobody has edited it.
	"""
	if not cint(get_settings().reconcile_late_checkins):
		return []

	since = add_days(today(), -cint(days))
	groups = {
		(log.employee, log.shift, log.shift_start)
		for log in frappe.get_all(
			"Employee Checkin",
			filters={
				"attendance": ["is", "not set"],
				"offshift": 0,
				"shift": ["is", "set"],
				"time": [">=", since],
			},
			fields=["employee", "shift", "shift_start"],
		)
	}

	changes = []
	for employee, shift, shift_start in sorted(groups, key=str):
		attendance = frappe.db.get_value(
			"Attendance",
			{"employee": employee, "attendance_date": getdate(shift_start), "docstatus": ["<", 2]},
			[
				"name",
				"status",
				"working_hours",
				"leave_application",
				"attendance_request",
				"docstatus",
				"custom_needs_review",
				"owner",
				"modified_by",
			],
			as_dict=True,
		)
		if attendance and attendance.docstatus == 0:
			if cint(attendance.custom_needs_review):
				changes.append(refresh_draft(attendance, employee, shift, shift_start, dry_run))
			continue
		if (
			not attendance
			or attendance.status not in STATUS_RANK
			or attendance.status == "Present"
			or attendance.leave_application
			or attendance.attendance_request
		):
			continue

		logs = frappe.get_all(
			"Employee Checkin",
			filters={"employee": employee, "shift": shift, "shift_start": shift_start, "offshift": 0},
			fields=["name", "employee", "log_type", "time", "shift_start", "shift_end"],
			order_by="time asc",
		)
		status, hours, late_entry, early_exit, in_time, out_time = frappe.get_cached_doc(
			"Shift Type", shift
		).get_attendance(logs)

		if STATUS_RANK.get(status, -1) <= STATUS_RANK[attendance.status]:
			continue

		changes.append((attendance.name, employee, attendance.status, status, attendance.working_hours, hours))
		if dry_run:
			continue

		frappe.db.set_value(
			"Attendance",
			attendance.name,
			{
				"status": status,
				"working_hours": hours,
				"late_entry": late_entry,
				"early_exit": early_exit,
				"in_time": in_time,
				"out_time": out_time,
				"half_day_status": "Absent" if status == "Half Day" else None,
			},
		)
		names = [log.name for log in logs]
		frappe.db.set_value("Employee Checkin", {"name": ["in", names]}, "skip_auto_attendance", 0)
		update_attendance_in_checkins(names, attendance.name)
		frappe.get_doc("Attendance", attendance.name).add_comment(
			text=f"Recomputed after late check-ins: {attendance.status} to {status}, {hours} hours."
		)

	if not dry_run:
		frappe.db.commit()  # nosemgrep
	return changes


def refresh_draft(attendance, employee, shift, shift_start, dry_run):
	logs = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "shift": shift, "shift_start": shift_start, "offshift": 0},
		fields=["name", "employee", "log_type", "time", "shift_start", "shift_end"],
		order_by="time asc",
	)
	shift_type = frappe.get_cached_doc("Shift Type", shift)
	status, hours, late_entry, early_exit, in_time, out_time = shift_type.get_attendance(logs)
	reason = get_review_reason(logs, shift_type)
	if dry_run:
		return (attendance.name, employee, attendance.status, status, attendance.working_hours, hours)

	values = {
		"status": status,
		"working_hours": hours,
		"late_entry": late_entry,
		"early_exit": early_exit,
		"in_time": in_time,
		"out_time": out_time,
		"half_day_status": "Absent" if status == "Half Day" else None,
		"custom_review_reason": reason,
		"custom_needs_review": 1 if reason else 0,
	}
	if reason and attendance.modified_by != attendance.owner:
		# HR already edited the draft; only the hours and punches follow the late check-ins
		for fieldname in ("status", "half_day_status", "custom_review_reason", "custom_needs_review"):
			values.pop(fieldname)

	frappe.db.set_value("Attendance", attendance.name, values)
	names = [log.name for log in logs]
	frappe.db.set_value("Employee Checkin", {"name": ["in", names]}, "skip_auto_attendance", 0)
	update_attendance_in_checkins(names, attendance.name)

	if not reason and attendance.modified_by == attendance.owner:
		frappe.get_doc("Attendance", attendance.name).submit()

	frappe.db.commit()  # nosemgrep
	return (attendance.name, employee, attendance.status, status, attendance.working_hours, hours)
