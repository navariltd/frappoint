"""Names shared across the Vuna Hospitality module.

Keep role and DocType names here so services, permissions, tests, and fixtures refer to one
spelling.
"""

MODULE = "Vuna Hospitality"
SETTINGS_DOCTYPE = "Hospitality Settings"
EVENT_LOG_DOCTYPE = "Hospitality Event Log"

# The DocType that scopes hotel data. Users are restricted to properties with User Permissions.
PROPERTY_DOCTYPE = "Hotel Property"
PROPERTY_FIELD = "property"

# Roles. Maintenance work reuses ERPNext's "Maintenance User" and
# "Maintenance Manager" roles instead of defining new ones.
HOSPITALITY_MANAGER = "Hospitality Manager"
RESERVATIONS_AGENT = "Reservations Agent"
FRONT_DESK_AGENT = "Front Desk Agent"
FRONT_DESK_MANAGER = "Front Desk Manager"
CASHIER = "Cashier"
NIGHT_AUDITOR = "Night Auditor"
HOUSEKEEPING_ATTENDANT = "Housekeeping Attendant"
HOUSEKEEPING_SUPERVISOR = "Housekeeping Supervisor"
REVENUE_MANAGER = "Revenue Manager"
HOTEL_ACCOUNTANT = "Hotel Accountant"
GUEST_SERVICES_AGENT = "Guest Services Agent"
DATA_PROTECTION_OFFICER = "Data Protection Officer"

HOSPITALITY_ROLES = (
	HOSPITALITY_MANAGER,
	RESERVATIONS_AGENT,
	FRONT_DESK_AGENT,
	FRONT_DESK_MANAGER,
	CASHIER,
	NIGHT_AUDITOR,
	HOUSEKEEPING_ATTENDANT,
	HOUSEKEEPING_SUPERVISOR,
	REVENUE_MANAGER,
	HOTEL_ACCOUNTANT,
	GUEST_SERVICES_AGENT,
	DATA_PROTECTION_OFFICER,
)

# Roles that see every property regardless of User Permissions.
UNRESTRICTED_ROLES = ("System Manager", "Administrator")

# DocTypes that carry a required `property` field and are filtered by property.
# Each feature appends its DocTypes here; hooks.py builds the permission hooks from this list.
PROPERTY_SCOPED_DOCTYPES: tuple[str, ...] = (
	# F1 Property and rooms
	"Room Type",
	"Hotel Room",
	"Room State Period",
	# F2 Room inventory engine
	"Room Type Inventory Day",
	# F3 Charge codes, rates, and quote
	"Hotel Policy",
	"Rate Plan",
	"Room Rate Day",
	"Rate Season",
	# F5 Booking, hold, and confirm
	"Hotel Booking",
	"Stay Reservation",
	"Room Occupancy",
	"Occupancy Membership",
	"Stay Rate Night",
	# F6 Stay guests, room assignment, check-in and check-out
	"Stay Guest",
	"Room Assignment",
	# F7 Folio and posting engine
	"Guest Folio",
	"Folio Transaction",
	# F8 Night audit (minimal)
	"Night Audit Run",
	# F9 Taxes, packages, and occupancy pricing
	"Occupancy Pricing Rule",
	"Hotel Package",
	"Package Allowance Entry",
	# F10 Payments and cashier shifts
	"Cashier Shift",
	"Folio Payment",
	"Folio Payment Allocation",
)

# Roles that post charges to a folio by hand (§23.1: front desk posts within limits).
FOLIO_POSTING_ROLES = (
	"System Manager",
	HOSPITALITY_MANAGER,
	FRONT_DESK_MANAGER,
	FRONT_DESK_AGENT,
	CASHIER,
)

# Roles that reverse a posted transaction or override a check-out balance (§23.1, §23.2).
FOLIO_MANAGER_ROLES = ("System Manager", HOSPITALITY_MANAGER, FRONT_DESK_MANAGER)

# Roles that rebuild cached folio balances from their transactions.
FOLIO_REBUILD_ROLES = ("System Manager", HOSPITALITY_MANAGER, HOTEL_ACCOUNTANT)

# Roles that take payments at the desk and run a cashier shift (§23.1).
CASHIER_ROLES = ("System Manager", HOSPITALITY_MANAGER, CASHIER, FRONT_DESK_MANAGER, FRONT_DESK_AGENT)

# Roles that review a closed shift and post its variances (§16.1), and approve refunds.
CASHIER_SUPERVISOR_ROLES = ("System Manager", HOSPITALITY_MANAGER, FRONT_DESK_MANAGER, HOTEL_ACCOUNTANT)

# Roles that start night audit (§23.1). It is always started by a person, never scheduled.
NIGHT_AUDIT_ROLES = ("System Manager", HOSPITALITY_MANAGER, NIGHT_AUDITOR)

# Roles that take reservations (hold, confirm, cancel).
RESERVATION_ROLES = (
	"System Manager",
	HOSPITALITY_MANAGER,
	RESERVATIONS_AGENT,
	FRONT_DESK_AGENT,
	FRONT_DESK_MANAGER,
)

# Roles that settle a folio into a Sales Invoice (§17.3). Cashiers settle what they collect.
SETTLEMENT_ROLES = CASHIER_ROLES

# Roles that transfer a folio balance to a company's receivable, and issue credit notes for
# invoiced charges (§17.3, §17.4). Going over a credit limit also needs ERPNext's Credit Controller.
FOLIO_ACCOUNTING_ROLES = ("System Manager", HOSPITALITY_MANAGER, FRONT_DESK_MANAGER, HOTEL_ACCOUNTANT)
