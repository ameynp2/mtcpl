import frappe
from frappe.utils import cint, flt, get_first_day, get_last_day, getdate, nowdate

SHORT_LEAVE = "Short Leave"
DEFAULT_MONTHLY_SHORT_LEAVES = 2


def allocate_monthly_short_leave():
	"""Allocate this month's Short Leaves to active employees.

	Safe to run any day of the month: employees who already have an allocation are skipped,
	so it also covers new joiners and runs missed by the scheduler.
	"""
	leave_type = frappe.db.get_value(
		"Leave Type",
		SHORT_LEAVE,
		["custom_is_monthly_allocated", "custom_number_of_leaves_per_month_"],
		as_dict=True,
	)
	if not leave_type or not cint(leave_type.custom_is_monthly_allocated):
		return

	leaves = flt(leave_type.custom_number_of_leaves_per_month_) or DEFAULT_MONTHLY_SHORT_LEAVES
	month_start = get_first_day(getdate(nowdate()))
	month_end = get_last_day(month_start)

	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "company", "date_of_joining"],
	)
	for employee in employees:
		try:
			from_date = max(month_start, getdate(employee.date_of_joining or month_start))
			if from_date > month_end:
				continue

			allocation = frappe.db.get_value(
				"Leave Allocation",
				{
					"employee": employee.name,
					"leave_type": SHORT_LEAVE,
					"from_date": ("<=", month_end),
					"to_date": (">=", month_start),
					"docstatus": ("<", 2),
				},
				["name", "docstatus"],
				as_dict=True,
			)
			if allocation and allocation.docstatus == 1:
				continue

			if allocation:
				# a draft left behind by an earlier run never creates ledger entries
				doc = frappe.get_doc("Leave Allocation", allocation.name)
			else:
				doc = frappe.get_doc(
					{
						"doctype": "Leave Allocation",
						"employee": employee.name,
						"leave_type": SHORT_LEAVE,
						"from_date": from_date,
						"to_date": month_end,
						"new_leaves_allocated": leaves,
						"company": employee.company,
						"description": "Monthly Short Leave Allocation",
					}
				)
				doc.insert(ignore_permissions=True)

			doc.submit()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				frappe.get_traceback(), f"Monthly Short Leave allocation failed for {employee.name}"
			)


def flag_short_leave_on_attendance(doc, method=None):
	"""Attendance hook: an attendance marked after the Short Leave was approved (for example from
	biometric check-ins) gets the Short Leave flags, so the leave stays visible on the record."""
	from mtcpl.overrides.leave_application import get_approved_short_leave, set_short_leave_on_attendance

	if doc.status in ("On Leave", "Absent") or doc.custom_short_leave_applied:
		return

	short_leave, hours = get_approved_short_leave(doc.employee, doc.attendance_date)
	if short_leave:
		set_short_leave_on_attendance(doc.name, short_leave, hours)
