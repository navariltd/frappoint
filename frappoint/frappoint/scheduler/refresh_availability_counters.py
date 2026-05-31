from frappoint.frappoint.services.availability_projector import refresh_counter_horizon


def execute():
	"""Scheduler entrypoint for periodic availability projection refresh."""
	return refresh_counter_horizon()
