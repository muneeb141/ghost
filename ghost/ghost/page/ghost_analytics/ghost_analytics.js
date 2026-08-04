frappe.pages["ghost-analytics"].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Ghost Analytics"),
		single_column: true,
	});

	page.set_primary_action(__("Refresh"), () => load_data());

	let days_field = page.add_field({
		fieldname: "days",
		label: __("Timeframe"),
		fieldtype: "Select",
		options: [
			{ label: __("Last 7 Days"), value: "7" },
			{ label: __("Last 30 Days"), value: "30" },
			{ label: __("Last 90 Days"), value: "90" },
			{ label: __("Last 180 Days"), value: "180" },
		],
		default: "30",
		change: () => load_data(),
	});

	$(`
		<div class="ghost-analytics">
			<div class="ghost-metric-cards row" style="margin-bottom: 20px;"></div>
			<div class="ghost-daily-chart frappe-card" style="padding: 15px; margin-bottom: 20px;">
				<h5 class="chart-title" style="margin-bottom: 15px;">${__("Traffic & Conversions Trend")}</h5>
				<div class="chart-body"></div>
			</div>
			<div class="row">
				<div class="col-md-6" style="margin-bottom: 20px;">
					<div class="ghost-mode-chart frappe-card" style="padding: 15px; height: 100%;">
						<h5 style="margin-bottom: 15px;">${__("Conversions by Mode")}</h5>
						<div class="chart-body"></div>
					</div>
				</div>
				<div class="col-md-6" style="margin-bottom: 20px;">
					<div class="ghost-channel-chart frappe-card" style="padding: 15px; height: 100%;">
						<h5 style="margin-bottom: 15px;">${__("Conversions by Channel")}</h5>
						<div class="chart-body"></div>
					</div>
				</div>
			</div>
		</div>
	`).appendTo(page.main);

	function render_cards(data) {
		const cards = [
			{ label: __("Total Ghost Sessions"), value: data.total_sessions || 0 },
			{ label: __("Total Leads Captured"), value: data.total_leads || 0 },
			{ label: __("Total Conversions"), value: data.total_conversions || 0 },
			{ label: __("Merged Sessions"), value: data.total_merged_ghosts || 0 },
			{ label: __("Session Conversion Rate"), value: (data.conversion_rate || 0) + "%" },
			{ label: __("Lead Conversion Rate"), value: (data.lead_conversion_rate || 0) + "%" },
			{ label: __("Reminder Recovery Rate"), value: (data.reminder_recovery_rate || 0) + "%" },
			{ label: __("Avg Conversion Time"), value: (data.avg_conversion_duration_ms || 0) + " ms" },
		];
		const html = cards
			.map(
				(c) => `
				<div class="col-sm-6 col-md-3" style="margin-bottom: 15px;">
					<div class="frappe-card" style="padding: 15px; text-align: center; height: 100%;">
						<div style="font-size: 24px; font-weight: 600; color: var(--text-color);">${c.value}</div>
						<div class="text-muted" style="font-size: 12px; margin-top: 5px;">${c.label}</div>
					</div>
				</div>`
			)
			.join("");
		page.main.find(".ghost-metric-cards").html(html);
	}

	function get_date_range(days_count) {
		const days = [];
		for (let i = days_count - 1; i >= 0; i--) {
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

	function render_daily_chart(data, days_count) {
		const days = get_date_range(days_count);
		const sessions = daily_counts(data.daily.sessions);
		const conversions = daily_counts(data.daily.conversions);
		
		page.main.find(".ghost-daily-chart .chart-title").text(
			__("Traffic & Conversions Trend (Last {0} Days)", [days_count])
		);

		new frappe.Chart(page.main.find(".ghost-daily-chart .chart-body")[0], {
			data: {
				labels: days.map(d => frappe.datetime.str_to_user(d).substring(0, 5)),
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
			height: 260,
			colors: ["#5e64ff", "#28a745"],
			axisOptions: {
				xIsSeries: 1,
				shortenYAxisNumbers: 1,
			}
		});
	}

	function render_mode_chart(data) {
		const modes = data.conversions_by_mode || [];
		const $body = page.main.find(".ghost-mode-chart .chart-body");
		if (!modes.length) {
			$body.html(`<p class="text-muted" style="padding: 20px; text-align: center;">${__("No conversion modes logged yet.")}</p>`);
			return;
		}
		new frappe.Chart($body[0], {
			data: {
				labels: modes.map((m) => {
					const labelMap = {
						"manual_migration": __("Account Merge"),
						"rename": __("New Account"),
						"already_converted": __("Already Converted"),
					};
					return labelMap[m.conversion_mode] || m.conversion_mode;
				}),
				datasets: [{ name: __("Conversions"), values: modes.map((m) => m.count) }],
			},
			type: "bar",
			height: 220,
			colors: ["#5e64ff"],
		});
	}

	function render_channel_chart(data) {
		const channels = data.conversions_by_channel || [];
		const $body = page.main.find(".ghost-channel-chart .chart-body");
		if (!channels.length) {
			$body.html(`<p class="text-muted" style="padding: 20px; text-align: center;">${__("No conversion channels logged yet.")}</p>`);
			return;
		}
		new frappe.Chart($body[0], {
			data: {
				labels: channels.map((c) => c.channel || __("OTP")),
				datasets: [{ name: __("Conversions"), values: channels.map((c) => c.count) }],
			},
			type: "donut",
			height: 220,
			colors: ["#5e64ff", "#28a745", "#ffc107", "#17a2b8", "#e83e8c"],
		});
	}

	function load_data() {
		const days_val = parseInt(days_field ? days_field.get_value() : "30") || 30;
		frappe.call({
			method: "ghost.ghost.page.ghost_analytics.ghost_analytics.get_analytics_data",
			args: {
				days: days_val
			},
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
				render_daily_chart(data, days_val);
				render_mode_chart(data);
				render_channel_chart(data);
			},
		});
	}

	load_data();
};
