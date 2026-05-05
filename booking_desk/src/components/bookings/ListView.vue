<template>
	<div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
		<table class="w-full text-left border-collapse">
			<thead>
				<tr class="bg-gray-50/50 border-b border-gray-100">
					<th
						class="px-6 py-4 text-slate-500 text-[11px] font-bold uppercase tracking-widest"
					>
						Customer
					</th>
					<th
						class="px-6 py-4 text-slate-500 text-[11px] font-bold uppercase tracking-widest"
					>
						Schedule
					</th>
					<th
						class="px-6 py-4 text-slate-500 text-[11px] font-bold uppercase tracking-widest hidden sm:table-cell"
					>
						Service
					</th>
					<th
						class="px-6 py-4 text-slate-500 text-[11px] font-bold uppercase tracking-widest hidden md:table-cell"
					>
						Provider
					</th>
					<th
						class="px-6 py-4 text-slate-500 text-[11px] font-bold uppercase tracking-widest"
					>
						Status
					</th>
					<th
						class="px-6 py-4 text-right text-slate-500 text-[11px] font-bold uppercase tracking-widest"
					>
						Actions
					</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-50">
				<tr
					v-for="item in data"
					:key="item.name"
					class="hover:bg-blue-50/30 transition-colors group"
				>
					<td class="px-6 py-4">
						<div class="flex items-center gap-3">
							<div
								class="h-9 w-9 shrink-0 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs border border-primary/5"
							>
								{{ getInitials(item.full_name || "U") }}
							</div>
							<div class="flex flex-col min-w-0">
								<span class="text-sm font-semibold text-slate-900 truncate">{{
									item.full_name
								}}</span>
								<span class="text-[11px] font-mono text-slate-400 uppercase">{{
									item.name
								}}</span>
							</div>
						</div>
					</td>

					<td class="px-6 py-4">
						<div class="flex flex-col">
							<span class="text-sm font-medium text-slate-700">{{
								formatTime(item.start_time, item.end_time)
							}}</span>
							<span class="text-xs text-slate-400">{{ item.appointment_date }}</span>
						</div>
					</td>

					<td class="px-6 py-4 hidden sm:table-cell">
						<span class="text-sm text-slate-600">{{ item.appointment_type }}</span>
					</td>

					<td class="px-6 py-4 hidden md:table-cell">
						<div class="flex items-center gap-2">
							<div class="w-1.5 h-1.5 rounded-full bg-slate-300"></div>
							<span class="text-sm text-slate-600">{{
								item.service_provider_name
							}}</span>
						</div>
					</td>

					<td class="px-6 py-4">
						<span
							class="bg-emerald-100 text-emerald-800"
							:class="getStatusClasses(item.status)"
						>
							<span class="w-1 h-1 rounded-full bg-current mr-1.5"></span>
							{{ item.status }}
						</span>
					</td>

					<td class="px-6 py-4 text-right">
						<div
							class="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
						>
							<button
								@click="$emit('edit', item)"
								class="p-2 text-slate-400 hover:text-primary hover:bg-white hover:shadow-sm rounded-lg border border-transparent hover:border-gray-100 transition-all"
							>
								<span class="material-symbols-outlined text-[18px]">edit</span>
							</button>
							<button
								class="p-2 text-slate-400 hover:text-slate-600 hover:bg-white hover:shadow-sm rounded-lg border border-transparent hover:border-gray-100 transition-all"
							>
								<span class="material-symbols-outlined text-[18px]"
									>more_vert</span
								>
							</button>
						</div>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
defineProps({ data: { type: Array, required: true } });
defineEmits(["edit"]);

function getInitials(name) {
	return name
		.split(" ")
		.map((n) => n[0])
		.join("")
		.toUpperCase()
		.substring(0, 2);
}

function formatTime(start, end) {
	// Removes seconds if present (e.g. 09:00:00 -> 09:00)
	const s = start.split(":").slice(0, 2).join(":");
	const e = end.split(":").slice(0, 2).join(":");
	return `${s} - ${e}`;
}

function getStatusClasses(status) {
	const base = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ";
	const colors = {
		Confirmed: "bg-green-100 text-green-800",
		Open: "bg-blue-100 text-blue-800",
		Completed: "bg-gray-100 text-gray-800",
		Cancelled: "bg-red-100 text-red-800",
	};
	return base + (colors[status] || "bg-gray-100 text-gray-800");
}
</script>
