from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Attendance": [
				{
					"fieldname": "custom_needs_review",
					"label": "Needs Review",
					"fieldtype": "Check",
					"insert_after": "status",
					"read_only": 1,
					"no_copy": 1,
					"allow_on_submit": 1,
				},
				{
					"fieldname": "custom_review_reason",
					"label": "Review Reason",
					"fieldtype": "Data",
					"insert_after": "custom_needs_review",
					"read_only": 1,
					"no_copy": 1,
					"depends_on": "custom_needs_review",
					"allow_on_submit": 1,
				},
			]
		}
	)
