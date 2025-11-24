<template>
	<div class="flex h-screen bg-gray-100">
		<aside class="w-44 bg-white shadow-lg">
			<div class="p-6 border-b flex gap-2 hover:cursor-pointer">
				<Avatar
					:shape="'square'"
					:ref_for="true"
					image="/favicon.png"
					label="EY"
					size="md"
				/>
				<h2 class="text-2xl font-bold text-blue-500">Frappoint</h2>
			</div>
			<nav class="p-4 flex flex-col h-[calc(100%-65px)]">
				<div class="flex-grow">
					<a
						href="#"
						class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
					>
						<LayoutDashboard :size="20" />
						<span>Dashboard</span>
					</a>
					<a
						href="#"
						class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
					>
						<User :size="20" />
						<span>Profile</span>
					</a>
				</div>

				<div>
					<a
						href="#"
						class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
					>
						<LogOut :size="20" />
						<span>Logout</span>
					</a>
				</div>
			</nav>
		</aside>
		<main class="flex-1 p-8 overflow-auto">
			<Welcome :username="session.user" />
		</main>
	</div>
</template>

<script setup>
import { Avatar } from "frappe-ui";
import { createResource } from "frappe-ui";
import { LayoutDashboard, LogOut, User } from "lucide-vue-next";
import { ref } from "vue";
import { session } from "../data/session";
import Welcome from "../components/Welcome.vue";

const ping = createResource({
	url: "ping",
	auto: true,
});

const showDialog = ref(false);
</script>
