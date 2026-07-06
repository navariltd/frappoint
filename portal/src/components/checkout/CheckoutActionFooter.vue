<template>
	<div class="space-y-3">
		<div v-if="isMpesa" class="space-y-2">
			<label class="text-label-sm font-semibold text-on-surface-variant">
				Phone Number for M-Pesa
			</label>
			<input
				class="w-full px-4 py-3 rounded-xl border border-outline-variant bg-surface focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-body-md outline-none"
				placeholder="07XX XXX XXX"
				type="tel"
				:value="mpesaPhone"
				@input="$emit('updatePhone', ($event.target as HTMLInputElement).value)"
			/>
		</div>

		<button
			class="w-full bg-primary py-4 rounded-xl text-on-primary font-headline-sm shadow-lg hover:opacity-90 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
			:disabled="!canSubmit"
			@click="$emit('submit')"
			type="button"
		>
			<span
				v-if="submitting"
				class="w-5 h-5 rounded-full border-2 border-on-primary/40 border-t-on-primary animate-spin"
			></span>
			{{ label }}
		</button>

		<p class="text-label-sm text-center text-on-surface-variant/60">
			<span class="material-symbols-outlined text-[14px] align-middle mr-0.5">lock</span>
			Secured with SSL encryption
		</p>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	label: string;
	canSubmit: boolean;
	submitting: boolean;
	isMpesa: boolean;
	mpesaPhone: string;
}>();

defineEmits<{
	submit: [];
	updatePhone: [phone: string];
}>();
</script>
