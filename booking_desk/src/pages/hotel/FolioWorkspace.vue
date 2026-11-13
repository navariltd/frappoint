<template>
	<div class="px-6 py-5 space-y-5 max-w-6xl">
		<div class="flex gap-4 text-[12px] font-semibold">
			<RouterLink
				v-if="isHouseAccount"
				:to="{ name: 'HotelHouseAccounts' }"
				class="text-primary"
				>← House Accounts</RouterLink
			>
			<RouterLink
				v-else
				:to="{ name: 'HotelStay', params: { stayId: route.params.stayId } }"
				class="text-primary"
				>← Reservation {{ route.params.stayId }}</RouterLink
			>
			<RouterLink :to="{ name: 'FrontDeskToday' }" class="text-primary"
				>Front Desk</RouterLink
			>
		</div>

		<p v-if="loading && !data" class="text-[13px] text-on-surface-variant">Loading…</p>
		<p v-if="error" class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px]">
			{{ error }}
		</p>
		<ActionBanner
			:banner="banner"
			:busy="busy"
			@confirm="confirmBanner"
			@cancel="cancelBanner"
		/>

		<template v-if="data">
			<header class="flex flex-wrap items-start justify-between gap-4">
				<div>
					<div class="flex items-center gap-3">
						<h1 class="text-[22px] font-semibold text-on-surface">
							Folios · {{ data.stay.lead_guest_name }}
						</h1>
						<HotelStatusBadge :status="data.stay.status" />
					</div>
					<p class="text-[13px] text-on-surface-variant">
						<template v-if="data.house_account">
							House account · {{ data.house_account.account_type }} ·
						</template>
						{{ data.stay.name }} · Business date
						{{ formatNight(data.business_date) }}
					</p>
				</div>
				<div class="flex gap-3">
					<div
						class="rounded-xl border border-outline-variant bg-surface-container-lowest px-4 py-2 text-right"
					>
						<p class="text-[11px] text-on-surface-variant">Balance</p>
						<p class="text-[18px] font-semibold">
							{{ money(data.totals.balance) }}
						</p>
					</div>
					<div
						class="rounded-xl border border-dashed border-outline-variant px-4 py-2 text-right"
						title="Nights not posted yet. Night audit posts them; they are not part of the balance."
					>
						<p class="text-[11px] text-on-surface-variant">Pending, not in balance</p>
						<p class="text-[18px] font-semibold text-on-surface-variant">
							{{ money(data.totals.pending) }}
						</p>
					</div>
				</div>
			</header>

			<p
				v-if="!data.folios.length && !isHouseAccount"
				class="text-[13px] text-on-surface-variant"
			>
				This stay has no folio yet. It gets one when it is confirmed.
			</p>
			<div
				v-if="data.actions.can_open_house_folio"
				class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-dashed border-outline-variant px-4 py-3"
			>
				<p class="text-[13px] text-on-surface-variant">
					The last folio is settled. Start a new one to post more charges to this
					account.
				</p>
				<button
					type="button"
					class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
					:disabled="busy"
					@click="run(() => openHouseAccountFolioApi(route.params.accountId))"
				>
					Start a new folio
				</button>
			</div>

			<!-- Deposit (F12) -->
			<section
				v-if="data.deposit"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
			>
				<div class="flex flex-wrap items-center justify-between gap-3">
					<h2 class="text-[15px] font-semibold">Deposit</h2>
					<HotelStatusBadge :status="data.deposit.status" />
				</div>
				<p class="text-[13px]">
					{{ money(data.deposit.required_amount) }} required ·
					{{ money(data.deposit.held) }} held
					<template v-if="Number(data.deposit.refunded)">
						· {{ money(data.deposit.refunded) }} refunded</template
					>
					<template v-if="depositOpen">
						· <b>{{ money(data.deposit.outstanding) }}</b> due by
						{{ formatNight(data.deposit.due_date) }}</template
					>
				</p>
				<p class="text-[12px] text-on-surface-variant">
					A deposit is an advance Payment Entry on the {{ depositFolioLabel }} folio. It
					pays the invoice at settlement, or the fee if the stay is cancelled inside the
					penalty window.
				</p>
				<form
					v-if="
						depositOpen &&
						data.actions.can_take_payment &&
						data.cashier_shift &&
						!waiting
					"
					class="grid gap-3 md:grid-cols-4 items-end"
					@submit.prevent="takeDeposit"
				>
					<label class="text-[12px] text-on-surface-variant">
						Amount
						<input
							v-model.number="deposit.amount"
							type="number"
							min="0"
							step="0.01"
							class="folio-input"
						/>
					</label>
					<label class="text-[12px] text-on-surface-variant">
						Paid by
						<select v-model="deposit.tender" class="folio-input">
							<option v-for="mode in tenders" :key="mode.value" :value="mode.value">
								{{ mode.label }}
							</option>
						</select>
					</label>
					<label
						v-if="deposit.tender.startsWith('gateway:')"
						class="text-[12px] text-on-surface-variant"
					>
						Phone number
						<input
							v-model="deposit.phone"
							type="tel"
							placeholder="07..."
							class="folio-input"
						/>
					</label>
					<label v-else class="text-[12px] text-on-surface-variant">
						Reference
						<input v-model="deposit.reference" class="folio-input" />
					</label>
					<button
						type="submit"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="busy || !(deposit.amount > 0) || !deposit.tender"
					>
						Take deposit
					</button>
				</form>
				<p
					v-else-if="depositOpen && data.actions.can_take_payment && !data.cashier_shift"
					class="text-[12px] text-on-surface-variant"
				>
					Open your cashier shift to take the deposit.
					<RouterLink :to="{ name: 'Cashier' }" class="font-semibold text-primary"
						>Go to Cashier →</RouterLink
					>
				</p>
			</section>

			<!-- Post a charge -->
			<section
				v-if="data.actions.can_post && postableFolios.length"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
			>
				<h2 class="text-[15px] font-semibold">Post a charge</h2>
				<div class="grid gap-3 md:grid-cols-[2fr_1fr]">
					<div class="space-y-2">
						<div
							v-if="form.item"
							class="flex items-center justify-between rounded-lg border border-secondary bg-secondary-container/40 px-3 py-2"
						>
							<span>
								<span class="text-[13px] font-semibold">{{
									form.item.item_name
								}}</span>
								<span class="block text-[11px] text-on-surface-variant">
									{{ form.item.name }} · {{ form.item.item_group }}
									<template v-if="form.chargeCode">
										· posts as {{ form.chargeCode }}</template
									>
								</span>
							</span>
							<button
								type="button"
								class="text-[12px] font-semibold text-primary"
								@click="clearItem"
							>
								Change
							</button>
						</div>
						<template v-else>
							<input
								v-model="itemQuery"
								type="search"
								class="folio-input"
								placeholder="Search items: massage, breakfast, laundry…"
								@input="onItemSearch"
							/>
							<ul
								v-if="itemResults.length"
								class="max-h-56 overflow-y-auto divide-y divide-outline-variant rounded-lg border border-outline-variant"
							>
								<li v-for="item in itemResults" :key="item.name">
									<button
										type="button"
										class="w-full text-left px-3 py-2 hover:bg-surface-container"
										@click="chooseItem(item)"
									>
										<span class="text-[13px] font-semibold">{{
											item.item_name
										}}</span>
										<span class="block text-[11px] text-on-surface-variant">
											{{ item.name }} · {{ item.item_group }}
										</span>
									</button>
								</li>
							</ul>
							<p
								v-else-if="itemSearched"
								class="text-[12px] text-on-surface-variant"
							>
								No postable item found. Items need a charge code that covers their
								Item Group.
							</p>
						</template>
					</div>
					<div class="grid grid-cols-2 gap-2">
						<label class="text-[12px] text-on-surface-variant">
							Quantity
							<input
								v-model.number="form.quantity"
								type="number"
								min="1"
								step="1"
								class="folio-input"
							/>
						</label>
						<label class="text-[12px] text-on-surface-variant">
							Rate
							<input
								v-model.number="form.rate"
								type="number"
								min="0"
								step="0.01"
								class="folio-input"
							/>
						</label>
					</div>
				</div>
				<div class="grid gap-3 md:grid-cols-3">
					<label
						v-if="postableFolios.length > 1"
						class="text-[12px] text-on-surface-variant"
					>
						Folio
						<select v-model="form.folio" class="folio-input">
							<option
								v-for="entry in postableFolios"
								:key="entry.folio.name"
								:value="entry.folio.name"
							>
								{{ entry.folio.folio_label }} · {{ entry.folio.payee_name }}
							</option>
						</select>
					</label>
					<label class="text-[12px] text-on-surface-variant">
						Consumed by
						<select v-model="form.stayGuest" class="folio-input">
							<option :value="null">Not recorded</option>
							<option
								v-for="guest in data.guests"
								:key="guest.name"
								:value="guest.name"
							>
								{{ guest.guest_name }} ({{ guest.role }})
							</option>
						</select>
					</label>
					<label class="text-[12px] text-on-surface-variant">
						Notes
						<input v-model="form.notes" class="folio-input" />
					</label>
				</div>
				<label v-if="lateCharge" class="block text-[12px] text-on-surface-variant">
					The guest has checked out. Why is this charged now? (a Front Desk Manager posts
					late charges)
					<input
						v-model="form.reason"
						class="folio-input"
						placeholder="Minibar count, damage report…"
					/>
				</label>
				<div class="flex items-center justify-between">
					<p class="text-[13px]">
						Total <b>{{ money(formTotal) }}</b>
					</p>
					<button
						type="button"
						class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
						:disabled="
							busy ||
							!form.item ||
							!(form.quantity > 0) ||
							!(form.rate > 0) ||
							(lateCharge && !form.reason.trim())
						"
						@click="postCharge"
					>
						Post charge
					</button>
				</div>
			</section>

			<!-- Take a payment (F10) -->
			<section
				v-if="data.actions.can_take_payment && postableFolios.length"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
			>
				<h2 class="text-[15px] font-semibold">Take a payment</h2>
				<p v-if="!data.cashier_shift" class="text-[13px] text-on-surface-variant">
					Open your cashier shift to take payments.
					<RouterLink :to="{ name: 'Cashier' }" class="font-semibold text-primary"
						>Go to Cashier →</RouterLink
					>
				</p>
				<template v-else-if="waiting">
					<p class="text-[13px]">
						Waiting for the guest to approve
						<b>{{ money(waiting.amount) }}</b> on their phone…
					</p>
					<button
						type="button"
						class="rounded-lg border border-outline-variant px-3 py-2 text-[12px] font-semibold"
						:disabled="busy"
						@click="cancelWaiting"
					>
						Cancel request
					</button>
				</template>
				<form v-else class="space-y-3" @submit.prevent="takePayment">
					<div class="grid gap-3 md:grid-cols-3">
						<label
							v-for="entry in postableFolios"
							:key="entry.folio.name"
							class="text-[12px] text-on-surface-variant"
						>
							{{ entry.folio.folio_label }} (owes {{ money(entry.folio.balance) }})
							<input
								v-model.number="pay.amounts[entry.folio.name]"
								type="number"
								min="0"
								step="0.01"
								class="folio-input"
							/>
						</label>
					</div>
					<div class="grid gap-3 md:grid-cols-3">
						<label class="text-[12px] text-on-surface-variant">
							Paid by
							<select v-model="pay.tender" class="folio-input">
								<option
									v-for="mode in tenders"
									:key="mode.value"
									:value="mode.value"
								>
									{{ mode.label }}
								</option>
							</select>
						</label>
						<label v-if="isPhoneTender" class="text-[12px] text-on-surface-variant">
							Phone number
							<input
								v-model="pay.phone"
								type="tel"
								placeholder="07..."
								class="folio-input"
							/>
						</label>
						<label v-else class="text-[12px] text-on-surface-variant">
							Reference (slip or transfer number)
							<input v-model="pay.reference" class="folio-input" />
						</label>
					</div>
					<div class="flex items-center justify-between">
						<p class="text-[13px]">
							Total <b>{{ money(payTotal) }}</b>
						</p>
						<button
							type="submit"
							class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
							:disabled="busy || payTotal <= 0 || !pay.tender"
						>
							{{ isPhoneTender ? "Send payment request" : "Take payment" }}
						</button>
					</div>
				</form>
			</section>

			<!-- Open another folio (F11) -->
			<section
				v-if="data.actions.can_post && data.folios.length && data.actions.can_add_folio"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
			>
				<div class="flex items-center justify-between">
					<h2 class="text-[15px] font-semibold">Another folio</h2>
					<button
						v-if="!newFolio.open"
						type="button"
						class="text-[12px] font-semibold text-primary"
						@click="newFolio.open = true"
					>
						Open a folio
					</button>
				</div>
				<p v-if="!newFolio.open" class="text-[12px] text-on-surface-variant">
					<template v-if="data.stay.status === 'Checked Out'">
						The guest has checked out. A late charge for an invoiced stay goes on a new
						folio, open until the post-stay window ends.
					</template>
					<template v-else>
						Bill part of the stay to someone else: the company, a companion, or the
						guest's own extras.
					</template>
				</p>
				<form v-else class="space-y-3" @submit.prevent="addFolio">
					<div class="grid gap-3 md:grid-cols-3">
						<label class="text-[12px] text-on-surface-variant">
							Name
							<input
								v-model="newFolio.label"
								class="folio-input"
								placeholder="Company, Spouse, Extras…"
							/>
						</label>
						<label class="text-[12px] text-on-surface-variant">
							Bill to
							<select v-model="newFolio.payee" class="folio-input">
								<option value="">The stay's usual payee</option>
								<option
									v-for="guest in payeeGuests"
									:key="guest.guest_profile"
									:value="`guest:${guest.guest_profile}`"
								>
									{{ guest.guest_name }} ({{ guest.role }})
								</option>
								<option value="customer">A company (ERPNext Customer)</option>
							</select>
						</label>
						<label
							v-if="newFolio.payee === 'customer'"
							class="text-[12px] text-on-surface-variant"
						>
							Customer ID
							<input v-model="newFolio.customer" class="folio-input" />
						</label>
					</div>
					<div class="flex justify-end gap-2">
						<button
							type="button"
							class="rounded-lg border border-outline-variant px-3 py-2 text-[12px] font-semibold"
							@click="resetNewFolio"
						>
							Cancel
						</button>
						<button
							type="submit"
							class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
							:disabled="
								busy ||
								(newFolio.payee === 'customer' && !newFolio.customer.trim())
							"
						>
							Open folio
						</button>
					</div>
				</form>
			</section>

			<!-- Routing (F12) -->
			<section
				v-if="
					!isHouseAccount &&
					data.actions.can_route &&
					(data.routing_rules.length || routeTargets.length > 1)
				"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
			>
				<div class="flex items-center justify-between">
					<h2 class="text-[15px] font-semibold">Routing</h2>
					<button
						v-if="!routeForm.open && routeTargets.length > 1"
						type="button"
						class="text-[12px] font-semibold text-primary"
						@click="routeForm.open = true"
					>
						Add a rule
					</button>
				</div>
				<p class="text-[12px] text-on-surface-variant">
					Night audit and policy fees post to the stay's default folio unless a rule
					sends them elsewhere. Charges you post by hand go where you post them.
				</p>
				<ul
					v-if="data.routing_rules.length"
					class="divide-y divide-outline-variant text-[13px]"
				>
					<li
						v-for="rule in data.routing_rules"
						:key="rule.name"
						class="flex items-center justify-between gap-3 py-2"
					>
						<span>
							<b>{{ rule.description }}</b> → {{ rule.target_label }}
							<span class="text-on-surface-variant">({{ rule.target_folio }})</span>
							<span
								v-if="!['Open', 'Post-Stay Open'].includes(rule.target_status)"
								class="text-on-surface-variant"
							>
								· folio {{ rule.target_status }}, so the rule is skipped</span
							>
						</span>
						<button
							type="button"
							class="text-[12px] font-semibold text-primary disabled:opacity-50"
							:disabled="busy"
							@click="removeRule(rule)"
						>
							Remove
						</button>
					</li>
				</ul>
				<form
					v-if="routeForm.open"
					class="grid gap-3 md:grid-cols-4 items-end"
					@submit.prevent="addRule"
				>
					<label class="text-[12px] text-on-surface-variant">
						Send
						<select v-model="routeForm.route" class="folio-input">
							<option value="Room Charges">Room charges</option>
							<option value="All Charges">All charges</option>
							<option value="Item Group">An item group</option>
							<option value="Charge Code">A charge code</option>
						</select>
					</label>
					<label
						v-if="routeForm.route === 'Item Group'"
						class="text-[12px] text-on-surface-variant"
					>
						Item group
						<input v-model="routeForm.itemGroup" class="folio-input" />
					</label>
					<label
						v-if="routeForm.route === 'Charge Code'"
						class="text-[12px] text-on-surface-variant"
					>
						Charge code
						<input v-model="routeForm.chargeCode" class="folio-input" />
					</label>
					<label class="text-[12px] text-on-surface-variant">
						To folio
						<select v-model="routeForm.target" class="folio-input">
							<option
								v-for="entry in routeTargets"
								:key="entry.folio.name"
								:value="entry.folio.name"
							>
								{{ entry.folio.folio_label }} · {{ entry.folio.payee_name }}
							</option>
						</select>
					</label>
					<div class="flex gap-2">
						<button
							type="button"
							class="rounded-lg border border-outline-variant px-3 py-2 text-[12px] font-semibold"
							@click="resetRouteForm"
						>
							Cancel
						</button>
						<button
							type="submit"
							class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
							:disabled="
								busy ||
								!routeForm.target ||
								(routeForm.route === 'Item Group' &&
									!routeForm.itemGroup.trim()) ||
								(routeForm.route === 'Charge Code' && !routeForm.chargeCode.trim())
							"
						>
							Add rule
						</button>
					</div>
				</form>
			</section>

			<!-- Folios -->
			<section
				v-for="entry in data.folios"
				:key="entry.folio.name"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-3"
			>
				<div class="flex flex-wrap items-start justify-between gap-3">
					<div>
						<div class="flex items-center gap-3">
							<h2 class="text-[15px] font-semibold">
								{{ entry.folio.folio_label }}
							</h2>
							<HotelStatusBadge :status="entry.folio.status" />
						</div>
						<p class="text-[12px] text-on-surface-variant">
							{{ entry.folio.name }} · Payee
							{{ entry.folio.payee_name || "not set yet" }}
							<template v-if="entry.folio.sales_invoice">
								· Invoice
								<a
									:href="`/app/sales-invoice/${entry.folio.sales_invoice}`"
									target="_blank"
									class="font-semibold text-primary"
									>{{ entry.folio.sales_invoice }}</a
								>
							</template>
						</p>
					</div>
					<div class="text-right">
						<p class="text-[11px] text-on-surface-variant">Balance</p>
						<p class="text-[16px] font-semibold">{{ money(entry.folio.balance) }}</p>
						<button
							v-if="data.actions.can_rebuild"
							type="button"
							class="text-[11px] font-semibold text-primary disabled:opacity-50"
							:disabled="busy"
							title="Recompute the balance from the posted lines"
							@click="rebuild(entry.folio.name)"
						>
							Check balance
						</button>
					</div>
				</div>

				<div
					v-if="entry.folio.status === 'Settlement Pending'"
					class="rounded-lg bg-error-container/40 px-4 py-3 text-[13px] space-y-2"
				>
					<p>
						<b>The invoice was rejected.</b>
						{{ entry.folio.settlement_error || "No reason was given." }}
					</p>
					<p class="text-[12px] text-on-surface-variant">
						Nothing was invoiced. Fix the cause (for example the Item's or Customer's
						tax details), then try again. Trying again never creates a second invoice.
					</p>
					<div v-if="data.actions.can_settle" class="flex gap-2">
						<button
							type="button"
							class="rounded-lg bg-primary text-on-primary px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy"
							@click="settle(entry, { retry: true })"
						>
							Try again
						</button>
						<button
							type="button"
							class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy"
							@click="releaseSettlement(entry.folio)"
						>
							Reopen to correct it
						</button>
					</div>
				</div>

				<p v-if="!entry.transactions.length" class="text-[13px] text-on-surface-variant">
					Nothing posted yet.
				</p>
				<div v-else class="overflow-x-auto">
					<table class="w-full text-[12px]">
						<thead class="text-left text-on-surface-variant">
							<tr class="border-b border-outline-variant">
								<th class="py-1.5 font-semibold">Date</th>
								<th class="py-1.5 font-semibold">Description</th>
								<th class="py-1.5 font-semibold">Guest</th>
								<th class="py-1.5 font-semibold">Room</th>
								<th class="py-1.5 text-right font-semibold">Charges</th>
								<th class="py-1.5 text-right font-semibold">Credits</th>
								<th class="py-1.5"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="line in entry.transactions"
								:key="line.name"
								class="border-b border-outline-variant align-top"
								:class="{ 'text-on-surface-variant': line.reversed_by }"
							>
								<td class="py-1.5 whitespace-nowrap">
									{{ formatNight(line.service_date) }}
								</td>
								<td class="py-1.5">
									<span :class="{ 'line-through': line.reversed_by }">{{
										line.description_snapshot
									}}</span>
									<span v-if="line.quantity > 1" class="text-on-surface-variant">
										× {{ line.quantity }}</span
									>
									<span class="block text-[11px] text-on-surface-variant">
										{{ line.charge_code }}
										<template v-if="line.tax_amount">
											· tax {{ money(line.tax_amount) }}</template
										>
										<template v-if="line.reversed_by"> · reversed</template>
										<template v-if="line.transfer_folio">
											·
											{{
												line.direction === "Credit"
													? "moved to"
													: "moved from"
											}}
											{{ folioLabel(line.transfer_folio) }}</template
										>
										<template v-if="line.sales_invoice">
											· {{ line.sales_invoice }}</template
										>
										<template v-if="line.reason">
											· {{ line.reason }}</template
										>
									</span>
								</td>
								<td class="py-1.5">{{ line.consumer_name || "" }}</td>
								<td class="py-1.5">{{ line.room_number_snapshot || "" }}</td>
								<td class="py-1.5 text-right whitespace-nowrap">
									<template v-if="line.direction === 'Debit'">{{
										money(line.gross_amount)
									}}</template>
								</td>
								<td class="py-1.5 text-right whitespace-nowrap">
									<template v-if="line.direction === 'Credit'">{{
										money(line.gross_amount)
									}}</template>
								</td>
								<td class="py-1.5 pl-3 text-right whitespace-nowrap space-x-3">
									<button
										v-if="canMove(entry.folio, line)"
										type="button"
										class="text-[11px] font-semibold text-primary disabled:opacity-50"
										:disabled="busy"
										@click="startMove(entry.folio, line)"
									>
										Move
									</button>
									<button
										v-if="canCredit(line)"
										type="button"
										class="text-[11px] font-semibold text-error disabled:opacity-50"
										:disabled="busy"
										@click="creditNote(line)"
									>
										Credit note
									</button>
									<button
										v-if="canReverse(entry.folio, line)"
										type="button"
										class="text-[11px] font-semibold text-error disabled:opacity-50"
										:disabled="busy"
										@click="reverse(line)"
									>
										Reverse
									</button>
								</td>
							</tr>
						</tbody>
					</table>
				</div>

				<form
					v-if="move.line && move.from === entry.folio.name"
					class="rounded-lg border border-secondary bg-secondary-container/30 p-3 space-y-3"
					@submit.prevent="moveCharge"
				>
					<p class="text-[13px] font-semibold">
						Move "{{ move.line.description_snapshot }}" to another folio
					</p>
					<div class="grid gap-3 md:grid-cols-3">
						<label class="text-[12px] text-on-surface-variant">
							To
							<select v-model="move.to" class="folio-input">
								<option
									v-for="target in moveTargets"
									:key="target.folio.name"
									:value="target.folio.name"
								>
									{{ target.folio.folio_label }} · {{ target.folio.payee_name }}
								</option>
							</select>
						</label>
						<label class="text-[12px] text-on-surface-variant">
							Amount (up to {{ money(move.left) }})
							<input
								v-model.number="move.amount"
								type="number"
								min="0"
								step="0.01"
								:max="move.left"
								class="folio-input"
							/>
						</label>
						<label class="text-[12px] text-on-surface-variant">
							Reason
							<input
								v-model="move.reason"
								class="folio-input"
								placeholder="Company pays the room"
							/>
						</label>
					</div>
					<div class="flex items-center justify-between gap-2">
						<span class="space-x-2 text-[12px]">
							<button
								type="button"
								class="font-semibold text-primary"
								@click="move.amount = move.left"
							>
								All
							</button>
							<button
								type="button"
								class="font-semibold text-primary"
								@click="move.amount = Math.round(move.left * 50) / 100"
							>
								Half
							</button>
						</span>
						<span class="flex gap-2">
							<button
								type="button"
								class="rounded-lg border border-outline-variant px-3 py-2 text-[12px] font-semibold"
								@click="cancelMove"
							>
								Cancel
							</button>
							<button
								type="submit"
								class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
								:disabled="
									busy ||
									!move.to ||
									!(move.amount > 0) ||
									move.amount > move.left
								"
							>
								Move {{ money(move.amount) }}
							</button>
						</span>
					</div>
				</form>

				<div
					v-if="entry.invoice && entry.folio.status !== 'Settlement Pending'"
					class="border-t border-outline-variant pt-3 space-y-2"
				>
					<p v-if="entry.invoice.error" class="text-[12px] text-error">
						Can't invoice yet: {{ entry.invoice.error }}
					</p>
					<template v-else-if="entry.invoice.items.length">
						<p class="text-[12px] font-semibold">Invoice preview</p>
						<table class="w-full text-[12px]">
							<tbody>
								<tr
									v-for="row in entry.invoice.items"
									:key="`${row.item}-${row.description}`"
								>
									<td class="py-0.5">{{ row.description }}</td>
									<td class="py-0.5 text-right">{{ money(row.net) }}</td>
								</tr>
								<tr
									v-for="row in entry.invoice.taxes"
									:key="row.account"
									class="text-on-surface-variant"
								>
									<td class="py-0.5">{{ row.description }}</td>
									<td class="py-0.5 text-right">{{ money(row.amount) }}</td>
								</tr>
								<tr class="font-semibold border-t border-outline-variant">
									<td class="py-0.5">Total</td>
									<td class="py-0.5 text-right">
										{{ money(entry.invoice.total) }}
									</td>
								</tr>
								<tr class="text-on-surface-variant">
									<td class="py-0.5">Paid</td>
									<td class="py-0.5 text-right">
										{{ money(entry.invoice.paid) }}
									</td>
								</tr>
							</tbody>
						</table>
					</template>
					<div
						v-if="!entry.invoice.error && data.actions.can_settle"
						class="flex flex-wrap items-center justify-end gap-2"
					>
						<span
							v-if="entry.invoice.outstanding > 0"
							class="text-[12px] text-on-surface-variant"
						>
							{{ money(entry.invoice.outstanding) }} still to pay before settling.
						</span>
						<button
							v-if="entry.invoice.outstanding > 0 && data.actions.can_bill_company"
							type="button"
							class="rounded-lg border border-outline-variant px-3 py-2 text-[12px] font-semibold disabled:opacity-50"
							:disabled="busy"
							@click="billCompany(entry)"
						>
							Bill to company account
						</button>
						<button
							type="button"
							class="rounded-lg bg-primary text-on-primary px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
							:disabled="busy || entry.invoice.outstanding !== 0"
							@click="settle(entry)"
						>
							{{ entry.invoice.items.length ? "Settle and invoice" : "Close folio" }}
						</button>
					</div>
				</div>

				<div v-if="entry.payments?.length" class="border-t border-outline-variant pt-2">
					<p class="text-[12px] font-semibold">Payments</p>
					<ul class="text-[12px]">
						<li
							v-for="payment in entry.payments"
							:key="payment.name"
							class="flex flex-wrap items-center justify-between gap-2 py-1"
						>
							<span>
								{{ payment.direction === "Debit" ? "Refund" : "Payment" }} ·
								{{ payment.mode_of_payment }}
								<span class="text-on-surface-variant">
									· {{ payment.folio_payment }}
									<template v-if="payment.reference_no">
										· {{ payment.reference_no }}</template
									>
								</span>
							</span>
							<span class="flex items-center gap-3">
								<b
									>{{ payment.direction === "Debit" ? "−" : ""
									}}{{ money(payment.amount) }}</b
								>
								<button
									v-if="
										data.actions.can_take_payment &&
										data.cashier_shift &&
										payment.refundable > 0
									"
									type="button"
									class="text-[11px] font-semibold text-error disabled:opacity-50"
									:disabled="busy"
									@click="refund(entry.folio, payment)"
								>
									Refund
								</button>
							</span>
						</li>
					</ul>
				</div>
			</section>

			<section
				v-if="data.pending_nights.length"
				class="rounded-xl border border-dashed border-outline-variant p-4"
			>
				<h2 class="text-[15px] font-semibold">Pending nights</h2>
				<p class="text-[12px] text-on-surface-variant">
					Night audit posts each night to the folio. Until then they are estimates and
					not part of the balance.
				</p>
				<table class="mt-2 w-full text-[12px]">
					<tbody>
						<tr
							v-for="night in data.pending_nights"
							:key="night.night_date"
							class="border-b border-outline-variant"
						>
							<td class="py-1.5">{{ formatNight(night.night_date) }}</td>
							<td class="py-1.5 text-right">{{ money(night.total) }}</td>
						</tr>
					</tbody>
				</table>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
	cancelPaymentApi,
	fetchPaymentApi,
	refundPaymentApi,
	takePaymentApi,
	addFolioApi,
	issueCreditNoteApi,
	releaseSettlementApi,
	settleFolioApi,
	transferChargeApi,
	fetchFolioItemRateApi,
	fetchStayFoliosApi,
	hotelErrorMessage,
	postFolioChargeApi,
	rebuildFolioBalanceApi,
	reverseFolioTransactionApi,
	searchFolioItemsApi,
	addRoutingRuleApi,
	fetchHouseAccountFoliosApi,
	openHouseAccountFolioApi,
	removeRoutingRuleApi,
	takeDepositApi,
} from "@/api/hotel.api";
import ActionBanner from "@/components/hotel/ActionBanner.vue";
import HotelStatusBadge from "@/components/hotel/HotelStatusBadge.vue";
import { useActionBanner } from "@/composables/hotel/useActionBanner";
import { formatMoney, formatNight } from "@/utils/hotelFormat";

const POSTABLE = ["Open", "Post-Stay Open"];

const route = useRoute();
const { banner, ask, notify, confirm: confirmBanner, cancel: cancelBanner } = useActionBanner();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");

const itemQuery = ref("");
const itemResults = ref([]);
const itemSearched = ref(false);
const form = reactive(emptyForm());

const postableFolios = computed(() =>
	(data.value?.folios || []).filter((entry) => POSTABLE.includes(entry.folio.status))
);
const formTotal = computed(() => (Number(form.quantity) || 0) * (Number(form.rate) || 0));

function newRequestId() {
	return window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function emptyForm(folio = null) {
	// One request id per charge: a retry of the same charge posts once.
	return {
		folio,
		item: null,
		chargeCode: null,
		quantity: 1,
		rate: null,
		stayGuest: null,
		notes: "",
		reason: "",
		requestId: newRequestId(),
	};
}

function resetForm() {
	const folio =
		postableFolios.value.find((entry) => entry.folio.is_default)?.folio.name ||
		postableFolios.value[0]?.folio.name ||
		null;
	Object.assign(form, emptyForm(folio));
	itemQuery.value = "";
	itemResults.value = [];
	itemSearched.value = false;
}

function money(amount) {
	return formatMoney(amount, data.value?.stay?.currency);
}

// F12: house accounts share this workspace; post-stay folios need a reason for a late charge.
const isHouseAccount = computed(() => Boolean(route.params.accountId));
const lateCharge = computed(
	() =>
		(data.value?.folios || []).find((entry) => entry.folio.name === form.folio)?.folio
			.status === "Post-Stay Open"
);

// Deposit (F12): taken like a payment, on the stay's default folio.
const deposit = reactive({ amount: null, tender: "", phone: "", reference: "", requestId: "" });
const depositOpen = computed(() =>
	["Requested", "Partly Paid"].includes(data.value?.deposit?.status)
);
const depositFolioLabel = computed(
	() =>
		(data.value?.folios || []).find(
			(entry) => entry.folio.name === data.value?.deposit?.guest_folio
		)?.folio.folio_label || "default"
);

function resetDeposit() {
	deposit.amount = Number(data.value?.deposit?.outstanding) || null;
	deposit.reference = "";
	deposit.requestId = newRequestId();
	if (!tenders.value.some((tender) => tender.value === deposit.tender)) {
		deposit.tender = tenders.value[0]?.value || "";
	}
}

async function takeDeposit() {
	const tender = tenders.value.find((option) => option.value === deposit.tender);
	const phone = deposit.tender.startsWith("gateway:");
	const answer = await ask({
		title: `Take a deposit of ${money(deposit.amount)} by ${tender?.label}?`,
		message: phone
			? `A payment request goes to ${deposit.phone}. The deposit is received when the guest approves it.`
			: "The deposit is received now, as an advance for the stay.",
		confirmLabel: phone ? "Send request" : "Take deposit",
	});
	if (!answer) return;
	const kind = deposit.tender.split(":")[0];
	const value = deposit.tender.slice(deposit.tender.indexOf(":") + 1);
	let result = null;
	await run(async () => {
		result = await takeDepositApi({
			deposit: data.value.deposit.name,
			amount: deposit.amount,
			modeOfPayment: kind === "mode" ? value : null,
			paymentGateway: kind === "gateway" ? value : null,
			phone: deposit.phone,
			referenceNo: deposit.reference,
			requestId: deposit.requestId,
		});
	});
	if (!result) return; // failed: the same request id is kept for a retry
	const payment = await fetchPaymentApi(result.payment);
	if (payment.status === "Pending") {
		waiting.value = payment;
		pollPayment();
	} else {
		notify({
			title: `Deposit received: ${money(payment.amount)}`,
			message: `Payment ${payment.name}.`,
		});
	}
}

// Routing (F12)
const routeForm = reactive(emptyRouteForm());
const routeTargets = computed(() => postableFolios.value);

function emptyRouteForm() {
	return { open: false, route: "Room Charges", chargeCode: "", itemGroup: "", target: "" };
}

function resetRouteForm() {
	Object.assign(routeForm, emptyRouteForm());
}

async function addRule() {
	const done = await run(() =>
		addRoutingRuleApi({
			stay: data.value.stay.name,
			targetFolio: routeForm.target,
			route: routeForm.route,
			chargeCode: routeForm.chargeCode.trim(),
			itemGroup: routeForm.itemGroup.trim(),
		})
	);
	if (done) resetRouteForm();
}

async function removeRule(rule) {
	const answer = await ask({
		title: `Stop sending ${rule.description.toLowerCase()} to ${rule.target_label}?`,
		message: "Charges already posted stay where they are; move them if needed.",
		reasonLabel: "Reason",
		confirmLabel: "Remove rule",
	});
	if (answer) run(() => removeRoutingRuleApi(rule.name, answer.reason));
}

function canReverse(folio, line) {
	return (
		data.value.actions.can_reverse &&
		POSTABLE.includes(folio.status) &&
		!line.reverses &&
		!line.reversed_by
	);
}

// Payments (F10): one request id per payment, so a retried request is taken once.
const pay = reactive({
	amounts: {},
	tender: "",
	phone: "",
	reference: "",
	requestId: newRequestId(),
});
const waiting = ref(null);
let waitTimer = null;

const tenders = computed(() => {
	const options = data.value?.payment_options;
	if (!options) return [];
	return [
		...options.modes.map((mode) => ({ value: `mode:${mode}`, label: mode })),
		...options.phone_gateways.map((gateway) => ({
			value: `gateway:${gateway.name}`,
			label: gateway.label,
		})),
	];
});
const isPhoneTender = computed(() => pay.tender.startsWith("gateway:"));
const payTotal = computed(() =>
	Object.values(pay.amounts).reduce((sum, amount) => sum + (Number(amount) || 0), 0)
);

function resetPayment() {
	pay.amounts = Object.fromEntries(
		postableFolios.value.map((entry) => [
			entry.folio.name,
			Math.max(Number(entry.folio.balance) || 0, 0),
		])
	);
	pay.reference = "";
	pay.requestId = newRequestId();
	if (!tenders.value.some((tender) => tender.value === pay.tender)) {
		pay.tender = tenders.value[0]?.value || "";
	}
}

async function takePayment() {
	const tender = tenders.value.find((option) => option.value === pay.tender);
	const answer = await ask({
		title: `Take ${money(payTotal.value)} by ${tender?.label}?`,
		message: isPhoneTender.value
			? `A payment request goes to ${pay.phone}. The folios are credited when the guest approves it.`
			: "The folios are credited now.",
		confirmLabel: isPhoneTender.value ? "Send request" : "Take payment",
	});
	if (!answer) return;
	const [kind, value] = [
		pay.tender.split(":")[0],
		pay.tender.slice(pay.tender.indexOf(":") + 1),
	];
	let result = null;
	await run(async () => {
		result = await takePaymentApi({
			property: data.value.stay.property,
			splits: Object.entries(pay.amounts)
				.filter(([, amount]) => Number(amount) > 0)
				.map(([folio, amount]) => ({ folio, amount })),
			modeOfPayment: kind === "mode" ? value : null,
			paymentGateway: kind === "gateway" ? value : null,
			phone: pay.phone,
			referenceNo: pay.reference,
			requestId: pay.requestId,
		});
	});
	if (!result) return; // failed: the same request id is kept for a retry
	if (result.status === "Pending") {
		waiting.value = result;
		pollPayment();
	} else {
		notify({ title: `Received ${money(result.amount)}`, message: `Payment ${result.name}.` });
		resetPayment();
	}
}

function pollPayment() {
	clearTimeout(waitTimer);
	waitTimer = setTimeout(async () => {
		if (!waiting.value) return;
		try {
			const result = await fetchPaymentApi(waiting.value.name);
			if (result.status === "Pending") return pollPayment();
			waiting.value = null;
			await load();
			resetPayment();
			notify(
				result.status === "Received"
					? {
							title: `Received ${money(result.amount)}`,
							message: `Payment ${result.name}.`,
					  }
					: {
							tone: "danger",
							title: `Payment ${result.status.toLowerCase()}`,
							message: result.reason || "",
					  }
			);
		} catch (e) {
			error.value = hotelErrorMessage(e);
			pollPayment();
		}
	}, 3000);
}

async function cancelWaiting() {
	const answer = await ask({
		tone: "danger",
		title: "Cancel the payment request?",
		message: "If the guest approves it later, the payment can't be matched automatically.",
		reasonLabel: "Reason",
		confirmLabel: "Cancel request",
		cancelLabel: "Keep waiting",
	});
	if (!answer) return;
	clearTimeout(waitTimer);
	await run(() => cancelPaymentApi(waiting.value.name, answer.reason));
	waiting.value = null;
	resetPayment();
}

async function refund(folioRow, payment) {
	const answer = await ask({
		tone: "danger",
		title: `Refund ${money(payment.refundable)} of ${payment.folio_payment} to ${
			folioRow.folio_label
		}?`,
		message: `Paid back by ${payment.mode_of_payment}, from your shift. The folio is charged the amount again.`,
		reasonLabel: "Reason for the refund",
		confirmLabel: "Refund",
	});
	if (answer) {
		run(() =>
			refundPaymentApi(
				payment.folio_payment,
				{ [folioRow.name]: payment.refundable },
				answer.reason
			)
		);
	}
}

// Several folios, moving charges, settlement and credit notes (F11).
const newFolio = reactive({ open: false, label: "", payee: "", customer: "" });
const move = reactive({
	line: null,
	from: null,
	to: null,
	amount: null,
	left: 0,
	reason: "",
	requestId: null,
});

const payeeGuests = computed(() =>
	(data.value?.guests || []).filter((guest) => guest.guest_profile)
);
const moveTargets = computed(() =>
	postableFolios.value.filter((entry) => entry.folio.name !== move.from)
);

function folioLabel(name) {
	return (
		data.value?.folios.find((entry) => entry.folio.name === name)?.folio.folio_label || name
	);
}

function resetNewFolio() {
	Object.assign(newFolio, { open: false, label: "", payee: "", customer: "" });
}

async function addFolio() {
	const guest = newFolio.payee.startsWith("guest:") ? newFolio.payee.slice(6) : null;
	const added = await run(() =>
		addFolioApi({
			stay: data.value.stay.name,
			label: newFolio.label.trim(),
			payeeCustomer: newFolio.payee === "customer" ? newFolio.customer.trim() : null,
			payeeGuestProfile: guest,
		})
	);
	if (added) resetNewFolio();
}

/** What is left of a charge after the parts already moved to other folios. */
function leftToMove(entry, line) {
	const moved = entry.transactions
		.filter((row) => row.transfer_of === line.name && row.direction === "Credit")
		.reduce((sum, row) => sum + Number(row.gross_amount), 0);
	return Math.round((Number(line.gross_amount) - moved) * 100) / 100;
}

function canMove(folio, line) {
	const entry = data.value.folios.find((row) => row.folio.name === folio.name);
	return (
		data.value.actions.can_post &&
		POSTABLE.includes(folio.status) &&
		line.direction === "Debit" &&
		line.transaction_type === "Revenue" &&
		!line.reverses &&
		!line.reversed_by &&
		!line.sales_invoice &&
		postableFolios.value.length > 1 &&
		leftToMove(entry, line) > 0
	);
}

function startMove(folio, line) {
	const entry = data.value.folios.find((row) => row.folio.name === folio.name);
	const left = leftToMove(entry, line);
	Object.assign(move, {
		line,
		from: folio.name,
		to: postableFolios.value.find((row) => row.folio.name !== folio.name)?.folio.name || null,
		amount: left,
		left,
		reason: "",
		// One id per move: a retry after a failure moves the charge once.
		requestId: newRequestId(),
	});
}

function cancelMove() {
	move.line = null;
	move.from = null;
}

async function moveCharge() {
	const moved = await run(() =>
		transferChargeApi({
			transaction: move.line.name,
			toFolio: move.to,
			// Moving everything left sends no amount, so the server moves exactly the rest.
			amount: move.amount >= move.left ? null : move.amount,
			reason: move.reason.trim(),
			requestId: move.requestId,
		})
	);
	if (moved) cancelMove();
}

async function settle(entry, { retry = false } = {}) {
	const invoice = entry.invoice;
	if (!retry) {
		const answer = await ask({
			title: invoice?.items.length
				? `Invoice ${money(invoice.total)} to ${entry.folio.payee_name}?`
				: `Close ${entry.folio.folio_label}?`,
			message: invoice?.items.length
				? "A Sales Invoice is submitted with the payments applied, and the folio closes. Later corrections use a credit note."
				: "Nothing is billed on this folio. It closes without an invoice.",
			confirmLabel: invoice?.items.length ? "Settle and invoice" : "Close folio",
		});
		if (!answer) return;
	}
	await finishSettlement(entry.folio, () => settleFolioApi(entry.folio.name));
}

async function billCompany(entry, overrideReason = null) {
	if (!overrideReason) {
		const answer = await ask({
			title: `Bill ${money(entry.invoice.outstanding)} to ${
				entry.folio.payee_name
			}'s account?`,
			message:
				"The folio is invoiced and closes. The balance stays on the company's invoice, in Accounts Receivable.",
			confirmLabel: "Bill to account",
		});
		if (!answer) return;
	}
	await finishSettlement(
		entry.folio,
		() => settleFolioApi(entry.folio.name, { transferToAr: true, overrideReason }),
		entry
	);
}

async function finishSettlement(folio, command, companyEntry = null) {
	let result = null;
	const done = await run(async () => {
		result = (await command())?.settled;
	});
	if (!done) {
		// Over the credit limit: someone allowed to approve it can, with a reason.
		if (companyEntry && /credit limit/i.test(error.value) && /reason/i.test(error.value)) {
			const answer = await ask({
				tone: "danger",
				title: "Approve billing over the credit limit?",
				message: error.value,
				reasonLabel: "Reason for the approval",
				confirmLabel: "Approve and bill",
			});
			if (answer) await billCompany(companyEntry, answer.reason);
		}
		return;
	}
	if (result?.status === "Settlement Pending") {
		notify({
			tone: "danger",
			title: "The invoice was rejected",
			message: `${folio.folio_label} is waiting for settlement: ${result.error}`,
		});
	} else if (result) {
		notify({
			title: result.sales_invoice
				? `Invoiced as ${result.sales_invoice}`
				: `${folio.folio_label} closed`,
			message: `${folio.folio_label} is ${result.status}.`,
		});
	}
}

async function releaseSettlement(folio) {
	const answer = await ask({
		title: `Reopen ${folio.folio_label}?`,
		message: "The folio takes postings again, so it can be corrected before settling.",
		reasonLabel: "What needs correcting",
		confirmLabel: "Reopen",
	});
	if (answer) run(() => releaseSettlementApi(folio.name, answer.reason));
}

function canCredit(line) {
	return (
		data.value.actions.can_credit &&
		line.sales_invoice &&
		line.direction === "Debit" &&
		line.transaction_type === "Revenue" &&
		!line.reverses &&
		!line.reversed_by
	);
}

async function creditNote(line) {
	const answer = await ask({
		tone: "danger",
		title: `Credit "${line.description_snapshot}" (${money(line.gross_amount)})?`,
		message: `A credit note is issued against ${line.sales_invoice} and the charge is reversed on the folio. The invoice itself stays as it is.`,
		reasonLabel: "Reason for the credit note",
		confirmLabel: "Issue credit note",
	});
	if (!answer) return;
	let result = null;
	const done = await run(async () => {
		result = (await issueCreditNoteApi(line.name, answer.reason))?.credited;
	});
	if (done && result) {
		notify({
			title: `Credit note ${result.credit_note}`,
			message: "If the guest already paid, refund them from the Cashier page.",
		});
	}
}

async function load() {
	loading.value = true;
	error.value = "";
	try {
		data.value = isHouseAccount.value
			? await fetchHouseAccountFoliosApi(route.params.accountId)
			: await fetchStayFoliosApi(route.params.stayId);
		if (!form.folio || !postableFolios.value.some((e) => e.folio.name === form.folio)) {
			resetForm();
		}
		if (!waiting.value) {
			resetPayment();
			resetDeposit();
		}
	} catch (e) {
		error.value = hotelErrorMessage(e);
	} finally {
		loading.value = false;
	}
}

let searchTimer = null;
let lastSearch = 0;

function onItemSearch() {
	clearTimeout(searchTimer);
	searchTimer = setTimeout(searchItems, 300);
}

async function searchItems() {
	const request = ++lastSearch;
	try {
		const rows = await searchFolioItemsApi(form.folio, itemQuery.value.trim());
		if (request === lastSearch) {
			itemResults.value = rows || [];
			itemSearched.value = true;
		}
	} catch (e) {
		error.value = hotelErrorMessage(e);
	}
}

async function chooseItem(item) {
	form.item = item;
	itemResults.value = [];
	try {
		const details = await fetchFolioItemRateApi(form.folio, item.name);
		form.chargeCode = details?.charge_code || null;
		form.rate = details?.rate || null;
	} catch (e) {
		form.item = null;
		error.value = hotelErrorMessage(e);
	}
}

function clearItem() {
	form.item = null;
	form.chargeCode = null;
	form.rate = null;
}

async function run(command) {
	busy.value = true;
	error.value = "";
	try {
		await command();
		await load();
		return true;
	} catch (e) {
		const message = hotelErrorMessage(e);
		// Reload first: loading clears the error, and the message must stay on screen.
		await load();
		error.value = message;
		return false;
	} finally {
		busy.value = false;
	}
}

async function postCharge() {
	const posted = await run(() =>
		postFolioChargeApi({
			folio: form.folio,
			item: form.item.name,
			quantity: form.quantity,
			rate: form.rate,
			stayGuest: form.stayGuest,
			notes: form.notes,
			reason: lateCharge.value ? form.reason : null,
			requestId: form.requestId,
		})
	);
	// After a failure the same request id is kept, so trying again can't post twice.
	if (posted) resetForm();
}

async function reverse(line) {
	const answer = await ask({
		tone: "danger",
		title: `Reverse "${line.description_snapshot}" (${money(line.gross_amount)})?`,
		message: "A reversing line is posted. The original line stays on the folio.",
		reasonLabel: "Reason for the reversal",
		confirmLabel: "Reverse",
	});
	if (answer) run(() => reverseFolioTransactionApi(line.name, answer.reason));
}

async function rebuild(folio) {
	let result = null;
	const checked = await run(async () => {
		result = await rebuildFolioBalanceApi(folio);
	});
	if (!checked || !result) return;
	notify(
		result.drift
			? {
					tone: "warning",
					title: "The folio balance was corrected",
					message: `It showed ${money(
						result.before.balance
					)}. It now matches the posted lines: ${money(result.after.balance)}.`,
			  }
			: {
					title: "The balance matches the posted lines",
					message: `${folio}: ${money(result.after.balance)}.`,
			  }
	);
}

onMounted(load);
onBeforeUnmount(() => clearTimeout(waitTimer));
watch(() => [route.params.stayId, route.params.accountId], load);
</script>

<style scoped>
.folio-input {
	@apply mt-1 w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[13px] text-on-surface;
}
</style>
