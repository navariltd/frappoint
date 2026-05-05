<template>
	<section class="space-y-6">
		<div class="grid grid-cols-1 md:grid-cols-2 gap-5">
			<div class="flex flex-col gap-2 md:col-span-2">
				<label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1"
					>Full Name *</label
				>
				<input
					v-model="modelValue.guest_full_name"
					class="bg-slate-100 dark:bg-slate-800 border-2 border-transparent focus:border-primary/20 focus:bg-white dark:focus:bg-slate-900 rounded-xl p-4 text-sm outline-none transition-all"
					placeholder="e.g. Jane Doe"
					type="text"
				/>
			</div>

			<div class="flex flex-col gap-2">
				<label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1"
					>Email Address</label
				>
				<input
					v-model="modelValue.guest_email"
					class="bg-slate-100 dark:bg-slate-800 border-2 border-transparent focus:border-primary/20 focus:bg-white dark:focus:bg-slate-900 rounded-xl p-4 text-sm outline-none transition-all"
					placeholder="jane@example.com"
					type="email"
				/>
			</div>

			<div class="flex flex-col gap-2">
				<label class="text-[10px] font-bold uppercase tracking-widest text-slate-400 ml-1"
					>Mobile Number</label
				>
				<input
					v-model="modelValue.guest_mobile_no"
					class="bg-slate-100 dark:bg-slate-800 border-2 border-transparent focus:border-primary/20 focus:bg-white dark:focus:bg-slate-900 rounded-xl p-4 text-sm outline-none transition-all"
					placeholder="+254 700 000 000"
					type="tel"
				/>
			</div>
		</div>
	</section>
</template>

<script setup>
const props = defineProps(["modelValue"]);

function getInitials(name) {
	if (!name || typeof name !== "string") return "??";
	const parts = name.trim().split(" ");
	if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
	return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
</script>
