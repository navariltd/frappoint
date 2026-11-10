"""Checks on the hospitality DocType JSON files themselves."""

import json
from collections import Counter
from pathlib import Path
from unittest import TestCase

DOCTYPE_DIR = Path(__file__).resolve().parent.parent / "doctype"


def _doctype_definitions():
	for path in sorted(DOCTYPE_DIR.glob("*/*.json")):
		definition = json.loads(path.read_text())
		if definition.get("doctype") == "DocType":
			yield definition


class TestDocTypeDefinitions(TestCase):
	def test_one_permission_rule_per_role_level_and_owner(self):
		"""Frappe refuses to save a DocType with two rules for the same role, level and if-owner."""
		duplicates = {}
		for definition in _doctype_definitions():
			rules = Counter(
				(rule["role"], rule.get("permlevel", 0), rule.get("if_owner", 0))
				for rule in definition.get("permissions", [])
			)
			repeated = [key for key, count in rules.items() if count > 1]
			if repeated:
				duplicates[definition["name"]] = repeated
		self.assertEqual(duplicates, {})

	def test_connections_point_at_existing_link_fields(self):
		broken = []
		definitions = {definition["name"]: definition for definition in _doctype_definitions()}
		for definition in definitions.values():
			for link in definition.get("links", []):
				target = definitions.get(link["link_doctype"])
				if target and link["link_fieldname"] not in {f["fieldname"] for f in target["fields"]}:
					broken.append(f"{definition['name']} -> {link['link_doctype']}.{link['link_fieldname']}")
		self.assertEqual(broken, [])
