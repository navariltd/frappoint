<template>
	<aside
		class="w-72 border-r border-outline-variant/20 bg-surface-container-lowest overflow-y-auto"
	>
		<div class="p-4 space-y-3">
			<div
				v-for="(group, index) in groups"
				:key="`${group.serviceKey}-${index}`"
				class="space-y-2"
			>
				<p
					class="text-label-sm uppercase tracking-wider font-semibold text-on-surface-variant px-2"
				>
					{{ group.serviceName }}
				</p>
				<div class="space-y-2">
					<button
						v-for="(assignment, assignmentIndex) in group.assignments"
						:key="assignment.id"
						class="w-full text-left px-3 py-3 rounded-lg transition-all"
						:class="[
							assignment.id === activeAssignmentId
								? 'bg-primary-container text-on-primary-container shadow-sm'
								: 'bg-surface-container hover:bg-surface-container-high',
							assignment.status === 'completed'
								? 'border-l-4 border-primary'
								: assignment.status === 'slot_selected'
								? 'border-l-4 border-secondary'
								: 'border-l-4 border-outline-variant/30',
						]"
						@click="$emit('select', assignment.globalIndex)"
					>
						<div class="flex items-start justify-between">
							<div>
								<p class="text-label-md font-semibold">
									{{
										assignment.guest_full_name ||
										`Guest ${assignment.guest_index + 1}`
									}}
								</p>
								<p class="text-label-sm opacity-70">
									{{ assignment.package_name }}
								</p>
							</div>
							<span
								v-if="assignment.status === 'completed'"
								class="material-symbols-outlined text-sm text-primary"
								>check_circle</span
							>
							<span
								v-else-if="assignment.status === 'slot_selected'"
								class="material-symbols-outlined text-sm text-secondary"
								>calendar_check</span
							>
							<span v-else class="material-symbols-outlined text-sm opacity-50"
								>schedule</span
							>
						</div>
					</button>
				</div>
			</div>
		</div>
	</aside>
</template>

<script setup lang="ts">
import type { GuestAssignment } from "@/stores/bookingWorkflow.store";

interface AssignmentWithIndex extends GuestAssignment {
	globalIndex: number;
}

defineProps<{
	groups: Array<{
		serviceKey: string;
		serviceName: string;
		assignments: AssignmentWithIndex[];
	}>;
	activeAssignmentId?: string;
}>();

defineEmits<{
	select: [index: number];
}>();
</script>
