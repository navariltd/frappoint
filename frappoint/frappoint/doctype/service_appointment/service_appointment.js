// Copyright (c) 2025, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Appointment", {
	onload(frm) {
		if (frm.doc.start_time && frm.doc.end_time) {
			frm._slot_selected = true;
		} else {
			frm._slot_selected = false;
		}
	},

	refresh(frm) {
		frm._button_state = null;

		if (frm._button_update_timeout) {
			clearTimeout(frm._button_update_timeout);
			frm._button_update_timeout = null;
		}

		frm.events._update_buttons(frm);

		if (
			frm.doc.status === "Confirmed" ||
			(frm.doc.docstatus === 1 && frm.doc.status === "Completed")
		) {
			if (frm.page.btn_secondary) {
				frm.page.btn_secondary.hide();
			}
		}

		// Handle rescheduled appointment submission
		if (frm.doc.__islocal && frm.doc.__reschedule_from) {
			frappe.show_alert({
				message: __(
					"This is a rescheduled appointment. Select new date/time and save to complete the reschedule."
				),
				indicator: "blue",
			});
		}
	},

	validate(frm) {
		calculate_guest_pricing(frm);
	},

	add_context_buttons(frm) {
		// Clear any pending button update
		if (frm._button_update_timeout) {
			clearTimeout(frm._button_update_timeout);
		}

		// Debounce button updates by 100ms
		frm._button_update_timeout = setTimeout(() => {
			frm.events._update_buttons(frm);
		}, 100);
	},

	_update_buttons(frm) {
		// Determine which button state we should be in
		let button_state = null;

		if (frm.doc.docstatus === 1 && frm.doc.status === "Completed") {
			button_state = "completed";
		} else if (frm.doc.status === "Confirmed") {
			button_state = "confirmed";
		} else if (frm.doc.appointment_type && !frm._slot_selected && frm.doc.docstatus === 0) {
			button_state = "fetch_slots";
		} else if (frm._slot_selected && frm.is_new() && frm.doc.docstatus === 0) {
			button_state = "save";
		} else if (frm._slot_selected && !frm.is_new() && frm.doc.docstatus === 0) {
			button_state = "confirm";
		}

		// If button state hasn't changed, don't update
		if (frm._button_state === button_state) {
			return;
		}

		// Clear previous buttons
		frm.page.clear_primary_action();
		if (frm.custom_buttons) frm.clear_custom_buttons();

		// Keep default Save behavior aligned with computed state
		if (button_state === "fetch_slots") {
			frm.disable_save();
		} else {
			frm.enable_save();
		}

		// Update button state
		frm._button_state = button_state;

		if (button_state === "completed") {
			// Issue Consumables button (if not auto-issued)
			if (frm.doc.docstatus === 1 && frm.doc.status === "Completed") {
				frm.add_custom_button(
					__("Issue Consumables"),
					function () {
						frappe.call({
							method: "frappoint.frappoint.doctype.service_appointment.service_appointment.issue_consumables_manual",
							args: {
								appointment: frm.doc.name,
							},
							callback: function (r) {
								frm.reload_doc();
							},
						});
					},
					__("Stock")
				);

				// Material Request button
				frm.add_custom_button(
					__("Create Material Request"),
					function () {
						const d = new frappe.ui.Dialog({
							title: "Select Target Warehouse",
							fields: [
								{
									fieldname: "t_warehouse",
									label: "Target Warehouse",
									fieldtype: "Link",
									options: "Warehouse",
									reqd: 1,
								},
							],
							primary_action_label: "Create Request",
							primary_action(values) {
								d.hide();

								frappe.call({
									method: "frappoint.frappoint.doctype.service_appointment.service_appointment.create_material_request_manual",
									args: {
										appointment: frm.doc.name,
										t_warehouse: values.t_warehouse,
									},
									callback: function (r) {
										if (r.message) {
											frappe.set_route(
												"Form",
												"Material Request",
												r.message
											);
										}
									},
								});
							},
						});
						d.show();
					},
					__("Stock")
				);
			}

			if (frm.page.btn_secondary) {
				frm.page.btn_secondary.hide();
			}
			return;
		}

		// Case 1: Status is "Confirmed" - show Cancel and Reschedule buttons
		if (button_state === "confirmed") {
			frm.page.set_primary_action(__("Complete Appointment"), function () {
				show_complete_appointment_dialog(frm);
			});

			frm.add_custom_button(__("Cancel Appointment"), function () {
				show_cancellation_dialog(frm);
			});

			frm.add_custom_button(__("Reschedule Appointment"), function () {
				reschedule_appointment(frm);
			});

			frm.add_custom_button(__("Change Service Provider"), function () {
				show_change_service_provider_dialog(frm);
			});

			if (frm.page.btn_secondary) {
				frm.page.btn_secondary.hide();
			}
			return;
		}

		// Case 2: Has appointment_type but no start_time and end_time, is new (docstatus == 0)
		if (button_state === "fetch_slots") {
			frm.page.set_primary_action(__("Fetch Available Slots"), function () {
				show_slot_picker(frm);
			});
			return;
		}

		// Case 3: Has start_time and end_time, is new (not saved yet)
		if (button_state === "save") {
			// Show normal save button (default behavior)
			frm.page.set_primary_action(__("Save"), function () {
				frm.save();
			});
			return;
		}

		// Case 4: Has start_time and end_time, saved but not confirmed (not new, docstatus == 0)
		if (button_state === "confirm") {
			// Primary: Confirm Appointment
			frm.page.set_primary_action(__("Confirm Appointment"), function () {
				confirm_appointment(frm);
			});

			// Secondary: Fetch Available Slots (if they want to change)
			frm.add_custom_button(__("Fetch Available Slots"), function () {
				show_slot_picker(frm);
			});
			return;
		}
	},

	start_time(frm) {
		if (frm.doc.start_time) {
			frm._slot_selected = true;
			calculate_end_time(frm);
			validate_appointment_times(frm);
			frm.events._update_buttons(frm);
		}
	},

	end_time(frm) {
		validate_appointment_times(frm);
		if (frm._slot_selected) {
			calculate_end_time(frm);
		}
	},

	appointment_date(frm) {
		validate_appointment_times(frm);
		if (frm._slot_selected) {
			calculate_end_time(frm);
		}
	},

	appointment_type(frm) {
		frm.set_value({ start_time: null, end_time: null });
		frm._slot_selected = false;

		if (!frm.doc.appointment_type) {
			frm.events._update_buttons(frm);
			return;
		}

		// Load appointment type details including prices
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Service Type",
				name: frm.doc.appointment_type,
			},
			callback: function (r) {
				if (r.message) {
					let apt_type = r.message;

					// Handle price selection
					if (apt_type.prices && apt_type.prices.length > 0) {
						if (apt_type.prices.length === 1) {
							// Only one price, auto-select
							frm.set_value("appointment_price", apt_type.prices[0].price_name);
							frm.set_value("total_amount", apt_type.prices[0].amount);
							frm.set_value("grand_total", apt_type.prices[0].amount);
							frm.set_value("currency", apt_type.prices[0].currency);
							frm.set_value("duration", apt_type.prices[0].duration);
						} else {
							// Multiple prices, let user select
							show_price_selector(frm, apt_type.prices);
						}
					}

					frm.events._update_buttons(frm);
				}
			},
		});
	},

	before_save(frm) {
		if (
			frm.doc.selected_slot_ids &&
			frm.doc.appointment_provider &&
			frm.doc.appointment_date &&
			frm.doc.start_time
		) {
			frm.doc.__booking_required = true;
		}
	},

	after_save(frm) {
		// Complete the reschedule by cancelling the old appointment
		// Only execute after submission and if not already processed
		if (
			frm.doc.rescheduled_from &&
			frm.doc.docstatus === 1 &&
			!frm.doc.__reschedule_processed
		) {
			frm.doc.__reschedule_processed = true;
			complete_reschedule(frm, frm.doc.rescheduled_from);
		}
	},

	customer(frm) {
		if (frm.doc.customer) {
			frappe.call({
				method: "frappoint.utils.get_customer_contact_details",
				args: {
					customer: frm.doc.customer,
				},
				callback: function (res) {
					if (!frm.doc.full_name && res.message.contact_display) {
						frm.set_value("full_name", res.message.contact_display);
					}

					if (!frm.doc.email && res.message.contact_email) {
						frm.set_value("email", res.message.contact_email);
					}

					if (!frm.doc.phone && res.message.contact_phone) {
						frm.set_value("mobile_no", res.message.contact_phone);
					}
				},
			});
		}
	},
});

frappe.ui.form.on("Service Appointment Guest", {
	guests_add(frm, cdt, cdn) {
		calculate_guest_pricing(frm);
	},

	guests_remove(frm, cdt, cdn) {
		calculate_guest_pricing(frm);
	},
});

function calculate_guest_pricing(frm) {
	if (!frm.doc.appointment_type || !frm.doc.appointment_price) {
		return;
	}

	// Count total guests
	let guest_count = (frm.doc.guests || []).length || 1;
	frm.set_value("total_guests", guest_count);

	// Fetch the Service Type document to get price details
	frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "Service Type",
			name: frm.doc.appointment_type,
		},
		callback: function (r) {
			if (r.message) {
				let service_type = r.message;

				let selected_price = null;
				if (service_type.prices) {
					let matching_prices = service_type.prices.filter(
						(p) => p.price_name === frm.doc.appointment_price
					);

					// Sort by guest_count descending to get highest applicable tier
					matching_prices.sort((a, b) => (b.guest_count || 0) - (a.guest_count || 0));

					for (let price of matching_prices) {
						let pricing_model = price.pricing_model || "Per Booking";

						if (pricing_model === "Guest Tier") {
							if (!price.guest_count || price.guest_count <= guest_count) {
								selected_price = price;
								break;
							}
						} else {
							selected_price = price;
							break;
						}
					}
				}

				if (selected_price) {
					let pricing_model = selected_price.pricing_model || "Per Booking";
					let base_amount = selected_price.amount;
					let estimated_total = base_amount;

					// Calculate estimated total based on pricing model
					if (pricing_model === "Per Guest") {
						estimated_total = base_amount * guest_count;
					} else if (pricing_model === "Guest Tier") {
						let tier_msg = selected_price.guest_count
							? __("Tier pricing: {0} for {1}+ guests", [
									format_currency(base_amount, selected_price.currency),
									selected_price.guest_count,
							  ])
							: __("Tier pricing: {0}", [
									format_currency(base_amount, selected_price.currency),
							  ]);

						frappe.show_alert({
							message: tier_msg,
							indicator: "orange",
						});
					} else {
						frappe.show_alert({
							message: __("Flat rate: {0}", [
								format_currency(base_amount, selected_price.currency),
							]),
							indicator: "green",
						});
					}

					// Update total amount
					frm.set_value("grand_total", estimated_total);
					frm.set_value("total_amount", estimated_total);
					frm.set_value("currency", selected_price.currency);
				}
			}
		},
	});
}

// Helper: Convert date + time strings into a JS Date object
function parse_time_to_datetime(date_str, time_str) {
	if (!time_str) return null;
	let time_parts = time_str.split(":");
	if (time_parts.length < 2) return null;

	const year = date_str.split("-")[0];
	const month = parseInt(date_str.split("-")[1], 10) - 1;
	const day = date_str.split("-")[2];
	const hours = parseInt(time_parts[0], 10);
	const minutes = parseInt(time_parts[1], 10);

	return new Date(year, month, day, hours, minutes, 0);
}

function calculate_end_time(frm) {
	const start_time = frm.doc.start_time;
	const appointment_date = frm.doc.appointment_date;

	let duration = frm.doc.duration;
	if (!start_time || !appointment_date || duration <= 0) return;

	let start_dt = parse_time_to_datetime(appointment_date, start_time);
	if (!start_dt) return;

	start_dt.setMinutes(start_dt.getMinutes() + duration);

	const end_hours = start_dt.getHours().toString().padStart(2, "0");
	const end_minutes = start_dt.getMinutes().toString().padStart(2, "0");

	frm.set_value("end_time", `${end_hours}:${end_minutes}`);
}

function validate_appointment_times(frm) {
	const start_time = frm.doc.start_time;
	const end_time = frm.doc.end_time;
	const appointment_date = frm.doc.appointment_date;

	if (!start_time || !end_time || !appointment_date) return;

	const start_dt = parse_time_to_datetime(appointment_date, start_time);
	const end_dt = parse_time_to_datetime(appointment_date, end_time);
	const now = new Date();

	if (!start_dt || !end_dt) return;

	if (start_dt >= end_dt) {
		frappe.msgprint(__("End Time must be after Start Time"));
		return;
	}

	if (start_dt < now) {
		frappe.msgprint(__("You cannot schedule an appointment in the past"));
		return;
	}
}

function load_available_slots(frm) {
	if (!frm.doc.appointment_type) {
		return Promise.reject("No appointment type selected");
	}

	return new Promise((resolve, reject) => {
		frappe.call({
			method: "frappoint.frappoint.doctype.service_appointment.service_appointment.get_appointment_slots",
			args: {
				appointment_type: frm.doc.appointment_type,
				duration: frm.doc.duration,
				provider: frm.doc.appointment_provider || null,
				date: frm.doc.appointment_date || null,
			},
			callback: function (r) {
				if (r.message) {
					frm.available_slots = r.message;
					resolve(r.message);
				} else {
					reject("No slots available");
				}
			},
			error: function (err) {
				reject(err);
			},
		});
	});
}

function show_slot_picker(frm) {
	frappe.dom.freeze(__("Loading available slots..."));

	load_available_slots(frm)
		.then((slots) => {
			frappe.dom.unfreeze();

			if (!slots || slots.length === 0) {
				frappe.msgprint(
					__("No available slots found. Please adjust your search criteria.")
				);
				return;
			}

			// Create dialog to show available slots
			let d = new frappe.ui.Dialog({
				title: __("Select Appointment Slot"),
				fields: [
					{
						fieldname: "focus_sink",
						fieldtype: "HTML",
						options: '<div tabindex="-1"></div>',
					},
					{
						fieldname: "provider_filter",
						fieldtype: "Link",
						label: __("Provider (optional)"),
						options: "Service Provider",
						get_query: function () {
							let all_providers = new Set();
							(frm.available_slots || []).forEach((date_data) => {
								date_data.slots.forEach((time_slot) => {
									time_slot.providers.forEach((p) =>
										all_providers.add(p.provider)
									);
								});
							});
							return {
								filters: { name: ["in", [...all_providers]] },
							};
						},
						onchange: function () {
							update_slot_display(d, frm);
						},
					},
					{
						fieldname: "slot_display",
						fieldtype: "HTML",
					},
				],
				size: "extra-large",
				primary_action_label: __("Book Selected Slot"),
				primary_action: function () {
					let selected_slot = d.selected_slot;
					if (!selected_slot) {
						frappe.msgprint(__("Please select a slot"));
						return;
					}

					select_slot(frm, selected_slot, d);
				},
			});

			update_slot_display(d, frm);
			d.show();
		})
		.catch((err) => {
			frappe.dom.unfreeze();
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to load available slots. Please try again."),
				indicator: "red",
			});
			console.error("Error loading slots:", err);
		});
}

function update_slot_display(dialog, frm) {
	const provider_filter = dialog.get_value("provider_filter");
	const slots = frm.available_slots;

	let html = `
	<style>
		.slot-picker { padding: 16px; }
		.date-block {
			border: 0.5px solid var(--border-color);
			border-radius: 10px;
			margin-bottom: 16px;
			overflow: hidden;
		}
		.date-label {
			font-size: 12px;
			font-weight: 500;
			color: var(--text-muted);
			text-transform: uppercase;
			letter-spacing: 0.04em;
			padding: 10px 14px;
			background: var(--control-bg);
			border-bottom: 0.5px solid var(--border-color);
		}
		.slot-grid {
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
			gap: 8px;
			padding: 12px;
		}
		.slot-btn {
			border: 0.5px solid var(--border-color);
			border-radius: 8px;
			padding: 10px 8px;
			background: var(--card-bg);
			cursor: pointer;
			transition: all 0.15s ease;
			text-align: center;
			display: flex;
			flex-direction: column;
			align-items: center;
			gap: 4px;
			width: 100%;
		}
		.slot-btn:hover { border-color: var(--primary); background: var(--primary-extra-light); }
		.slot-btn.selected { background: var(--primary); border-color: var(--primary); }
		.slot-time { font-size: 13px; font-weight: 500; color: var(--text-color); }
		.slot-btn.selected .slot-time { color: white; }
		.slot-badge {
			font-size: 10px;
			color: var(--text-muted);
			background: var(--control-bg);
			border-radius: 20px;
			padding: 1px 7px;
			line-height: 1.6;
		}
		.slot-btn.selected .slot-badge { background: rgba(255,255,255,0.25); color: white; }
		.slot-provider-name {
			font-size: 11px;
			color: var(--text-muted);
		}
		.slot-btn.selected .slot-provider-name { color: rgba(255,255,255,0.85); }
	</style>
	<div class="slot-picker">`;

	slots.forEach((date_data) => {
		// When filtering, only keep time slots that have the selected provider
		let time_slots = date_data.slots;
		if (provider_filter) {
			time_slots = time_slots.filter((ts) =>
				ts.providers.some((p) => p.provider === provider_filter)
			);
		}

		if (!time_slots.length) return;

		html += `
		<div class="date-block">
			<div class="date-label">${frappe.datetime.str_to_user(date_data.date)}</div>
			<div class="slot-grid">`;

		time_slots.forEach((time_slot) => {
			const start_display = time_slot.start_time.substring(0, 5);
			const end_display = time_slot.end_time.substring(0, 5);

			// When a specific provider is chosen, store only that provider in the payload
			// so the backend knows the explicit preference; otherwise pass all providers
			// for auto-assignment
			const providers_payload = provider_filter
				? time_slot.providers.filter((p) => p.provider === provider_filter)
				: time_slot.providers;

			const slot_data = JSON.stringify({
				date: date_data.date,
				start_time: time_slot.start_time,
				end_time: time_slot.end_time,
				// null means "auto-assign"; a value means "use this provider"
				preferred_provider: provider_filter || null,
				providers: providers_payload,
			}).replace(/'/g, "&#39;");

			// Badge changes meaning depending on filter state
			let badge_html = "";
			if (provider_filter) {
				// Show the provider name so it's clear who you're booking
				const match = time_slot.providers.find((p) => p.provider === provider_filter);
				badge_html = `<span class="slot-provider-name">${
					match ? match.provider_name : ""
				}</span>`;
			} else {
				const count = time_slot.providers.length;
				const label = count === 1 ? __("1 provider") : `${count} ${__("providers")}`;
				badge_html = `<span class="slot-badge">${label}</span>`;
			}

			html += `
			<button
				type="button"
				class="slot-btn"
				data-slot='${slot_data}'
				onclick="(function(btn){
					document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
					btn.classList.add('selected');
					cur_dialog.selected_slot = JSON.parse(btn.dataset.slot);
				})(this)"
			>
				<span class="slot-time">${start_display} – ${end_display}</span>
				${badge_html}
			</button>`;
		});

		html += `</div></div>`;
	});

	html += `</div>`;

	dialog.fields_dict.slot_display.$wrapper.html(html);
}

function show_change_service_provider_dialog(frm) {
	if (!frm.doc.name) {
		frappe.msgprint(__("Save the appointment before changing the service provider."));
		return;
	}

	frappe.dom.freeze(__("Loading available providers..."));
	frappe.call({
		method: "frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot.change_appointment_provider",
		args: {
			appointment_name: frm.doc.name,
		},
		callback: function (r) {
			frappe.dom.unfreeze();

			const response = r.message || {};
			const provider_options = response.provider_change_options || [];

			if (!provider_options.length) {
				frappe.msgprint(
					__("No replacement providers are available for this appointment time.")
				);
				return;
			}

			const dialog = new frappe.ui.Dialog({
				title: __("Change Service Provider"),
				fields: [
					{
						fieldname: "provider_intro",
						fieldtype: "HTML",
					},
					{
						fieldname: "provider_list",
						fieldtype: "HTML",
					},
				],
				primary_action_label: __("Change Provider"),
				primary_action: function () {
					const selected_option = dialog.selected_provider_option;
					if (!selected_option) {
						frappe.msgprint(__("Please select a replacement provider."));
						return;
					}

					dialog.hide();
					frappe.dom.freeze(__("Updating service provider..."));
					frappe.call({
						method: "frappoint.frappoint.doctype.service_provider_appointment_slot.service_provider_appointment_slot.change_appointment_provider",
						args: {
							appointment_name: frm.doc.name,
							slot_ids: JSON.stringify(selected_option.slot_ids || []),
						},
						callback: function (update_response) {
							frappe.dom.unfreeze();
							const update_result = update_response.message || {};
							if (!update_result.success) {
								frappe.msgprint(
									update_result.message ||
										__(
											"Failed to change the service provider. Please try again."
										)
								);
								return;
							}

							frappe.show_alert({
								message: __("Service provider updated successfully."),
								indicator: "green",
							});
							frm.reload_doc();
						},
						error: function () {
							frappe.dom.unfreeze();
							frappe.msgprint({
								title: __("Error"),
								message: __(
									"Failed to change the service provider. Please try again."
								),
								indicator: "red",
							});
						},
					});
				},
			});

			dialog.fields_dict.provider_intro.$wrapper.html(`
				<div class="text-sm text-muted" style="margin-bottom: 12px;">
					${__("Select a replacement provider for this appointment's current time slot.")}
				</div>
			`);

			const provider_list_html = provider_options
				.map((option, index) => {
					const provider_name = option.provider_name || option.provider;
					const service_unit_name =
						option.service_unit_name || option.service_unit || "";
					const slot_count = (option.slot_ids || []).length;

					return `
						<button
							type="button"
							class="provider-change-option"
							data-index="${index}"
							style="width:100%; text-align:left; padding:12px 14px; border:1px solid var(--border-color); border-radius:10px; background:var(--card-bg); margin-bottom:10px; transition:all 0.15s ease;"
						>
							<div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
								<div>
									<div style="font-weight:600; color:var(--text-color);">${provider_name}</div>
									<div style="font-size:12px; color:var(--text-muted); margin-top:4px;">
										${service_unit_name ? `${service_unit_name} · ` : ""}${slot_count} slot${
						slot_count === 1 ? "" : "s"
					}
									</div>
								</div>
								<span class="material-symbols-outlined" style="color:var(--primary);">swap_horiz</span>
							</div>
						</button>
					`;
				})
				.join("");

			dialog.fields_dict.provider_list.$wrapper.html(`
				<div class="provider-change-options">${provider_list_html}</div>
			`);

			dialog.selected_provider_option = provider_options[0] || null;
			dialog.fields_dict.provider_list.$wrapper.find(".provider-change-option").first().css({
				borderColor: "var(--primary)",
				background: "var(--primary-extra-light)",
			});

			dialog.fields_dict.provider_list.$wrapper.on(
				"click",
				".provider-change-option",
				function () {
					const index = Number($(this).attr("data-index"));
					const option = provider_options[index];
					if (!option) return;

					dialog.selected_provider_option = option;
					dialog.fields_dict.provider_list.$wrapper.find(".provider-change-option").css({
						borderColor: "var(--border-color)",
						background: "var(--card-bg)",
					});
					$(this).css({
						borderColor: "var(--primary)",
						background: "var(--primary-extra-light)",
					});
				}
			);

			dialog.show();
		},
		error: function () {
			frappe.dom.unfreeze();
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to load replacement providers. Please try again."),
				indicator: "red",
			});
		},
	});
	return;
}

function select_slot(frm, selected_slot, dialog) {
	frm.set_value("appointment_date", selected_slot.date);
	frm.set_value("start_time", selected_slot.start_time);
	frm.set_value("end_time", selected_slot.end_time);

	// If user explicitly picked a provider, set it so before_save skips auto-assign;
	// otherwise leave blank and let _perform_provider_assignment decide
	if (selected_slot.preferred_provider) {
		frm.set_value("appointment_provider", selected_slot.preferred_provider);

		// Resolve slot_ids immediately from the chosen provider's data
		const winner = selected_slot.providers.find(
			(p) => p.provider === selected_slot.preferred_provider
		);
		frm.set_value("selected_slot_ids", JSON.stringify(winner ? winner.slot_ids : []));
	} else {
		frm.set_value("appointment_provider", null);
		// Leave selected_slot_ids empty — before_save will populate it after assignment
		frm.set_value("selected_slot_ids", "[]");
	}

	// Always pass the full provider list so before_save has everything it needs
	frm.set_value("all_available_providers", JSON.stringify(selected_slot.providers));

	frappe.show_alert({
		message: selected_slot.preferred_provider
			? __("Slot selected with specific provider. Save to confirm.")
			: __("Slot selected. Provider will be auto-assigned on save."),
		indicator: "green",
	});

	dialog.hide();
}

// Global function to handle slot selection
window.selectSlot = function (btn) {
	// Remove previous selection
	document.querySelectorAll(".slot-btn").forEach((b) => b.classList.remove("selected"));

	btn.classList.add("selected");

	let dialog = cur_dialog;
	dialog.selected_slot = {
		provider: btn.dataset.provider,
		provider_name: btn.dataset.providerName,
		date: btn.dataset.date,
		start_time: btn.dataset.start,
		end_time: btn.dataset.end,
		slot_ids: JSON.parse(btn.dataset.slots),
	};
};

function confirm_appointment(frm) {
	// Check if price is selected
	if (!frm.doc.appointment_price) {
		frappe.msgprint(__("Please select a price for this appointment"));
		return;
	}

	frappe.call({
		method: "confirm_appointment",
		doc: frm.doc,
		args: {},
		freeze: true,
		freeze_message: __("Confirming appointment..."),
		callback: function () {
			frm.reload_doc();
		},
	});
}

function show_price_selector(frm, prices) {
	let d = new frappe.ui.Dialog({
		title: __("Select Appointment Price"),
		fields: [
			{
				fieldname: "price_selection",
				fieldtype: "HTML",
			},
		],
		primary_action_label: __("Select"),
		primary_action: function () {
			let selected_price = d.selected_price;
			if (!selected_price) {
				frappe.msgprint(__("Please select a price"));
				return;
			}

			frm.set_value("appointment_price", selected_price.price_name);
			frm.set_value("duration", selected_price.duration);

			// The total_amount will be calculated in validate based on pricing_model
			// But we can show an estimate here
			let guest_count = (frm.doc.guests || []).length || 1;
			let estimated_amount = selected_price.amount;

			if (selected_price.pricing_model === "Per Guest") {
				estimated_amount = selected_price.amount * guest_count;
			}

			frm.set_value("total_amount", estimated_amount);
			frm.set_value("grand_total", estimated_amount);
			frm.set_value("currency", selected_price.currency);

			d.hide();
		},
	});

	// Build price selection HTML with pricing model info
	let html = '<div class="price-selector">';

	prices.forEach((price) => {
		let pricing_info = price.pricing_model || "Per Booking";
		let price_label = `${format_currency(price.amount, price.currency)}`;

		// Add pricing model badge
		let badge_color =
			{
				"Per Booking": "blue",
				"Per Guest": "green",
				"Guest Tier": "orange",
			}[pricing_info] || "blue";

		// For Guest Tier, show the tier info
		let tier_info = "";
		if (pricing_info === "Guest Tier" && price.guest_count) {
			tier_info = `<div class="tier-info"><small>For ${price.guest_count}+ guests</small></div>`;
		}

		html += `
			<div class="price-card" data-price='${JSON.stringify(price)}' onclick="selectPrice(this)">
				<div class="price-header">
					<div class="price-name">${price.price_name}</div>
					<span class="badge badge-${badge_color}">${pricing_info}</span>
				</div>
				<div class="price-amount">${price_label}</div>
				${tier_info}
				<div class="price-details">
					<small class="text-muted">${price.duration} minutes</small>
				</div>
			</div>
		`;
	});

	html += "</div>";

	html += `
		<style>
			.price-selector {
				display: grid;
				grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
				gap: 15px;
				margin-top: 15px;
			}
			.price-card {
				border: 2px solid #d1d8dd;
				border-radius: 8px;
				padding: 15px;
				cursor: pointer;
				transition: all 0.3s;
			}
			.price-card:hover {
				border-color: #5e64ff;
				transform: translateY(-2px);
				box-shadow: 0 4px 8px rgba(0,0,0,0.1);
			}
			.price-card.selected {
				border-color: #5e64ff;
				background-color: #f0f4ff;
			}
			.price-header {
				display: flex;
				justify-content: space-between;
				align-items: center;
				margin-bottom: 8px;
			}
			.price-name {
				font-weight: bold;
				font-size: 16px;
			}
			.badge {
				padding: 2px 8px;
				border-radius: 12px;
				font-size: 11px;
				font-weight: 600;
			}
			.badge-blue { background: #e8f4ff; color: #2490ef; }
			.badge-green { background: #e8f7ed; color: #2e844a; }
			.badge-orange { background: #fff4e6; color: #ff9d00; }
			.price-amount {
				font-size: 24px;
				color: #5e64ff;
				font-weight: bold;
				margin: 8px 0;
			}
			.tier-info {
				background: #f8f9fa;
				padding: 4px 8px;
				border-radius: 4px;
				margin: 6px 0;
			}
			.price-details {
				margin-top: 8px;
			}
		</style>
	`;

	d.fields_dict.price_selection.$wrapper.html(html);
	d.show();
}

// Global function to handle price selection
window.selectPrice = function (card) {
	// Remove previous selection
	document.querySelectorAll(".price-card").forEach((c) => c.classList.remove("selected"));

	// Mark as selected
	card.classList.add("selected");

	// Store selected price
	let dialog = cur_dialog;
	dialog.selected_price = JSON.parse(card.dataset.price);
};

function reschedule_appointment(frm) {
	frappe.confirm(
		__(
			"This will create a new appointment with the same details. You can then select a new date and time. Continue?"
		),
		() => {
			// Create new appointment doc with prefilled data
			frappe.new_doc("Service Appointment", {
				customer: frm.doc.customer,
				full_name: frm.doc.full_name,
				mobile_no: frm.doc.mobile_no,
				email: frm.doc.email,
				company: frm.doc.company,
				appointment_type: frm.doc.appointment_type,
				appointment_provider: frm.doc.appointment_provider,
				duration: frm.doc.duration,
				service_unit: frm.doc.service_unit,
				appointment_price: frm.doc.appointment_price,
				total_amount: frm.doc.total_amount,
				grand_total: frm.doc.grand_total,
				currency: frm.doc.currency,
				details: frm.doc.details,
				rescheduled_from: frm.doc.name,
				notes:
					(frm.doc.notes || "") +
					`\n\nRescheduled from: ${
						frm.doc.name
					} (Original: ${frappe.datetime.str_to_user(frm.doc.appointment_date)} ${
						frm.doc.start_time
					})`,
				source: frm.doc.source,
				guests: frm.doc.guests,
				add_video_conferencing: frm.doc.add_video_conferencing,
				booking_id: frm.doc.booking_id,
				is_rescheduling: 1,
			});
		}
	);
}

function complete_reschedule(frm, old_appointment_name) {
	// Cancel the old appointment
	frappe.call({
		method: "frappoint.frappoint.doctype.service_appointment.service_appointment.cancel_old_appointment",
		args: {
			old_appointment_name: old_appointment_name,
			new_appointment_name: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Completing reschedule..."),
		callback: function (r) {
			if (r.message && r.message.success) {
				frappe.show_alert({
					message: __(
						"Appointment rescheduled successfully. Old appointment {0} has been cancelled.",
						[old_appointment_name]
					),
					indicator: "green",
				});

				// Reload to show updated fields
				frm.reload_doc();
			}
		},
		error: function (r) {
			frappe.msgprint({
				title: __("Reschedule Failed"),
				message: __("Failed to cancel the old appointment. Please cancel it manually."),
				indicator: "red",
			});
		},
	});
}

function show_complete_appointment_dialog(frm) {
	// Get current time as default
	let now = new Date();
	let default_time = `${now.getHours().toString().padStart(2, "0")}:${now
		.getMinutes()
		.toString()
		.padStart(2, "0")}`;

	let d = new frappe.ui.Dialog({
		title: __("Complete Appointment"),
		fields: [
			{
				fieldname: "actual_start_time",
				fieldtype: "Time",
				label: __("Actual Start Time"),
				reqd: 1,
				default: frm.doc.start_time,
				description: __("Enter the actual time the appointment started"),
			},
			{
				fieldname: "actual_end_time",
				fieldtype: "Time",
				label: __("Actual End Time"),
				reqd: 1,
				default: default_time,
				description: __("Enter the actual time the appointment ended"),
			},
			{
				fieldname: "section_break",
				fieldtype: "Section Break",
			},
			{
				fieldname: "info",
				fieldtype: "HTML",
				options: `
					<div style="padding: 10px; background-color: #f0f4ff; border-radius: 6px; margin-top: 10px;">
						<p style="margin: 0; color: #5e64ff; font-weight: 500;">
							<i class="fa fa-info-circle"></i> The actual duration will be calculated automatically and used for invoicing.
						</p>
						<p style="margin: 5px 0 0 0; color: #666; font-size: 12px;">
							Appointment started at: ${frm.doc.start_time}
						</p>
					</div>
				`,
			},
		],
		primary_action_label: __("Complete & Create Invoice"),
		primary_action: function (values) {
			frappe.dom.freeze(__("Completing appointment..."));

			// Set the actual end time first, then status, then save
			frappe.call({
				method: "complete_and_invoice",
				doc: frm.doc,
				args: {
					actual_start_time: values.actual_start_time,
					actual_end_time: values.actual_end_time,
				},
				callback: function (res) {
					frappe.dom.unfreeze();
					d.hide();

					if (res.message) {
						frappe.set_route("Form", "Sales Invoice", res.message);
					}
				},
				error: function () {
					frappe.dom.unfreeze();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to complete appointment. Please try again."),
						indicator: "red",
					});
				},
			});
		},
		secondary_action_label: __("Cancel"),
	});

	d.show();
}

function show_cancellation_dialog(frm) {
	// Fetch all available cancellation reasons
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Service Appointment Lost Reason",
			fields: ["lost_reason"],
			limit_page_length: 0,
		},
		callback: function (r) {
			if (r.message && r.message.length > 0) {
				build_cancellation_dialog(frm, r.message);
			} else {
				frappe.msgprint({
					title: __("No Reasons Available"),
					message: __(
						"Please configure cancellation reasons in Service Appointment Lost Reason doctype first."
					),
					indicator: "orange",
				});
			}
		},
	});
}

function build_cancellation_dialog(frm, reasons) {
	// Build options string for MultiSelect field
	let reason_options = reasons.map((r) => r.lost_reason).join("\n");

	let d = new frappe.ui.Dialog({
		title: __("Cancel Appointment"),
		fields: [
			{
				fieldname: "reasons_section",
				fieldtype: "Section Break",
				label: __("Select Cancellation Reasons"),
			},
			{
				fieldname: "selected_reasons",
				fieldtype: "MultiSelect",
				label: __("Cancellation Reasons"),
				options: reason_options,
				reqd: 1,
				description: __("Select one or more reasons for cancelling this appointment"),
			},
			{
				fieldname: "cancellation_notes",
				fieldtype: "Text",
				label: __("Additional Notes"),
				description: __("Provide any additional information about the cancellation"),
			},
			// {
			// 	fieldname: "warning_section",
			// 	fieldtype: "Section Break",
			// },
			// {
			// 	fieldname: "warning_html",
			// 	fieldtype: "HTML",
			// 	options: `
			// 		<div style="padding: 12px; background-color: #fff4e6; border-left: 4px solid #ff9d00; border-radius: 4px; margin-top: 10px;">
			// 			<p style="margin: 0; color: #333; font-weight: 500;">
			// 				<i class="fa fa-exclamation-triangle" style="color: #ff9d00;"></i>
			// 				Important: Once cancelled, this appointment cannot be recovered. Any associated bookings will be released.
			// 			</p>
			// 		</div>
			// 	`,
			// },
		],
		primary_action_label: __("Cancel Appointment"),
		primary_action: function (values) {
			// Get selected reasons (MultiSelect returns comma-separated string)
			let selected_reasons = values.selected_reasons
				? values.selected_reasons.split(",").map((r) => r.trim())
				: [];

			if (selected_reasons.length === 0) {
				frappe.msgprint(__("Please select at least one cancellation reason"));
				return;
			}

			frappe.dom.freeze(__("Cancelling appointment..."));

			// Clear existing reasons and add new ones
			frm.clear_table("cancellation_reasons");
			selected_reasons.forEach((reason) => {
				frm.add_child("cancellation_reasons", {
					lost_reason: reason,
				});
			});

			// Set cancellation notes and status
			frm.set_value("cancellation_notes", values.cancellation_notes)
				.then(() => {
					return frm.set_value("status", "Cancelled");
				})
				.then(() => {
					// Save the document
					return frm.save("Cancel");
				})
				.then(() => {
					frappe.dom.unfreeze();
					d.hide();

					frappe.show_alert({
						message: __("Appointment cancelled successfully."),
						indicator: "orange",
					});

					// Reload to show updated information
					setTimeout(() => {
						frm.reload_doc();
					}, 1000);
				})
				.catch((error) => {
					frappe.dom.unfreeze();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to cancel appointment. Please try again."),
						indicator: "red",
					});
				});
		},
		secondary_action_label: __("Don't Cancel"),
	});

	d.show();
}
