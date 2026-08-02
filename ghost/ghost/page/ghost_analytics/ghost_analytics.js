frappe.pages["ghost-analytics"].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Ghost Analytics"),
		single_column: true,
	});

	page.set_primary_action(__("Refresh"), () => load_data());

	$(`
		<div class="ghost-analytics">
			<div class="ghost-metric-cards row" style="margin-bottom: 20px;"></div>
			<div class="ghost-daily-chart frappe-card" style="padding: 15px; margin-bottom: 20px;">
				<h5 style="margin-bottom: 15px;">${__("Last 30 Days")}</h5>
				<div class="chart-body"></div>
			</div>
			<div class="ghost-mode-chart frappe-card" style="padding: 15px;">
				<h5 style="margin-bottom: 15px;">${__("Conversions by Mode")}</h5>
				<div class="chart-body"></div>
			</div>
		</div>
	`).appendTo(page.main);

	function render_cards(data) {
		const cards = [
			{ label: __("Total Ghost Sessions"), value: data.total_sessions },
			{ label: __("Total Conversions"), value: data.total_conversions },
			{ label: __("Conversion Rate"), value: data.conversion_rate + "%" },
			{ label: __("Avg Conversion Time"), value: data.avg_conversion_duration_ms + " ms" },
		];
		const html = cards
			.map(
				(c) => `
				<div class="col-sm-6 col-md-3" style="margin-bottom: 15px;">
					<div class="frappe-card" style="padding: 15px; text-align: center;">
						<div style="font-size: 24px; font-weight: 600;">${c.value}</div>
						<div class="text-muted">${c.label}</div>
					</div>
				</div>`
			)
			.join("");
		page.main.find(".ghost-metric-cards").html(html);
	}

	function last_30_days() {
		const days = [];
		for (let i = 29; i >= 0; i--) {
			days.push(frappe.datetime.add_days(frappe.datetime.get_today(), -i));
		}
		return days;
	}

	function daily_counts(rows) {
		const map = {};
		(rows || []).forEach((r) => {
			map[frappe.datetime.obj_to_str(r.day)] = r.count;
		});
		return map;
	}

	function render_daily_chart(data) {
		const days = last_30_days();
		const sessions = daily_counts(data.daily.sessions);
		const conversions = daily_counts(data.daily.conversions);
		new frappe.Chart(page.main.find(".ghost-daily-chart .chart-body")[0], {
			data: {
				labels: days,
				datasets: [
					{
						name: __("Ghost Sessions"),
						values: days.map((d) => sessions[d] || 0),
					},
					{
						name: __("Conversions"),
						values: days.map((d) => conversions[d] || 0),
					},
				],
			},
			type: "line",
			height: 250,
			colors: ["#5e64ff", "#28a745"],
		});
	}

	function render_mode_chart(data) {
		const modes = data.conversions_by_mode || [];
		const $body = page.main.find(".ghost-mode-chart .chart-body");
		if (!modes.length) {
			$body.html(`<p class="text-muted">${__("No conversions logged yet.")}</p>`);
			return;
		}
		new frappe.Chart($body[0], {
			data: {
				labels: modes.map((m) => m.conversion_mode),
				datasets: [{ name: __("Conversions"), values: modes.map((m) => m.count) }],
			},
			type: "bar",
			height: 250,
			colors: ["#5e64ff"],
		});
	}

	function load_data() {
		frappe.call({
			method: "ghost.ghost.page.ghost_analytics.ghost_analytics.get_analytics_data",
			callback: function (r) {
				if (!r.message) {
					return;
				}
				const data = r.message;
				if (!data.logging_enabled) {
					frappe.show_alert({
						message: __(
							"Conversion logging is disabled. Enable it in Ghost Settings > Analytics to start collecting data."
						),
						indicator: "orange",
					});
				}
				render_cards(data);
				render_daily_chart(data);
				render_mode_chart(data);
			},
		});
	}

	load_data();
};
