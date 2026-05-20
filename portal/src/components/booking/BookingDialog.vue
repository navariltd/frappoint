<template>
	<!-- TopAppBar -->
	<header
		class="bg-surface dark:bg-background shadow-sm docked full-width top-0 z-50 flex justify-between items-center h-16 px-gutter w-full max-w-[1440px] mx-auto"
	>
		<div class="flex items-center gap-4">
			<span
				class="font-headline-md text-headline-md font-semibold text-primary dark:text-inverse-primary"
				>Frappoint</span
			>
		</div>
		<div class="flex items-center gap-4">
			<span class="material-symbols-outlined text-primary cursor-pointer"
				>notifications</span
			>
			<span class="material-symbols-outlined text-primary cursor-pointer"
				>account_circle</span
			>
		</div>
	</header>
	<div class="flex flex-1 overflow-hidden">
		<!-- LEFT PANEL: Navigation -->
		<aside
			class="fixed left-0 top-16 bottom-0 flex flex-col p-4 w-72 z-40 bg-surface-container-low dark:bg-surface-container-lowest border-r border-outline-variant"
		>
			<div class="mb-6 px-2">
				<h2 class="font-headline-sm text-headline-sm text-primary">Booking Session</h2>
				<p class="font-label-sm text-label-sm text-on-surface-variant opacity-70">
					3 Services in progress
				</p>
			</div>
			<nav class="space-y-3 flex-1 overflow-y-auto">
				<!-- Deep Tissue Massage [Active] -->
				<div
					class="text-primary dark:text-inverse-primary font-bold bg-secondary-container/30 dark:bg-secondary-container/10 rounded-lg p-3 spa-card border-none"
				>
					<div class="flex justify-between items-start mb-1">
						<span class="font-label-md text-label-md uppercase tracking-wider"
							>Active</span
						>
						<span
							class="material-symbols-outlined text-primary"
							style="font-variation-settings: 'FILL' 1"
							>spa</span
						>
					</div>
					<p class="font-headline-sm text-headline-sm leading-tight mb-2">
						Deep Tissue Massage
					</p>
					<div class="flex items-center gap-4 text-on-surface-variant">
						<div class="flex items-center gap-1">
							<span class="material-symbols-outlined text-[16px]">groups</span>
							<span class="text-xs">4 Guests</span>
						</div>
						<div class="flex items-center gap-1">
							<span class="material-symbols-outlined text-[16px]"
								>pending_actions</span
							>
							<span class="text-xs">Incomplete</span>
						</div>
					</div>
				</div>
				<!-- Back Massage [Pending] -->
				<div
					class="text-on-surface-variant dark:text-surface-variant font-medium p-3 hover:bg-surface-container-high transition-all rounded-lg cursor-pointer"
				>
					<div class="flex justify-between items-start mb-1 opacity-60">
						<span class="font-label-sm text-label-sm">Pending</span>
						<span class="material-symbols-outlined">calendar_today</span>
					</div>
					<p class="font-body-md text-body-md font-semibold">Back Massage</p>
					<div class="flex items-center gap-1 mt-1 opacity-60">
						<span class="material-symbols-outlined text-[14px]">groups</span>
						<span class="text-xs">2 Guests</span>
					</div>
				</div>
				<!-- Facial Treatment [Pending] -->
				<div
					class="text-on-surface-variant dark:text-surface-variant font-medium p-3 hover:bg-surface-container-high transition-all rounded-lg cursor-pointer"
				>
					<div class="flex justify-between items-start mb-1 opacity-60">
						<span class="font-label-sm text-label-sm">Pending</span>
						<span class="material-symbols-outlined">spa</span>
					</div>
					<p class="font-body-md text-body-md font-semibold">Facial Treatment</p>
					<div class="flex items-center gap-1 mt-1 opacity-60">
						<span class="material-symbols-outlined text-[14px]">groups</span>
						<span class="text-xs">1 Guest</span>
					</div>
				</div>
			</nav>
			<div class="mt-auto pt-4 border-t border-outline-variant space-y-2">
				<button
					class="w-full flex items-center gap-3 p-2 rounded-lg text-on-surface-variant hover:bg-surface-container-high"
				>
					<span class="material-symbols-outlined">settings</span>
					<span class="font-label-md text-label-md">Settings</span>
				</button>
				<button
					class="w-full flex items-center gap-3 p-2 rounded-lg text-on-surface-variant hover:bg-surface-container-high"
				>
					<span class="material-symbols-outlined">help_outline</span>
					<span class="font-label-md text-label-md">Help</span>
				</button>
			</div>
		</aside>
		<!-- CENTER PANEL: Active Workspace -->
		<main class="ml-72 mr-[320px] flex-1 h-full overflow-y-auto bg-surface-bright">
			<div class="max-w-[800px] mx-auto px-10 py-12">
				<header class="mb-10">
					<div class="flex items-center gap-2 text-primary mb-2">
						<span class="material-symbols-outlined">arrow_back</span>
						<span class="font-label-md text-label-md">Service Dashboard</span>
					</div>
					<h1 class="font-headline-lg text-headline-lg text-primary">
						Deep Tissue Massage
					</h1>
					<p class="font-body-lg text-body-lg text-on-surface-variant">
						Configure your therapy details, guest allocations, and scheduling
						preferences.
					</p>
				</header>
				<div class="space-y-section-gap">
					<!-- STEP A: Package Selection -->
					<section>
						<div class="flex items-center gap-3 mb-6">
							<span
								class="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-white font-bold text-sm"
								>A</span
							>
							<h3 class="font-headline-sm text-headline-sm">Package Selection</h3>
						</div>
						<div class="grid grid-cols-2 gap-6">
							<div
								class="spa-card rounded-2xl p-6 active-ring border-primary/20 relative group cursor-pointer overflow-hidden"
							>
								<div class="absolute top-0 right-0 p-3">
									<span
										class="material-symbols-outlined text-primary"
										style="font-variation-settings: 'FILL' 1"
										>check_circle</span
									>
								</div>
								<h4 class="font-headline-sm text-headline-sm text-primary mb-1">
									Essential Relief
								</h4>
								<p class="text-on-surface-variant text-sm mb-4">
									Focused therapy for major muscle groups.
								</p>
								<div class="flex items-end justify-between">
									<div class="flex flex-col">
										<span class="font-label-sm text-label-sm opacity-60"
											>Duration</span
										>
										<span class="font-body-md text-body-md font-semibold"
											>30 Minutes</span
										>
									</div>
									<div class="text-right">
										<span
											class="font-headline-sm text-headline-sm text-primary"
											>KES 4,500</span
										>
									</div>
								</div>
							</div>
							<div
								class="spa-card rounded-2xl p-6 hover:border-primary/40 cursor-pointer overflow-hidden"
							>
								<h4 class="font-headline-sm text-headline-sm text-on-surface mb-1">
									Deep Restoration
								</h4>
								<p class="text-on-surface-variant text-sm mb-4">
									Full body reset with targeted intensity.
								</p>
								<div class="flex items-end justify-between">
									<div class="flex flex-col">
										<span class="font-label-sm text-label-sm opacity-60"
											>Duration</span
										>
										<span class="font-body-md text-body-md font-semibold"
											>60 Minutes</span
										>
									</div>
									<div class="text-right">
										<span class="font-headline-sm text-headline-sm"
											>KES 8,000</span
										>
									</div>
								</div>
							</div>
						</div>
					</section>
					<!-- STEP B: Guest Population -->
					<section>
						<div class="flex items-center gap-3 mb-6">
							<span
								class="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-white font-bold text-sm"
								>B</span
							>
							<h3 class="font-headline-sm text-headline-sm">Guest Population</h3>
						</div>
						<div class="grid grid-cols-2 gap-4">
							<!-- Guest 1 -->
							<div class="spa-card rounded-xl p-4 flex items-center gap-4">
								<img
									class="w-12 h-12 rounded-full object-cover"
									data-alt="A professional headshot of a woman with a serene expression, Sarah J., in a high-key studio setting. The lighting is soft and flattering, reflecting a luxury wellness brand aesthetic. The background is a clean, minimalist off-white, maintaining the brand's quiet luxury tone."
									src="https://lh3.googleusercontent.com/aida-public/AB6AXuBIaZl2epibCKPK7TuCUKVrRM8b2OOzTrFD7uIsfIM3PRTDj1tdMmQjjoeuv_UBqpU59DMld-Qdpak_FBgtBmIoD-fjze90yMxTHb81sF-Qys3K-zan0HpQfTbVf7sls0-5N_ftB5D2OqCm0xVJ44fWqNC850soTyZHr6_Omefcgn7BahuOi3BagvMI1AgC4LNYN6OqofodZUcSeWlmV755ZZAn2cWybmgn9hsnSbfS8J6NP4XYS6zGC8WU_oip_msM0snf-zzgJNkL"
								/>
								<div class="flex-1">
									<p class="font-label-md text-label-md text-primary">
										Sarah J.
									</p>
									<p class="font-label-sm text-label-sm opacity-60">
										Guest 1 • Primary
									</p>
								</div>
								<span class="material-symbols-outlined text-outline cursor-pointer"
									>edit</span
								>
							</div>
							<!-- Guest 2 -->
							<div class="spa-card rounded-xl p-4 flex items-center gap-4">
								<img
									class="w-12 h-12 rounded-full object-cover"
									data-alt="A professional headshot of a man with a gentle smile, Michael C., in a modern studio environment. The image is brightly lit with a soft-box effect, emphasizing a clean and premium feel. The color palette is neutral with soft shadows, consistent with a high-end wellness platform."
									src="https://lh3.googleusercontent.com/aida-public/AB6AXuAugeYNg9hPenpAk8HJ4-BrmIj2ulB7z4uBFWy-MWDX_3N567D2H5jazJFgWNz3f0jtFSNbEq6sVO3H_YdrfnwVxqANzK37-zM1WTW9SFQI6xvJzw-SUEd5JtyZVtLytw6gL3Gubx36Dc7ej8VKa9bY8hSBK-cun9Jtrw9dHa8aCjRV6GqtLpqI_0A1A71Ecgx4qoUVqIGffdih7yJG5qVlyTA_WZsrUDUiyzF7lbavyUag0NSWwt_zFB-64uR4P0r7aCYFL0_KFB7J"
								/>
								<div class="flex-1">
									<p class="font-label-md text-label-md text-primary">
										Michael C.
									</p>
									<p class="font-label-sm text-label-sm opacity-60">Guest 2</p>
								</div>
								<span class="material-symbols-outlined text-outline cursor-pointer"
									>edit</span
								>
							</div>
							<!-- Empty Slots -->
							<button
								class="spa-card rounded-xl p-4 flex items-center gap-4 border-dashed border-2 border-outline-variant bg-transparent hover:bg-surface-container-low"
							>
								<div
									class="w-12 h-12 rounded-full bg-surface-container-highest flex items-center justify-center text-outline"
								>
									<span class="material-symbols-outlined">person_add</span>
								</div>
								<div class="flex-1 text-left">
									<p class="font-label-md text-label-md text-outline">
										Select Guest
									</p>
									<p class="font-label-sm text-label-sm opacity-60">
										Guest 3 • Empty
									</p>
								</div>
							</button>
							<button
								class="spa-card rounded-xl p-4 flex items-center gap-4 border-dashed border-2 border-outline-variant bg-transparent hover:bg-surface-container-low"
							>
								<div
									class="w-12 h-12 rounded-full bg-surface-container-highest flex items-center justify-center text-outline"
								>
									<span class="material-symbols-outlined">person_add</span>
								</div>
								<div class="flex-1 text-left">
									<p class="font-label-md text-label-md text-outline">
										Select Guest
									</p>
									<p class="font-label-sm text-label-sm opacity-60">
										Guest 4 • Empty
									</p>
								</div>
							</button>
						</div>
					</section>
					<!-- STEP C: Scheduling Preference -->
					<section>
						<div class="flex items-center gap-3 mb-6">
							<span
								class="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-white font-bold text-sm"
								>C</span
							>
							<h3 class="font-headline-sm text-headline-sm">
								Scheduling Preference
							</h3>
						</div>
						<div class="flex flex-wrap gap-3">
							<button
								class="px-6 py-2 rounded-full bg-secondary-container text-on-secondary-container border border-secondary font-label-md text-label-md"
							>
								Keep Together
							</button>
							<button
								class="px-6 py-2 rounded-full bg-surface text-on-surface-variant border border-outline-variant font-label-md text-label-md hover:bg-surface-container-high transition-colors"
							>
								Spread Apart
							</button>
							<button
								class="px-6 py-2 rounded-full bg-surface text-on-surface-variant border border-outline-variant font-label-md text-label-md hover:bg-surface-container-high transition-colors"
							>
								Auto-Optimize
							</button>
						</div>
					</section>
					<!-- STEP D: Slot Allocation -->
					<section>
						<div class="flex items-center gap-3 mb-6">
							<span
								class="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-white font-bold text-sm"
								>D</span
							>
							<h3 class="font-headline-sm text-headline-sm">Slot Allocation</h3>
						</div>
						<div class="space-y-4">
							<!-- Slot 1 -->
							<div class="spa-card rounded-2xl overflow-hidden">
								<div
									class="p-4 bg-surface-container flex justify-between items-center"
								>
									<div class="flex items-center gap-3">
										<span class="material-symbols-outlined text-primary"
											>schedule</span
										>
										<span class="font-label-md text-label-md"
											>10:00 AM Slot</span
										>
									</div>
									<span
										class="px-3 py-1 rounded-full bg-secondary-container text-[10px] uppercase font-bold tracking-widest text-on-secondary-container"
										>Fully Allocated</span
									>
								</div>
								<div class="p-6">
									<div class="flex items-center justify-between mb-4">
										<div class="flex -space-x-3">
											<img
												class="w-10 h-10 rounded-full border-2 border-white"
												data-alt="Portrait of Sarah J."
												src="https://lh3.googleusercontent.com/aida-public/AB6AXuCgHzQf1QW7P4sxz2P7MkKw1LwoLf2asDvAeBZgHXi3ILw_-gNO60z8XUNINyLGMDhAEvWpdqkclrHAxwsWuKwpUOJIRIUJgG4ovc2nmBXqvXMPAq4ymw35czhRYOU3DYB57CtAB8F_6p3KENt5D3O1WpYULcoRR9j45sS6RfZhbZD-x2fsaSwfWptKXgyf-T-wQTy8o7BXNkXkIF_VVBKtnpPG--EAGuaRYIZ9uP8WTM5Vt8ZW1Xvb5OmZ1xzsCSwRalIksQVpmuQF"
											/>
											<img
												class="w-10 h-10 rounded-full border-2 border-white"
												data-alt="Portrait of Michael C."
												src="https://lh3.googleusercontent.com/aida-public/AB6AXuDhJLqgj7wKHPC28ucWjlrnjUdsC-SefdvwptJVpKrRWBoafVCZIYMkbozepon2Xmuwhp0HD9ghDQMx3oZE1RX2fixeEj_n_RJxrDtBs6MkIZ_pDq0_Mypa1sX0dF7WWJ6uaOyKJHHzOmgOs2cNk2UQPkDbQ0z34VuW3YsSZOy30WuHje_glwtg72tYenzmMXWFhdIGGQBRjHn1Qn9EndtNxIWIa-TV4nNNFYsI7pluDsRGmRUF_1nL0-87dbjCsUtKRxuhIm3XA5RX"
											/>
										</div>
										<div class="text-right">
											<p
												class="font-label-sm text-label-sm text-on-surface-variant"
											>
												Capacity
											</p>
											<p
												class="font-body-md text-body-md font-bold text-primary"
											>
												2/2 Guests Assigned
											</p>
										</div>
									</div>
									<div
										class="flex items-center gap-2 text-on-surface-variant text-sm"
									>
										<span class="material-symbols-outlined text-sm"
											>person_check</span
										>
										<span>2 Providers Available (Maria, David)</span>
									</div>
								</div>
							</div>
							<!-- Slot 2 -->
							<div class="spa-card rounded-2xl overflow-hidden opacity-60">
								<div
									class="p-4 bg-surface-container-high flex justify-between items-center"
								>
									<div class="flex items-center gap-3">
										<span class="material-symbols-outlined">schedule</span>
										<span class="font-label-md text-label-md"
											>11:30 AM Slot</span
										>
									</div>
									<span
										class="px-3 py-1 rounded-full bg-surface-variant text-[10px] uppercase font-bold tracking-widest text-on-surface-variant"
										>Unallocated</span
									>
								</div>
								<div class="p-6">
									<div class="flex items-center justify-between mb-4">
										<div
											class="w-10 h-10 rounded-full bg-surface-container-highest border-2 border-dashed border-outline-variant flex items-center justify-center"
										>
											<span class="material-symbols-outlined text-sm"
												>add</span
											>
										</div>
										<div class="text-right">
											<p
												class="font-label-sm text-label-sm text-on-surface-variant"
											>
												Capacity
											</p>
											<p class="font-body-md text-body-md font-bold">
												0/2 Guests Assigned
											</p>
										</div>
									</div>
									<div
										class="flex items-center gap-2 text-on-surface-variant text-sm"
									>
										<span class="material-symbols-outlined text-sm"
											>person_check</span
										>
										<span>2 Providers Available</span>
									</div>
								</div>
							</div>
						</div>
					</section>
					<!-- STEP E: Validation -->
					<section class="mt-12">
						<div
							class="p-4 rounded-xl bg-primary-container/10 border border-primary-container/20 flex items-center gap-4"
						>
							<span class="material-symbols-outlined text-primary">info</span>
							<div class="flex-1">
								<p class="font-label-md text-label-md text-on-primary-container">
									Configuration Status
								</p>
								<p
									class="font-label-sm text-label-sm text-on-primary-container/70"
								>
									2 / 4 guests assigned. 1 additional slot group required.
								</p>
							</div>
							<div
								class="w-24 h-2 bg-surface-container-highest rounded-full overflow-hidden"
							>
								<div class="bg-primary h-full w-[50%]"></div>
							</div>
						</div>
					</section>
				</div>
			</div>
		</main>
		<!-- RIGHT PANEL: Summary -->
		<aside
			class="fixed right-0 top-16 bottom-0 w-[320px] bg-white border-l border-outline-variant p-6 flex flex-col z-40"
		>
			<h3 class="font-headline-sm text-headline-sm text-primary mb-6">Booking Summary</h3>
			<div class="flex-1 space-y-6">
				<!-- Active Service Item -->
				<div class="pb-6 border-b border-outline-variant">
					<p
						class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-2"
					>
						Current Service
					</p>
					<div class="flex justify-between items-start mb-1">
						<span class="font-body-md text-body-md font-bold"
							>Deep Tissue Massage</span
						>
						<span class="text-sm font-semibold">KES 9,000</span>
					</div>
					<p class="text-sm text-on-surface-variant">
						Essential Relief (30m) x 2 Guests
					</p>
				</div>
				<!-- Totals Section -->
				<div class="space-y-3">
					<div class="flex justify-between text-sm">
						<span class="text-on-surface-variant">Subtotal</span>
						<span class="font-semibold text-on-surface">KES 9,000</span>
					</div>
					<div class="flex justify-between text-sm">
						<span class="text-on-surface-variant">Taxes &amp; Levies</span>
						<span class="font-semibold text-on-surface">KES 1,440</span>
					</div>
					<div class="flex justify-between text-sm">
						<span class="text-on-surface-variant">Service Fee</span>
						<span class="font-semibold text-on-surface">KES 500</span>
					</div>
					<div class="pt-4 flex justify-between items-center">
						<span class="font-headline-sm text-headline-sm text-on-surface"
							>Total</span
						>
						<span class="font-headline-sm text-headline-sm text-primary"
							>KES 10,940</span
						>
					</div>
				</div>
				<!-- Image Focus -->
				<div class="pt-6">
					<div class="rounded-2xl overflow-hidden aspect-[4/3] spa-card border-none">
						<img
							class="w-full h-full object-cover"
							data-alt="A luxurious and calm spa treatment room interior with minimalist architectural lines. Soft, warm teal lighting washes over natural stone walls and a pristine massage bed. The atmosphere is peaceful, professional, and reflects a high-end wellness sanctuary designed for maximum relaxation and aesthetic focus."
							src="https://lh3.googleusercontent.com/aida-public/AB6AXuAhYirU-LHbWE2H2pNlLVO_zE6aUEPw_q-PIHVLPqb-YCvr82mYJOGaC09LTaaEojCZe-4raL4Gy2W1Ng-_EdR0xTRJYi3nLInOdrvUITMxu1dZ8AMBw8rlWnJHJm5QPJ7dKcIPycDXvzPmu4FxKZtZbvPwtAd5khsA4fWxbLhk5NHMauGuUIXlkl1o8Fe7v9rjyyPW0W95GIQIttv-WruL1_jtR8jzZl2HmBhWTmSjO9BVQ46SR8m4mhME4NMw72yMXVyYsRja7neU"
						/>
					</div>
				</div>
			</div>
			<div class="mt-auto space-y-3">
				<button
					class="w-full py-4 rounded-xl bg-primary text-white font-label-md text-label-md hover:opacity-90 active:scale-[0.98] transition-all"
				>
					Save Service Configuration
				</button>
				<button
					class="w-full py-3 rounded-xl border border-primary text-primary font-label-md text-label-md hover:bg-primary/5 active:scale-[0.98] transition-all"
				>
					Save as Draft
				</button>
			</div>
		</aside>
	</div>
	<!-- <div class="max-w-6xl mx-auto px-4 sm:px-6 py-4 sm:py-6"> -->
	<!-- Backdrop for better contrast -->
	<!-- <div
			v-if="alertOptions.message"
			class="fixed inset-0 bg-black/20 backdrop-blur-sm z-[100] transition-opacity duration-300"
			@click="alertOptions.message = ''"
		></div> -->

	<!-- Alert with enhanced visibility -->
	<!-- <Alert
			v-if="alertOptions.message"
			:title="alertOptions.title"
			:description="alertOptions.message"
			:variant="alertOptions.variant"
			:theme="alertOptions.theme"
			class="fixed top-4 md:top-8 left-1/2 -translate-x-1/2 z-[101] w-[90%] md:w-auto md:min-w-[400px] md:max-w-[500px] shadow-2xl animate-slide-down"
			@close="alertOptions.message = ''"
		/> -->

	<!-- Show errors at the top -->
	<!-- <ErrorMessage
			v-if="getAvailableDates.error"
			:message="getAvailableDates.error"
			class="mb-4"
		/>
		<ErrorMessage
			v-if="getAvailableTimeSlots.error"
			:message="getAvailableTimeSlots.error"
			class="mb-4"
		/>
		<ErrorMessage
			v-if="checkSlotAvailability.error"
			:message="checkSlotAvailability.error"
			class="mb-4"
		/>

		<div class="flex flex-col gap-4 sm:gap-6">
			<div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4"> -->
	<!-- header section  -->
	<!-- <div class="flex-1">
					<h1
						class="font-semibold text-xl sm:text-2xl md:text-3xl text-gray-900 leading-tight"
					>
						{{ stepTitle }}
					</h1>
					<p class="text-sm sm:text-base md:text-lg text-gray-600 mt-1">
						{{ stepSubtitle }}
					</p>
				</div> -->

	<!-- progress section  -->
	<!-- <div class="flex gap-3 sm:gap-4 md:gap-6 text-xs sm:text-sm md:text-base">
					<div class="flex items-center gap-1.5">
						<span
							:class="[
								currentStep >= 1
									? 'bg-primary text-white'
									: 'bg-gray-200 text-gray-500',
								'w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center font-semibold text-xs sm:text-sm',
							]"
							>1</span
						>
						<span
							:class="
								currentStep >= 1 ? 'font-semibold text-gray-900' : 'text-gray-500'
							"
							class="hidden sm:inline"
							>Select Time</span
						>
					</div>
					<div class="flex items-center gap-1.5">
						<span
							:class="[
								currentStep >= 2
									? 'bg-primary text-white'
									: 'bg-gray-200 text-gray-500',
								'w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center font-semibold text-xs sm:text-sm',
							]"
							>2</span
						>
						<span
							:class="
								currentStep >= 2 ? 'font-semibold text-gray-900' : 'text-gray-500'
							"
							class="hidden sm:inline"
							>Details</span
						>
					</div>
					<div class="flex items-center gap-1.5">
						<span
							:class="[
								currentStep >= 3
									? 'bg-primary text-white'
									: 'bg-gray-200 text-gray-500',
								'w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center font-semibold text-xs sm:text-sm',
							]"
							>3</span
						>
						<span
							:class="
								currentStep >= 3 ? 'font-semibold text-gray-900' : 'text-gray-500'
							"
							class="hidden sm:inline"
							>Payment</span
						>
					</div>
				</div>
			</div> -->

	<!-- Main Booking Card Step Content  -->
	<!-- <div
				class="bg-white rounded-xl sm:rounded-2xl shadow-lg overflow-hidden flex flex-col min-h-[500px] sm:min-h-[600px]"
			> -->
	<!-- Step Components -->
	<!-- <div class="flex-1 flex flex-col lg:flex-row"> -->
	<!-- Show skeleton while initially loading dates -->
	<!-- <SlotPickerSkeleton
						v-if="
							currentStep === 1 &&
							getAvailableDates.loading &&
							availableDates.length === 0
						"
					/> -->

	<!-- Show SlotPicker once dates are available or loaded -->
	<!-- <SlotPicker
						v-else-if="currentStep === 1"
						:date="booking.draft.date"
						:slot="booking.draft.slot"
						:provider="booking.draft.provider"
						:available-dates="availableDates"
						:available-slots="availableSlots"
						:can-proceed="canProceed"
						:dates-loading="getAvailableDates.loading"
						:slots-loading="getAvailableTimeSlots.loading"
						@update:date="booking.setDate"
						@update:slot="booking.setSlot"
						@update:provider="booking.setProvider"
						@continue="currentStep++"
					/>

					<UserDetails v-if="currentStep === 2" :is-logged-in="isLoggedIn" />

					<PaymentStep
						v-if="currentStep === 3"
						:can-proceed="canProceed"
						@back="currentStep--"
						@submit="submitBooking"
					/>
				</div>

				<div
					v-if="appointmentBasket.length"
					class="border-t border-gray-100 bg-gray-50/70 px-6 md:px-8 py-5"
				>
					<div class="flex flex-col gap-4">
						<div class="flex items-center justify-between gap-4">
							<div>
								<h3 class="text-sm font-semibold text-gray-900">Booking Basket</h3>
								<p class="text-xs text-gray-500">
									{{ appointmentBasket.length }} appointment{{
										appointmentBasket.length === 1 ? "" : "s"
									}}
									added
								</p>
							</div>
							<div class="text-right">
								<p class="text-xs text-gray-500">Estimated total</p>
								<p class="text-lg font-bold text-primary">
									{{ formatCurrency(basketTotal, booking.draft.currency) }}
								</p>
							</div>
						</div>

						<div class="space-y-3 max-h-56 overflow-auto pr-1">
							<div
								v-for="(appointment, index) in appointmentBasket"
								:key="`${appointment.appointment_type}-${index}`"
								class="rounded-xl border border-gray-200 bg-white p-4 flex items-start justify-between gap-4"
							>
								<div class="space-y-1">
									<p class="font-semibold text-gray-900">
										{{ appointment.appointment_type }}
									</p>
									<p class="text-sm text-gray-600">
										{{ appointment.guest_full_name }}
									</p>
									<p class="text-xs text-gray-500">
										{{ appointment.date }} •
										{{ formatSlotLabel(appointment.slot) }}
									</p>
								</div>
								<div class="text-right space-y-2">
									<p class="text-sm font-semibold text-gray-900">
										{{
											formatCurrency(
												appointment.price,
												appointment.currency || booking.draft.currency
											)
										}}
									</p>
									<button
										type="button"
										class="text-xs text-red-600 hover:underline"
										@click="booking.removeAppointmentFromBasket(index)"
									>
										Remove
									</button>
								</div>
							</div>
						</div>

						<div class="flex items-center justify-between gap-3">
							<button
								type="button"
								class="text-sm text-gray-500 hover:text-gray-800"
								@click="booking.clearAppointmentBasket()"
							>
								Clear basket
							</button>
							<p class="text-xs text-gray-500">
								You can keep adding services before payment.
							</p>
						</div>
					</div>
				</div> -->

	<!-- Buttons for step 1 (Choose Time) -->
	<!-- <div
					v-if="currentStep === 1"
					class="mt-auto px-6 md:px-8 pb-6 md:pb-8 flex items-center justify-between border-t border-gray-100 pt-6"
				>
					<button
						@click="closeDialog"
						class="px-6 py-3 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-semibold hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
						type="button"
					>
						Back
					</button>
					<button
						:disabled="!canProceed"
						@click="currentStep++"
						class="px-8 py-3 rounded-lg bg-primary hover:bg-primary-dark text-white font-semibold shadow-lg shadow-primary/30 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
						type="button"
					>
						Continue to Details
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 5l7 7-7 7"
							/>
						</svg>
					</button>
				</div> -->

	<!-- Buttons for step 2 (integrated in form) -->
	<!-- <div
					v-if="currentStep === 2"
					class="mt-auto px-6 md:px-8 pb-6 md:pb-8 flex items-center justify-between border-t border-gray-100 pt-6"
				>
					<button
						@click="currentStep--"
						class="px-6 py-3 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-semibold hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
						type="button"
					>
						Back
					</button>
					<button
						:disabled="!canProceed"
						@click="
							() => {
								booking.addAppointmentToBasket({ resetCurrent: true });
								showAlert('Added', 'Appointment added to booking basket', 'green');
								currentStep = 1;
							}
						"
						class="px-8 py-3 rounded-lg border border-gray-300 text-gray-700 font-semibold hover:bg-gray-50 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
						type="button"
					>
						Add to Booking
					</button>
					<button
						:disabled="!canProceed"
						@click="
							() => {
								booking.addAppointmentToBasket({ resetCurrent: true });
								currentStep = 3;
							}
						"
						class="px-8 py-3 rounded-lg bg-primary hover:bg-primary-dark text-white font-semibold shadow-lg shadow-primary/30 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
						type="button"
					>
						Pay Now
					</button>
				</div>
			</div>
		</div>
	</div> -->
</template>

<script setup>
import { createResource, ErrorMessage, Alert } from "frappe-ui";
import { ref, watch, computed, onMounted } from "vue";
import { useAlert } from "@/composables/useAlert";
import { useBookingStore } from "@/stores/bookingStore";
import { useAuthStore } from "@/stores/auth";
import { useRouter, useRoute } from "vue-router";
import SlotPicker from "./steps/ChooseTime.vue";
import SlotPickerSkeleton from "./SlotPickerSkeleton.vue";
import UserDetails from "./steps/CustomerDetails.vue";
import PaymentStep from "./steps/PaymentAndConfirmation.vue";
import { flattenSlotsByProviderForDate } from "@/utils/slotTransformation";
import { formatCurrency } from "@/utils";

const booking = useBookingStore();
const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const { alertOptions, showAlert } = useAlert();

const serviceType = computed(() => booking.draft.serviceType || route.params.serviceType);

function closeDialog() {
	router.back();
}

const availableDates = ref([]);
const availableSlots = ref([]);
const isLoggedIn = ref(false);

const currentStep = computed({
	get: () => booking.currentStep,
	set: (v) => (booking.currentStep = v),
});

const stepTitle = computed(() => {
	if (currentStep.value === 1) return "Select a Date & Time";
	if (currentStep.value === 2) return "Your Details";
	return "Payment";
});

const stepSubtitle = computed(() => {
	if (currentStep.value === 1) return `Choose the best time for your ${serviceType.value}`;
	if (currentStep.value === 2) return "Enter your details or confirm your information";
	return "Confirm your booking and proceed to payment";
});

const canProceed = computed(() => {
	if (currentStep.value === 1) return booking.draft.date && booking.draft.slot;
	if (currentStep.value === 2) {
		// Check primary guest info
		const hasBasicInfo =
			booking.draft.email && booking.draft.mobileNo && booking.draft.fullName;

		// Check all guests have required full_name
		const allGuestsValid =
			booking.draft.guests &&
			Array.isArray(booking.draft.guests) &&
			booking.draft.guests.length > 0 &&
			booking.draft.guests.every((guest) => guest.full_name && guest.full_name.trim());

		return hasBasicInfo && allGuestsValid;
	}
	return appointmentBasket.value.length > 0;
});

const appointmentBasket = computed(() => booking.draft.appointments || []);

const basketTotal = computed(() =>
	appointmentBasket.value.reduce((total, item) => total + (Number(item.price) || 0), 0)
);

const getAvailableDates = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_dates",
	method: "GET",
	makeParams() {
		return {
			service_type: serviceType.value,
			duration: booking.draft.duration,
		};
	},
});

const getAvailableTimeSlots = createResource({
	url: "frappoint.frappoint.api.slot_availability.get_available_time_slots",
	method: "GET",
	makeParams() {
		return {
			service_type: serviceType.value,
			duration: booking.draft.duration,
			date: booking.draft.date,
		};
	},
});

const checkSlotAvailability = createResource({
	url: "frappoint.frappoint.api.slot_availability.check_slot_availability",
	method: "GET",
	makeParams() {
		return {
			slot_ids: booking.draft.slot.slot_ids,
		};
	},
});

const paymentLinkResource = createResource({
	url: "frappoint.payments.get_payment_link",
	auto: false,
});

const bookingDeskResource = createResource({
	url: "frappoint.frappoint.api.service_booking.create_booking_with_appointments",
	auto: false,
});

function formatSlotLabel(slot) {
	if (!slot?.start_time || !slot?.end_time) return "Time not set";
	return `${slot.start_time} - ${slot.end_time}`;
}

onMounted(async () => {
	booking.loadFromStorage();

	if (!booking.draft.serviceType) {
		const routeServiceType = route.params.serviceType;
		if (!routeServiceType) {
			router.replace({ name: "Services" });
			return;
		}
		booking.setServiceType(routeServiceType);
	}

	await booking.hydrateServiceDetails();

	if (booking.draft.date) {
		await loadSlotsForDate(booking.draft.date);
	}
	availableDates.value = await getAvailableDates.fetch();
});

watch(
	() => booking.draft.date,
	(date) => {
		if (booking.isResettings) return;
		if (!date || !booking.draft.serviceType) return;

		loadSlotsForDate(date);
	}
);

async function loadSlotsForDate(date) {
	if (!date || !booking.draft.serviceType) return;

	const response = await getAvailableTimeSlots.fetch();
	availableSlots.value = flattenSlotsByProviderForDate(response, date);
}

const customerResource = createResource({
	url: "frappoint.frappoint.api.user.get_logged_in_customer",
	method: "GET",
	auto: false,
});

watch(
	() => currentStep.value,
	async (step) => {
		if (step === 2 && auth.isLoggedIn) {
			try {
				const res = await customerResource.fetch();
				if (res) {
					booking.draft.customer = res.customer || "";
					booking.draft.fullName = res.contact.contact_display || "";
					booking.draft.email = res.contact.contact_email || "";
					booking.draft.mobileNo = res.contact.contact_phone || "";
				}
			} catch (err) {
				console.error("Failed to fetch customer info", err);
			}
		}
	},
	{ immediate: true }
);

// TODO: Check validate customer appointment for same date and time
async function submitBooking() {
	const appointmentItems =
		booking.draft.appointments && booking.draft.appointments.length
			? [...booking.draft.appointments]
			: booking.isComplete
			? [booking.createAppointmentSnapshot()]
			: [];

	if (!appointmentItems.length) return;

	if (!auth.isLoggedIn) {
		booking.currentStep = currentStep.value;
		booking.saveToStorage();

		router.push({
			name: "Login",
			query: {
				redirect: route.fullPath,
			},
		});
		return;
	}

	try {
		const payload = {
			customer: {
				customer: booking.draft.customer,
				fullName: booking.draft.fullName,
				email: booking.draft.email,
				mobileNo: booking.draft.mobileNo,
			},
			guests: appointmentItems,
		};

		const resp = await bookingDeskResource.submit(payload);

		if (!resp || !resp.booking_id) {
			return;
		}

		const bookingTotal = Number(resp.grand_total || 0);
		if (bookingTotal > 0) {
			const redirectTo = `${window.location.origin}/portal/booking/${resp.booking_id}`;
			const response = await paymentLinkResource.submit({
				reference_doctype: "Service Booking",
				reference_docname: resp.booking_id,
				payment_gateway: booking.draft.selectedPaymentGateway,
				redirect_to: redirectTo,
			});

			if (typeof response === "string" && response) {
				booking.clearStorage();
				window.location.href = response;
				return;
			}
		} else {
			booking.clearStorage();
			router.push({
				name: "BookingConfirmation",
				params: { bookingId: resp.booking_id },
			});
		}
	} catch (error) {
		console.error("Failed to submit booking:", error);
		showAlert("Error", getErrorMessage(error), "red");
	}
}

function getErrorMessage(error) {
	if (error?.messages?.length) {
		return error.messages[0];
	}

	if (error?.message) {
		return error.message;
	}

	if (error?._server_messages) {
		try {
			const messages = JSON.parse(error._server_messages);
			if (messages.length > 0) {
				const parsed = JSON.parse(messages[0]);
				return parsed.message || "Failed to submit booking. Please try again.";
			}
		} catch (parseError) {
			console.error("Failed to parse server error message:", parseError);
		}
	}

	return "Failed to submit booking. Please try again.";
}
</script>

<style scoped>
@keyframes slide-down {
	from {
		opacity: 0;
		transform: translate(-50%, -100%);
	}

	to {
		opacity: 1;
		transform: translate(-50%, 0);
	}
}

.animate-slide-down {
	animation: slide-down 0.3s ease-out;
}
</style>
