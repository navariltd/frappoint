<template>
	<div class="space-y-3">
		<label
			v-for="gateway in gateways"
			:key="gateway"
			class="flex items-center gap-4 p-4 sm:p-5 border-2 rounded-xl sm:rounded-2xl cursor-pointer transition-all"
			:class="{
				'border-gray-200 hover:border-gray-300': !isSelected(gateway),
			}"
			:style="isSelected(gateway) ? selectedStyles(meta(gateway).color) : undefined"
		>
			<div
				class="flex items-center justify-center w-12 h-12 sm:w-14 sm:h-14 bg-white rounded-xl border border-gray-200 flex-shrink-0"
			>
				<component :is="meta(gateway).icon" v-if="meta(gateway).icon" />
				<span v-else class="text-sm font-semibold text-gray-700">
					{{ meta(gateway).label.charAt(0) }}
				</span>
			</div>
			<div class="flex-1 min-w-0">
				<h3
					class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-0.5"
				>
					{{ meta(gateway).label }}
				</h3>
				<p class="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
					{{ meta(gateway).description }}
				</p>
			</div>
			<div class="flex-shrink-0">
				<div
					class="w-5 h-5 sm:w-6 sm:h-6 rounded-full border-2 flex items-center justify-center transition-all"
					:style="
						isSelected(gateway)
							? {
									borderColor: meta(gateway).color,
									backgroundColor: meta(gateway).color,
							  }
							: undefined
					"
					:class="{ 'border-gray-300': !isSelected(gateway) }"
				>
					<div
						v-if="isSelected(gateway)"
						class="w-2 h-2 sm:w-2.5 sm:h-2.5 bg-white rounded-full"
					></div>
				</div>
			</div>
			<input
				type="radio"
				name="payment_gateway"
				:value="gateway"
				:checked="modelValue === gateway"
				@change="$emit('update:modelValue', gateway)"
				class="sr-only"
			/>
		</label>
	</div>
	<div v-if="!gateways?.length" class="text-sm text-gray-500">No payment methods available.</div>
</template>

<script setup>
import { computed } from "vue";
import MpesaIcon from "../icons/MpesaIcon.vue";
import PaypalIcon from "../icons/PaypalIcon.vue";

const props = defineProps({
	gateways: { type: Array, default: () => [] },
	modelValue: { type: String, default: null },
});

defineEmits(["update:modelValue"]);

function normalize(name) {
	return String(name || "").toLowerCase();
}

function meta(gateway) {
	const n = normalize(gateway);
	if (n.includes("mpesa") || n.includes("m-pesa") || n === "mpesa") {
		return {
			key: "mpesa",
			label: "M-Pesa",
			description: "Pay with your M-Pesa mobile money",
			color: "#16a34a",
			icon: MpesaIcon,
		};
	}
	if (n.includes("paypal")) {
		return {
			key: "paypal",
			label: "PayPal",
			description: "Pay safely with your PayPal account",
			color: "#0070ba",
			icon: PaypalIcon,
		};
	}
	return {
		key: n,
		label: gateway,
		description: "Pay securely with this method",
		color: "rgb(var(--color-primary))",
		icon: null,
	};
}

function isSelected(gateway) {
	return props.modelValue === gateway;
}

function selectedStyles(hex) {
	return {
		borderColor: hex,
		backgroundColor: hexToRgba(hex, 0.05),
	};
}

function hexToRgba(hex, alpha = 1) {
	const h = hex.replace("#", "");
	const bigint = parseInt(
		h.length === 3
			? h
					.split("")
					.map((c) => c + c)
					.join("")
			: h,
		16
	);
	const r = (bigint >> 16) & 255;
	const g = (bigint >> 8) & 255;
	const b = bigint & 255;
	return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// expose meta for template usage
const metaComputed = computed(() => meta);
</script>
