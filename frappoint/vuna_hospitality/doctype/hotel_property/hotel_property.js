// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

const HOTEL_PROPERTY_ACCOUNT_FIELDS = [
	"guest_ledger_account",
	"advance_account",
	"room_post_clearing_account",
	"breakage_income_account",
	"cash_over_short_account",
];

frappe.ui.form.on("Hotel Property", {
	setup(frm) {
		HOTEL_PROPERTY_ACCOUNT_FIELDS.forEach((fieldname) => {
			frm.set_query(fieldname, () => ({
				filters: { company: frm.doc.company, is_group: 0 },
			}));
		});
		frm.set_query("default_cost_center", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
	},

	onload(frm) {
		frappe
			.xcall(
				"frappoint.vuna_hospitality.doctype.hotel_property.hotel_property.get_time_zones"
			)
			.then((zones) => frm.set_df_property("time_zone", "options", zones));
		if (frm.is_new() && !frm.doc.time_zone) {
			frm.set_value("time_zone", frappe.boot.time_zone?.system);
		}
	},

	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(
			__("Rooms"),
			() => frappe.set_route("List", "Hotel Room", { property: frm.doc.name }),
			__("View")
		);
		frm.add_custom_button(
			__("Room Types"),
			() => frappe.set_route("List", "Room Type", { property: frm.doc.name }),
			__("View")
		);
		frm.add_custom_button(
			__("House Position"),
			() => frappe.set_route("query-report", "House Position", { property: frm.doc.name }),
			__("View")
		);
		frm.add_custom_button(__("Quote a Stay"), () => quote_stay(frm), __("Actions"));
		if (frappe.user.has_role(["System Manager", "Hospitality Manager"])) {
			frm.add_custom_button(
				__("Rebuild Inventory"),
				() =>
					frappe
						.xcall(
							"frappoint.vuna_hospitality.services.inventory.rebuild_property_inventory",
							{ property_name: frm.doc.name },
							__("Rebuilding room inventory...")
						)
						.then((result) =>
							frappe.msgprint(
								__(
									"Checked {0} room-type nights: {1} created, {2} corrected. Rows still differing: {3}.",
									[
										result.rows,
										result.created,
										result.updated,
										result.drift_after,
									]
								)
							)
						),
				__("Actions")
			);
		}
	},

	property_code(frm) {
		if (frm.doc.property_code) {
			frm.set_value("property_code", frm.doc.property_code.toUpperCase().trim());
		}
	},

	company(frm) {
		HOTEL_PROPERTY_ACCOUNT_FIELDS.concat(["default_cost_center"]).forEach((fieldname) =>
			frm.set_value(fieldname, null)
		);
	},
});

function quote_stay(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Quote a Stay at {0}", [frm.doc.property_name]),
		size: "large",
		fields: [
			{
				fieldname: "arrival",
				fieldtype: "Date",
				label: __("Arrival"),
				reqd: 1,
				default: frm.doc.business_date,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "departure",
				fieldtype: "Date",
				label: __("Departure"),
				reqd: 1,
				default: frappe.datetime.add_days(frm.doc.business_date, 1),
			},
			{ fieldtype: "Column Break" },
			{ fieldname: "adults", fieldtype: "Int", label: __("Adults"), default: 2, reqd: 1 },
			{ fieldtype: "Column Break" },
			{ fieldname: "children", fieldtype: "Int", label: __("Children"), default: 0 },
			{ fieldtype: "Section Break" },
			{ fieldname: "results", fieldtype: "HTML" },
		],
		primary_action_label: __("Search"),
		primary_action(values) {
			frappe
				.xcall("frappoint.vuna_hospitality.api.quote.search_availability", {
					property: frm.doc.name,
					...values,
				})
				.then((quotes) => dialog.fields_dict.results.$wrapper.html(render_quotes(quotes)));
		},
	});
	dialog.show();
}

function render_quotes(quotes) {
	if (!quotes.length) {
		return `<p class="text-muted">${__("No active room types or rate plans.")}</p>`;
	}
	const money = (value, currency) => format_currency(value, currency);
	const rows = quotes
		.map((q) => {
			const status = q.offered
				? `<span class="indicator-pill green">${__("Available")}</span>`
				: `<span class="indicator-pill red">${q.reasons
						.map((r) => __(r))
						.join(", ")}</span>`;
			const nights = q.nights
				.map(
					(n) =>
						`${frappe.datetime.str_to_user(n.night)}: ${
							n.rate === null ? __("no rate") : money(n.rate, q.currency)
						}${n.sellable ? "" : ` (${__(n.reason)})`}`
				)
				.join("<br>");
			return `<tr>
				<td><strong>${frappe.utils.escape_html(q.room_type_name)}</strong><br>
					<span class="text-muted">${frappe.utils.escape_html(q.rate_plan_name)}</span></td>
				<td>${status}</td>
				<td class="small">${nights}</td>
				<td class="text-right"><strong>${q.offered ? money(q.total, q.currency) : "-"}</strong></td>
			</tr>`;
		})
		.join("");
	return `<table class="table table-bordered">
		<thead><tr><th>${__("Room / Rate Plan")}</th><th>${__("Status")}</th>
		<th>${__("Per Night")}</th><th class="text-right">${__("Total")}</th></tr></thead>
		<tbody>${rows}</tbody></table>`;
}
