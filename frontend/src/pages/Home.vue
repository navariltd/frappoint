<template>
	<div class="flex h-screen bg-gray-100">
		<aside class="w-44 bg-white shadow-lg">
			<div class="p-6 border-b">
				<h2 class="text-2xl font-bold text-gray-800">Frappoint</h2>
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
			<div class="max-w-3xl py-12 mx-auto">
				<h2 class="font-bold text-lg text-gray-600 mb-4">Welcome {{ session.user }}!</h2>

				<Button
					theme="gray"
					variant="solid"
					icon-left="code"
					@click="ping.fetch"
					:loading="ping.loading"
				>
					Click to send 'ping' request
				</Button>
				<div>
					{{ ping.data }}
				</div>
				<pre>{{ ping }}</pre>

				<div class="flex flex-row space-x-2 mt-4">
					<Button @click="showDialog = true">Open Dialog</Button>
					<Button @click="session.logout.submit()">Logout</Button>
				</div>

				<!-- Dialog -->
				<Dialog title="Title" v-model="showDialog"> Dialog content </Dialog>
			</div>
		</main>
	</div>
</template>

<script setup>
import { Dialog } from "frappe-ui";
import { createResource } from "frappe-ui";
import { LayoutDashboard, LogOut, User } from "lucide-vue-next";
import { ref } from "vue";
import { session } from "../data/session";

const ping = createResource({
	url: "ping",
	auto: true,
});

const showDialog = ref(false);
</script>
