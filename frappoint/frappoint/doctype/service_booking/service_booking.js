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

		this.init_styles();
		this.setup_event_handlers();
		this.dialog.show();
	}

	async on_service_change() {
		const service = this.dialog.get_value("service_type");
		if (!service) return;

		// Reset lower fields while loading new service details
		this.dialog.set_df_property("selected_price_id", "options", []);
		this.available_dates = [];
		this.available_slots = [];
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
		const price_obj = this.service_details.prices.find((p) => p.price_name === selected_name);

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
		this.available_slots = [];
		this.render_picker();
	}

	async load_slots(date) {
		const res = await frappe.call({
			method: "frappoint.frappoint.api.slot_availability.get_available_time_slots",
			args: {
				service_type: this.dialog.get_value("service_type"),
				date: date,
				duration: this.dialog.get_value("duration"),
			},
		});
		// Flattening your provider-based response structure
		this.available_slots = res.message.flatMap((p) =>
			p.available_dates[0].slots.map((s) => ({
				...s,
				provider: p.provider,
				provider_name: p.provider_name,
			}))
		);
		this.render_picker();
	}

	setup_event_handlers() {
		const $wrapper = this.dialog.fields_dict.slot_picker_html.$wrapper;

		$wrapper.on("click", ".picker-item", (e) => {
			const date = $(e.currentTarget).attr("data-date");
			this.select_date(date);
		});

		$wrapper.on("click", ".slot-item", (e) => {
			const index = $(e.currentTarget).attr("data-index");
			const slot_obj = this.available_slots[index]; // Direct access!
			this.select_slot(slot_obj);
		});
	}

	render_picker() {
		let date_html = this.available_dates
			.map(
				(d) => `
            <div class="picker-item ${this.selected_date === d ? "active" : ""}" data-date="${d}">
                <span class="date-text">${frappe.datetime.global_date_format(d)}</span>
                <i class="octicon octicon-chevron-right"></i>
            </div>
        `
			)
			.join("");

		let slot_html = this.available_slots
			.map(
				(s, index) => `
    <div class="slot-item ${this.selected_slot === s.start_time ? "active" : ""}"
         data-index="${index}"> ${s.start_time.substring(0, 5)}
    </div>
`
			)
			.join("");

		this.dialog.fields_dict.slot_picker_html.$wrapper.html(`
            <div class="wizard-picker-container">
                <div class="picker-column border-right">
                    <div class="picker-header">${__("Available Dates")}</div>
                    ${date_html || '<div class="text-muted p-3">Select package...</div>'}
                </div>
                <div class="picker-column">
                    <div class="picker-header">${__("Available Slots")}</div>
                    <div class="slot-grid">${
						slot_html || '<div class="text-muted p-3">Select date...</div>'
					}</div>
                </div>
            </div>
        `);
	}

	select_date(date) {
		this.selected_date = date;
		this.selected_slot = null;
		this.load_slots(date);
	}

	select_slot(slot_obj) {
		this.current_slot_object = slot_obj;
		this.selected_slot = slot_obj.start_time;
		this.selected_end = slot_obj.end_time;
		this.render_picker();
	}

	submit_to_parent(values) {
		if (!this.selected_slot) return frappe.msgprint(__("Please select a time slot"));

		// Prepare the payload for the Python API
		const guest_payload = {
			guest_name: values.guest_name,
			guest_email: values.guest_email || "",
			guest_mobile: values.guest_mobile || "",
			service_type: values.service_type,
			price_id: values.selected_price_id,
			date: this.selected_date,
			start_time: this.selected_slot,
			end_time: this.selected_end,
			// Accessing provider and slot_ids from the selected slot object
			provider: this.current_slot_object.provider,
			slot_ids: this.current_slot_object.slot_ids,
			notes: values.notes || "",
		};

		frappe.call({
			method: "frappoint.frappoint.api.booking_desk.add_guest_to_booking",
			args: {
				booking_id: this.frm.doc.name,
				guest_data: guest_payload,
			},
			freeze: true,
			callback: (r) => {
				if (!r.exc) {
					this.dialog.hide();
					frappe.show_alert({ message: __("Appointment Added"), indicator: "green" });
					this.frm.reload_doc();
				}
			},
		});

		this.frm.refresh_field("items");
		this.dialog.hide();
	}

	init_styles() {
		const css = `
            .wizard-picker-container { display: flex; border: 1px solid #d1d8dd; border-radius: 8px; overflow: hidden; background: #fff; }
            .picker-column { flex: 1; max-height: 350px; overflow-y: auto; }
            .picker-header { padding: 10px; background: #f8fafc; font-weight: bold; font-size: 11px; text-transform: uppercase; border-bottom: 1px solid #d1d8dd; color: #64748b; position: sticky; top: 0; }
            .picker-item { padding: 12px 15px; border-bottom: 1px solid #f1f5f9; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s; }
            .picker-item:hover { background: #f1f5f9; }
            .picker-item.active { background: #e0f2fe; border-left: 4px solid #0ea5e9; color: #0369a1; font-weight: bold; }
            .slot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 8px; padding: 12px; }
            .slot-item { padding: 10px 5px; border: 1px solid #e2e8f0; border-radius: 6px; text-align: center; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
            .slot-item:hover { border-color: #0ea5e9; color: #0ea5e9; }
            .slot-item.active { background: #0ea5e9; color: white; border-color: #0ea5e9; box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.2); }
        `;
		if (!$("#wizard-styles").length) {
			$('<style id="wizard-styles">').prop("type", "text/css").html(css).appendTo("head");
		}
	}
}
