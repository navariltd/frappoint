<template>
	<div>
		<p>Hello {{ userName }}</p>
	</div>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { computed } from "vue";

const auth = useAuthStore();

const userName = computed(() => auth.userName);
</script>
