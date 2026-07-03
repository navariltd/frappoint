<template>
	<div class="hidden md:flex items-center gap-4 relative z-[60]">
		<RouterLink
			v-if="!isLoggedIn"
			class="bg-primary/10 text-primary px-4 py-2 rounded-full font-label-md text-label-md hover:bg-primary/20 transition-colors"
			:to="{ name: 'Login' }"
		>
			Log In
		</RouterLink>

		<div v-else ref="menuRef" class="relative">
			<button
				type="button"
				class="w-10 h-10 rounded-full overflow-hidden border border-outline-variant/30 hover:ring-2 hover:ring-primary/30 transition-all"
				aria-label="User menu"
				@click="toggleMenu"
			>
				<img
					:src="userImage || defaultAvatar"
					alt="User profile"
					class="w-full h-full object-cover"
				/>
			</button>
			<Transition
				enter-active-class="transition-all duration-150 ease-out"
				enter-from-class="opacity-0 -translate-y-1"
				enter-to-class="opacity-100 translate-y-0"
				leave-active-class="transition-all duration-100 ease-in"
				leave-from-class="opacity-100 translate-y-0"
				leave-to-class="opacity-0 -translate-y-1"
			>
				<div
					v-if="menuOpen"
					class="absolute right-0 mt-2 w-44 rounded-xl border border-outline-variant/30 bg-surface shadow-lg overflow-hidden"
				>
					<button
						type="button"
						class="w-full px-4 py-2.5 text-left text-on-surface font-medium hover:bg-surface-container-high transition-colors"
						@click="onLogout"
					>
						Log Out
					</button>
				</div>
			</Transition>
		</div>
	</div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import defaultAvatar from "@/assets/images/profile-circle.svg";

defineProps({
	isLoggedIn: { type: Boolean, default: false },
	userImage: { type: String, default: "" },
});

const emit = defineEmits(["logout"]);

const menuRef = ref(null);
const menuOpen = ref(false);

function toggleMenu() {
	menuOpen.value = !menuOpen.value;
}

function onLogout() {
	menuOpen.value = false;
	emit("logout");
}

function onDocumentClick(event) {
	if (!menuRef.value?.contains(event.target)) {
		menuOpen.value = false;
	}
}

onMounted(() => {
	document.addEventListener("click", onDocumentClick);
});

onBeforeUnmount(() => {
	document.removeEventListener("click", onDocumentClick);
});
</script>
