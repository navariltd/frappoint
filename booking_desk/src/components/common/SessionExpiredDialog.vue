<template>
	<div
		v-if="session.expired"
		class="fixed inset-0 z-[100] flex items-center justify-center bg-on-surface/40 px-4 backdrop-blur-[2px]"
	>
		<form
			role="dialog"
			aria-modal="true"
			aria-labelledby="session-expired-title"
			aria-describedby="session-expired-body"
			class="w-full max-w-[400px] space-y-4 rounded-2xl border border-outline-variant bg-surface-container-lowest p-6 shadow-xl"
			@submit.prevent="submit"
		>
			<div class="flex items-start gap-3">
				<span
					class="material-symbols-outlined mt-0.5 text-[22px] text-primary"
					aria-hidden="true"
					>lock_clock</span
				>
				<div>
					<h2
						id="session-expired-title"
						class="text-[17px] font-semibold text-on-surface"
					>
						You've been signed out
					</h2>
					<p id="session-expired-body" class="mt-1 text-[13px] text-on-surface-variant">
						Your session ended after a period of inactivity. Sign in again to carry on.
						This page and anything you've typed will stay as they are.
					</p>
				</div>
			</div>

			<label class="block text-[12px] font-semibold text-on-surface-variant">
				Email or username
				<input
					v-model="email"
					type="text"
					autocomplete="username"
					class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[14px] font-normal text-on-surface"
				/>
			</label>
			<label class="block text-[12px] font-semibold text-on-surface-variant">
				Password
				<input
					ref="passwordInput"
					v-model="password"
					type="password"
					autocomplete="current-password"
					class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-[14px] font-normal text-on-surface"
				/>
			</label>

			<p
				v-if="error"
				role="alert"
				class="rounded-lg bg-error-container/40 px-3 py-2 text-[12px] text-on-surface"
			>
				{{ error }}
			</p>

			<button
				type="submit"
				class="w-full rounded-lg bg-primary px-4 py-2.5 text-[13px] font-semibold text-on-primary disabled:opacity-50"
				:disabled="busy || !email.trim() || !password"
			>
				{{ busy ? "Signing in…" : "Sign in and continue" }}
			</button>
			<button
				type="button"
				class="w-full text-center text-[12px] font-semibold text-primary"
				:disabled="busy"
				@click="signInAsSomeoneElse"
			>
				Sign in as someone else
			</button>
		</form>
	</div>
</template>

<script setup>
import { nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { abandon, resume, session, signIn } from "@/utils/session";
import { readableError } from "@/utils/errorMessage";
import { navigateTo } from "@/utils";

const router = useRouter();
const email = ref("");
const password = ref("");
const busy = ref(false);
const error = ref("");
const passwordInput = ref(null);

watch(
	() => session.expired,
	async (expired) => {
		if (!expired) return;
		email.value = session.user || "";
		password.value = "";
		error.value = "";
		await nextTick();
		passwordInput.value?.focus();
	},
	{ immediate: true }
);

function here() {
	return `booking_desk${router.currentRoute.value.fullPath}`;
}

async function submit() {
	busy.value = true;
	error.value = "";
	try {
		const user = await signIn(email.value.trim(), password.value);
		if (user && user !== session.user) {
			// Another person's roles and properties: start their desk from scratch.
			abandon();
			window.location.assign("/booking_desk");
			return;
		}
		password.value = "";
		resume();
	} catch (e) {
		const status = e?.response?.status;
		error.value =
			status === 401
				? "That email and password don't match. Check them and try again."
				: readableError(e);
	} finally {
		busy.value = false;
	}
}

function signInAsSomeoneElse() {
	abandon();
	navigateTo("Login", { redirect: here() });
}
</script>
