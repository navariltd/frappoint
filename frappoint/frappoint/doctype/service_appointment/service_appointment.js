// Copyright (c) 2025, Navari LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Appointment", {
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
		} else if (
			frm.doc.appointment_type &&
			!frm.doc.start_time &&
			!frm.doc.end_time &&
			frm.doc.docstatus === 0
		) {
			button_state = "fetch_slots";
		} else if (
			frm.doc.start_time &&
			frm.doc.end_time &&
			frm.is_new() &&
			frm.doc.docstatus === 0
		) {
			button_state = "save";
		} else if (
			frm.doc.start_time &&
			frm.doc.end_time &&
			!frm.is_new() &&
			frm.doc.docstatus === 0
		) {
			button_state = "confirm";
		}

		// If button state hasn't changed, don't update
		if (frm._button_state === button_state) {
			return;
		}

		// Clear previous buttons
		frm.page.clear_primary_action();
		if (frm.custom_buttons) frm.clear_custom_buttons();

		// Update button state
		frm._button_state = button_state;

		if (button_state === "completed") {
			frm.add_custom_button(__("Cancel Appointment"), function () {
				show_cancellation_dialog(frm);
			}).addClass("btn-primary");

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
		calculate_end_time(frm);
		validate_appointment_times(frm);
		if (frm.doc.start_time && frm.doc.end_time) {
			frm.events.add_context_buttons(frm);
		}
	},

	end_time(frm) {
		validate_appointment_times(frm);
		if (frm.doc.start_time && frm.doc.end_time) {
			frm.events.add_context_buttons(frm);
		}
	},

	appointment_date(frm) {
		calculate_end_time(frm);
		validate_appointment_times(frm);
	},

	appointment_type(frm) {
		calculate_end_time(frm);

		if (frm.doc.appointment_type) {
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

						// Set duration
						if (apt_type.default_duration_in_minutes) {
							frm.set_value("duration", apt_type.default_duration_in_minutes);
						}

						// Handle price selection
						if (apt_type.prices && apt_type.prices.length > 0) {
							if (apt_type.prices.length === 1) {
								// Only one price, auto-select
								frm.set_value("appointment_price", apt_type.prices[0].price_name);
								frm.set_value("total_amount", apt_type.prices[0].rate);
								frm.set_value("currency", apt_type.prices[0].currency);
							} else {
								// Multiple prices, let user select
								show_price_selector(frm, apt_type.prices);
							}
						}

						frm.events.add_context_buttons(frm);
					}
				},
			});
		} else {
			frm.events.add_context_buttons(frm);
		}
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
				method: "get_customer_contact_details",
				doc: frm.doc,
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
						label: __("Provider"),
						options: "Service Provider",
						get_query: function () {
							return {
								filters: {
									name: ["in", frm.available_slots.map((s) => s.provider)],
								},
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
				primary_action: function (values) {
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

function select_slot(frm, slot_data, dialog) {
	frm.set_value("appointment_provider", slot_data.provider);
	frm.set_value("appointment_date", slot_data.date);
	frm.set_value("start_time", slot_data.start_time);
	frm.set_value("end_time", slot_data.end_time);

	frm.set_value("selected_slot_ids", JSON.stringify(slot_data.slot_ids));

	frappe.show_alert({
		message: __("Slot selected. Please save the appointment to confirm booking."),
		indicator: "green",
	});

	dialog.hide();
}

function update_slot_display(dialog, frm) {
	let provider_filter = dialog.get_value("provider_filter");
	let slots = frm.available_slots;

	if (provider_filter) {
		slots = slots.filter((s) => s.provider === provider_filter);
	}

	let html = `<div class="slot-picker">`;

	slots.forEach((provider_data) => {
		html += `
		<div class="provider-card">
			<div class="provider-header">
				<span class="provider-name">${provider_data.provider_name}</span>
			</div>
		`;

		provider_data.available_dates.forEach((date_data) => {
			html += `
			<div class="date-block">
				<div class="date-label">
					${frappe.datetime.str_to_user(date_data.date)}
				</div>
				<div class="slot-grid">
			`;

			date_data.slots.forEach((slot) => {
				html += `
				<button
					type="button"
					class="slot-btn"
					data-provider="${provider_data.provider}"
					data-provider-name="${provider_data.provider_name}"
					data-date="${date_data.date}"
					data-start="${slot.start_time}"
					data-end="${slot.end_time}"
					data-slots='${JSON.stringify(slot.slot_ids)}'
					onclick="selectSlot(this)"
				>
					<span class="slot-time">
						${slot.start_time} – ${slot.end_time}
					</span>
				</button>
				`;
			});

			html += `</div></div>`;
		});

		html += `</div>`;
	});

	html += `</div>`;

	html += `
	<style>
		.slot-picker {
			padding: 16px;
		}

		.provider-card {
			border: 1px solid var(--border-color);
			border-radius: 10px;
			padding: 14px;
			margin-bottom: 18px;
			background: var(--card-bg);
		}

		.provider-header {
			font-weight: 600;
			font-size: 15px;
			margin-bottom: 10px;
		}

		.date-block {
			margin-bottom: 14px;
		}

		.date-label {
			font-size: 13px;
			font-weight: 500;
			color: var(--text-muted);
			margin-bottom: 8px;
		}

		.slot-grid {
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
			gap: 8px;
		}

		.slot-btn {
			border: 1px solid var(--border-color);
			border-radius: 8px;
			padding: 8px 6px;
			background: white;
			cursor: pointer;
			transition: all 0.15s ease;
			text-align: center;
		}

		.slot-btn:hover {
			border-color: var(--primary);
			background: var(--primary-extra-light);
		}

		.slot-btn.selected {
			background: var(--primary);
			color: white;
			border-color: var(--primary);
		}

		.slot-time {
			font-size: 13px;
			font-weight: 500;
		}
	</style>
	`;

	dialog.fields_dict.slot_display.$wrapper.html(html);
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

	frm.set_value("status", "Confirmed").then(() => {
		frm.save("Submit");
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
			frm.set_value("total_amount", selected_price.rate);
			frm.set_value("currency", selected_price.currency);
			d.hide();
		},
	});

	// Build price selection HTML
	let html = '<div class="price-selector">';

	prices.forEach((price) => {
		html += `
			<div class="price-card" data-price='${JSON.stringify(price)}' onclick="selectPrice(this)">
				<div class="price-name">${price.price_name}</div>
				<div class="price-amount">${format_currency(price.rate, price.currency)}</div>
				<div class="price-details">
					<small class="text-muted">Price List: ${price.price_list}</small>
				</div>
			</div>
		`;
	});

	html += "</div>";

	html += `
		<style>
			.price-selector {
				display: grid;
				grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
				gap: 15px;
				margin-top: 15px;
			}
			.price-card {
				border: 2px solid #d1d8dd;
				border-radius: 8px;
				padding: 15px;
				cursor: pointer;
				transition: all 0.3s;
				text-align: center;
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
			.price-name {
				font-weight: bold;
				font-size: 16px;
				margin-bottom: 8px;
			}
			.price-amount {
				font-size: 24px;
				color: #5e64ff;
				font-weight: bold;
				margin-bottom: 8px;
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
				add_video_conferencing: frm.doc.add_video_conferencing,
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
			frm.set_value("actual_end_time", values.actual_end_time)
				.then(() => {
					return frm.set_value("status", "Completed");
				})
				.then(() => {
					// Save the document
					return frm.save("Update");
				})
				.then(() => {
					frappe.dom.unfreeze();
					d.hide();

					frappe.show_alert({
						message: __(
							"Appointment completed successfully. Invoice will be created."
						),
						indicator: "green",
					});

					// Reload to show updated information including calculated actual_duration
					setTimeout(() => {
						frm.reload_doc();
					}, 1000);
				})
				.catch((error) => {
					frappe.dom.unfreeze();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to complete appointment. Please try again."),
						indicator: "red",
					});
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
