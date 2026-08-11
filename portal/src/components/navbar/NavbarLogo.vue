<template>
	<RouterLink :to="{ name: 'Services' }" class="flex items-center gap-2">
		<img
			class="h-7 w-7 object-contain md:h-8 md:w-8"
			:src="branding.sidebarLogo || defaultLogo"
			:alt="`${branding.company} logo`"
		/>
		<span
			class="font-headline-md text-headline-md font-semibold text-primary dark:text-primary-fixed"
		>
			{{ branding.company }}
		</span>
	</RouterLink>
</template>

<script setup>
import { branding } from "@/branding";
import defaultLogo from "@/assets/images/logo_img.png";
</script>
