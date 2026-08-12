from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from frappoint.frappoint.services import booking_transaction_service as service


class _AllocationDoc:
	def __init__(self, payload, name, events):
		self.payload = payload
		self.name = name
		self._events = events

	def insert(self, ignore_permissions=False):
		self._events.append(("insert", self.payload["service_appointment"]))
		return self


def _appointment_records():
	return {
		"APT-1": {
			"booking_id": "BOOKING-1",
			"appointment_type": "SERVICE-1",
			"appointment_provider": "PROVIDER-A",
			"service_unit": None,
			"appointment_date": "2026-08-10",
			"start_time": "09:00:00",
			"end_time": "09:45:00",
			"couple_appointment_id": "APT-2",
			"is_primary_in_couple": 1,
		},
		"APT-2": {
			"booking_id": "BOOKING-1",
			"appointment_type": "SERVICE-2",
			"appointment_provider": "PROVIDER-B",
			"service_unit": None,
			"appointment_date": "2026-08-10",
			"start_time": "09:00:00",
			"end_time": "10:00:00",
			"couple_appointment_id": "APT-1",
			"is_primary_in_couple": 0,
		},
	}


def _allocation(provider, end_time, start_time="09:00:00"):
	return {
		"resource_type": "Service Provider",
		"resource_reference": provider,
		"allocation_date": "2026-08-10",
		"start_time": start_time,
		"end_time": end_time,
		"appointment_start_time": "09:00:00",
		"appointment_end_time": end_time,
		"capacity_consumed": 1,
		"buffer_before_minutes": 0,
		"buffer_after_minutes": 0,
	}


def _couple_requests():
	return [
		{
			"appointment_name": "APT-1",
			"booking_name": "BOOKING-1",
			"allocations": [_allocation("PROVIDER-A", "09:45:00")],
			"allocation_status": "Held",
		},
		{
			"appointment_name": "APT-2",
			"booking_name": "BOOKING-1",
			"allocations": [_allocation("PROVIDER-B", "10:00:00")],
			"allocation_status": "Held",
		},
	]


class TestBookingTransactionService(TestCase):
	def _database(self, records=None):
		records = records or _appointment_records()

		def get_value(doctype, name, fields=None, as_dict=False):
			if doctype == "Service Appointment":
				return records[name]
			if doctype == "Service Type":
				return {"buffer_before": 0, "buffer_after": 0}
			return None

		return SimpleNamespace(
			_cursor=SimpleNamespace(rowcount=1),
			exists=MagicMock(return_value=True),
			get_value=MagicMock(side_effect=get_value),
			savepoint=MagicMock(),
			rollback=MagicMock(),
			commit=MagicMock(),
			set_value=MagicMock(),
			sql=MagicMock(),
		)

	def test_reserves_both_couple_ledgers_only_after_all_counter_deltas(self):
		database = self._database()
		events = []
		created_docs = []

		def get_doc(payload):
			self.assertEqual(
				events[:3],
				["resource_lock", "ensure_counters", ("counter_deltas", 2)],
			)
			doc = _AllocationDoc(payload, f"ALLOC-{len(created_docs) + 1}", events)
			created_docs.append(doc)
			return doc

		requests = _couple_requests()
		requests[0]["allocations"][0].update(
			start_time="08:45:00",
			end_time="09:50:00",
			buffer_before_minutes=15,
			buffer_after_minutes=5,
		)
		requests[1]["allocations"][0].update(
			end_time="10:15:00",
			buffer_after_minutes=15,
		)
		records = _appointment_records()
		database.get_value.side_effect = lambda doctype, name, fields=None, as_dict=False: (
			records[name]
			if doctype == "Service Appointment"
			else (
				{
					"buffer_before": 15 if name == "SERVICE-1" else 0,
					"buffer_after": 5 if name == "SERVICE-1" else 15,
				}
				if doctype == "Service Type"
				else None
			)
		)

		with (
			patch.object(service.frappe, "db", database),
			patch.object(service.frappe, "get_doc", side_effect=get_doc),
			patch.object(service.frappe, "get_all", return_value=[]),
			patch.object(
				service,
				"_ensure_counter_rows",
				side_effect=lambda rows: events.append("ensure_counters"),
			),
			patch.object(
				service,
				"lock_counter_resource_rows",
				side_effect=lambda **kwargs: events.append("resource_lock"),
			),
			patch.object(
				service,
				"_apply_counter_deltas",
				side_effect=lambda rows, direction: events.append(("counter_deltas", len(rows))),
			) as apply_deltas,
			patch.object(service, "_update_appointment_allocation_status") as update_status,
			patch.object(service, "_savepoint_name", return_value="reserve_couple_test"),
		):
			result = service.reserve_couple_appointment_allocations(requests)

		self.assertEqual(result, {"APT-1": ["ALLOC-1"], "APT-2": ["ALLOC-2"]})
		apply_deltas.assert_called_once()
		self.assertEqual(apply_deltas.call_args.kwargs, {"direction": "reserve"})
		self.assertEqual(
			[
				(row["start_time"], row["end_time"], row["appointment_end_time"])
				for row in apply_deltas.call_args.args[0]
			],
			[
				("08:45:00", "09:50:00", "09:45:00"),
				("09:00:00", "10:15:00", "10:00:00"),
			],
		)
		self.assertEqual([doc.payload["service_appointment"] for doc in created_docs], ["APT-1", "APT-2"])
		for doc in created_docs:
			self.assertEqual(doc.payload["metadata_json"]["reservation_group"], "reserve_couple_test")
			self.assertEqual(doc.payload["metadata_json"]["couple_appointment_names"], ["APT-1", "APT-2"])
		update_status.assert_has_calls([call("APT-1", "Held"), call("APT-2", "Held")])
		database.rollback.assert_not_called()

	def test_rejects_caller_supplied_provider_allocation_that_does_not_match_appointment(self):
		database = self._database()
		requests = _couple_requests()
		requests[0]["allocations"][0]["resource_reference"] = "PROVIDER-OTHER"

		with (
			patch.object(service.frappe, "db", database),
			patch.object(service.frappe, "get_all", return_value=[]),
			patch.object(service, "lock_counter_resource_rows"),
			patch.object(service, "_ensure_counter_rows"),
			patch.object(service, "_savepoint_name", return_value="reserve_couple_test"),
			patch.object(service, "_", side_effect=lambda message: message),
		):
			with self.assertRaises(service.CapacityReservationError):
				service.reserve_couple_appointment_allocations(requests)

		database.rollback.assert_called_once_with(save_point="reserve_couple_test")

	def test_rolls_back_first_provider_delta_when_second_provider_has_no_capacity(self):
		database = self._database()
		database._cursor = SimpleNamespace(rowcount=1)
		updated_resources = []

		def sql(query, values):
			if query.lstrip().startswith("UPDATE"):
				updated_resources.append(values["resource_reference"])
				database._cursor.rowcount = 0 if values["resource_reference"] == "PROVIDER-B" else 1
			else:
				database._cursor.rowcount = 1

		database.sql = MagicMock(side_effect=sql)
		get_doc = MagicMock()

		requests = _couple_requests()
		requests[0]["allocations"] = [_allocation("PROVIDER-A", "09:15:00")]
		records = _appointment_records()
		records["APT-1"]["end_time"] = "09:15:00"
		database.get_value.side_effect = lambda doctype, name, fields=None, as_dict=False: (
			records[name]
			if doctype == "Service Appointment"
			else ({"buffer_before": 0, "buffer_after": 0} if doctype == "Service Type" else None)
		)
		requests[1]["allocations"] = [_allocation("PROVIDER-B", "09:15:00")]
		records["APT-2"]["end_time"] = "09:15:00"

		with (
			patch.object(service.frappe, "db", database),
			patch.object(service.frappe, "get_doc", get_doc),
			patch.object(service.frappe, "get_all", return_value=[]),
			patch.object(service, "_ensure_counter_rows"),
			patch.object(service, "lock_counter_resource_rows"),
			patch.object(service, "_update_appointment_allocation_status") as update_status,
			patch.object(service, "_slot_size_minutes", return_value=15),
			patch.object(service, "_savepoint_name", return_value="reserve_couple_test"),
			patch.object(service, "_", side_effect=lambda message: message),
		):
			with self.assertRaises(service.CapacityReservationError):
				service.reserve_couple_appointment_allocations(requests)

		self.assertEqual(updated_resources, ["PROVIDER-A", "PROVIDER-B"])
		database.rollback.assert_called_once_with(save_point="reserve_couple_test")
		get_doc.assert_not_called()
		update_status.assert_not_called()

	def test_counter_deltas_lock_all_rows_then_apply_each_individual_interval(self):
		database = SimpleNamespace(
			_cursor=SimpleNamespace(rowcount=1),
			sql=MagicMock(),
		)
		prepared = [
			{
				"resource_type": "Service Unit",
				"resource_reference": "UNIT-1",
				"allocation_date": date(2026, 8, 10),
				"start_time": "09:00:00",
				"end_time": "09:45:00",
				"capacity_consumed": 1,
			},
			{
				"resource_type": "Service Unit",
				"resource_reference": "UNIT-1",
				"allocation_date": date(2026, 8, 10),
				"start_time": "09:00:00",
				"end_time": "10:00:00",
				"capacity_consumed": 1,
			},
		]

		with (
			patch.object(service.frappe, "db", database),
			patch.object(service, "_slot_size_minutes", return_value=15),
			patch.object(service, "lock_counter_resource_rows"),
		):
			service._apply_counter_deltas(prepared, direction="reserve")

		queries = [args.args[0].lstrip() for args in database.sql.call_args_list]
		self.assertEqual(len(queries), 8)
		self.assertTrue(all(query.startswith("SELECT") for query in queries[:4]))
		self.assertTrue(all(query.startswith("UPDATE") for query in queries[4:]))

		updates = [args.args[1] for args in database.sql.call_args_list[4:]]
		self.assertEqual(
			{row["counter_slot_time"]: row["qty"] for row in updates},
			{
				"09:00:00": 2,
				"09:15:00": 2,
				"09:30:00": 2,
				"09:45:00": 1,
			},
		)

	def test_pair_release_is_explicit_and_generic_release_stays_scoped(self):
		database = self._database()
		rows = [
			{
				"name": "ALLOC-1",
				"allocation_date": "2026-08-10",
				"resource_type": "Service Provider",
				"resource_reference": "PROVIDER-A",
				"start_time": "09:00:00",
				"end_time": "09:45:00",
				"capacity_consumed": 1,
			},
		]
		get_all = MagicMock(return_value=rows)

		with (
			patch.object(service.frappe, "db", database),
			patch.object(service.frappe, "get_all", get_all),
			patch.object(service, "_apply_counter_deltas"),
			patch.object(service, "_update_appointment_allocation_status"),
			patch.object(service, "_savepoint_name", return_value="release_test"),
		):
			service.release_capacity_for_allocations(appointment_name="APT-1")
			self.assertEqual(get_all.call_args.kwargs["filters"]["service_appointment"], "APT-1")

			service.release_couple_appointment_allocations(["APT-1", "APT-2"])
			self.assertEqual(
				get_all.call_args.kwargs["filters"]["service_appointment"],
				["in", ["APT-1", "APT-2"]],
			)

	def test_pair_confirmation_rolls_back_both_status_changes_on_failure(self):
		database = self._database()
		database.set_value.side_effect = [None, RuntimeError("second allocation failed")]

		allocation_rows = [
			{"name": "ALLOC-1", "service_appointment": "APT-1", **_allocation("PROVIDER-A", "09:45:00")},
			{"name": "ALLOC-2", "service_appointment": "APT-2", **_allocation("PROVIDER-B", "10:00:00")},
		]
		allocation_query_count = 0

		def get_all(doctype, **kwargs):
			nonlocal allocation_query_count
			if doctype == "Service Type Unit Type":
				return []
			allocation_query_count += 1
			return ["ALLOC-1", "ALLOC-2"] if allocation_query_count == 1 else allocation_rows

		with (
			patch.object(service.frappe, "db", database),
			patch.object(service.frappe, "get_all", side_effect=get_all) as get_all_mock,
			patch.object(service, "_update_appointment_allocation_status") as update_status,
			patch.object(service, "_savepoint_name", return_value="confirm_couple_test"),
			patch.object(service, "now_datetime", return_value="2026-08-10 08:00:00"),
		):
			with self.assertRaisesRegex(RuntimeError, "second allocation failed"):
				service.confirm_couple_held_allocations(["APT-1", "APT-2"])

		self.assertEqual(
			get_all_mock.call_args_list[1].kwargs["filters"]["service_appointment"],
			["in", ["APT-1", "APT-2"]],
		)
		database.rollback.assert_called_once_with(save_point="confirm_couple_test")
		update_status.assert_not_called()
