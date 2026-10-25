// Employee Dashboard entry points: a navbar button, and a redirect once per login.
$(document).on("app_ready", () => {
	const page = frappe.boot.mtcpl_dashboard;
	if (!page) return;

	const marker = frappe.boot.mtcpl_login_marker;
	if (frappe.boot.mtcpl_landing_page && marker) {
		let landed = null;
		try {
			landed = localStorage.getItem("mtcpl_landed");
			localStorage.setItem("mtcpl_landed", marker);
		} catch (e) {
			// storage blocked: fall back to the bare desk URL
			landed = /^\/app(\/home)?\/?$/.test(window.location.pathname) ? null : marker;
		}
		if (landed !== marker) {
			frappe.set_route(page);
		}
	}

	const add_button = (tries = 0) => {
		const $nav = $("header.navbar .navbar-nav").last();
		if (!$nav.length) {
			if (tries < 20) setTimeout(() => add_button(tries + 1), 250);
			return;
		}
		if ($nav.find(".mtcpl-dashboard-link").length) return;
		$(`<li class="nav-item mtcpl-dashboard-link">
			<a class="btn btn-default btn-sm" href="/app/${page}">${__("My Dashboard")}</a>
		</li>`).prependTo($nav);
	};
	add_button();
});
