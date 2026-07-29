<template>
	<ServiceDetailsSkeleton v-if="loading && !serviceDetails" />

	<main v-else class="mx-auto max-w-7xl space-y-10 px-container-padding py-section-gap">
		<ServiceHero v-if="serviceDetails" :service="serviceDetails" />

		<div
			v-if="error && !serviceDetails"
			class="mx-auto max-w-2xl rounded-3xl border border-error/25 bg-error-container p-8 text-on-error-container"
		>
			<p class="font-headline-sm text-headline-sm">Unable to load service details</p>
			<p class="mt-2 text-body-md">{{ error }}</p>
			<div class="mt-6 flex flex-wrap gap-3">
				<button
					class="rounded-full bg-primary px-6 py-3 font-semibold text-on-primary hover:bg-primary-dark"
					type="button"
					@click="refreshServiceDetails"
				>
					Try again
				</button>
				<RouterLink
					:to="{ name: 'Services' }"
					class="rounded-full border border-outline px-6 py-3 font-semibold text-on-surface hover:border-primary hover:text-primary"
				>
					Back to services
				</RouterLink>
			</div>
		</div>

		<div v-if="serviceDetails" class="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-16">
			<div class="space-y-section-gap lg:col-span-7">
				<ServiceDescription
					v-if="longDescription"
					title="About the Service"
					:content="longDescription"
				/>
				<section
					v-if="formattedBenefits.length || formattedTechniques.length"
					class="grid grid-cols-1 gap-stack-md md:grid-cols-2"
				>
					<ServiceBenefitsTable
						v-if="formattedBenefits.length"
						:items="formattedBenefits"
					/>
					<ServiceTechniquesTable
						v-if="formattedTechniques.length"
						:items="formattedTechniques"
					/>
				</section>
			</div>

			<aside class="lg:col-span-5">
				<div
					class="sticky top-28 rounded-3xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-xl shadow-primary/10 sm:p-8"
				>
					<h3 class="font-headline-md text-headline-md text-on-surface mb-6">
						Customize Your Service
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
							:success="bookingSuccess"
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
	bookingSuccess,
	selectPackage,
	handleAddToBooking,
	refreshServiceDetails,
} = useServiceDetails();
</script>
