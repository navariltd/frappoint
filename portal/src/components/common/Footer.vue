<template>
	<footer class="bg-surface-light border-t border-outline-variant/50">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 py-12 md:py-16">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
				<!-- Brand Section -->
				<div class="lg:col-span-1">
					<div class="flex items-center gap-2 mb-4">
						<img
							class="h-8 w-8 object-contain"
							:src="branding.sidebarLogo || defaultLogo"
							:alt="`${branding.company} logo`"
						/>
						<h3 class="text-xl font-bold text-on-surface">{{ branding.company }}</h3>
					</div>
					<p class="text-sm text-on-surface-variant leading-relaxed">
						Premium wellness booking made simple. Restore your balance today.
					</p>
				</div>

				<!-- Company Links -->
				<div>
					<h4 class="text-sm font-semibold text-on-surface mb-4">Company</h4>
					<ul class="space-y-3">
						<li>
							<a
								href="#"
								class="text-sm text-on-surface-variant hover:text-primary transition-colors"
								>About Us</a
							>
						</li>
						<li>
							<a
								href="#"
								class="text-sm text-on-surface-variant hover:text-primary transition-colors"
								>Careers</a
							>
						</li>
						<li>
							<a
								href="#"
								class="text-sm text-on-surface-variant hover:text-primary transition-colors"
								>Blog</a
							>
						</li>
					</ul>
				</div>

				<!-- Support Links -->
				<div>
					<h4 class="text-sm font-semibold text-on-surface mb-4">Support</h4>
					<ul class="space-y-3">
						<li>
							<a
								href="#"
								class="text-sm text-on-surface-variant hover:text-primary transition-colors"
								>Help Center</a
							>
						</li>
						<li>
							<a
								href="#"
								class="text-sm text-on-surface-variant hover:text-primary transition-colors"
								>Safety</a
							>
						</li>
						<li>
							<a
								href="#"
								class="text-sm text-on-surface-variant hover:text-primary transition-colors"
								>Terms of Service</a
							>
						</li>
					</ul>
				</div>

				<!-- Newsletter Section -->
				<div>
					<h4 class="text-sm font-semibold text-on-surface mb-4">Stay updated</h4>
					<div class="flex gap-2">
						<input
							v-model="email"
							type="email"
							placeholder="Enter your email"
							class="flex-1 px-4 py-2.5 text-sm text-on-surface bg-surface border border-outline-variant rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
						/>
						<button
							@click="handleSubscribe"
							class="bg-primary text-white p-2.5 rounded-lg hover:bg-primary/90 transition-colors flex-shrink-0"
						>
							<FeatherIcon class="h-5 w-5" name="arrow-right" />
						</button>
					</div>
				</div>
			</div>

			<!-- Copyright -->
			<div
				class="mt-12 pt-8 border-t border-outline-variant/50 text-center text-sm text-on-surface-variant"
			>
				© 2025. All rights reserved.
			</div>
		</div>
	</footer>
</template>

<script setup>
import { ref } from "vue";
import { FeatherIcon } from "frappe-ui";
import { branding } from "@/branding";
import defaultLogo from "@/assets/images/logo_img.png";

const email = ref("");

function handleSubscribe() {
	// TODO: Logic will be implemented later
	console.log("Subscribe email:", email.value);
}
</script>
