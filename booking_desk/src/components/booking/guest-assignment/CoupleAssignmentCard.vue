<template>
	<section
		class="rounded-xl border border-primary/30 bg-surface-container-lowest overflow-hidden"
	>
		<header
			class="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant bg-primary-container/25 px-4 py-3"
		>
			<div>
				<div class="flex items-center gap-2">
					<span class="material-symbols-outlined text-[18px] text-primary">group</span>
					<h2 class="text-[14px] font-semibold text-on-surface">Couple Booking</h2>
				</div>
				<p class="mt-1 text-[11px] text-on-surface-variant">
					Both appointments start together and are reserved atomically.
				</p>
			</div>
			<span
				class="rounded-full bg-primary px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-on-primary"
			>
				Linked pair
			</span>
		</header>

		<div v-if="pairs.length !== 2" class="p-4 text-[12px] text-error">
			A couple booking needs exactly two selected services. Return to Services and choose a
			service for each guest.
		</div>

		<div v-else class="p-4 space-y-5">
			<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
				<section
					v-for="(pair, index) in pairs"
					:key="pair.guest.guestKey"
					class="rounded-xl border border-outline-variant bg-surface-container-low p-3 space-y-3"
				>
					<div class="flex items-center justify-between gap-2">
						<div>
							<p class="text-[12px] font-semibold text-on-surface">
								Guest {{ index + 1 }}
							</p>
							<p class="text-[10px] uppercase tracking-wide text-on-surface-variant">
								{{ index === 0 ? "Primary appointment" : "Linked appointment" }}
							</p>
						</div>
						<span
							v-if="pair.guest.isComplete"
							class="rounded-full bg-tertiary-container px-2 py-1 text-[10px] font-semibold text-on-tertiary-container"
						>
							Scheduled
						</span>
					</div>

					<div>
						<label class="block text-[10px] text-on-surface-variant mb-1">
							Service <span class="text-error">*</span>
						</label>
						<select
							:value="pair.service.serviceKey"
							disabled
							title="Service pairing is selected before the draft booking is created"
							class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] text-on-surface-variant disabled:cursor-not-allowed"
						>
							<option
								v-for="service in serviceOptions"
								:key="service.serviceKey"
								:value="service.serviceKey"
							>
								{{ service.serviceName }} · {{ service.duration }} min
							</option>
						</select>
					</div>

					<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
						<div class="sm:col-span-2">
							<label class="block text-[10px] text-on-surface-variant mb-1">
								Full Name <span class="text-error">*</span>
							</label>
							<input
								:list="`couple-customers-${index}`"
								type="text"
								:disabled="isReserving"
								:value="pair.guest.fullName"
								placeholder="Search or type guest name"
								class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary"
								@change="onNameChange(pair, $event.target.value)"
							/>
							<datalist :id="`couple-customers-${index}`">
								<option
									v-for="customer in customers"
									:key="customer.id"
									:value="customer.name"
								/>
							</datalist>
						</div>
						<div>
							<label class="block text-[10px] text-on-surface-variant mb-1"
								>Email</label
							>
							<input
								type="email"
								:disabled="isReserving"
								:value="pair.guest.email"
								placeholder="email@example.com"
								class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary"
								@change="updateGuest(pair, { email: $event.target.value })"
							/>
						</div>
						<div>
							<label class="block text-[10px] text-on-surface-variant mb-1"
								>Phone</label
							>
							<input
								type="tel"
								:disabled="isReserving"
								:value="pair.guest.mobileNo"
								placeholder="+254 700 000 000"
								class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary"
								@change="updateGuest(pair, { mobileNo: $event.target.value })"
							/>
						</div>
					</div>

					<div>
						<label class="block text-[10px] text-on-surface-variant mb-1">
							Preferred Provider (Optional)
						</label>
						<select
							:value="pair.guest.providerPreference"
							:disabled="isReserving"
							class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary"
							@change="
								$emit(
									'provider-preference',
									pair.service.serviceKey,
									pair.guest.guestKey,
									$event.target.value
								)
							"
						>
							<option value="">Auto-assign an available provider</option>
							<option
								v-for="provider in pair.service.providerOptions || []"
								:key="provider.id"
								:value="provider.id"
							>
								{{ provider.name }}
							</option>
						</select>
					</div>

					<div>
						<label class="block text-[10px] text-on-surface-variant mb-1">Notes</label>
						<textarea
							:value="pair.guest.notes"
							:disabled="isReserving"
							rows="2"
							placeholder="Appointment notes"
							class="w-full resize-none rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary"
							@change="
								$emit(
									'notes-change',
									pair.service.serviceKey,
									pair.guest.guestKey,
									$event.target.value
								)
							"
						/>
					</div>
				</section>
			</div>

			<div class="space-y-2 border-t border-outline-variant pt-4">
				<div class="flex items-center justify-between gap-3">
					<div>
						<p
							class="text-[11px] font-semibold uppercase tracking-wide text-on-surface"
						>
							Select a shared date
						</p>
						<p class="text-[11px] text-on-surface-variant">
							Only dates with simultaneous provider capacity are shown.
						</p>
					</div>
					<button
						type="button"
						:disabled="isReserving || isLoadingDates || isLoadingSlots"
						class="text-[11px] font-semibold text-primary"
						@click="$emit('load-dates')"
					>
						{{ isLoadingDates ? "Searching..." : "Refresh availability" }}
					</button>
				</div>
				<p
					v-if="isLoadingDates && !dates.length"
					class="text-[11px] text-on-surface-variant"
				>
					Finding dates for both providers...
				</p>
				<div v-else-if="dates.length" class="flex flex-wrap gap-2">
					<button
						v-for="dateRow in dates"
						:key="dateRow.date"
						type="button"
						:disabled="isReserving || isLoadingSlots"
						class="rounded-full border px-3 py-1.5 text-[11px]"
						:class="
							selectedDate === dateRow.date
								? 'border-primary bg-primary text-on-primary'
								: 'border-outline-variant bg-surface hover:bg-surface-container'
						"
						@click="$emit('select-date', dateRow.date)"
					>
						{{ dateRow.label }}
					</button>
				</div>
				<p v-else class="text-[11px] text-on-surface-variant">
					Enter both guests, then refresh to find simultaneous availability.
				</p>
			</div>

			<div class="space-y-2 border-t border-outline-variant pt-4">
				<div>
					<p class="text-[11px] font-semibold uppercase tracking-wide text-on-surface">
						Select a couple slot
					</p>
					<p class="text-[11px] text-on-surface-variant">
						Each guest can have a different provider, duration and end time.
					</p>
				</div>
				<p v-if="isLoadingSlots" class="text-[11px] text-on-surface-variant">
					Checking both provider counters...
				</p>
				<p v-else-if="error" class="text-[11px] text-error">{{ error }}</p>
				<div
					v-else-if="selectedCandidateId && !slots.length"
					class="rounded-xl border border-tertiary/30 bg-tertiary-container/30 p-3"
				>
					<p class="text-[11px] font-semibold text-on-surface">Reserved couple slot</p>
					<p
						v-for="(pair, index) in pairs"
						:key="`reserved-${pair.guest.guestKey}`"
						class="mt-1 text-[11px] text-on-surface-variant"
					>
						Guest {{ index + 1 }}: {{ formatTime(pair.guest.slot?.startTime) }}–{{
							formatTime(pair.guest.slot?.endTime)
						}}
						· {{ pair.guest.slot?.providerSummary }}
					</p>
				</div>
				<p
					v-else-if="selectedDate && !slots.length"
					class="text-[11px] text-on-surface-variant"
				>
					No simultaneous slots are available on this date.
				</p>
				<div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-2">
					<button
						v-for="slot in slots"
						:key="slot.id"
						type="button"
						class="rounded-xl border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-70"
						:class="
							selectedCandidateId === slot.id || reservingSlotId === slot.id
								? 'border-primary bg-primary text-on-primary'
								: 'border-outline-variant bg-surface hover:bg-surface-container'
						"
						:disabled="isReserving || !canReserve"
						@click="$emit('select-slot', slot.id)"
					>
						<div class="flex items-start justify-between gap-3">
							<div>
								<p class="text-[12px] font-semibold">
									Starts {{ formatTime(slot.startTime) }}
								</p>
								<p class="mt-1 text-[11px] opacity-85">
									Guest 1: {{ formatTime(slot.guest1.startTime) }}–{{
										formatTime(slot.guest1.endTime)
									}}
									·
									{{ slot.guest1.providerName }}
								</p>
								<p class="text-[11px] opacity-85">
									Guest 2: {{ formatTime(slot.guest2.startTime) }}–{{
										formatTime(slot.guest2.endTime)
									}}
									·
									{{ slot.guest2.providerName }}
								</p>
							</div>
							<span
								v-if="reservingSlotId === slot.id"
								class="material-symbols-outlined text-[17px] animate-spin"
							>
								progress_activity
							</span>
						</div>
					</button>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	pairs: { type: Array, default: () => [] },
	customers: { type: Array, default: () => [] },
	dates: { type: Array, default: () => [] },
	slots: { type: Array, default: () => [] },
	selectedDate: { type: String, default: "" },
	isLoadingDates: { type: Boolean, default: false },
	isLoadingSlots: { type: Boolean, default: false },
	isReserving: { type: Boolean, default: false },
	reservingSlotId: { type: String, default: "" },
	error: { type: String, default: "" },
});

const emit = defineEmits([
	"select-customer",
	"quick-create",
	"provider-preference",
	"notes-change",
	"load-dates",
	"select-date",
	"select-slot",
]);

const serviceOptions = computed(() => {
	const unique = new Map();
	props.pairs.forEach(({ service }) => unique.set(service.serviceKey, service));
	return Array.from(unique.values());
});

const selectedCandidateId = computed(() => props.pairs[0]?.guest.slot?.candidateId || "");
const canReserve = computed(
	() => props.pairs.length === 2 && props.pairs.every((pair) => pair.guest.fullName)
);

const formatTime = (value) => {
	const parts = String(value || "").split(":");
	return parts.length >= 2 ? `${parts[0]}:${parts[1]}` : String(value || "");
};

const updateGuest = (pair, overrides = {}) => {
	emit("quick-create", pair.service.serviceKey, pair.guest.guestKey, {
		fullName: overrides.fullName ?? pair.guest.fullName,
		email: overrides.email ?? pair.guest.email,
		mobileNo: overrides.mobileNo ?? pair.guest.mobileNo,
		providerGender: pair.guest.providerGender || "",
		providerPreference: pair.guest.providerPreference || "",
	});
};

const onNameChange = (pair, value) => {
	const fullName = String(value || "").trim();
	if (!fullName) return;
	const customer = props.customers.find((item) => item.name === fullName);
	if (customer) {
		emit("select-customer", pair.service.serviceKey, pair.guest.guestKey, customer.id);
		return;
	}
	updateGuest(pair, { fullName });
};
</script>
