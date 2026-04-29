// Copyright (c) 2026, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Booking", {
	refresh(frm) {
		if (!frm.doc.customer) return;

		frm.add_custom_button(
			__("Add Guest Appointment"),
			() => {
				new GuestBookingWizard(frm);
			},
			__("Actions")
		);

		if (frm.doc.__onload && frm.doc.__onload.appointment_list_html) {
			frm.get_field("service_appointments").$wrapper.html(
				frm.doc.__onload.appointment_list_html
			);
		} else {
			frm.trigger("render_appointment_list");
		}

		if (!frm.is_new() && frm.doc.outstanding_amount > 0) {
			frm.add_custom_button(
				__("Payment"),
				function () {
					frm.trigger("make_payment");
				},
				__("Create")
			);
		}
	},

	render_appointment_list: function (frm) {
		frappe.call({
			method: "get_appointment_table",
			doc: frm.doc,
			callback: function (r) {
				if (r.message) {
					frm.get_field("service_appointments").$wrapper.html(r.message);
				}
			},
		});
	},

	make_payment: function (frm) {
		frappe.model.with_doctype("Service Appointment Payment", () => {
			let payment = frappe.model.get_new_doc("Service Appointment Payment");

			payment.customer = frm.doc.customer;
			payment.reference_doctype = frm.doc.doctype;
			payment.reference_docname = frm.doc.name;
			payment.amount = frm.doc.outstanding_amount;
			payment.currency = frm.doc.currency;

			frappe.set_route("Form", "Service Appointment Payment", payment.name);
		});
	},
});

class GuestBookingWizard {
	constructor(frm) {
		this.frm = frm;
		// 1. Bind methods so 'this' is always the Wizard instance
		this.select_date = this.select_date.bind(this);
		this.select_slot = this.select_slot.bind(this);
		this.setup_dialog();
	}

	setup_dialog() {
		this.dialog = new frappe.ui.Dialog({
			title: __("Guest Appointment Wizard"),
			fields: [
				// STEP 1: GUEST INFO
				{
					label: __("Guest Details"),
					fieldtype: "Section Break",
					fieldname: "guest_details_section",
				},
				{ label: __("Full Name"), fieldtype: "Data", fieldname: "guest_name", reqd: 1 },
				{ fieldtype: "Column Break" },
				{
					label: __("Email"),
					fieldtype: "Data",
					fieldname: "guest_email",
					options: "Email",
				},
				{ fieldtype: "Column Break" },
				{ label: __("Phone"), fieldtype: "Data", fieldname: "guest_mobile" },

				// STEP 2: SERVICE & PACKAGE
				{ fieldtype: "Section Break", label: __("Service & Package") },
				{
					label: __("Service Type"),
					fieldtype: "Link",
					options: "Service Type",
					fieldname: "service_type",
					reqd: 1,
					onchange: () => this.on_service_change(),
				},
				{
					label: __("Duration (mins)"),
					fieldtype: "Int",
					fieldname: "duration",
					read_only: 1,
				},
				{ fieldtype: "Column Break" },
				{
					label: __("Select Package/Price"),
					fieldtype: "Select",
					fieldname: "selected_price_id",
					options: [],
					reqd: 1,
					onchange: () => this.on_price_change(),
				},
				{ label: __("Amount"), fieldtype: "Currency", fieldname: "amount", read_only: 1 },

				// STEP 3: THE CALENDAR & SLOT PICKER
				{
					fieldtype: "Section Break",
					label: __("Select Time Slot"),
					fieldname: "sec_slots",
				},
				{ fieldtype: "HTML", fieldname: "slot_picker_html" },
			],
			size: "extra-large",
			primary_action_label: __("Add Guest"),
			primary_action: (values) => this.submit_to_parent(values),
		});

		this.dialog.wizard = this;

		this.setup_event_handlers();
		this.dialog.show();
		this.init_styles();
	}

	async on_service_change() {
		const service = this.dialog.get_value("service_type");
		if (!service) return;

		// Reset lower fields while loading new service details
		this.dialog.set_df_property("selected_price_id", "options", []);
		this.available_dates = [];
		this.available_slots = [];
		this.filter_provider = null;
		this.selected_date = null;
		this.selected_slot = null;
		this.current_slot_object = null;
		this.render_picker();

		const res = await frappe.call({
			method: "frappoint.frappoint.api.service_type.get_service_type_details",
			args: { service_type: service },
		});

		this.service_details = res.message;

		// Populate Price Select options
		const price_options = this.service_details.prices.map((p) => ({
			label: `${p.price_name} (${p.duration}m) - ${format_currency(p.amount, p.currency)}`,
			value: p.price_name,
		}));

		this.dialog.set_df_property("selected_price_id", "options", price_options);
	}

	on_price_change() {
		const selected_name = this.dialog.get_value("selected_price_id");
		const service = this.dialog.get_value("service_type");
		const price_obj = this.service_details?.prices.find((p) => p.price_name === selected_name);

		if (price_obj) {
			this.dialog.set_values({
				duration: price_obj.duration,
				amount: price_obj.amount,
			});
			this.load_available_dates(service, price_obj.duration);
		}
	}

	async load_available_dates(service, duration) {
		const res = await frappe.call({
			method: "frappoint.frappoint.api.slot_availability.get_available_dates",
			args: { service_type: service, duration: duration },
		});
		this.available_dates = res.message || [];
		this.selected_date = null;
		this.selected_slot = null;
		this.current_slot_object = null;
		this.available_slots = [];
		this.render_picker();
	}

	async load_slots(date) {
		const service = this.dialog.get_value("service_type");
		const duration = this.dialog.get_value("duration");

		if (!service || !duration) return;

		const res = await frappe.call({
			method: "frappoint.frappoint.api.slot_availability.get_available_time_slots",
			args: {
				service_type: service,
				date: date,
				duration: duration,
			},
		});

		const day_data = (res.message || []).find((m) => m.date === date);
		this.available_slots = day_data ? day_data.slots : [];
		this.render_picker();
	}

	setup_event_handlers() {
		const $wrapper = this.dialog.fields_dict.slot_picker_html.$wrapper;

		$wrapper.off("click", ".picker-item").on("click", ".picker-item", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const date = $(e.currentTarget).attr("data-date");
			if (date) this.select_date(date);
		});

		$wrapper.off("click", ".slot-item").on("click", ".slot-item", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const index = $(e.currentTarget).attr("data-index");
			this.select_slot(index);
		});

		$wrapper.on("change", ".provider-filter", (e) => {
			this.filter_provider = $(e.currentTarget).val() || null;
			this.render_picker();
		});
	}

	date_html_builder() {
		if (!this.available_dates?.length) return "";

		return this.available_dates
			.map(
				(d) => `
				<div class="picker-item ${this.selected_date === d ? "active" : ""}" data-date="${d}">
					<span class="date-text">${frappe.datetime.global_date_format(d)}</span>
					<i class="octicon octicon-chevron-right"></i>
				</div>`
			)
			.join("");
	}

	render_picker() {
		const all_providers = [];
		const provider_set = new Set();

		// Use available_slots to find all possible providers for this day
		this.available_slots.forEach((s) => {
			s.providers.forEach((p) => {
				if (!provider_set.has(p.provider)) {
					provider_set.add(p.provider);
					all_providers.push(p);
				}
			});
		});

		const provider_options = all_providers
			.map(
				(p) =>
					`<option value="${p.provider}" ${
						this.filter_provider === p.provider ? "selected" : ""
					}>${p.provider_name}</option>`
			)
			.join("");

		const provider_select = all_providers.length
			? `<select class="provider-filter">
					<option value="">${__("Any Provider")}</option>
					${provider_options}
			   </select>`
			: "";

		let slot_html = this.available_slots
			.map((s, original_index) => {
				// Check if this slot should be hidden based on provider filter
				const has_filtered_provider = s.providers.some(
					(p) => p.provider === this.filter_provider
				);

				if (this.filter_provider && !has_filtered_provider) return "";

				const active_class = this.selected_slot === s.start_time ? "active" : "";
				const count = s.providers?.length || 0;
				const badge_text = this.filter_provider
					? __("available")
					: `${count} ${count === 1 ? __("provider") : __("providers")}`;

				return `
				<div class="slot-item ${active_class}" data-index="${original_index}">
					<span class="slot-time">${s.start_time.substring(0, 5)}</span>
					<span class="slot-badge">${badge_text}</span>
				</div>`;
			})
			.join("");

		const dates_html =
			this.date_html_builder() ||
			`<div class="picker-empty">${__("Select a package to see dates")}</div>`;

		const slots_empty = this.selected_date
			? `<div class="picker-empty">${__("No slots available for this date")}</div>`
			: `<div class="picker-empty">${__("Select a date to see slots")}</div>`;

		this.dialog.fields_dict.slot_picker_html.$wrapper.html(`
			<div class="wizard-picker-container">
				<div class="picker-column border-right">
					<div class="picker-header">${__("Date")}</div>
					${dates_html}
				</div>
				<div class="picker-column">
					<div class="picker-header">
						<span>${__("Time")}</span>
						${provider_select}
					</div>
					<div class="slot-grid">${slot_html || slots_empty}</div>
				</div>
			</div>
		`);
	}

	select_date(date) {
		this.selected_date = date;
		this.selected_slot = null;
		this.current_slot_object = null;
		this.filter_provider = null;
		this.available_slots = [];
		this.render_picker();
		this.load_slots(date);
	}

	select_slot(index) {
		const slot_obj = this.available_slots[parseInt(index)];
		if (!slot_obj) return;

		this.current_slot_object = slot_obj;
		this.selected_slot = slot_obj.start_time;
		this.selected_end = slot_obj.end_time;
		this.selected_provider = this.filter_provider || null;

		this.render_picker();
	}

	submit_to_parent(values) {
		if (!this.selected_slot) {
			frappe.msgprint(__("Please select a time slot"));
			return;
		}

		const guest_payload = {
			guest_name: values.guest_name,
			guest_email: values.guest_email || "",
			guest_mobile: values.guest_mobile || "",
			service_type: values.service_type,
			price_id: values.selected_price_id,
			date: this.selected_date,
			start_time: this.selected_slot,
			end_time: this.selected_end,
			// null = auto-assign; a value = user explicitly chose this provider
			provider: this.selected_provider,
			all_available_providers: this.current_slot_object.providers,
			notes: values.notes || "",
		};

		this.frm.call({
			doc: this.frm.doc,
			method: "add_guest",
			args: { guest_data: guest_payload },
			freeze: true,
			callback: (r) => {
				if (!r.exc) {
					this.dialog.hide();
					frappe.show_alert({
						message: __("Guest added successfully"),
						indicator: "green",
					});
					this.frm.reload_doc();
				}
			},
		});

		this.frm.refresh_field("items");
		this.dialog.hide();
	}

	init_styles() {
		const $dialog_wrapper = this.dialog.$wrapper;

		if ($dialog_wrapper.find("#wizard-styles").length) return;

		$dialog_wrapper.find(".modal-content").prepend(`
			<style id="wizard-styles">
				.wizard-picker-container {
					display: flex;
					border: 0.5px solid var(--border-color);
					border-radius: 10px;
					overflow: hidden;
					background: var(--card-bg);
				}

				.picker-column {
					flex: 1;
					max-height: 380px;
					overflow-y: auto;
				}

				.picker-column.border-right {
					border-right: 0.5px solid var(--border-color);
					flex: 0 0 220px;
				}

				.picker-header {
					padding: 10px 14px;
					background: var(--control-bg);
					font-weight: 500;
					font-size: 11px;
					text-transform: uppercase;
					letter-spacing: 0.05em;
					border-bottom: 0.5px solid var(--border-color);
					color: var(--text-muted);
					position: sticky;
					top: 0;
					z-index: 1;
					display: flex;
					justify-content: space-between;
					align-items: center;
				}

				.picker-item {
					padding: 11px 14px;
					border-bottom: 0.5px solid var(--border-color);
					cursor: pointer;
					display: flex;
					justify-content: space-between;
					align-items: center;
					transition: background 0.15s;
					font-size: 13px;
					color: var(--text-color);
				}

				.picker-item:last-child { border-bottom: none; }
				.picker-item:hover { background: var(--control-bg); }

				.picker-item.active {
					background: var(--primary-extra-light);
					border-left: 3px solid var(--primary);
					padding-left: 11px;
					color: var(--primary);
					font-weight: 500;
				}

				.picker-item .date-text { flex: 1; }

				.picker-item .octicon {
					font-size: 10px;
					color: var(--text-muted);
					opacity: 0.5;
				}

				.picker-item.active .octicon { opacity: 1; color: var(--primary); }

				.picker-empty {
					padding: 24px 14px;
					font-size: 12px;
					color: var(--text-muted);
					text-align: center;
				}

				.slot-grid {
					display: grid;
					grid-template-columns: repeat(auto-fill, minmax(75px, 1fr));
					gap: 7px;
					padding: 12px;
				}

				.slot-item {
					padding: 9px 4px 7px;
					border: 0.5px solid var(--border-color);
					border-radius: 7px;
					text-align: center;
					cursor: pointer;
					transition: all 0.15s ease;
					background: var(--card-bg);
				}

				.slot-item:hover {
					border-color: var(--primary);
					background: var(--primary-extra-light);
				}

				.slot-item.active {
					background: var(--primary);
					border-color: var(--primary);
				}

				.slot-time {
					font-size: 12px;
					font-weight: 500;
					color: var(--text-color);
					display: block;
				}

				.slot-item.active .slot-time { color: white; }

				.slot-badge {
					display: block;
					font-size: 10px;
					color: var(--text-muted);
					margin-top: 3px;
				}

				.slot-item.active .slot-badge { color: rgba(255,255,255,0.75); }

				.provider-filter {
					font-size: 11px;
					height: 22px;
					padding: 0 6px;
					border: 0.5px solid var(--border-color);
					border-radius: 5px;
					background: var(--card-bg);
					color: var(--text-color);
					max-width: 120px;
					cursor: pointer;
				}
			</style>
		`);
	}
}
