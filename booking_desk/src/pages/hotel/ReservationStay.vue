<template>
	<div :class="embedded ? 'space-y-5' : 'px-6 py-5 space-y-5 max-w-[1600px]'">
		<div class="flex gap-4 text-[12px] font-semibold">
			<RouterLink v-if="!embedded" :to="{ name: 'FrontDeskToday' }" class="text-primary"
				>← Front Desk</RouterLink
			>
			<RouterLink
				v-if="stay"
				:to="{ name: 'HotelBooking', params: { bookingId: stay.hotel_booking } }"
				class="text-primary"
				>Booking {{ stay.hotel_booking }}</RouterLink
			>
		</div>

		<p v-if="loading && !details" class="text-[13px] text-on-surface-variant">Loading…</p>
		<p v-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
			{{ error }}
		</p>
		<ActionBanner
			:banner="banner"
			:busy="busy"
			@confirm="confirmBanner"
			@cancel="cancelBanner"
		/>

		<template v-if="details">
			<header class="flex flex-wrap items-start justify-between gap-3">
				<div>
					<div class="flex items-center gap-3">
						<h1 class="text-[22px] font-semibold text-on-surface">
							{{ stay.lead_guest_name }}
						</h1>
						<HotelStatusBadge :status="stay.status" />
					</div>
					<p class="text-[13px] text-on-surface-variant">
						{{ stay.name }} · {{ stay.room_type_name }} · {{ stay.rate_plan_name }} ·
						{{ formatNight(stay.arrival_date) }} →
						{{ formatNight(stay.departure_date) }} ({{ stay.nights }} night{{
							stay.nights === 1 ? "" : "s"
						}})
					</p>
				</div>
				<div class="flex gap-2">
					<button
						v-if="actions.can_change_dates && !dates.open"
						type="button"
						class="rounded-lg border border-outline-variant px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="busy"
						@click="openDates"
					>
						Change dates
					</button>
					<button
						v-if="actions.can_check_in"
						type="button"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="busy"
						@click="startCheckIn"
					>
						Check in
					</button>
					<button
						v-if="actions.can_check_out"
						type="button"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="busy"
						@click="checkOut"
					>
						Check out
					</button>
				</div>
			</header>

			<!-- What still stands between this stay and check-in -->
			<section
				v-if="checkInReview && actions.can_check_in"
				class="rounded-xl border border-tertiary bg-tertiary-container/20 p-4 space-y-3"
				aria-live="polite"
			>
				<div class="flex items-start justify-between gap-3">
					<div>
						<h2 class="text-[15px] font-semibold">
							{{
								checkInBlockers.length ? "Before checking in" : "Ready to check in"
							}}
						</h2>
						<p class="text-[12px] text-on-surface-variant">
							{{
								checkInBlockers.length
									? "Sort these out, then check the stay in."
									: "Everything is in place."
							}}
						</p>
					</div>
					<button
						type="button"
						class="text-[12px] font-semibold text-on-surface-variant"
						@click="checkInReview = false"
					>
						Close
					</button>
				</div>

				<ul class="space-y-2 text-[13px]">
					<li
						v-for="blocker in checkInBlockers"
						:key="blocker.key"
						class="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-surface-container-lowest px-3 py-2"
					>
						<span class="flex items-center gap-2">
							<span class="material-symbols-outlined text-[18px] text-tertiary">
								{{ blocker.icon }}
							</span>
							<span>
								<b>{{ blocker.title }}</b>
								<span class="block text-[12px] text-on-surface-variant">
									{{ blocker.detail }}
								</span>
							</span>
						</span>
						<button
							v-if="blocker.guest && actions.can_edit_guests"
							type="button"
							class="rounded-lg border border-primary px-3 py-1 text-[12px] font-semibold text-primary disabled:opacity-50"
							:disabled="busy"
							@click="run(() => registerGuestApi(blocker.guest))"
						>
							Register
						</button>
					</li>
				</ul>

				<div class="flex flex-wrap gap-2">
					<button
						v-if="unregisteredAdults.length > 1 && actions.can_edit_guests"
						type="button"
						class="rounded-lg border border-primary px-4 py-2 text-[13px] font-semibold text-primary disabled:opacity-50"
						:disabled="busy"
						@click="registerAll"
					>
						Register all {{ unregisteredAdults.length }} guests
					</button>
					<button
						type="button"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="busy || checkInBlockers.length > 0"
						@click="checkInNow()"
					>
						Check in
					</button>
				</div>
				<form
					v-if="canOverrideRoom"
					class="flex flex-wrap items-end gap-2 border-t border-outline-variant pt-3"
					@submit.prevent="checkInNow(roomOverrideReason)"
				>
					<label class="min-w-[240px] flex-1 text-[12px] text-on-surface-variant">
						Check in anyway (manager): why can the guest have this room now?
						<input
							v-model="roomOverrideReason"
							required
							class="mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface"
							placeholder="For example: finishing while the guest has lunch"
						/>
					</label>
					<button
						type="submit"
						class="rounded-lg border border-error px-4 py-2 text-[13px] font-semibold text-error disabled:opacity-50"
						:disabled="busy || !roomOverrideReason.trim()"
					>
						Check in anyway
					</button>
				</form>
			</section>

			<p
				v-if="stay.restriction_override_reason"
				class="rounded-lg border border-tertiary bg-tertiary-container/30 px-4 py-2 text-[12px] text-on-surface"
			>
				Booked against {{ stay.overridden_restrictions }}, by
				{{ stay.restriction_override_by }}: {{ stay.restriction_override_reason }}
			</p>

			<!-- Extend or shorten (F13) -->
			<section
				v-if="dates.open"
				class="rounded-xl border border-primary bg-surface-container-lowest p-4 space-y-3"
				aria-label="Change dates"
			>
				<div class="flex flex-wrap items-end gap-3">
					<label class="text-[12px] text-on-surface-variant">
						Leaves on
						<input
							v-model="dates.departure"
							type="date"
							:min="minDeparture"
							class="mt-1 block rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
						/>
					</label>
					<p class="pb-2 text-[12px] text-on-surface-variant">
						Now {{ formatNight(stay.departure_date) }} · arrives
						{{ formatNight(stay.arrival_date) }}
					</p>
				</div>
				<p v-if="dates.loading" class="text-[12px] text-on-surface-variant">Checking…</p>
				<template v-else-if="dates.preview">
					<p class="text-[13px] text-on-surface">
						<template v-if="dates.preview.extend">
							Adds <b>{{ dates.preview.nights }}</b> night{{
								dates.preview.nights === 1 ? "" : "s"
							}}
							for <b>{{ formatMoney(dates.preview.amount, stay.currency) }}</b
							>, at today's rates.
						</template>
						<template v-else>
							Gives back <b>{{ -dates.preview.nights }}</b> night{{
								dates.preview.nights === -1 ? "" : "s"
							}}
							({{ formatMoney(-dates.preview.amount, stay.currency) }}).
							<template v-if="Number(dates.preview.fee)">
								Leaving early charges a fee of
								<b>{{ formatMoney(dates.preview.fee, stay.currency) }}</b
								>.
							</template>
						</template>
					</p>
					<ul
						v-if="dates.preview.problems.length"
						class="space-y-1 text-[12px] text-error"
					>
						<li v-for="problem in dates.preview.problems" :key="problem">
							{{ problem }}
						</li>
					</ul>
					<label
						v-if="dates.preview.restrictions.length"
						class="block rounded-lg border border-tertiary bg-tertiary-container/30 p-3 text-[12px]"
					>
						<span class="font-semibold">The new dates break a restriction:</span>
						{{ dates.preview.restrictions.map((item) => item.reason).join(", ") }}.
						<template v-if="dates.preview.can_override">
							Give a reason to override it.
							<textarea
								v-model="dates.reason"
								rows="2"
								class="mt-1 w-full rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
							/>
						</template>
						<template v-else>
							Only a Revenue or Front Desk Manager can override it.
						</template>
					</label>
				</template>
				<div class="flex justify-end gap-2">
					<button
						type="button"
						class="rounded-lg border border-outline-variant px-3 py-2 text-[12px] font-semibold"
						@click="dates.open = false"
					>
						Cancel
					</button>
					<button
						type="button"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="!canApplyDates || busy"
						@click="applyDates"
					>
						{{ dates.preview?.extend ? "Extend stay" : "Shorten stay" }}
					</button>
				</div>
			</section>

			<div
				class="grid gap-5"
				:class="
					embedded
						? '2xl:grid-cols-[minmax(0,1fr)_340px]'
						: 'xl:grid-cols-[minmax(0,1fr)_380px]'
				"
			>
				<div class="min-w-0 space-y-5">
					<div class="grid md:grid-cols-2 gap-5">
						<!-- Room -->
						<section
							class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
						>
							<div class="flex items-center justify-between">
								<h2 class="text-[15px] font-semibold">Room</h2>
								<label
									v-if="stay.room && (actions.can_assign || actions.can_move)"
									class="flex items-center gap-2 text-[12px] text-on-surface-variant"
								>
									<input
										type="checkbox"
										:checked="stay.room_locked"
										:disabled="busy"
										@change="
											run(() =>
												setRoomLockApi(stay.name, $event.target.checked)
											)
										"
									/>
									Do not move
								</label>
							</div>
							<p class="text-[14px]">
								<template v-if="stay.room_number">
									Room <b>{{ stay.room_number }}</b> · {{ stay.room_condition }}
								</template>
								<span v-else class="text-on-surface-variant"
									>No room assigned yet.</span
								>
							</p>

							<div v-if="actions.can_assign || actions.can_move" class="space-y-2">
								<p class="text-[12px] font-semibold text-on-surface">
									{{
										actions.can_move
											? "Move to"
											: stay.room
											? "Change room"
											: "Assign a room"
									}}
								</p>
								<div class="flex flex-wrap gap-1.5">
									<button
										v-for="room in rooms"
										:key="room.name"
										type="button"
										class="rounded border px-2.5 py-1 text-[12px] disabled:opacity-40"
										:class="
											room.is_current
												? 'border-primary bg-primary text-on-primary'
												: room.ready
												? 'border-outline-variant'
												: 'border-tertiary text-on-tertiary-container'
										"
										:disabled="
											busy ||
											room.is_current ||
											!room.available ||
											(actions.can_move && !room.ready)
										"
										:title="
											room.unavailable_reason || room.housekeeping_condition
										"
										@click="pickRoom(room)"
									>
										{{ room.room_number }}
										<span class="text-[10px]">{{
											room.unavailable_reason || room.housekeeping_condition
										}}</span>
									</button>
								</div>
								<label
									v-if="actions.can_move"
									class="block text-[12px] text-on-surface-variant"
								>
									Move reason
									<select
										v-model="moveReason"
										class="mt-1 block w-full rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
									>
										<option
											v-for="reason in moveReasons"
											:key="reason"
											:value="reason"
										>
											{{ reason }}
										</option>
									</select>
								</label>
							</div>

							<div v-if="details.assignments.length">
								<p class="text-[12px] font-semibold text-on-surface">History</p>
								<ol class="mt-1 space-y-1 text-[12px] text-on-surface-variant">
									<li v-for="segment in details.assignments" :key="segment.name">
										Room {{ segment.room_number }} ·
										{{ formatTimestamp(segment.start_datetime) }} →
										{{ formatTimestamp(segment.end_datetime) }} ·
										{{ segment.status }}
										<span v-if="segment.move_reason">
											· moved: {{ segment.move_reason }}</span
										>
									</li>
								</ol>
							</div>
						</section>

						<!-- Guests -->
						<section
							class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
						>
							<h2 class="text-[15px] font-semibold">Guests</h2>
							<ul class="divide-y divide-outline-variant">
								<li
									v-for="guest in details.guests"
									:key="guest.name"
									class="flex flex-wrap items-center justify-between gap-2 py-2"
								>
									<span>
										<span class="text-[13px] font-semibold">{{
											guest.guest_name
										}}</span>
										<span class="block text-[11px] text-on-surface-variant">
											{{ guest.role }} · {{ guest.age_category }} ·
											{{ guest.status }}
											<span
												v-if="needsRegistration(guest)"
												class="ml-1 rounded-full bg-tertiary-container px-2 py-0.5 font-semibold text-on-tertiary-container"
											>
												Not registered
											</span>
										</span>
									</span>
									<span
										v-if="actions.can_edit_guests"
										class="flex gap-2 text-[12px] font-semibold"
									>
										<button
											v-if="
												['Expected'].includes(guest.status) &&
												guest.age_category === 'Adult'
											"
											type="button"
											class="text-primary"
											:disabled="busy"
											@click="run(() => registerGuestApi(guest.name))"
										>
											Register
										</button>
										<button
											v-if="
												actions.can_move &&
												['Expected', 'Registered'].includes(guest.status)
											"
											type="button"
											class="text-primary"
											:disabled="busy"
											@click="run(() => checkInGuestApi(guest.name))"
										>
											Check in
										</button>
										<button
											v-if="
												guest.role !== 'Primary' &&
												guest.age_category === 'Adult' &&
												isActive(guest)
											"
											type="button"
											class="text-on-surface-variant"
											:disabled="busy"
											@click="run(() => setPrimaryGuestApi(guest.name))"
										>
											Make primary
										</button>
										<button
											v-if="
												guest.role !== 'Primary' &&
												['Expected', 'Registered'].includes(guest.status)
											"
											type="button"
											class="text-error"
											:disabled="busy"
											@click="removeGuest(guest)"
										>
											Remove
										</button>
									</span>
								</li>
							</ul>
							<div
								v-if="actions.can_edit_guests"
								class="space-y-2 border-t border-outline-variant pt-3"
							>
								<p class="text-[12px] font-semibold">Add a guest</p>
								<GuestPicker v-model="newGuest" />
								<div v-if="newGuest" class="flex items-end gap-2">
									<select
										v-model="newGuestAge"
										class="rounded-lg border border-outline-variant px-3 py-2 text-[13px]"
									>
										<option>Adult</option>
										<option>Child</option>
										<option>Infant</option>
									</select>
									<button
										type="button"
										class="rounded-lg bg-primary text-on-primary px-3 py-2 text-[12px] font-semibold disabled:opacity-50"
										:disabled="busy"
										@click="addGuest"
									>
										Add to stay
									</button>
								</div>
							</div>
						</section>
					</div>

					<section
						v-if="details.folios.length"
						class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-2"
					>
						<div class="flex items-center justify-between">
							<h2 class="text-[15px] font-semibold">Folios</h2>
							<RouterLink
								v-if="actions.can_view_folios"
								:to="{ name: 'HotelFolios', params: { stayId: stay.name } }"
								class="text-[12px] font-semibold text-primary"
								>Open folios →</RouterLink
							>
						</div>
						<ul class="divide-y divide-outline-variant text-[13px]">
							<li
								v-for="folio in details.folios"
								:key="folio.name"
								class="flex items-center justify-between gap-3 py-2"
							>
								<span>
									<b>{{ folio.folio_label }}</b>
									<span class="text-on-surface-variant">
										· {{ folio.payee_name || "Payee not set" }}</span
									>
								</span>
								<span class="flex items-center gap-3">
									<HotelStatusBadge :status="folio.status" />
									<b>{{ formatMoney(folio.balance, folio.currency) }}</b>
								</span>
							</li>
						</ul>
						<p
							v-if="details.post_stay_until"
							class="text-[12px] text-on-surface-variant"
						>
							Late charges can post until {{ formatNight(details.post_stay_until) }}.
							Night audit then closes the folios that owe nothing.
						</p>
					</section>

					<!-- Deposit and policies (F12) -->
					<section
						v-if="details.deposit || details.policies?.length"
						class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
					>
						<div class="flex items-center justify-between">
							<h2 class="text-[15px] font-semibold">Deposit and policies</h2>
							<RouterLink
								v-if="details.deposit && depositOpen && actions.can_view_folios"
								:to="{ name: 'HotelFolios', params: { stayId: stay.name } }"
								class="text-[12px] font-semibold text-primary"
								>Take the deposit →</RouterLink
							>
						</div>
						<div
							v-if="details.deposit"
							class="flex flex-wrap items-center gap-3 text-[13px]"
						>
							<HotelStatusBadge :status="details.deposit.status" />
							<span>
								{{ formatMoney(details.deposit.required_amount, stay.currency) }}
								required
								<template v-if="details.deposit.policy_name">
									({{ details.deposit.policy_name }})</template
								>
								· {{ formatMoney(details.deposit.held, stay.currency) }} held
								<template v-if="Number(details.deposit.refunded)">
									·
									{{ formatMoney(details.deposit.refunded, stay.currency) }}
									refunded
								</template>
							</span>
							<span v-if="depositOpen" class="text-on-tertiary-container">
								{{ formatMoney(details.deposit.outstanding, stay.currency) }} due
								by
								{{ formatNight(details.deposit.due_date) }}
								<template v-if="details.deposit.release_if_unpaid">
									· the stay is released if unpaid</template
								>
							</span>
							<button
								v-if="depositOpen && actions.can_waive_deposit"
								type="button"
								class="rounded border border-outline-variant px-2.5 py-1 text-[12px] font-semibold disabled:opacity-50"
								:disabled="busy"
								@click="waiveDeposit"
							>
								Waive
							</button>
						</div>
						<p
							v-if="details.deposit?.reason"
							class="text-[12px] text-on-surface-variant"
						>
							{{ details.deposit.reason }}
						</p>
						<ul
							v-if="details.policies?.length"
							class="text-[12px] text-on-surface-variant space-y-1"
						>
							<li v-for="policy in details.policies" :key="policy.event">
								<b class="text-on-surface">{{ policy.event }}:</b>
								{{ policy.policy_name }}
								<template v-if="policy.fee_type && policy.fee_type !== 'None'">
									· {{ describeFee(policy) }}</template
								>
								<template v-if="policy.guest_text">
									· {{ policy.guest_text }}</template
								>
							</li>
						</ul>
					</section>
				</div>

				<!-- Prices and history beside the stay, where there is room -->
				<aside class="space-y-5 min-w-0">
					<section
						class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
					>
						<h2 class="text-[15px] font-semibold">Nightly prices</h2>
						<table class="mt-2 w-full text-[12px]">
							<tbody>
								<tr
									v-for="night in details.nights"
									:key="night.night_date"
									class="border-b border-outline-variant"
								>
									<td class="py-1.5">{{ formatNight(night.night_date) }}</td>
									<td class="py-1.5 text-right">
										{{ formatMoney(night.total, stay.currency) }}
									</td>
									<td class="py-1.5 pl-3 text-right text-on-surface-variant">
										{{ night.posting_state }}
									</td>
								</tr>
							</tbody>
						</table>
						<p class="mt-2 text-right text-[13px] font-semibold">
							{{ formatMoney(stay.total_amount, stay.currency) }}
						</p>
					</section>

					<section
						v-if="details.services?.length"
						class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
					>
						<h2 class="text-[15px] font-semibold">Services</h2>
						<p class="text-[12px] text-on-surface-variant">
							Spa and salon appointments charged to this stay. They post to the
							guest's folio when completed.
						</p>
						<ul class="mt-2 divide-y divide-outline-variant text-[12px]">
							<li v-for="row in details.services" :key="row.name" class="py-1.5">
								<div class="flex items-center justify-between gap-2">
									<span class="min-w-0">
										<b>{{ row.service_type }}</b>
										<span class="text-on-surface-variant">
											· {{ row.guest_name }}</span
										>
									</span>
									<span class="whitespace-nowrap">
										{{
											formatMoney(row.amount, row.currency || stay.currency)
										}}
									</span>
								</div>
								<div class="text-on-surface-variant">
									{{ formatNight(row.appointment_date) }}
									<template v-if="row.start_time">
										· {{ String(row.start_time).slice(0, 5) }}</template
									>
									· {{ row.status }}
									<template v-if="row.fee_amount">
										· {{ row.fee_waived ? "fee waived" : "fee" }}
										{{
											formatMoney(
												row.fee_amount,
												row.currency || stay.currency
											)
										}}
									</template>
								</div>
								<div v-if="row.posting_error" class="text-error">
									{{ row.posting_error }}
								</div>
							</li>
						</ul>
					</section>

					<section
						class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
					>
						<h2 class="text-[15px] font-semibold">History</h2>
						<ol class="mt-2 max-h-[420px] space-y-1.5 overflow-y-auto text-[12px]">
							<li v-for="(event, index) in details.events" :key="index">
								<span class="text-on-surface-variant">{{
									formatTimestamp(event.timestamp)
								}}</span>
								· <b>{{ event.event_type }}</b>
								<span v-if="event.to_status"> → {{ event.to_status }}</span>
								<span v-if="event.reason" class="text-on-surface-variant">
									· {{ event.reason }}</span
								>
								<span class="text-on-surface-variant"> · {{ event.user }}</span>
							</li>
						</ol>
					</section>
				</aside>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
	addStayGuestApi,
	assignRoomApi,
	checkInApi,
	checkInGuestApi,
	changeDepartureApi,
	checkOutApi,
	departEarlyApi,
	fetchAssignableRoomsApi,
	fetchMoveReasonsApi,
	fetchStayApi,
	hotelErrorMessage,
	moveRoomApi,
	previewDepartureChangeApi,
	registerGuestApi,
	removeStayGuestApi,
	setPrimaryGuestApi,
	setRoomLockApi,
	waiveDepositApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import GuestPicker from "@/components/hotel/GuestPicker.vue";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { addDays, formatMoney, formatNight } from "@/utils/hotelFormat";

// `embedded`: shown beside the Front Desk list, without its own margins. `stayId` then names the
// stay; on its own page the route does.
const props = defineProps({
	embedded: { type: Boolean, default: false },
	stayId: { type: String, default: null },
});
// After a command changed the stay, so the page around it can refresh its list.
const emit = defineEmits(["changed"]);

const route = useRoute();
const currentStayId = computed(() => props.stayId || route.params.stayId);
const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const details = ref(null);
const rooms = ref([]);
const moveReasons = ref([]);
const moveReason = ref("");
const newGuest = ref(null);
const newGuestAge = ref("Adult");
const loading = ref(false);
const busy = ref(false);
const error = ref("");

const stay = computed(() => details.value?.stay);
const actions = computed(() => details.value?.actions || {});

// Check-in readiness: the same rules the server applies, shown before anyone presses the button.
const checkInReview = ref(false);
const roomOverrideReason = ref("");

function needsRegistration(guest) {
	return (
		guest.age_category === "Adult" &&
		!guest.registration_complete &&
		["Expected", "Registered"].includes(guest.status)
	);
}

const unregisteredAdults = computed(() => (details.value?.guests || []).filter(needsRegistration));

const checkInBlockers = computed(() => {
	const blockers = [];
	if (!stay.value?.room_number) {
		blockers.push({
			key: "room",
			icon: "bed",
			title: "No room assigned",
			detail: "Pick a room in the Room section.",
		});
	} else if (!stay.value.room_ready) {
		blockers.push({
			key: "condition",
			icon: "cleaning_services",
			title: `Room ${stay.value.room_number} is ${stay.value.room_condition || "not ready"}`,
			detail: `Housekeeping must release it as ${
				stay.value.room_ready_text || "Clean or Inspected"
			}. Ask them, or move the guest.`,
			overridable: true,
		});
	}
	unregisteredAdults.value.forEach((guest) =>
		blockers.push({
			key: guest.name,
			icon: "badge",
			title: `${guest.guest_name} isn't registered`,
			detail: "Every adult is registered before check-in. Check their details and register them.",
			guest: guest.name,
		})
	);
	return blockers;
});

function startCheckIn() {
	if (checkInBlockers.value.length) {
		checkInReview.value = true;
		return;
	}
	checkInNow();
}

// Only the room stands in the way, and a manager may put the guest in it anyway.
const canOverrideRoom = computed(
	() =>
		actions.value.can_override_room &&
		checkInBlockers.value.length > 0 &&
		checkInBlockers.value.every((blocker) => blocker.overridable)
);

async function checkInNow(overrideReason = null) {
	await run(() => checkInApi(stay.value.name, null, overrideReason));
	if (!error.value) {
		checkInReview.value = false;
		roomOverrideReason.value = "";
	}
}

async function registerAll() {
	for (const guest of unregisteredAdults.value.slice()) {
		await run(() => registerGuestApi(guest.name));
		if (error.value) return;
	}
}

function isActive(guest) {
	return ["Expected", "Registered", "Checked In"].includes(guest.status);
}

function formatTimestamp(value) {
	if (!value) return "";
	const date = new Date(String(value).replace(" ", "T"));
	return date.toLocaleString(undefined, {
		day: "numeric",
		month: "short",
		hour: "2-digit",
		minute: "2-digit",
	});
}

async function loadRooms() {
	rooms.value =
		actions.value.can_assign || actions.value.can_move
			? (await fetchAssignableRoomsApi(stay.value.name)) || []
			: [];
}

async function load() {
	loading.value = true;
	error.value = "";
	try {
		details.value = await fetchStayApi(currentStayId.value);
		await loadRooms();
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

async function run(command) {
	busy.value = true;
	error.value = "";
	try {
		details.value = await command();
		await loadRooms();
		emit("changed");
	} catch (e) {
		const message = hotelErrorMessage(e);
		// Reload first: loading clears the error, and the message must stay on screen.
		await load();
		error.value = message;
	} finally {
		busy.value = false;
	}
}

async function pickRoom(room) {
	if (actions.value.can_move) {
		if (!moveReason.value) {
			error.value = "Choose a move reason first.";
			return;
		}
		const answer = await ask({
			title: `Move ${stay.value.lead_guest_name} to room ${room.room_number} now?`,
			message: `Reason: ${moveReason.value}. Room ${stay.value.room_number} stays in the stay's history.`,
			confirmLabel: `Move to ${room.room_number}`,
		});
		if (answer) run(() => moveRoomApi(stay.value.name, room.name, moveReason.value));
	} else {
		run(() => assignRoomApi(stay.value.name, room.name));
	}
}

// Extend or shorten (F13): pick a departure, see what changes, then apply.
const dates = reactive({
	open: false,
	departure: "",
	preview: null,
	loading: false,
	reason: "",
});
let previewTimer = null;
const minDeparture = computed(() => (stay.value ? addDays(stay.value.arrival_date, 1) : ""));
const canApplyDates = computed(
	() =>
		dates.preview &&
		!dates.loading &&
		!dates.preview.problems.length &&
		(!dates.preview.restrictions.length || (dates.preview.can_override && dates.reason.trim()))
);

function openDates() {
	Object.assign(dates, {
		open: true,
		departure: stay.value.departure_date,
		preview: null,
		reason: "",
	});
}

watch(
	() => dates.departure,
	(value) => {
		clearTimeout(previewTimer);
		dates.preview = null;
		if (!dates.open || !value || value === stay.value?.departure_date) return;
		dates.loading = true;
		previewTimer = setTimeout(async () => {
			try {
				dates.preview = await previewDepartureChangeApi(stay.value.name, value);
			} catch (e) {
				dates.preview = { problems: [hotelErrorMessage(e)], restrictions: [] };
			} finally {
				dates.loading = false;
			}
		}, 300);
	}
);

async function applyDates() {
	const reason = dates.preview.restrictions.length ? dates.reason.trim() : null;
	await run(() => changeDepartureApi(stay.value.name, dates.departure, reason));
	if (!error.value) dates.open = false;
}

const depositOpen = computed(() =>
	["Requested", "Partly Paid"].includes(details.value?.deposit?.status)
);

function describeFee(policy) {
	const value = Number(policy.fee_value || 0);
	const fee = {
		"First Night": "the first night",
		"Full Stay": "the full stay",
		"Percentage of Stay": `${value}% of the stay`,
		"Fixed Amount": formatMoney(value, stay.value.currency),
	}[policy.fee_type];
	if (policy.event === "Cancellation") {
		const hours = Number(policy.free_until_hours_before_arrival || 0);
		return hours
			? `free until ${hours} hours before arrival, then ${fee}`
			: `no free cancellation: ${fee}`;
	}
	if (policy.event === "Early Departure") return `${fee} of the nights given up`;
	return fee;
}

async function waiveDeposit() {
	const answer = await ask({
		title: `Waive the deposit for ${stay.value.lead_guest_name}?`,
		message: "The guest can check in without paying it.",
		reasonLabel: "Why is the deposit waived?",
		confirmLabel: "Waive deposit",
	});
	if (answer) {
		run(async () => {
			await waiveDepositApi(details.value.deposit.name, answer.reason);
			return fetchStayApi(stay.value.name);
		});
	}
}

async function checkOut() {
	const name = stay.value.lead_guest_name;
	const fee = Number(details.value.early_departure_fee || 0);
	if (actions.value.leaving_early && fee) {
		// Charge the fee first, so the guest can pay it before checking out.
		const answer = await ask({
			title: `${name} is leaving before ${formatNight(stay.value.departure_date)}`,
			message: `Leaving early charges a fee of ${formatMoney(
				fee,
				stay.value.currency
			)} and gives the remaining nights back. Take payment for it, then check out.`,
			confirmLabel: "Charge the fee",
		});
		if (answer) run(() => departEarlyApi(stay.value.name));
		return;
	}
	const owing = Number(details.value.open_balance || 0);
	if (!owing) {
		const answer = await ask({
			title: `Check out ${name}?`,
			message: stay.value.room_number
				? `Room ${stay.value.room_number} becomes vacant and is marked dirty.`
				: "",
			confirmLabel: "Check out",
		});
		if (answer) run(() => checkOutApi(stay.value.name));
		return;
	}
	const amount = formatMoney(owing, stay.value.currency);
	if (!actions.value.can_override_check_out) {
		notify({
			tone: "danger",
			title: `${name} still owes ${amount}`,
			message: "Settle the folio first, or ask a Front Desk Manager to check the guest out.",
		});
		return;
	}
	const answer = await ask({
		tone: "danger",
		title: `${name} still owes ${amount}`,
		message: "Check out anyway? The balance stays on the folio for settlement.",
		reasonLabel: "Why check out with a balance?",
		confirmLabel: "Check out anyway",
	});
	if (answer) run(() => checkOutApi(stay.value.name, answer.reason));
}

async function removeGuest(guest) {
	const answer = await ask({
		tone: "danger",
		title: `Remove ${guest.guest_name} from this stay?`,
		reasonLabel: "Reason",
		confirmLabel: "Remove guest",
	});
	if (answer) run(() => removeStayGuestApi(guest.name, answer.reason));
}

async function addGuest() {
	await run(() => addStayGuestApi(stay.value.name, newGuest.value.name, newGuestAge.value));
	if (!error.value) newGuest.value = null;
}

onMounted(async () => {
	await load();
	moveReasons.value = (await fetchMoveReasonsApi().catch(() => [])) || [];
	moveReason.value = moveReasons.value.includes("Guest Request")
		? "Guest Request"
		: moveReasons.value[0] || "";
});
watch(currentStayId, load);
</script>
