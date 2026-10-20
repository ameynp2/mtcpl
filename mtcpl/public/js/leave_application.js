frappe.ui.form.on("Leave Application", {
	refresh(frm) {
		set_short_leave_dates(frm);
	},

	leave_type(frm) {
		set_short_leave_dates(frm);
		update_short_leave_hours(frm);
	},

	from_date(frm) {
		set_short_leave_dates(frm);
	},

	custom_short_leave_from_time(frm) {
		update_short_leave_hours(frm);
	},

	custom_short_leave_to_time(frm) {
		update_short_leave_hours(frm);
	},
});

function is_short_leave(frm) {
	return frm.doc.leave_type === "Short Leave";
}

// a Short Leave is always for a single day
function set_short_leave_dates(frm) {
	if (is_short_leave(frm) && frm.doc.from_date && frm.doc.to_date !== frm.doc.from_date) {
		frm.set_value("to_date", frm.doc.from_date);
	}
}

// the server recalculates these on save, this only shows the hours while typing
function update_short_leave_hours(frm) {
	if (!is_short_leave(frm)) {
		return;
	}

	const { custom_short_leave_from_time: from, custom_short_leave_to_time: to } = frm.doc;
	if (!from || !to) {
		return;
	}

	const hours = moment(to, "HH:mm:ss").diff(moment(from, "HH:mm:ss"), "minutes") / 60;
	frm.set_value("custom_short_leave_hours", hours > 0 ? hours : 0);
	if (hours > 0) {
		frm.set_value("total_leave_days", hours);
	}
}
