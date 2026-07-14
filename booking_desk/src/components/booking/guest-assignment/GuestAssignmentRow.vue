<template>
	<div
		class="rounded-lg border border-outline-variant bg-surface-container-lowest overflow-hidden"
	>
		<!-- Collapsible header -->
		<button
			type="button"
			class="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left hover:bg-surface-container/30 transition-colors"
			@click="isExpanded = !isExpanded"
		>
			<div class="flex items-center gap-2 min-w-0">
				<span
					class="material-symbols-outlined text-[16px] text-on-surface-variant shrink-0 transition-transform duration-200"
					:class="isExpanded ? '' : '-rotate-90'"
					>expand_more</span
				>
				<p class="text-[12px] font-semibold text-on-surface shrink-0">
					Guest {{ guest.sequence }}
				</p>
				<span v-if="guest.fullName" class="text-[11px] text-on-surface-variant truncate"
					>— {{ guest.fullName }}</span
				>
			</div>
			<span
				class="rounded-full px-2 py-0.5 text-[10px] font-semibold shrink-0"
				:class="
					guest.isComplete
						? 'bg-tertiary-container text-on-tertiary-container'
						: 'bg-secondary-container text-on-secondary-container'
				"
			>
				{{ guest.isComplete ? "Scheduled" : "Pending" }}
			</span>
		</button>

		<!-- Collapsible body -->
		<div v-show="isExpanded" class="px-3 pb-3 space-y-3 border-t border-outline-variant">
			<!-- 1. Assign Guest: inline fields -->
			<div class="space-y-2 pt-3">
				<div class="flex items-center justify-between">
					<p class="text-[11px] font-semibold uppercase tracking-wide text-on-surface">
						1. Assign Guest
					</p>
					<button
						v-if="guest.fullName"
						type="button"
						class="text-[11px] text-error hover:underline"
						@click.stop="onClear"
					>
						Clear
					</button>
				</div>

				<div class="grid grid-cols-3 gap-2">
					<div>
						<label class="block text-[10px] text-on-surface-variant mb-1">
							Full Name <span class="text-error">*</span>
						</label>
						<input
							:list="datalistId"
							type="text"
							class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary transition-colors"
							placeholder="Search or type name"
							v-model="localName"
							@change="onNameChange"
						/>
						<datalist :id="datalistId">
							<option v-for="c in customers" :key="c.id" :value="c.name" />
						</datalist>
					</div>
					<div>
						<label class="block text-[10px] text-on-surface-variant mb-1">Email</label>
						<input
							type="email"
							class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary transition-colors"
							placeholder="email@example.com"
							v-model="localEmail"
							@change="onDetailChange"
						/>
					</div>
					<div>
						<label class="block text-[10px] text-on-surface-variant mb-1">Phone</label>
						<input
							type="tel"
							class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary transition-colors"
							placeholder="+254 700 000 000"
							v-model="localPhone"
							@change="onDetailChange"
						/>
					</div>
				</div>

				<!-- Provider Gender Preference (Optional) -->
				<div class="grid grid-cols-3 gap-2">
					<div>
						<label class="block text-[10px] text-on-surface-variant mb-1">
							Provider Gender (Optional)
						</label>
						<select
							v-model="localProviderGender"
							class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary transition-colors"
							@change="onGenderChange"
						>
							<option value="">— No preference</option>
							<option
								v-for="gender in availableGenders"
								:key="gender.name"
								:value="gender.name"
							>
								{{ gender.label }}
							</option>
						</select>
					</div>
					<div>
						<label class="block text-[10px] text-on-surface-variant mb-1">
							Provider (Optional)
						</label>
						<select
							v-model="localProviderPreference"
							class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary transition-colors"
							@change="onProviderPreferenceChange"
						>
							<option value="">Any available provider</option>
							<option
								v-for="provider in filteredProviderOptions"
								:key="provider.id"
								:value="provider.id"
							>
								{{ provider.name }}
							</option>
						</select>
					</div>
				</div>

				<div>
					<label class="block text-[10px] text-on-surface-variant mb-1">Notes</label>
					<textarea
						v-model="localNotes"
						rows="2"
						class="w-full resize-none rounded-lg border border-outline-variant bg-surface px-3 py-2 text-[12px] outline-none focus:border-primary transition-colors"
						placeholder="Appointment notes"
						@change="onNotesChange"
					/>
				</div>

				<p v-if="error" class="text-[11px] text-error">{{ error }}</p>
			</div>

			<DateSelectionSection
				:dates="guest.availableDates"
				:selectedDate="guest.date"
				:isLoading="isLoadingDates"
				:error="!guest.fullName ? '' : error"
				@load-dates="$emit('load-dates')"
				@select-date="$emit('select-date', $event)"
			/>

			<SlotSelectionSection
				:slots="guest.availableSlots"
				:selectedSlotId="guest.slot?.id || ''"
				:isLoading="isLoadingSlots"
				:isReserving="isReservingSlot"
				:reservingSlotId="reservingSlotId"
				:error="!guest.date ? '' : error"
				@select-slot="$emit('select-slot', $event)"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import DateSelectionSection from "./DateSelectionSection.vue";
import SlotSelectionSection from "./SlotSelectionSection.vue";
import { fetchAvailableGenders } from "@/api/provider.api";

const emit = defineEmits([
	"select-customer",
	"quick-create",
	"provider-preference",
	"notes-change",
	"clear-guest",
	"load-dates",
	"select-date",
	"select-slot",
]);

const props = defineProps({
	guest: {
		type: Object,
		required: true,
	},
	quantity: {
		type: Number,
		default: 1,
	},
	customers: {
		type: Array,
		default: () => [],
	},
	providerOptions: {
		type: Array,
		default: () => [],
	},
	isLoadingDates: {
		type: Boolean,
		default: false,
	},
	isLoadingSlots: {
		type: Boolean,
		default: false,
	},
	isReservingSlot: {
		type: Boolean,
		default: false,
	},
	reservingSlotId: {
		type: String,
		default: "",
	},
	error: {
		type: String,
		default: "",
	},
});

const isExpanded = ref(!props.guest.isComplete);

const localName = ref(props.guest.fullName || "");
const localEmail = ref(props.guest.email || "");
const localPhone = ref(props.guest.mobileNo || "");
const localProviderGender = ref(props.guest.providerGender || "");
const localProviderPreference = ref(props.guest.providerPreference || "");
const localNotes = ref(props.guest.notes || "");

const availableGenders = ref([]);

// Fetch available genders on mount
onMounted(async () => {
	try {
		availableGenders.value = await fetchAvailableGenders();
	} catch (error) {
		console.error("Failed to fetch genders:", error);
	}
});

// Sync from store when props change (e.g., after select-customer resolves)
watch(
	() => props.guest.fullName,
	(v) => {
		localName.value = v || "";
	}
);
watch(
	() => props.guest.email,
	(v) => {
		localEmail.value = v || "";
	}
);
watch(
	() => props.guest.mobileNo,
	(v) => {
		localPhone.value = v || "";
	}
);
watch(
	() => props.guest.providerGender,
	(v) => {
		localProviderGender.value = v || "";
	}
);
watch(
	() => props.guest.providerPreference,
	(v) => {
		localProviderPreference.value = v || "";
	}
);
watch(
	() => props.guest.notes,
	(v) => {
		localNotes.value = v || "";
	}
);

const datalistId = computed(() => `dl-${props.guest.guestKey.replace(/[^a-z0-9]/gi, "-")}`);
const filteredProviderOptions = computed(() => {
	const selectedGender = String(localProviderGender.value || "")
		.trim()
		.toLowerCase();
	if (!selectedGender) {
		return props.providerOptions;
	}
	return props.providerOptions.filter(
		(provider) =>
			String(provider.gender || "")
				.trim()
				.toLowerCase() === selectedGender
	);
});

const onNameChange = () => {
	const trimmed = localName.value.trim();
	if (!trimmed) return;
	const matched = props.customers.find((c) => c.name === trimmed);
	if (matched) {
		emit("select-customer", matched.id);
	} else {
		emit("quick-create", {
			fullName: trimmed,
			email: localEmail.value,
			mobileNo: localPhone.value,
			providerGender: localProviderGender.value,
			providerPreference: localProviderPreference.value,
		});
	}
};

const onDetailChange = () => {
	const trimmed = localName.value.trim();
	if (!trimmed) return;
	emit("quick-create", {
		fullName: trimmed,
		email: localEmail.value,
		mobileNo: localPhone.value,
		providerGender: localProviderGender.value,
		providerPreference: localProviderPreference.value,
	});
};

const onGenderChange = () => {
	const selectedProviderStillAvailable = filteredProviderOptions.value.some(
		(provider) => provider.id === localProviderPreference.value
	);
	if (localProviderPreference.value && !selectedProviderStillAvailable) {
		localProviderPreference.value = "";
		emit("provider-preference", "");
	}

	// Emit an event or you can handle this in the parent composable
	// For now, the value is stored in localProviderGender
	// The parent can access it when needed
	if (props.guest.fullName) {
		emit("quick-create", {
			fullName: localName.value,
			email: localEmail.value,
			mobileNo: localPhone.value,
			providerGender: localProviderGender.value,
			providerPreference: localProviderPreference.value,
		});
	}
};

const onProviderPreferenceChange = () => {
	emit("provider-preference", localProviderPreference.value);
};

const onNotesChange = () => {
	emit("notes-change", localNotes.value);
};

const onClear = () => {
	localName.value = "";
	localEmail.value = "";
	localPhone.value = "";
	localProviderGender.value = "";
	localProviderPreference.value = "";
	emit("clear-guest");
};
</script>
