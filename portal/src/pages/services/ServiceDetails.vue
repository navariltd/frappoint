<template>
	<ServiceDetailsSkeleton v-if="loading && !serviceDetails" />

	<main v-else class="max-w-[1200px] mx-auto px-container-padding py-section-gap space-y-10">
		<ServiceHero
			v-if="serviceDetails"
			:service="serviceDetails"
			:selected-package="selectedPackage"
		/>

		<div
			v-if="error && !serviceDetails"
			class="rounded-3xl border border-red-200 bg-red-50 p-8 text-red-900"
		>
			<p class="font-headline-sm text-headline-sm">Unable to load service details</p>
			<p class="mt-2 text-body-md text-red-800">{{ error }}</p>
			<button
				class="mt-6 rounded-full bg-primary px-6 py-3 text-white font-semibold"
				type="button"
				@click="refreshServiceDetails"
			>
				Try again
			</button>
		</div>

		<div v-if="serviceDetails" class="grid grid-cols-1 lg:grid-cols-12 gap-stack-md lg:gap-16">
			<div class="lg:col-span-7 space-y-section-gap">
				<ServiceDescription :content="longDescription" />
				<section class="grid grid-cols-1 md:grid-cols-2 gap-stack-md">
					<ServiceBenefitsTable
						:items="formattedBenefits"
						:raw-html="serviceDetails?.benefits || ''"
					/>
					<ServiceTechniquesTable
						:items="formattedTechniques"
						:raw-html="serviceDetails?.techniques || ''"
					/>
				</section>
			</div>

			<aside class="lg:col-span-5">
				<div
					class="sticky top-28 bg-surface-container-lowest rounded-3xl p-8 shadow-[0px_12px_32px_rgba(45,52,54,0.08)] border border-outline-variant/20"
				>
					<h3 class="font-headline-md text-headline-md text-on-surface mb-6">
						Customize Your Ritual
					</h3>
					<div class="space-y-6">
						<ServicePackageSelector
							:packages="packages"
							:selected-package="selectedPackage"
							:service="serviceDetails"
							@select="selectPackage"
						/>
						<AddToBookingPanel
							:selected-package="selectedPackage"
							:service="serviceDetails"
							:busy="isAddingToBooking"
							:error="bookingError"
							@add="handleAddToBooking"
						/>
					</div>
				</div>
			</aside>
		</div>
	</main>
</template>

<script setup>
import AddToBookingPanel from "@/components/service-details/AddToBookingPanel.vue";
import ServiceBenefitsTable from "@/components/service-details/ServiceBenefitsTable.vue";
import ServiceDescription from "@/components/service-details/ServiceDescription.vue";
import ServiceDetailsSkeleton from "@/components/service-details/ServiceDetailsSkeleton.vue";
import ServiceHero from "@/components/service-details/ServiceHero.vue";
import ServicePackageSelector from "@/components/service-details/ServicePackageSelector.vue";
import ServiceTechniquesTable from "@/components/service-details/ServiceTechniquesTable.vue";
import { useServiceDetails } from "@/composables/useServiceDetails";

const {
	serviceDetails,
	loading,
	error,
	packages,
	selectedPackage,
	formattedBenefits,
	formattedTechniques,
	longDescription,
	isAddingToBooking,
	bookingError,
	selectPackage,
	handleAddToBooking,
	refreshServiceDetails,
} = useServiceDetails();
</script>
