<template>
	<main class="max-w-7xl mx-auto px-gutter py-section-gap">
		<div class="grid grid-cols-1 lg:grid-cols-12 gap-10">
			<!-- Left Column: Payment Details -->
			<div class="lg:col-span-7 space-y-8">
				<!-- Header -->
				<header class="space-y-2">
					<div class="flex items-center gap-2 text-primary font-label-md">
						<span class="material-symbols-outlined text-[18px]">lock</span>
						<span class="uppercase tracking-widest">Secure Checkout</span>
					</div>
					<h1 class="font-headline-lg text-headline-lg text-on-surface">
						Payment Mode: Full Booking
					</h1>
					<p class="text-on-surface-variant font-body-lg">
						Review your selection and complete your transaction securely.
					</p>
				</header>
				<!-- Main Payment Card -->
				<div class="glass-card rounded-xl p-8 shadow-sm space-y-8">
					<!-- Toggle Area -->
					<div
						class="bg-surface-container-low p-2 rounded-full flex items-center max-w-md"
					>
						<button
							class="flex-1 py-3 px-6 rounded-full bg-primary text-on-primary font-label-md transition-all shadow-md"
						>
							Pay Full Amount
						</button>
						<button
							class="flex-1 py-3 px-6 rounded-full text-on-surface-variant font-label-md hover:bg-surface-container transition-all"
						>
							Pay Deposit
						</button>
					</div>
					<div class="space-y-6">
						<div
							class="flex justify-between items-end border-b border-outline-variant/30 pb-6"
						>
							<div>
								<p
									class="text-label-md text-on-surface-variant uppercase tracking-tighter"
								>
									Amount Due Today
								</p>
								<h2 class="font-headline-lg text-headline-lg text-primary">
									KES 70,000
								</h2>
							</div>
							<div class="text-right">
								<span
									class="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-lg text-label-sm font-bold"
								>
									FULL BOOKING
								</span>
							</div>
						</div>
						<!-- Summary Breakdown -->
						<div class="space-y-4">
							<div class="flex justify-between text-body-md">
								<span class="text-on-surface-variant"
									>Signature Wellness Retreat (3 Days)</span
								>
								<span class="text-on-surface font-semibold">KES 62,500</span>
							</div>
							<div class="flex justify-between text-body-md">
								<span class="text-on-surface-variant"
									>Service Taxes &amp; Fees</span
								>
								<span class="text-on-surface font-semibold">KES 7,500</span>
							</div>
							<div class="flex justify-between text-body-md pt-2">
								<span class="text-on-surface-variant italic"
									>Note: Paying in full grants early access to spa
									bookings.</span
								>
								<span class="text-secondary font-bold text-label-md"
									>Deposit Opt: KES 20,000</span
								>
							</div>
						</div>
					</div>
					<!-- Trust Signals -->
					<div class="grid grid-cols-3 gap-4 pt-4">
						<div
							class="flex flex-col items-center text-center p-4 rounded-xl border border-outline-variant/20"
						>
							<span class="material-symbols-outlined text-primary mb-2"
								>verified</span
							>
							<p class="text-label-sm text-on-surface-variant">SSL Encrypted</p>
						</div>
						<div
							class="flex flex-col items-center text-center p-4 rounded-xl border border-outline-variant/20"
						>
							<span class="material-symbols-outlined text-primary mb-2"
								>event_available</span
							>
							<p class="text-label-sm text-on-surface-variant">
								Instant Confirmation
							</p>
						</div>
						<div
							class="flex flex-col items-center text-center p-4 rounded-xl border border-outline-variant/20"
						>
							<span class="material-symbols-outlined text-primary mb-2">replay</span>
							<p class="text-label-sm text-on-surface-variant">Flexible Refund</p>
						</div>
					</div>
				</div>
				<!-- Footer Image for Atmosphere -->
				<div class="rounded-xl overflow-hidden h-48 relative shadow-sm group">
					<img
						class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
						data-alt="A tranquil and luxuriously designed spa treatment room with soft, ambient lighting. The scene features clean white linens on a massage table, smooth decorative stones, and a touch of lush greenery. The warm cream and soft teal color palette reflects a serene and peaceful environment, reinforcing the brand's 'Serene Wellness' identity and inviting the user into a state of relaxation."
						src="https://lh3.googleusercontent.com/aida-public/AB6AXuDhCg3J4cNxzeHN8TI6UqF0Q3Xkg4oDyMOL92rO8znhG4DMOjcj_ywtw2lW_qcdcZtAixZ-MH-v5aU9H71nnfZxU0mjh0dAyFgorwNNbsnuvsr0yobPBRcbNP56fv7g12ZP9HcG20tttE0LeoQbgVgkHaL5PERCkHW_HoZyrsYB0hPxN9wF0eSLoVuK7masOxI7kS4DMQcGOPbbWyeA48c-noik1cWmie6aOBAr9qBVQScegTyTVd8uUF-qmlq-WIeYEaX7ljes9Vxn"
					/>
					<div
						class="absolute inset-0 bg-gradient-to-t from-on-surface/60 to-transparent flex items-end p-6"
					>
						<p class="text-on-primary font-headline-sm italic">
							"Your journey to serenity starts here."
						</p>
					</div>
				</div>
			</div>
			<!-- Right Column: Payment & Status -->
			<div class="lg:col-span-5 space-y-6">
				<!-- Payment Method Panel -->
				<div
					class="bg-surface-container-highest rounded-xl p-8 shadow-lg border border-primary/10"
				>
					<h3 class="font-headline-sm text-headline-sm text-on-surface mb-6">
						Payment Method
					</h3>
					<div class="space-y-4">
						<!-- M-PESA Option -->
						<div
							class="p-4 rounded-xl bg-surface border-2 border-primary flex items-center justify-between cursor-pointer"
						>
							<div class="flex items-center gap-4">
								<div
									class="w-12 h-12 bg-secondary-container rounded-lg flex items-center justify-center font-bold text-secondary"
								>
									M
								</div>
								<div>
									<p class="font-label-md text-on-surface">M-PESA Express</p>
									<p class="text-label-sm text-on-surface-variant">
										Direct push to phone
									</p>
								</div>
							</div>
							<span
								class="material-symbols-outlined text-primary"
								style="font-variation-settings: 'FILL' 1"
								>check_circle</span
							>
						</div>
						<!-- Card Option -->
						<div
							class="p-4 rounded-xl bg-surface/50 border border-outline-variant/30 flex items-center justify-between cursor-pointer hover:bg-surface transition-colors"
						>
							<div class="flex items-center gap-4">
								<div
									class="w-12 h-12 bg-surface-container-high rounded-lg flex items-center justify-center"
								>
									<span class="material-symbols-outlined text-on-surface-variant"
										>credit_card</span
									>
								</div>
								<div>
									<p class="font-label-md text-on-surface">
										Credit / Debit Card
									</p>
									<p class="text-label-sm text-on-surface-variant">
										Visa, Mastercard, Amex
									</p>
								</div>
							</div>
						</div>
					</div>
					<div class="mt-8 space-y-4">
						<div class="space-y-2">
							<label class="text-label-sm font-semibold text-on-surface-variant ml-1"
								>Phone Number for M-PESA</label
							>
							<input
								class="w-full p-4 rounded-xl border-outline-variant bg-surface focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
								placeholder="07XX XXX XXX"
								type="text"
							/>
						</div>
						<button
							class="w-full bg-primary py-4 rounded-xl text-on-primary font-headline-sm shadow-xl hover:shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all"
						>
							Complete Payment
						</button>
					</div>
				</div>
				<!-- Status Tracking / Stepper -->
				<div class="glass-card rounded-xl p-6">
					<h4 class="font-label-md text-on-surface mb-4 uppercase tracking-wider">
						Booking Progress
					</h4>
					<div class="relative space-y-6">
						<!-- Line -->
						<div
							class="absolute left-[15px] top-2 bottom-2 w-0.5 bg-outline-variant/30"
						></div>
						<!-- Step 1 (Completed) -->
						<div class="flex items-start gap-4 relative z-10">
							<div
								class="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-on-secondary shadow-sm"
							>
								<span class="material-symbols-outlined text-[18px]">check</span>
							</div>
							<div>
								<p class="font-label-md text-on-surface">Service Selected</p>
								<p class="text-label-sm text-on-surface-variant">
									3-Day Signature Retreat
								</p>
							</div>
						</div>
						<!-- Step 2 (Active) -->
						<div class="flex items-start gap-4 relative z-10">
							<div
								class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary shadow-md ring-4 ring-primary-container/20"
							>
								<span class="material-symbols-outlined text-[18px]">payments</span>
							</div>
							<div>
								<p class="font-label-md text-primary font-bold">
									Payment Execution
								</p>
								<p class="text-label-sm text-on-surface-variant">
									Verifying transaction details
								</p>
							</div>
						</div>
						<!-- Step 3 (Pending) -->
						<div class="flex items-start gap-4 relative z-10">
							<div
								class="w-8 h-8 rounded-full bg-surface-container-high border-2 border-outline-variant/30 flex items-center justify-center text-on-surface-variant/40"
							>
								<span class="material-symbols-outlined text-[18px]">done_all</span>
							</div>
							<div>
								<p class="font-label-md text-on-surface-variant/60">
									Confirmation
								</p>
								<p class="text-label-sm text-on-surface-variant/40">
									Instant itinerary generation
								</p>
							</div>
						</div>
					</div>
				</div>
				<!-- Need Help -->
				<div
					class="flex items-center justify-center gap-2 p-4 border border-dashed border-outline-variant/50 rounded-xl text-on-surface-variant"
				>
					<span class="material-symbols-outlined">support_agent</span>
					<span class="text-label-md">Need help? Chat with a Concierge</span>
				</div>
			</div>
		</div>
	</main>
</template>
