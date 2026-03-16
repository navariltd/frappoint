<template>
	<!-- BEGIN: MainHeader -->
	<header
		class="h-16 bg-white border-b border-espresso-200 flex items-center justify-between px-6 sticky top-0 z-50"
	>
		<div class="flex items-center gap-3">
			<div class="w-8 h-8 bg-espresso-700 rounded-lg flex items-center justify-center">
				<span class="text-white font-bold">F</span>
			</div>
			<h1 class="text-xl font-semibold text-espresso-900 tracking-tight">
				Frappoint <span class="text-espresso-500">Booking Desk</span>
			</h1>
		</div>
		<!-- Search Bar -->
		<div class="flex-1 max-w-2xl px-8" data-purpose="global-search">
			<div class="relative">
				<span class="absolute inset-y-0 left-0 pl-3 flex items-center text-espresso-400">
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewbox="0 0 24 24">
						<path
							d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
						></path>
					</svg>
				</span>
				<input
					class="w-full bg-espresso-100 border-none rounded-full py-2 pl-10 pr-4 focus:ring-2 focus:ring-frappe-teal transition-all text-sm"
					placeholder="Search appointments, customers, or services (Ctrl+K)"
					type="text"
				/>
			</div>
		</div>
		<div class="flex items-center gap-4">
			<div class="text-right">
				<p class="text-xs text-slate-500">Receptionist</p>
				<p class="text-sm font-medium">Administrator</p>
			</div>
			<div
				class="w-10 h-10 rounded-full bg-espresso-200 border-2 border-white shadow-sm overflow-hidden"
			>
				<img alt="User Profile" src="" />
			</div>
		</div>
	</header>
	<!-- END: MainHeader -->
</template>
