<template>
	<section class="space-y-4">
		<h2 class="font-headline-md text-headline-md text-on-surface">{{ title }}</h2>
		<div
			class="space-y-4 text-on-surface-variant font-body-md text-body-md leading-relaxed [&_p]:mb-4 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5"
			v-html="content"
		></div>
	</section>
</template>

<script setup>
defineProps({
	title: {
		type: String,
		default: "About the Ritual",
	},
	content: {
		type: String,
		default: "",
	},
});
</script>
