<template>
	<div class="flex h-screen bg-gray-300">
		<!-- SIDEBAR -->
		<aside class="w-46 bg-white shadow-lg flex-shrink-0">
			<div class="p-6 border-b flex gap-2 hover:cursor-pointer">
				<Avatar shape="square" image="/frappoint.jpeg" label="EY" size="lg" />
				<h2 class="text-2xl font-bold text-blue-500">Frappoint</h2>
			</div>

			<nav class="p-4 flex flex-col h-[calc(100%-65px)]">
				<div class="flex-grow">
					<router-link
						to="/"
						class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg"
						active-class="!text-blue-500"
					>
						<CalendarCheck :size="20" />
						<span>Appointments</span>
					</router-link>

					<router-link
						to="/services"
						class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg"
						active-class="!text-blue-500"
					>
						<CalendarCheck :size="20" />
						<span>Services</span>
					</router-link>

					<router-link
						to="/dashboard"
						class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg"
						active-class="!text-blue-500"
					>
						<User :size="20" />
						<span>Dashboard</span>
					</router-link>
				</div>

				<div>
					<button
						@click="session.logout.submit()"
						class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg"
					>
						<LogOut :size="20" />
						<span>Logout</span>
					</button>
				</div>
			</nav>
		</aside>

		<main class="flex-1 flex flex-col overflow-hidden">
			<slot />
		</main>
	</div>
</template>

<script setup>
import { Avatar } from "frappe-ui";
import { RouterLink } from "vue-router";
import { CalendarCheck, LogOut, User } from "lucide-vue-next";
import { sessionStore } from "../data/session";

const session = sessionStore();
</script>
