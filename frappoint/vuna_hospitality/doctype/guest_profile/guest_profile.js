// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

const GUEST_API = "frappoint.vuna_hospitality.api.guests";

frappe.ui.form.on("Guest Profile", {
	setup(frm) {
		frm.set_query("merged_into", () => ({ filters: { name: ["!=", frm.doc.name] } }));
	},

	refresh(frm) {
		if (frm.doc.restriction_flag) {
			frm.dashboard.set_headline_alert(
				`<b>${__("Do Not Rent")}</b>: ${frappe.utils.escape_html(
					frm.doc.restriction_reason || ""
				)}`,
				"red"
			);
		} else if (frm.doc.is_provisional) {
			frm.dashboard.set_headline_alert(
				__("Provisional guest: complete their details before check-in."),
				"orange"
			);
		}
		if (frm.doc.merged_into) {
			frm.set_intro(__("This profile was merged into {0}.", [frm.doc.merged_into.bold()]));
		}
		if (frm.is_new()) return;

		if (!frm.doc.customer && !frm.doc.is_provisional && frappe.model.can_create("Customer")) {
			frm.add_custom_button(
				__("Create Customer"),
				() => create_customer(frm),
				__("Actions")
			);
		}
		if (frm.doc.id_document_hint && frm.perm[1]?.read) {
			frm.add_custom_button(__("Show ID Number"), () => reveal_id(frm), __("Actions"));
		}
		if (frappe.model.can_create("Guest Relationship")) {
			frm.add_custom_button(
				__("Add Relationship"),
				() => frappe.new_doc("Guest Relationship", { guest_profile: frm.doc.name }),
				__("Actions")
			);
		}
		render_relationships(frm);
	},
});

function create_customer(frm) {
	frappe.confirm(
		__("Create an individual Customer named {0}?", [frm.doc.full_name.bold()]),
		() =>
			frappe
				.call({
					method: `${GUEST_API}.link_customer`,
					args: { guest_profile: frm.doc.name },
					freeze: true,
				})
				.then((r) => {
					frappe.show_alert({
						message: __("Customer {0} created", [r.message]),
						indicator: "green",
					});
					frm.reload_doc();
				})
	);
}

function reveal_id(frm) {
	frappe
		.call({ method: `${GUEST_API}.reveal_id_document`, args: { guest_profile: frm.doc.name } })
		.then((r) => {
			const { id_document_type, id_document_number } = r.message || {};
			frappe.msgprint({
				title: __("ID Document"),
				message: `${frappe.utils.escape_html(
					__(id_document_type || "")
				)}<br><b>${frappe.utils.escape_html(
					id_document_number || __("Not recorded")
				)}</b><p class="text-muted small mt-3">${__("This view has been recorded.")}</p>`,
			});
		});
}

function render_relationships(frm) {
	const wrapper = frm.get_field("relationships_html").$wrapper;
	frappe
		.call({ method: `${GUEST_API}.get_relationships`, args: { guest_profile: frm.doc.name } })
		.then((r) => {
			const rows = r.message || [];
			if (!rows.length) {
				wrapper.html(`<p class="text-muted">${__("No relationships recorded.")}</p>`);
				return;
			}
			const esc = frappe.utils.escape_html;
			wrapper.html(`
				<table class="table table-bordered table-sm">
					<thead><tr><th>${__("Guest")}</th><th>${__("Relationship")}</th><th>${__(
				"Until"
			)}</th><th></th></tr></thead>
					<tbody>${rows
						.map(
							(row) => `<tr>
								<td><a href="/app/guest-profile/${encodeURIComponent(row.guest)}">${esc(
								row.full_name || row.guest
							)}</a></td>
								<td>${esc(__(row.relationship_type))}</td>
								<td>${row.valid_to ? frappe.datetime.str_to_user(row.valid_to) : ""}</td>
								<td><a class="text-muted" href="/app/guest-relationship/${encodeURIComponent(
									row.relationship
								)}">${__("Open")}</a></td>
							</tr>`
						)
						.join("")}</tbody>
				</table>`);
		});
}
