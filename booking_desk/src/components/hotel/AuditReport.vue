<template>
	<div class="space-y-4">
		<!-- The day in four numbers -->
		<div class="grid gap-3 grid-cols-2 lg:grid-cols-4">
			<div
				v-for="tile in tiles"
				:key="tile.label"
				class="rounded-xl border border-outline-variant bg-surface-container-lowest px-4 py-3"
			>
				<p class="text-[11px] text-on-surface-variant">{{ tile.label }}</p>
				<p class="text-[20px] font-semibold tabular-nums">{{ tile.value }}</p>
				<p v-if="tile.note" class="text-[11px] text-on-surface-variant">{{ tile.note }}</p>
			</div>
		</div>

		<p class="text-[12px] text-on-surface-variant">
			{{ rooms.arrivals }} arrival{{ rooms.arrivals === 1 ? "" : "s" }} ·
			{{ rooms.departures }} departure{{ rooms.departures === 1 ? "" : "s" }} ·
			{{ rooms.in_house }} in house · {{ rooms.no_shows }} no-show{{
				rooms.no_shows === 1 ? "" : "s"
			}}
			· {{ rooms.cancellations }} cancellation{{ rooms.cancellations === 1 ? "" : "s" }}
		</p>

		<div class="grid gap-4 lg:grid-cols-2">
			<section class="space-y-1.5">
				<h3 class="text-[13px] font-semibold">Revenue by charge code</h3>
				<p v-if="!report.revenue.length" class="text-[12px] text-on-surface-variant">
					Nothing posted.
				</p>
				<table v-else class="w-full text-[12px]">
					<thead class="text-on-surface-variant">
						<tr class="border-b border-outline-variant">
							<th class="py-1 text-left font-semibold">Charge</th>
							<th class="py-1 text-right font-semibold">Net</th>
							<th class="py-1 text-right font-semibold">Tax</th>
							<th class="py-1 text-right font-semibold">Gross</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in report.revenue"
							:key="row.charge_code"
							class="border-b border-outline-variant/60"
						>
							<td class="py-1">{{ row.description }}</td>
							<td class="py-1 text-right tabular-nums">{{ money(row.net) }}</td>
							<td class="py-1 text-right tabular-nums">{{ money(row.tax) }}</td>
							<td class="py-1 text-right tabular-nums">{{ money(row.gross) }}</td>
						</tr>
						<tr class="font-semibold">
							<td class="py-1">Total</td>
							<td class="py-1 text-right tabular-nums">
								{{ money(sum(report.revenue, "net")) }}
							</td>
							<td class="py-1 text-right tabular-nums">
								{{ money(sum(report.revenue, "tax")) }}
							</td>
							<td class="py-1 text-right tabular-nums">
								{{ money(sum(report.revenue, "gross")) }}
							</td>
						</tr>
					</tbody>
				</table>
			</section>

			<section class="space-y-1.5">
				<h3 class="text-[13px] font-semibold">Payments taken</h3>
				<p v-if="!report.payments.length" class="text-[12px] text-on-surface-variant">
					No payments.
				</p>
				<table v-else class="w-full text-[12px]">
					<tbody>
						<tr
							v-for="row in report.payments"
							:key="row.charge_code"
							class="border-b border-outline-variant/60"
						>
							<td class="py-1">{{ row.charge_code }}</td>
							<td class="py-1 text-right text-on-surface-variant">
								{{ row.lines }} line{{ row.lines === 1 ? "" : "s" }}
							</td>
							<td class="py-1 text-right tabular-nums">{{ money(row.amount) }}</td>
						</tr>
						<tr class="font-semibold">
							<td class="py-1" colspan="2">Total</td>
							<td class="py-1 text-right tabular-nums">
								{{ money(sum(report.payments, "amount")) }}
							</td>
						</tr>
					</tbody>
				</table>

				<h3 class="pt-2 text-[13px] font-semibold">Guest ledger</h3>
				<table class="w-full text-[12px]">
					<tbody>
						<tr
							v-for="row in report.ledger"
							:key="row.group"
							class="border-b border-outline-variant/60"
						>
							<td class="py-1">{{ row.group }}</td>
							<td class="py-1 text-right text-on-surface-variant">
								{{ row.folios }} folio{{ row.folios === 1 ? "" : "s" }}
							</td>
							<td class="py-1 text-right tabular-nums">{{ money(row.balance) }}</td>
						</tr>
						<tr class="font-semibold">
							<td class="py-1" colspan="2">Owed to the hotel</td>
							<td class="py-1 text-right tabular-nums">
								{{ money(sum(report.ledger, "balance")) }}
							</td>
						</tr>
						<tr>
							<td class="py-1" colspan="2">
								Deposits held ({{ report.deposits.deposits }})
							</td>
							<td class="py-1 text-right tabular-nums">
								{{ money(report.deposits.held) }}
							</td>
						</tr>
					</tbody>
				</table>
			</section>
		</div>

		<!-- What the night let through -->
		<section v-if="exceptions" class="space-y-1.5">
			<h3 class="text-[13px] font-semibold">Exceptions</h3>
			<ul class="space-y-1 text-[12px]">
				<li v-for="row in report.overrides" :key="`o-${row.check}`">
					<b>{{ row.check }}</b> ({{ row.found }}) let pass by {{ row.by }} as
					{{ row.role }}: {{ row.reason }}
				</li>
				<li v-for="row in report.warnings" :key="`w-${row.check}`">
					<b>{{ row.check }}</b> ({{ row.count }}): {{ row.items.join("; ") }}
				</li>
				<li v-for="text in report.differences" :key="`d-${text}`" class="text-error">
					{{ text }}
				</li>
			</ul>
		</section>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { formatMoney } from "@/utils/hotelFormat";

// A night audit's stored report: the closed day's figures as they were at the audit.
const props = defineProps({
	report: { type: Object, required: true },
});

const rooms = computed(() => props.report.rooms || {});
const money = (value) => formatMoney(value, props.report.currency);
const sum = (rows, field) => rows.reduce((total, row) => total + Number(row[field] || 0), 0);
const exceptions = computed(
	() =>
		props.report.overrides?.length ||
		props.report.warnings?.length ||
		props.report.differences?.length
);
const tiles = computed(() => [
	{
		label: "Occupancy",
		value: `${rooms.value.occupancy}%`,
		note: `${rooms.value.rooms_sold} of ${rooms.value.rooms_available} rooms`,
	},
	{
		label: "ADR",
		value: money(rooms.value.adr),
		note: rooms.value.complimentary ? `${rooms.value.complimentary} complimentary` : "",
	},
	{ label: "RevPAR", value: money(rooms.value.revpar) },
	{ label: "Room revenue", value: money(rooms.value.room_revenue), note: "Net of tax" },
]);
</script>
