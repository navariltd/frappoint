<template>
	<div class="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
		<div class="max-w-4xl mx-auto">
			<nav class="flex items-center text-sm text-gray-500 mb-6">
				<router-link
					:to="{ name: 'Bookings' }"
					class="hover:text-primary transition-colors"
					>My Bookings</router-link
				>
				<span class="mx-2">/</span>
				<span class="text-gray-900 font-medium">Booking #{{ booking.doc.name }}</span>
			</nav>

			<div v-if="booking.loading" class="flex justify-center items-center py-20">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
			</div>

			<div v-else-if="booking.doc" class="space-y-6">
				<div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
					<div class="flex justify-between items-start gap-4">
						<div>
							<h1 class="text-2xl font-bold text-gray-900">
								Booking #{{ booking.doc.name }}
							</h1>
							<p class="text-sm text-gray-500">
								Customer: {{ booking.doc.full_name || booking.doc.customer }}
							</p>
							<p class="text-sm text-gray-500">
								Guests:
								{{ booking.doc.total_guests || booking.doc.items?.length || 1 }}
							</p>
						</div>
						<div class="text-right">
							<div
								:class="
									getStatusColor(booking.doc.status) +
									' inline-flex items-center px-3 py-1 rounded-full text-sm font-medium'
								"
							>
								<div class="w-1.5 h-1.5 rounded-full bg-current mr-2"></div>
								{{ booking.doc.status }}
							</div>
							<div class="mt-3 text-lg font-semibold">
								{{ formatCurrency(booking.doc.grand_total, booking.doc.currency) }}
							</div>
							<div class="text-sm text-gray-500">
								Outstanding:
								{{
									formatCurrency(
										booking.doc.outstanding_amount,
										booking.doc.currency
									)
								}}
							</div>
						</div>
					</div>

					<div class="mt-6 border-t border-primary/15 pt-5">
						<div class="mb-3 flex items-center justify-between">
							<h3 class="text-sm font-semibold text-primary">
								Service appointments
							</h3>
							<span
								class="rounded-full bg-primary-container/30 px-2.5 py-1 text-xs font-semibold text-on-primary-container"
							>
								{{ appointmentsList.length }}
							</span>
						</div>

						<div v-if="appointments.list.loading" class="space-y-3">
							<div
								class="h-16 animate-pulse rounded-xl bg-primary-container/20"
							></div>
							<div
								class="h-16 animate-pulse rounded-xl bg-primary-container/20"
							></div>
						</div>
						<p
							v-else-if="!appointmentsList.length"
							class="rounded-xl bg-primary-container/10 px-4 py-3 text-sm text-on-primary-container"
						>
							No service appointments are attached to this booking.
						</p>
						<div v-else class="space-y-3">
							<div
								v-for="appointment in appointmentsList"
								:key="appointment.name"
								class="rounded-xl border border-primary/15 bg-primary-container/10 px-4 py-3"
							>
								<div class="flex items-start justify-between gap-4">
									<div class="min-w-0">
										<p class="font-semibold text-gray-900">
											{{
												appointment.appointment_type ||
												"Service appointment"
											}}
										</p>
										<p class="mt-1 text-sm text-gray-600">
											{{ formatDate(appointment.appointment_date) }}
											<span v-if="formatTime(appointment.start_time)">
												· {{ formatTime(appointment.start_time) }}
												<span v-if="formatTime(appointment.end_time)"
													>– {{ formatTime(appointment.end_time) }}</span
												>
											</span>
										</p>
										<p
											v-if="appointmentProvider(appointment)"
											class="mt-1 text-xs text-gray-500"
										>
											Provider: {{ appointmentProvider(appointment) }}
										</p>
									</div>
									<span
										:class="appointmentStatusClass(appointment.status)"
										class="shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold"
									>
										{{ appointment.status || "Scheduled" }}
									</span>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div v-else-if="!booking.loading" class="text-center py-20">
				<div
					class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4"
				>
					<svg
						class="w-8 h-8 text-gray-400"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M13 16h-1v-4h-1m1-4h.01"
						/>
					</svg>
				</div>
				<h3 class="text-lg font-bold text-gray-900 mb-2">Booking Not Found</h3>
				<p class="text-gray-500 mb-6">
					The booking you are looking for does not exist or has been deleted.
				</p>
				<router-link
					:to="{ name: 'Bookings' }"
					class="text-primary font-medium hover:underline"
					>Go back to bookings</router-link
				>
			</div>
		</div>
	</div>
</template>

<script setup>
import { createDocumentResource, createListResource } from "frappe-ui";
import { useRoute } from "vue-router";
import { computed } from "vue";

const route = useRoute();
const bookingId = route.params.id;

const booking = createDocumentResource({
	doctype: "Service Booking",
	name: bookingId,
	auto: true,
});

const appointments = createListResource({
	doctype: "Service Appointment",
	fields: ["*"],
	filters: { booking_id: ["=", bookingId] },
	orderBy: "appointment_date asc, start_time asc",
	auto: true,
});

const appointmentsList = computed(() => appointments.data || []);

function formatDate(d) {
	if (!d) return "";
	const date = new Date(d);
	return date.toLocaleDateString("en-US", {
		weekday: "long",
		year: "numeric",
		month: "short",
		day: "numeric",
	});
}
function formatTime(t) {
	if (!t) return "";
	const [h, m] = t.split(":");
	const hh = parseInt(h);
	const ampm = hh >= 12 ? "PM" : "AM";
	const disp = hh % 12 || 12;
	return `${disp}:${m} ${ampm}`;
}
function formatCurrency(amount, currency) {
	try {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: currency || "USD",
		}).format(amount || 0);
	} catch (e) {
		return amount || 0;
	}
}
function getStatusColor(status) {
	const colors = {
		Confirmed: "bg-teal-100 text-teal-700",
		Open: "bg-blue-100 text-blue-700",
		Completed: "bg-gray-100 text-gray-700",
		Cancelled: "bg-red-100 text-red-700",
		Rescheduled: "bg-orange-100 text-orange-700",
	};
	return colors[status] || "bg-gray-100 text-gray-700";
}

function appointmentProvider(appointment) {
	return appointment.service_provider_name || appointment.appointment_provider || "";
}

function appointmentStatusClass(status) {
	if (["Cancelled", "No Show"].includes(status))
		return "bg-error-container text-on-error-container";
	if (["Completed", "Closed"].includes(status)) return "bg-gray-200 text-gray-700";
	return "bg-primary/15 text-primary";
}
</script>
