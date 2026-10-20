import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

SHORT_LEAVE_ONLY = 'eval:doc.leave_type=="Short Leave"'


def execute():
	create_custom_fields(
		{
			"Leave Application": [
				{
					"fieldname": "custom_short_leave_section",
					"label": "Short Leave",
					"fieldtype": "Section Break",
					"insert_after": "half_day_date",
					"depends_on": SHORT_LEAVE_ONLY,
				},
				{
					"fieldname": "custom_short_leave_from_time",
					"label": "Short Leave From Time",
					"fieldtype": "Time",
					"insert_after": "custom_short_leave_section",
					"depends_on": SHORT_LEAVE_ONLY,
					"mandatory_depends_on": SHORT_LEAVE_ONLY,
				},
				{
					"fieldname": "custom_short_leave_to_time",
					"label": "Short Leave To Time",
					"fieldtype": "Time",
					"insert_after": "custom_short_leave_from_time",
					"depends_on": SHORT_LEAVE_ONLY,
					"mandatory_depends_on": SHORT_LEAVE_ONLY,
				},
				{
					"fieldname": "custom_short_leave_hours",
					"label": "Short Leave Hours",
					"fieldtype": "Float",
					"insert_after": "custom_short_leave_to_time",
					"read_only": 1,
					"depends_on": SHORT_LEAVE_ONLY,
				},
			]
		}
	)

	# leave type decides a Short Leave now, so the old checkbox and date are not needed
	for fieldname in ("custom_short_leave", "custom_short_leave_date"):
		name = f"Leave Application-{fieldname}"
		if frappe.db.exists("Custom Field", name):
			frappe.db.set_value("Custom Field", name, "hidden", 1)

	frappe.clear_cache(doctype="Leave Application")
