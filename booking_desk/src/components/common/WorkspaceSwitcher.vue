<template>
	<div
		v-if="workspace.showSwitcher"
		role="tablist"
		aria-label="Workspace"
		class="grid grid-cols-2 gap-1 rounded-lg bg-black/20 p-1"
	>
		<button
			v-for="key in workspace.available"
			:key="key"
			type="button"
			role="tab"
			:aria-selected="workspace.active === key"
			class="flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-[13px] font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-secondary"
			:class="
				workspace.active === key
					? 'bg-white text-primary shadow-sm'
					: 'text-white/80 hover:bg-white/10 hover:text-white'
			"
			@click="open(key)"
		>
			<span class="material-symbols-outlined text-[18px]">{{ WORKSPACES[key].icon }}</span>
			{{ WORKSPACES[key].label }}
		</button>
	</div>
</template>

<script setup>
import { useRouter } from "vue-router";
import { WORKSPACES, useWorkspaceStore } from "@/stores/workspace.store";

const workspace = useWorkspaceStore();
const router = useRouter();

function open(key) {
	if (key === workspace.active) return;
	workspace.setActive(key);
	router.push(workspace.homeRoute(key));
}
</script>
