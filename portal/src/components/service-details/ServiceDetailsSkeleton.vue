<template>
	<main
		class="max-w-[1200px] mx-auto px-container-padding py-section-gap space-y-10 animate-pulse"
	>
		<section
			class="rounded-[2rem] border border-outline-variant/20 bg-surface-container-lowest p-8 shadow-[0px_18px_42px_rgba(45,52,54,0.12)]"
		>
			<div class="h-4 w-40 rounded-full bg-surface-container-high"></div>
			<div class="mt-6 h-12 w-3/4 rounded-2xl bg-surface-container-high"></div>
			<div class="mt-4 h-5 w-2/3 rounded-full bg-surface-container-high"></div>
			<div class="mt-8 flex flex-wrap gap-2">
				<div
					v-for="index in 4"
					:key="index"
					class="h-8 w-24 rounded-full bg-surface-container-high"
				></div>
			</div>
		</section>

		<div class="grid grid-cols-1 lg:grid-cols-12 gap-stack-md lg:gap-16">
			<div class="lg:col-span-7 space-y-section-gap">
				<section
					class="space-y-4 rounded-3xl border border-outline-variant/20 bg-surface-container-low p-6"
				>
					<div class="h-8 w-56 rounded-full bg-surface-container-high"></div>
					<div class="space-y-3">
						<div class="h-4 w-full rounded-full bg-surface-container-high"></div>
						<div class="h-4 w-11/12 rounded-full bg-surface-container-high"></div>
						<div class="h-4 w-5/6 rounded-full bg-surface-container-high"></div>
					</div>
				</section>

				<section class="grid grid-cols-1 md:grid-cols-2 gap-stack-md">
					<div
						class="rounded-xl border border-outline-variant/30 bg-surface-container-low p-6"
					>
						<div class="h-6 w-24 rounded-full bg-surface-container-high"></div>
						<div class="mt-5 space-y-3">
							<div
								v-for="index in 4"
								:key="index"
								class="h-4 w-full rounded-full bg-surface-container-high"
							></div>
						</div>
					</div>
					<div
						class="rounded-xl border border-outline-variant/30 bg-surface-container-low p-6"
					>
						<div class="h-6 w-28 rounded-full bg-surface-container-high"></div>
						<div class="mt-5 space-y-3">
							<div
								v-for="index in 4"
								:key="index"
								class="h-4 w-full rounded-full bg-surface-container-high"
							></div>
						</div>
					</div>
				</section>
			</div>

			<aside class="lg:col-span-5">
				<div
					class="sticky top-28 space-y-6 rounded-3xl border border-outline-variant/20 bg-surface-container-lowest p-8 shadow-[0px_12px_32px_rgba(45,52,54,0.08)]"
				>
					<div class="h-8 w-64 rounded-full bg-surface-container-high"></div>
					<div class="space-y-4">
						<div class="rounded-2xl border border-outline-variant/30 p-4">
							<div class="h-5 w-32 rounded-full bg-surface-container-high"></div>
							<div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
								<div
									v-for="index in 2"
									:key="index"
									class="h-24 rounded-2xl bg-surface-container-high"
								></div>
							</div>
						</div>
						<div class="rounded-2xl border border-outline-variant/30 p-4">
							<div class="h-6 w-24 rounded-full bg-surface-container-high"></div>
							<div class="mt-4 h-10 rounded-full bg-surface-container-high"></div>
							<div class="mt-3 h-12 rounded-full bg-surface-container-high"></div>
						</div>
					</div>
				</div>
			</aside>
		</div>
	</main>
</template>

<script setup></script>
