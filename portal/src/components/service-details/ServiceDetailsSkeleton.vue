<template>
	<main
		class="mx-auto max-w-7xl space-y-10 px-container-padding py-section-gap animate-pulse"
		aria-label="Loading service details"
	>
		<section
			class="flex min-h-[28rem] flex-col justify-end rounded-[2rem] bg-surface-container-high p-6 sm:p-10 lg:min-h-[34rem]"
		>
			<div class="grid items-end gap-8 lg:grid-cols-[minmax(0,1fr)_auto]">
				<div class="space-y-5">
					<div class="h-4 w-44 rounded-full bg-surface-container-highest"></div>
					<div class="h-12 w-3/4 rounded-xl bg-surface-container-highest"></div>
					<div class="h-5 w-2/3 rounded-full bg-surface-container-highest"></div>
					<div class="flex gap-2">
						<div
							v-for="index in 3"
							:key="index"
							class="h-8 w-24 rounded-full bg-surface-container-highest"
						></div>
					</div>
				</div>
				<div class="h-24 w-40 rounded-2xl bg-surface-container-lowest"></div>
			</div>
		</section>

		<div class="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-16">
			<div class="space-y-section-gap lg:col-span-7">
				<section class="space-y-4">
					<div class="h-8 w-56 rounded-full bg-surface-container-high"></div>
					<div class="space-y-3">
						<div class="h-4 w-full rounded-full bg-surface-container-high"></div>
						<div class="h-4 w-11/12 rounded-full bg-surface-container-high"></div>
						<div class="h-4 w-5/6 rounded-full bg-surface-container-high"></div>
					</div>
				</section>

				<section class="grid grid-cols-1 gap-stack-md md:grid-cols-2">
					<div
						v-for="index in 2"
						:key="index"
						class="h-56 rounded-xl bg-surface-container-high"
					></div>
				</section>
			</div>

			<aside class="lg:col-span-5">
				<div
					class="space-y-6 rounded-3xl border border-outline-variant/20 bg-surface-container-lowest p-8 shadow-xl shadow-primary/10"
				>
					<div class="h-8 w-64 rounded-full bg-surface-container-high"></div>
					<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
						<div
							v-for="index in 2"
							:key="index"
							class="h-24 rounded-xl bg-surface-container-high"
						></div>
					</div>
					<div class="h-16 rounded-xl bg-surface-container-high"></div>
					<div class="h-14 rounded-full bg-surface-container-high"></div>
				</div>
			</aside>
		</div>
	</main>
</template>

<script setup></script>
