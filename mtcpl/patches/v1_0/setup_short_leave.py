import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Leave Type": [
				{
					"fieldname": "custom_is_monthly_allocated",
					"label": "Is Monthly Allocated",
					"fieldtype": "Check",
					"insert_after": "is_compensatory",
				},
				{
					"fieldname": "custom_number_of_leaves_per_month_",
					"label": "Number of leaves per month",
					"fieldtype": "Float",
					"insert_after": "custom_is_monthly_allocated",
					"depends_on": "custom_is_monthly_allocated",
				},
			],
			"Attendance": [
				{
					"fieldname": "custom_short_leave_application",
					"label": "Short Leave Application",
					# Data, not Link: a Link would make Frappe list the shared Attendance as
					# linked to the Short Leave and offer to cancel it with the application
					"fieldtype": "Data",
					"insert_after": "custom_short_leave_source",
					"read_only": 1,
				},
			],
		}
	)

	if not frappe.db.exists("Leave Type", "Short Leave"):
		return

	# Leave Allocation rejects allocations above Max Leave Allocation, and it is 0.5 today
	max_allowed = frappe.db.get_value("Leave Type", "Short Leave", "max_leaves_allowed")
	values = {"custom_is_monthly_allocated": 1, "custom_number_of_leaves_per_month_": 2}
	if (max_allowed or 0) < 2:
		values["max_leaves_allowed"] = 24
	frappe.db.set_value("Leave Type", "Short Leave", values)
