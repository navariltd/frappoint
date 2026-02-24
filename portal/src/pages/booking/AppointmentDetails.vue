<template>
	<div class="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
		<div class="max-w-4xl mx-auto">
			<!-- Breadcrumb -->
			<nav class="flex items-center text-sm text-gray-500 mb-6">
				<router-link
					:to="{ name: 'Bookings' }"
					class="hover:text-primary transition-colors"
					>My Appointments</router-link
				>
				<span class="mx-2">/</span>
				<span class="text-gray-900 font-medium">Booking #{{ appointment.name }}</span>
			</nav>

			<!-- Loading State -->
			<div v-if="appointment.loading" class="flex justify-center items-center py-20">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
			</div>

			<!-- Main Content -->
			<div v-else-if="appointment.doc" class="space-y-6">
				<!-- Appointment Card -->
				<div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
					<!-- Header -->
					<div class="p-6 sm:p-8 border-b border-gray-100">
						<div
							class="flex flex-col sm:flex-row sm:items-start justify-between gap-4"
						>
							<div>
								<h1 class="text-2xl font-bold text-gray-900 mb-1">
									{{ appointment.doc.appointment_type }}
								</h1>
								<p class="text-gray-500 text-sm">
									Appointment ID: #{{ appointment.doc.name }}
								</p>
							</div>
							<div
								class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
								:class="getStatusColor(appointment.doc.status)"
							>
								<div class="w-1.5 h-1.5 rounded-full bg-current mr-2"></div>
								{{ appointment.doc.status }}
							</div>
						</div>
					</div>

					<!-- Provider Section -->
					<div class="p-6 sm:p-8 bg-gray-50/50 border-b border-gray-100">
						<div class="flex flex-col sm:flex-row justify-between items-start gap-6">
							<div class="flex items-center gap-4">
								<img
									v-if="serviceTypeImage"
									:src="serviceTypeImage"
									class="w-16 h-16 rounded object-cover border-2 border-white shadow-sm"
									alt="Service"
								/>
								<img
									v-else
									:src="providerImage || defaultAvatar"
									class="w-16 h-16 rounded-full object-cover border-2 border-white shadow-sm"
									alt="Provider"
								/>
								<div>
									<div
										class="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1"
									>
										Service Provider
									</div>
									<h3 class="text-lg font-bold text-gray-900">
										{{ appointment.doc.appointment_provider }}
									</h3>
									<p class="text-primary text-sm font-medium">
										{{ providerDesignation || "Service Provider" }}
									</p>
									<!-- <div class="flex items-center gap-1 mt-1 text-sm text-gray-500">
										<span class="text-yellow-400">★</span>
										<span class="font-medium text-gray-900">4.9</span>
										<span>(120 reviews)</span>
									</div> -->
								</div>
							</div>

							<!-- Optional Provider Actions -->
							<!-- <div class="flex flex-col gap-2 w-full sm:w-auto">
								<button class="bg-primary/10 text-primary px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/20 transition-colors">
									Contact Provider
								</button>
							</div> -->
						</div>
					</div>

					<!-- Details Grid -->
					<div class="p-6 sm:p-8 grid grid-cols-1 md:grid-cols-3 gap-8">
						<!-- Date & Time -->
						<div class="flex gap-4">
							<div
								class="w-10 h-10 rounded-lg bg-teal-50 flex items-center justify-center flex-shrink-0 text-teal-600"
							>
								<FeatherIcon name="calendar" class="w-5 h-5" />
							</div>
							<div>
								<div
									class="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1"
								>
									Date & Time
								</div>
								<div class="font-semibold text-gray-900">
									{{ formatDate(appointment.doc.appointment_date) }}
								</div>
								<div class="text-sm text-gray-500 mt-0.5">
									{{ formatTime(appointment.doc.start_time) }} -
									{{ formatTime(appointment.doc.end_time) }} ({{
										appointment.doc.duration
									}}
									min)
								</div>
							</div>
						</div>

						<!-- Location -->
						<div class="flex gap-4">
							<div
								class="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0 text-blue-600"
							>
								<FeatherIcon name="map-pin" class="w-5 h-5" />
							</div>
							<div>
								<div
									class="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1"
								>
									Location
								</div>
								<div class="font-semibold text-gray-900">
									{{ appointment.doc.service_unit || "Main Clinic" }}
								</div>
								<div
									class="text-sm text-gray-500 mt-0.5"
									v-if="appointment.doc.service_unit"
								>
									Suite 402, Wellness Center
								</div>
								<!-- <button class="text-primary text-xs font-medium mt-1 hover:underline">
									View on Map
								</button> -->
							</div>
						</div>

						<!-- Payment -->
						<div class="flex gap-4">
							<div
								class="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center flex-shrink-0 text-purple-600"
							>
								<FeatherIcon name="credit-card" class="w-5 h-5" />
							</div>
							<div>
								<div
									class="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1"
								>
									Total Amount
								</div>
								<div class="font-semibold text-gray-900">
									{{
										formatCurrency(
											appointment.doc.total_amount,
											appointment.doc.currency
										)
									}}
								</div>
								<div
									class="text-sm text-green-600 font-medium mt-0.5"
									v-if="appointment.doc.payment_status === 'Paid'"
								>
									Paid via {{ appointment.doc.mode_of_payment || "Card" }}
								</div>
								<div class="text-sm text-amber-600 font-medium mt-0.5" v-else>
									Payment Pending
								</div>
							</div>
						</div>
					</div>

					<!-- Actions Footer -->
					<div
						class="p-6 sm:p-8 bg-gray-50 border-t border-gray-100 flex flex-col sm:flex-row gap-4"
						v-if="
							['Confirmed', 'Open', 'Rescheduled'].includes(appointment.doc.status)
						"
					>
						<button
							@click="handleAppointmentReschedule(appointment.doc.name)"
							class="flex-1 bg-teal-600 text-white font-medium py-2.5 px-4 rounded-lg hover:bg-teal-700 transition-colors flex items-center justify-center gap-2 shadow-sm"
						>
							<FeatherIcon name="calendar" class="w-4 h-4" />
							Reschedule Appointment
						</button>
						<button
							@click="handleAppointmentCancel(appointment.doc.name)"
							class="flex-1 bg-white text-red-600 border border-red-200 font-medium py-2.5 px-4 rounded-lg hover:bg-red-50 hover:border-red-300 transition-colors flex items-center justify-center gap-2 shadow-sm"
						>
							<FeatherIcon name="x-circle" class="w-4 h-4" />
							Cancel Appointment
						</button>
					</div>
				</div>

				<!-- Info Box -->
				<div class="bg-teal-50 rounded-xl p-6 border border-teal-100 flex gap-4">
					<div class="flex-shrink-0 mt-0.5">
						<div
							class="w-6 h-6 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center"
						>
							<FeatherIcon name="info" class="w-3 h-3" />
						</div>
					</div>
					<div>
						<h4 class="font-semibold text-teal-900 mb-1">Preparing for your visit</h4>
						<p class="text-sm text-teal-700 leading-relaxed">
							Please arrive 15 minutes early to fill out any necessary intake forms.
							We recommend wearing comfortable clothing. If you need to cancel,
							please do so at least 24 hours in advance.
						</p>
					</div>
				</div>
			</div>

			<!-- Not Found State -->
			<div v-else-if="!appointment.loading" class="text-center py-20">
				<div
					class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4"
				>
					<FeatherIcon name="alert-circle" class="w-8 h-8 text-gray-400" />
				</div>
				<h3 class="text-lg font-bold text-gray-900 mb-2">Appointment Not Found</h3>
				<p class="text-gray-500 mb-6">
					The appointment you are looking for does not exist or has been deleted.
				</p>
				<router-link
					:to="{ name: 'Bookings' }"
					class="text-primary font-medium hover:underline"
				>
					Go back to appointments
				</router-link>
			</div>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon, createDocumentResource, createResource } from "frappe-ui";
import { useRoute } from "vue-router";
import { computed, watch } from "vue";
import { handleAppointmentCancel, handleAppointmentReschedule } from "@/utils";
import defaultAvatar from "@/assets/images/profile-circle.svg";

const route = useRoute();

const appointmentId = route.params.id;

const appointment = createDocumentResource({
	doctype: "Service Appointment",
	name: appointmentId,
	auto: true,
	onSuccess(doc) {
		if (doc.appointment_provider) {
			providerResource.fetch();
		}
	},
});

// TODO: Don't fetch providers, slots avail providers
const providerResource = createResource({
	url: "frappe.client.get",
	makeParams() {
		return {
			doctype: "Service Provider",
			name: appointment.doc?.appointment_provider,
		};
	},
});

const serviceTypeResource = createResource({
	url: "frappe.client.get",
	makeParams() {
		return {
			doctype: "Service Type",
			name: appointment.doc?.appointment_type,
		};
	},
});

const serviceTypeImage = computed(() => serviceTypeResource.data?.image);
const providerImage = computed(() => providerResource.data?.image);
const providerDesignation = computed(() => providerResource.data?.designation); // Assuming designation field exists

watch(
	() => appointment.doc?.appointment_type,
	(type) => {
		if (type) serviceTypeResource.fetch();
	},
	{ immediate: true }
);

function formatDate(dateStr) {
	if (!dateStr) return "";
	const date = new Date(dateStr);
	return date.toLocaleDateString("en-US", {
		weekday: "long",
		year: "numeric",
		month: "short",
		day: "numeric",
	});
}

function formatTime(timeStr) {
	if (!timeStr) return "";
	const [hours, minutes] = timeStr.split(":");
	const hour = parseInt(hours);
	const ampm = hour >= 12 ? "PM" : "AM";
	const displayHour = hour % 12 || 12;
	return `${displayHour}:${minutes} ${ampm}`;
}

function formatCurrency(amount, currency) {
	return new Intl.NumberFormat("en-US", {
		style: "currency",
		currency: currency || "USD",
	}).format(amount || 0);
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
</script>
