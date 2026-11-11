frappe.pages["employee-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("My Dashboard"),
		single_column: true,
	});
	wrapper.employee_dashboard = new EmployeeDashboard(page);
};

frappe.pages["employee-dashboard"].on_page_show = function (wrapper) {
	wrapper.employee_dashboard && wrapper.employee_dashboard.load();
};

const STATUS_CLASS = {
	Present: "ed-present",
	Absent: "ed-absent",
	"Half Day": "ed-half",
	"On Leave": "ed-leave",
	"Work From Home": "ed-present",
};

class EmployeeDashboard {
	constructor(page) {
		this.page = page;
		const now = new Date();
		this.year = now.getFullYear();
		this.month = now.getMonth() + 1;
		this.data = null;
		this.selected = null;
		this.$body = $(`<div class="ed-root"></div>`).appendTo(page.main);
		this.add_style();
		page.set_secondary_action(__("Refresh"), () => this.load(), "refresh");
		page.set_primary_action(__("ERP Workspace"), () => frappe.set_route("Workspaces"), "organization");
		page.add_inner_button(__("Apply Leave"), () => frappe.new_doc("Leave Application"));
		page.add_inner_button(__("My Leaves"), () => frappe.set_route("List", "Leave Application"));
		page.add_inner_button(__("My Attendance"), () => frappe.set_route("List", "Attendance"));
	}

	load() {
		frappe.call({
			method: "mtcpl.api.employee_dashboard.get_dashboard",
			args: { month: this.month, year: this.year },
			callback: (r) => {
				this.data = r.message;
				this.render();
			},
		});
	}

	change_month(delta) {
		this.month += delta;
		if (this.month < 1) {
			this.month = 12;
			this.year -= 1;
		} else if (this.month > 12) {
			this.month = 1;
			this.year += 1;
		}
		this.selected = null;
		this.load();
	}

	render() {
		const d = this.data;
		if (!d || !d.employee) {
			this.$body.html(
				`<div class="ed-card">${__("Your user is not linked to an active Employee record. Please contact HR.")}</div>`
			);
			return;
		}
		this.$body.html(`
			<div class="ed-grid">
				<div class="ed-col">
					${this.profile_html()}
					${this.today_html()}
					${this.leave_balance_html()}
				</div>
				<div class="ed-col ed-wide">
					${this.calendar_html()}
					${this.day_detail_html()}
					${this.recent_leaves_html()}
				</div>
			</div>`);
		this.bind();
	}

	profile_html() {
		const p = this.data.profile;
		const row = (label, value) =>
			value
				? `<div class="ed-row"><span class="ed-muted">${__(label)}</span><span>${frappe.utils.escape_html(String(value))}</span></div>`
				: "";
		const avatar = p.image
			? `<img class="ed-avatar" src="${encodeURI(p.image)}">`
			: `<div class="ed-avatar ed-avatar-ph">${frappe.get_abbr(p.employee_name)}</div>`;
		return `<div class="ed-card">
			<div class="ed-profile">${avatar}
				<div><div class="ed-name">${frappe.utils.escape_html(p.employee_name)}</div>
				<div class="ed-muted">${frappe.utils.escape_html(p.designation || "")}</div></div></div>
			${row("Employee ID", p.name)}
			${row("Department", p.department)}
			${row("Branch", p.branch)}
			${row("Company", p.company)}
			${row("Employment Type", p.employment_type)}
			${row("Date of Joining", p.date_of_joining && frappe.datetime.str_to_user(p.date_of_joining))}
			${row("Reports To", p.reports_to_name)}
			${row("Shift", p.default_shift)}
			${row("Mobile", p.cell_number)}
			${row("Email", p.company_email || p.personal_email)}
		</div>`;
	}

	time_of(value) {
		return value ? frappe.datetime.str_to_user(value).split(" ").slice(1).join(" ") : "—";
	}

	today_html() {
		const d = this.data;
		const day = d.days[d.today] || { punches: [] };
		const punches = day.punches;
		const first_in = punches.find((x) => x.log_type === "IN") || punches[0];
		const last_out = [...punches].reverse().find((x) => x.log_type === "OUT");
		const att = day.attendance;
		const list = punches.length
			? punches
					.map(
						(x) =>
							`<div class="ed-row"><span class="ed-pill ${x.log_type === "OUT" ? "ed-pill-out" : "ed-pill-in"}">${x.log_type || "—"}</span><span>${this.time_of(x.time)}</span></div>`
					)
					.join("")
			: `<div class="ed-muted">${__("No check-ins yet today")}</div>`;
		return `<div class="ed-card"><div class="ed-title">${__("Today")} · ${frappe.datetime.str_to_user(d.today)}</div>
			<div class="ed-inout">
				<div><div class="ed-muted">${__("First In")}</div><div class="ed-big">${this.time_of(first_in && first_in.time)}</div></div>
				<div><div class="ed-muted">${__("Last Out")}</div><div class="ed-big">${this.time_of(last_out && last_out.time)}</div></div>
			</div>
			${att ? `<div class="ed-row"><span class="ed-muted">${__("Attendance")}</span><span>${this.status_label(att)}</span></div>` : ""}
			<div class="ed-sub">${list}</div></div>`;
	}

	status_label(att) {
		if (att.docstatus === 0) return __("Pending HR review");
		return __(att.status);
	}

	leave_balance_html() {
		const rows = this.data.leave_balance;
		const body = rows.length
			? rows
					.map(
						(l) => `<div class="ed-leave-row">
						<div class="ed-leave-head"><b>${frappe.utils.escape_html(l.leave_type)}</b>
						<span class="ed-big-sm">${l.remaining}</span></div>
						<div class="ed-muted">${__("Allocated")} ${l.total} · ${__("Used")} ${l.taken}${l.pending ? ` · ${__("Pending approval")} ${l.pending}` : ""}</div>
						<div class="ed-bar"><span style="width:${l.total ? Math.min(100, (l.taken / l.total) * 100) : 0}%"></span></div>
					</div>`
					)
					.join("")
			: `<div class="ed-muted">${__("No leave allocated")}</div>`;
		return `<div class="ed-card"><div class="ed-title">${__("Leave Balance")}</div>${body}</div>`;
	}

	day_info(date) {
		const d = this.data;
		const att = (d.days[date] || {}).attendance;
		const leave = d.leaves[date];
		if (att) {
			if (att.docstatus === 0) return { cls: "ed-pending", label: __("Pending review") };
			return { cls: STATUS_CLASS[att.status] || "", label: this.status_label(att) };
		}
		if (leave) return { cls: "ed-leave", label: `${leave.leave_type}${leave.status === "Open" ? " (" + __("pending") + ")" : ""}` };
		if (date in d.holidays) return { cls: "ed-holiday", label: d.holidays[date] || __("Holiday") };
		return { cls: "", label: "" };
	}

	calendar_html() {
		const d = this.data;
		const start = new Date(d.month_start + "T00:00:00");
		const last = new Date(d.month_end + "T00:00:00").getDate();
		const lead = (start.getDay() + 6) % 7; // Monday first
		const counts = { Present: 0, Absent: 0, "Half Day": 0, Leave: 0, Holiday: 0 };
		let cells = "";
		for (let i = 0; i < lead; i++) cells += `<div class="ed-day ed-empty"></div>`;
		for (let n = 1; n <= last; n++) {
			const date = `${d.month_start.slice(0, 8)}${String(n).padStart(2, "0")}`;
			const info = this.day_info(date);
			const att = (d.days[date] || {}).attendance;
			if (att && att.docstatus === 1) {
				if (att.status === "Present" || att.status === "Work From Home") counts.Present++;
				else if (att.status === "Absent") counts.Absent++;
				else if (att.status === "Half Day") counts["Half Day"]++;
				else if (att.status === "On Leave") counts.Leave++;
			} else if (!att && info.cls === "ed-leave") counts.Leave++;
			else if (!att && info.cls === "ed-holiday") counts.Holiday++;
			const punches = (d.days[date] || { punches: [] }).punches;
			const times = punches.length
				? `${this.time_of(punches[0].time)}${punches.length > 1 ? " – " + this.time_of(punches[punches.length - 1].time) : ""}`
				: "";
			cells += `<div class="ed-day ${info.cls} ${date === d.today ? "ed-today" : ""} ${date === this.selected ? "ed-selected" : ""}" data-date="${date}" title="${frappe.utils.escape_html(info.label)}">
				<div class="ed-daynum">${n}</div><div class="ed-daylabel">${frappe.utils.escape_html(info.label)}</div><div class="ed-daytime">${times}</div></div>`;
		}
		const names = [__("Mon"), __("Tue"), __("Wed"), __("Thu"), __("Fri"), __("Sat"), __("Sun")];
		const month_name = frappe.datetime.str_to_user(d.month_start);
		const title = new Date(d.month_start + "T00:00:00").toLocaleString(frappe.boot.lang || "en", { month: "long", year: "numeric" });
		const legend = [
			["ed-present", __("Present"), counts.Present],
			["ed-absent", __("Absent"), counts.Absent],
			["ed-half", __("Half Day"), counts["Half Day"]],
			["ed-leave", __("Leave"), counts.Leave],
			["ed-holiday", __("Holiday"), counts.Holiday],
			["ed-pending", __("Pending review"), ""],
		]
			.map(([cls, label, n]) => `<span class="ed-legend"><i class="${cls}"></i>${label}${n !== "" ? ` <b>${n}</b>` : ""}</span>`)
			.join("");
		return `<div class="ed-card">
			<div class="ed-cal-head"><button class="btn btn-xs btn-default ed-prev">‹</button>
			<div class="ed-title" title="${month_name}">${title}</div>
			<button class="btn btn-xs btn-default ed-next">›</button></div>
			<div class="ed-legends">${legend}</div>
			<div class="ed-cal">${names.map((n) => `<div class="ed-dow">${n}</div>`).join("")}${cells}</div></div>`;
	}

	day_detail_html() {
		const date = this.selected;
		if (!date) return "";
		const day = this.data.days[date] || { punches: [] };
		const att = day.attendance;
		const info = this.day_info(date);
		const punches = day.punches.length
			? day.punches
					.map((x) => `<span class="ed-pill ${x.log_type === "OUT" ? "ed-pill-out" : "ed-pill-in"}">${x.log_type || "—"}</span> ${this.time_of(x.time)}`)
					.join(" &nbsp; ")
			: __("No check-ins");
		const extra = att
			? `<div class="ed-row"><span class="ed-muted">${__("Working Hours")}</span><span>${att.working_hours ? att.working_hours.toFixed(2) : "—"}</span></div>
				${att.late_entry ? `<div class="ed-row"><span class="ed-muted">${__("Late Entry")}</span><span>${__("Yes")}</span></div>` : ""}
				${att.early_exit ? `<div class="ed-row"><span class="ed-muted">${__("Early Exit")}</span><span>${__("Yes")}</span></div>` : ""}
				${att.custom_needs_review ? `<div class="ed-row"><span class="ed-muted">${__("Review Reason")}</span><span>${frappe.utils.escape_html(att.custom_review_reason || "")}</span></div>` : ""}`
			: "";
		return `<div class="ed-card"><div class="ed-title">${frappe.datetime.str_to_user(date)} ${info.label ? "· " + frappe.utils.escape_html(info.label) : ""}</div>
			<div>${punches}</div>${extra}</div>`;
	}

	recent_leaves_html() {
		const rows = this.data.recent_leaves;
		if (!rows.length) return "";
		return `<div class="ed-card"><div class="ed-title">${__("Recent Leave Applications")}</div>${rows
			.map(
				(l) => `<div class="ed-row"><a href="/app/leave-application/${encodeURIComponent(l.name)}">${frappe.utils.escape_html(l.leave_type)}</a>
				<span>${frappe.datetime.str_to_user(l.from_date)}${l.from_date !== l.to_date ? " → " + frappe.datetime.str_to_user(l.to_date) : ""} · ${l.total_leave_days}d</span>
				<span class="ed-muted">${__(l.status)}</span></div>`
			)
			.join("")}</div>`;
	}

	bind() {
		this.$body.find(".ed-prev").on("click", () => this.change_month(-1));
		this.$body.find(".ed-next").on("click", () => this.change_month(1));
		this.$body.find(".ed-day[data-date]").on("click", (e) => {
			this.selected = $(e.currentTarget).data("date");
			this.render();
		});
	}

	add_style() {
		if ($("#ed-style").length) return;
		$(`<style id="ed-style">
			.ed-grid{display:grid;grid-template-columns:minmax(260px,340px) 1fr;gap:16px;align-items:start}
			@media(max-width:900px){.ed-grid{grid-template-columns:1fr}}
			.ed-col{display:flex;flex-direction:column;gap:16px;min-width:0}
			.ed-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:var(--border-radius-md);padding:16px}
			.ed-title{font-weight:600;margin-bottom:10px}
			.ed-muted{color:var(--text-muted);font-size:var(--text-sm)}
			.ed-row{display:flex;justify-content:space-between;gap:12px;padding:5px 0;font-size:var(--text-sm)}
			.ed-profile{display:flex;gap:12px;align-items:center;margin-bottom:8px}
			.ed-avatar{width:52px;height:52px;border-radius:50%;object-fit:cover}
			.ed-avatar-ph{display:flex;align-items:center;justify-content:center;background:var(--bg-light-gray);font-weight:600}
			.ed-name{font-size:var(--text-lg);font-weight:600}
			.ed-inout{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:8px}
			.ed-big{font-size:20px;font-weight:600}.ed-big-sm{font-size:18px;font-weight:600}
			.ed-sub{margin-top:8px;border-top:1px solid var(--border-color);padding-top:6px}
			.ed-pill{display:inline-block;min-width:34px;text-align:center;border-radius:10px;padding:0 8px;font-size:11px;font-weight:600}
			.ed-pill-in{background:var(--green-100,#e4f5e9);color:var(--green-700,#2b6b3f)}
			.ed-pill-out{background:var(--orange-100,#fdf0dc);color:var(--orange-700,#8a5a14)}
			.ed-leave-row{padding:8px 0;border-top:1px solid var(--border-color)}
			.ed-leave-row:first-of-type{border-top:0}
			.ed-leave-head{display:flex;justify-content:space-between;align-items:baseline}
			.ed-bar{height:5px;background:var(--bg-light-gray);border-radius:3px;margin-top:6px;overflow:hidden}
			.ed-bar span{display:block;height:100%;background:var(--primary)}
			.ed-cal-head{display:flex;justify-content:space-between;align-items:center}
			.ed-cal-head .ed-title{margin:0}
			.ed-legends{display:flex;flex-wrap:wrap;gap:12px;margin:10px 0;font-size:var(--text-sm)}
			.ed-legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
			.ed-cal{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}
			.ed-dow{text-align:center;color:var(--text-muted);font-size:var(--text-sm);padding:4px 0}
			.ed-day{min-height:68px;border:1px solid var(--border-color);border-radius:var(--border-radius);padding:4px 6px;cursor:pointer;overflow:hidden;font-size:11px}
			.ed-day.ed-empty{border:0;cursor:default}
			.ed-daynum{font-weight:600;font-size:13px}
			.ed-daylabel{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
			.ed-daytime{color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
			.ed-day.ed-today{outline:2px solid var(--primary)}
			.ed-day.ed-selected{box-shadow:0 0 0 2px var(--primary) inset}
			.ed-present{background:var(--green-100,#e4f5e9)}.ed-absent{background:var(--red-100,#fde8e8)}
			.ed-half{background:var(--yellow-100,#fdf6d8)}.ed-leave{background:var(--blue-100,#e3f0fd)}
			.ed-holiday{background:var(--bg-light-gray)}
			.ed-pending{background:var(--bg-purple,#efe8fa);border-style:dashed}
			i.ed-present,i.ed-absent,i.ed-half,i.ed-leave,i.ed-holiday,i.ed-pending{border:1px solid var(--border-color)}
		</style>`).appendTo("head");
	}
}
