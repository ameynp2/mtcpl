import hashlib
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_first_day, get_last_day, getdate, nowdate
from hrms.hr.doctype.leave_application.leave_application import get_leave_details
from hrms.utils.holiday_list import get_holiday_dates_between

PROFILE_FIELDS = [
	"name",
	"employee_name",
	"image",
	"designation",
	"department",
	"branch",
	"company",
	"employment_type",
	"date_of_joining",
	"reports_to",
	"cell_number",
	"company_email",
	"personal_email",
	"default_shift",
	"holiday_list",
]


def get_session_employee():
	return frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")


def set_landing_page(bootinfo):
	"""Boot info for the Employee Dashboard: a navbar button for every employee, and a
	once-per-login redirect when enabled. The Administrator user gets neither."""
	if frappe.session.user in ("Guest", "Administrator") or not get_session_employee():
		return

	bootinfo.mtcpl_dashboard = "employee-dashboard"

	# a settings page saved before this field existed has no stored value; that means the default (on)
	stored = frappe.db.sql(
		"select value from tabSingles where doctype = 'MTCPL Settings' and field = 'employee_dashboard_as_landing_page'"
	)
	if not stored or cint(stored[0][0]):
		bootinfo.mtcpl_landing_page = bootinfo.mtcpl_dashboard
		# changes with every login, so the client redirects once per login and not on every page load
		bootinfo.mtcpl_login_marker = hashlib.sha256(frappe.session.sid.encode()).hexdigest()[:16]


@frappe.whitelist()
def get_dashboard(month=None, year=None):
	employee = get_session_employee()
	if not employee:
		return {"employee": None}

	today = getdate(nowdate())
	month_start = get_first_day(getdate(f"{cint(year) or today.year}-{cint(month) or today.month}-01"))
	month_end = get_last_day(month_start)

	profile = frappe.db.get_value("Employee", employee, PROFILE_FIELDS, as_dict=True)
	if profile.reports_to:
		profile.reports_to_name = frappe.db.get_value("Employee", profile.reports_to, "employee_name")

	days = get_attendance_days(employee, month_start, month_end)
	return {
		"employee": employee,
		"profile": profile,
		"today": str(today),
		"month_start": str(month_start),
		"month_end": str(month_end),
		"days": days,
		"holidays": get_holidays(profile, month_start, month_end),
		"leaves": get_leave_days(employee, month_start, month_end),
		"leave_balance": get_leave_balance(employee, today),
		"recent_leaves": frappe.get_all(
			"Leave Application",
			filters={"employee": employee, "docstatus": ["<", 2]},
			fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status"],
			order_by="from_date desc",
			limit=5,
		),
	}


def get_attendance_days(employee, start, end):
	"""Per date: attendance (if any) and every check-in punch."""
	days = defaultdict(lambda: {"punches": []})

	for a in frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": ["between", [start, end]], "docstatus": ["<", 2]},
		fields=[
			"attendance_date",
			"status",
			"docstatus",
			"working_hours",
			"in_time",
			"out_time",
			"late_entry",
			"early_exit",
			"custom_needs_review",
			"custom_review_reason",
		],
	):
		days[str(a.attendance_date)]["attendance"] = a

	for c in frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": ["between", [start, add_days(end, 1)]]},
		fields=["time", "log_type"],
		order_by="time asc",
	):
		if getdate(c.time) <= getdate(end):
			days[str(getdate(c.time))]["punches"].append({"time": c.time, "log_type": c.log_type})

	return days


def get_holidays(profile, start, end):
	holiday_list = profile.holiday_list or frappe.get_cached_value(
		"Company", profile.company, "default_holiday_list"
	)
	if not holiday_list:
		return {}

	names = {
		str(h.holiday_date): frappe.utils.strip_html(h.description or "").strip()
		for h in frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [start, end]]},
			fields=["holiday_date", "description"],
		)
	}
	# weekly offs have no description; make sure every holiday date is present
	for date in get_holiday_dates_between(holiday_list, start, end):
		names.setdefault(str(date), "")
	return names


def get_leave_days(employee, start, end):
	"""Date -> leave type / status for leave applications overlapping the month."""
	result = {}
	for leave in frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee,
			"docstatus": ["<", 2],
			"status": ["in", ["Open", "Approved"]],
			"from_date": ["<=", end],
			"to_date": [">=", start],
		},
		fields=["leave_type", "from_date", "to_date", "status", "half_day"],
	):
		date = max(getdate(leave.from_date), getdate(start))
		last = min(getdate(leave.to_date), getdate(end))
		while date <= last:
			result[str(date)] = {"leave_type": leave.leave_type, "status": leave.status}
			date = add_days(date, 1)
	return result


def get_leave_balance(employee, date):
	try:
		allocation = get_leave_details(employee, date)["leave_allocation"]
	except Exception:
		frappe.clear_messages()
		return []

	return [
		{
			"leave_type": leave_type,
			"total": values["total_leaves"],
			"taken": values["leaves_taken"],
			"pending": values["leaves_pending_approval"],
			"remaining": values["remaining_leaves"],
		}
		for leave_type, values in allocation.items()
	]
