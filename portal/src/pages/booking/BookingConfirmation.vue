<template>
	<!-- Loading / Guard state  -->
	<div v-if="!isReady" class="flex-grow flex items-center justify-center p-4 sm:p-6 lg:p-8">
		<div class="text-slate-500 text-sm animate-pulse">Preparing your booking…</div>
	</div>
	<div v-else class="flex-grow flex items-center justify-center p-4 sm:p-6 lg:p-8">
		<div class="max-w-3xl w-full flex flex-col gap-6">
			<!-- Success status  -->
			<div class="text-center space-y-4 py-6">
				<div
					class="inline-flex items-center justify-center size-20 rounded-full bg-primary text-white shadow-glow mb-2 animate-bounce-slow"
				>
					<FeatherIcon class="h-16 font-medium" name="check" color="white" />
				</div>
				<div class="space-y-1">
					<h1 class="font-extrabold text-3xl sm:text-4xl text-slate-900 tracking-tight">
						Booking Confirmed!
					</h1>
					<p class="text-lg text-slate-500">
						We've sent a confirmation email to
						<span class="text-slate-800 font-medium">{{ bookingResource.email }}</span>
					</p>
				</div>
			</div>

			<!-- Booking Details Card -->
			<div
				class="bg-white dark:bg-slate-800 rounded-xl shadow-soft overflow-hidden border border-slate-100 dark:border-slate-700"
			>
				<!-- Ticket Top: Service & Image -->
				<div
					class="flex flex-col md:flex-row border-b border-slate-100 dark:border-slate-700"
				>
					<div
						class="w-full md:w-1/3 h-48 md:h-auto bg-slate-100 relative group overflow-hidden"
					>
						<div
							class="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-105"
							data-alt="Relaxing spa massage therapy session"
							:style="{ backgroundImage: `url(${serviceTypeDetails.image})` }"
						></div>
						<div class="absolute inset-0 bg-primary/10 mix-blend-overlay"></div>
					</div>
					<div class="p-6 md:p-8 flex-1 flex flex-col justify-center">
						<div class="flex justify-between items-start mb-2">
							<span
								class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary uppercase tracking-wider"
							>
								Upcoming
							</span>
							<span class="text-slate-400 text-sm font-medium">{{
								bookingResource.name
							}}</span>
						</div>
						<h2 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">
							{{ bookingResource.appointment_type }}
						</h2>
						<div
							class="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-4"
						>
							<FeatherIcon class="h-4" name="clock" />
							<span class="text-sm font-medium"
								>{{ bookingResource.duration }} Minutes</span
							>
						</div>
						<div
							class="flex items-center gap-3 mt-auto pt-4 border-t border-slate-100 dark:border-slate-700"
						>
							<div class="size-10 rounded-full overflow-hidden bg-slate-200">
								<img
									class="w-full h-full object-cover"
									data-alt="Portrait of Dr. Sarah Mitchell therapist"
									src="https://lh3.googleusercontent.com/aida-public/AB6AXuBWo7iiTXJd1vaStPAc8abnmLCLYJz39ztLXNelQW7jqwxaR0iZPb2MXMI5oaGu-CpZqwiBPUt1_pDuKh4KN1mKCoutFfmDfTgVa5oIdbADpGurEG4HEpkLS55MaLUNzH_E_Pp0JRXMT-dXpBzm_2HfkmJtjyD791FtDkdE21t2fsGPYRNRqyoSRip6kjtjq2nAwZUHupf1G8h8TQje2RW9-86EujN1xxqlO2C1fohTdc4bC0veMr6gN536x08helvrwtsYYWk83QpT"
								/>
							</div>
							<div>
								<p
									class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide font-semibold"
								>
									Provider
								</p>
								<p class="text-sm font-bold text-slate-800 dark:text-slate-200">
									{{ bookingResource.appointment_provider }}
								</p>
							</div>
						</div>
					</div>
				</div>
				<!-- Ticket Bottom: Grid Details -->
				<div
					class="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-100 dark:divide-slate-700 bg-slate-50/50 dark:bg-slate-800/50"
				>
					<!-- Date & Time -->
					<div
						class="p-6 flex items-start gap-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
					>
						<div
							class="p-3 bg-white dark:bg-slate-700 rounded-lg shadow-sm text-primary border border-slate-100 dark:border-slate-600"
						>
							<FeatherIcon class="h-4" name="calendar" />
						</div>
						<div>
							<p
								class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1"
							>
								Date &amp; Time
							</p>
							<p class="text-base font-bold text-slate-900 dark:text-white">
								{{ formattedDate }}
							</p>
							<p class="text-sm text-slate-600 dark:text-slate-300">
								{{ formattedStartTime }} - {{ formattedEndTime }}
							</p>
							<button
								@click="downloadCalendarEvent"
								class="mt-2 text-xs text-primary font-medium cursor-pointer hover:underline inline-flex items-center gap-1"
							>
								<FeatherIcon class="h-3" name="download" />
								Add to Calendar
							</button>
						</div>
					</div>
					<!-- Location -->
					<div
						class="p-6 flex items-start gap-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors relative group"
					>
						<div
							class="p-3 bg-white dark:bg-slate-700 rounded-lg shadow-sm text-primary border border-slate-100 dark:border-slate-600"
						>
							<FeatherIcon class="h-4" name="map-pin" />
						</div>
						<div class="flex-1">
							<p
								class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1"
							>
								Location
							</p>
							<p class="text-base font-bold text-slate-900 dark:text-white">
								Coming Soon
							</p>
							<p class="text-sm text-slate-600 dark:text-slate-300">
								Street Coming Soon
							</p>
							<a
								class="mt-2 text-xs text-primary font-medium inline-flex items-center gap-1 hover:underline"
								href="#"
							>
								Get Directions <FeatherIcon class="h-4" name="arrow-right" />
							</a>
						</div>
					</div>
				</div>
			</div>

			<!-- Action Buttons -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
				<button
					@click="downloadCalendarEvent"
					class="flex items-center justify-center gap-2 h-14 rounded-xl bg-primary hover:bg-primary/90 text-white font-bold text-base shadow-lg shadow-primary/20 transition-all hover:scale-[1.01] active:scale-[0.98]"
				>
					<FeatherIcon class="h-4" name="download" />
					Add to Calendar
				</button>
				<button
					@click="navigateToAppointmentDetails"
					class="flex items-center justify-center gap-2 h-14 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 hover:border-primary/50 text-slate-700 dark:text-slate-200 font-bold text-base transition-all hover:bg-slate-50 dark:hover:bg-slate-700"
				>
					<FeatherIcon class="h-4" name="edit" />
					Manage Booking
				</button>
			</div>
			<div class="text-center pt-4">
				<router-link
					to="/"
					class="text-slate-500 dark:text-slate-400 hover:text-primary font-medium text-sm transition-colors inline-flex items-center gap-1 group"
				>
					<FeatherIcon class="h-4" name="arrow-left" />
					Back to Home
				</router-link>
			</div>
		</div>
	</div>
</template>

<script setup>
import { buildDate } from "@/utils";
import { FeatherIcon, createResource, createDocumentResource } from "frappe-ui";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createEvent } from "ics";

const route = useRoute();
const router = useRouter();
const bookingId = route.params.bookingId;

const serviceTypeDetailsResource = createResource({
	url: "frappoint.frappoint.api.service_type.get_service_type_details",
	cache: bookingId,
});

const bookingDocument = createDocumentResource({
	doctype: "Service Appointment",
	name: bookingId,
	onSuccess(doc) {
		serviceTypeDetailsResource.fetch({
			service_type: doc.appointment_type,
		});
	},
});

const serviceTypeDetails = computed(() => {
	return serviceTypeDetailsResource.data || null;
});

const bookingResource = computed(() => bookingDocument.doc || null);

const isReady = computed(() => {
	return !!(
		bookingResource.value &&
		serviceTypeDetails.value &&
		startDateTime.value &&
		endDateTime.value
	);
});

/**
 * Build Date objects from separate date + time fields
 */
const startDateTime = computed(() => {
	if (!bookingResource.value) return null;

	const { appointment_date, start_time } = bookingResource.value;
	if (!appointment_date || !start_time) return null;

	return buildDate(appointment_date, start_time);
});

const endDateTime = computed(() => {
	if (!bookingResource.value) return null;

	const { appointment_date, end_time } = bookingResource.value;
	if (!appointment_date || !end_time) return null;

	return buildDate(appointment_date, end_time);
});

/**
 * Formatted date: Friday, Oct 24
 */
const formattedDate = computed(() => {
	if (!startDateTime.value) return "";

	return new Intl.DateTimeFormat("en-US", {
		weekday: "long",
		month: "short",
		day: "numeric",
	}).format(startDateTime.value);
});

/**
 * Formatted start time: 12:00 PM
 */
const formattedStartTime = computed(() => {
	if (!startDateTime.value) return "";

	return new Intl.DateTimeFormat("en-US", {
		hour: "numeric",
		minute: "2-digit",
		hour12: true,
	}).format(startDateTime.value);
});

/**
 * Formatted end time: 12:30 PM
 */
const formattedEndTime = computed(() => {
	if (!endDateTime.value) return "";

	return new Intl.DateTimeFormat("en-US", {
		hour: "numeric",
		minute: "2-digit",
		hour12: true,
	}).format(endDateTime.value);
});

/**
 * Generate and download ICS calendar file
 */
function downloadCalendarEvent() {
	if (!startDateTime.value || !endDateTime.value || !bookingResource.value) return;

	const start = startDateTime.value;
	const end = endDateTime.value;

	const event = {
		start: [
			start.getFullYear(),
			start.getMonth() + 1,
			start.getDate(),
			start.getHours(),
			start.getMinutes(),
		],
		end: [
			end.getFullYear(),
			end.getMonth() + 1,
			end.getDate(),
			end.getHours(),
			end.getMinutes(),
		],
		title: bookingResource.value.appointment_type,
		description: `Appointment with ${bookingResource.value.appointment_provider}. Duration: ${bookingResource.value.duration} minutes. Booking ID: ${bookingResource.value.name}`,
		location: "Coming Soon",
		status: "CONFIRMED",
		url: window.location.href,
		organizer: {
			name: bookingResource.value.appointment_provider,
		},
		attendees: [
			{
				name: bookingResource.value.email,
				email: bookingResource.value.email,
			},
		],
	};

	createEvent(event, (error, value) => {
		if (error) {
			console.error("Error creating calendar event:", error);
			return;
		}

		// Create blob and download
		const blob = new Blob([value], { type: "text/calendar;charset=utf-8" });
		const link = document.createElement("a");
		link.href = URL.createObjectURL(blob);
		link.download = `appointment-${bookingResource.value.name}.ics`;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(link.href);
	});
}

/**
 * Navigate to appointment details page
 */
function navigateToAppointmentDetails() {
	router.push({
		name: "AppointmentDetails",
		params: { id: bookingId },
	});
}
</script>
