import frappe


def execute():
	# Link fields make Frappe offer to cancel the shared Attendance along with a Short Leave
	name = "Attendance-custom_short_leave_application"
	if frappe.db.exists("Custom Field", name):
		frappe.db.set_value("Custom Field", name, {"fieldtype": "Data", "options": None})
		frappe.clear_cache(doctype="Attendance")
