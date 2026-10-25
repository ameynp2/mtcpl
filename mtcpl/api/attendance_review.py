import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_url_to_form, now_datetime
from hrms.hr.doctype.employee_checkin.employee_checkin import update_attendance_in_checkins


def get_settings():
	return frappe.get_cached_doc("MTCPL Settings")


def is_review_enabled():
	return bool(cint(get_settings().enable_attendance_review))


def merge_punches(logs, gap_seconds):
	"""Drop punches that follow the previous one within gap_seconds (the device pushes duplicates)."""
	merged = []
	for log in sorted(logs, key=lambda log: log.time):
		if merged and (log.time - merged[-1].time).total_seconds() <= gap_seconds:
			continue
		merged.append(log)
	return merged


def get_review_reason(logs, shift):
	"""Why a shift's logs need HR's decision, or None if HRMS can decide on its own."""
	settings = get_settings()
	punches = merge_punches(logs, cint(settings.min_punch_gap_seconds))

	if len(punches) == 1:
		if not cint(settings.review_missing_punch):
			return None
		log_type = punches[0].log_type
		if log_type == "IN":
			return "Missing OUT punch"
		if log_type == "OUT":
			return "Missing IN punch"
		return "Single punch"

	if not cint(settings.review_short_hours):
		return None

	span = (punches[-1].time - punches[0].time).total_seconds()
	if span < cint(settings.double_tap_minutes) * 60:
		return "IN and OUT within a few minutes"

	full_day = flt(shift.working_hours_threshold_for_half_day)
	hours = span / 3600
	if full_day and hours < full_day - cint(settings.full_day_tolerance_minutes) / 60:
		return f"Worked {hours:.1f}h of {full_day:g}h"

	return None


def create_draft_attendance(shift, logs, reason):
	"""Create the Attendance as a draft with HRMS's suggested status; HR confirms and submits it."""
	status, hours, late_entry, early_exit, in_time, out_time = shift.get_attendance(logs)
	attendance = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": logs[0].employee,
			"attendance_date": logs[0].shift_start.date(),
			"status": status,
			"working_hours": hours,
			"shift": shift.name,
			"late_entry": late_entry,
			"early_exit": early_exit,
			"in_time": in_time,
			"out_time": out_time,
			"half_day_status": "Absent" if status == "Half Day" else None,
			"custom_needs_review": 1,
			"custom_review_reason": reason,
		}
	).insert()
	update_attendance_in_checkins([log.name for log in logs], attendance.name)
	return attendance


def get_pending_drafts(start_date=None, end_date=None, company=None, employee=None, older_than=None, limit=None):
	filters = {"docstatus": 0, "custom_needs_review": 1}
	if start_date and end_date:
		filters["attendance_date"] = ["between", [start_date, end_date]]
	if company:
		filters["company"] = company
	if employee:
		filters["employee"] = employee
	if older_than:
		filters["creation"] = ["<=", older_than]
	return frappe.get_all(
		"Attendance",
		filters=filters,
		fields=["name", "employee", "employee_name", "attendance_date", "status", "custom_review_reason"],
		order_by="attendance_date",
		limit=limit,
	)


def send_pending_review_reminder():
	"""Email the HR role the draft attendance that has waited for review too long."""
	settings = get_settings()
	if not (cint(settings.enable_attendance_review) and cint(settings.enable_pending_review_reminder)):
		return

	older_than = add_days(now_datetime(), -cint(settings.reminder_after_days))
	drafts = get_pending_drafts(older_than=older_than)
	if not drafts:
		return

	recipients = frappe.get_all(
		"User",
		filters={
			"enabled": 1,
			"name": ["in", frappe.get_all("Has Role", filters={"role": settings.reminder_role or "HR Manager", "parenttype": "User"}, pluck="parent")],
		},
		pluck="email",
	)
	if not recipients:
		return

	rows = "".join(
		f"<tr><td><a href='{get_url_to_form('Attendance', d.name)}'>{d.name}</a></td>"
		f"<td>{d.employee_name or d.employee}</td><td>{d.attendance_date}</td>"
		f"<td>{d.status}</td><td>{d.custom_review_reason or ''}</td></tr>"
		for d in drafts[:100]
	)
	more = f"<p>and {len(drafts) - 100} more.</p>" if len(drafts) > 100 else ""
	frappe.sendmail(
		recipients=recipients,
		subject=f"{len(drafts)} attendance record(s) waiting for review",
		message=(
			"<p>These attendance drafts are not counted in salary until they are confirmed and submitted.</p>"
			"<table border='1' cellpadding='4' style='border-collapse:collapse'>"
			"<tr><th>Attendance</th><th>Employee</th><th>Date</th><th>Suggested</th><th>Reason</th></tr>"
			f"{rows}</table>{more}"
		),
	)


def check_payroll_entry(doc, method=None):
	mode = get_settings().payroll_check
	if mode not in ("Warn", "Block"):
		return

	drafts = get_pending_drafts(doc.start_date, doc.end_date, company=doc.company)
	if not drafts:
		return

	message = _("{0} attendance record(s) are still waiting for review between {1} and {2}. Draft attendance is not counted in salary.").format(
		len(drafts), doc.start_date, doc.end_date
	) + "<br><a href='/app/attendance?docstatus=0&custom_needs_review=1'>" + _("Open the pending list") + "</a>"
	if mode == "Block":
		frappe.throw(message, title=_("Attendance Pending Review"))
	frappe.msgprint(message, title=_("Attendance Pending Review"), indicator="orange")


def check_salary_slip(doc, method=None):
	if get_settings().payroll_check != "Block":
		return

	drafts = get_pending_drafts(doc.start_date, doc.end_date, employee=doc.employee)
	if drafts:
		frappe.throw(
			_("{0} has {1} attendance record(s) pending review between {2} and {3}.").format(
				doc.employee_name or doc.employee, len(drafts), doc.start_date, doc.end_date
			),
			title=_("Attendance Pending Review"),
		)
