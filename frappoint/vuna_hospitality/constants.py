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
)

# Roles that take reservations (hold, confirm, cancel).
RESERVATION_ROLES = (
	"System Manager",
	HOSPITALITY_MANAGER,
	RESERVATIONS_AGENT,
	FRONT_DESK_AGENT,
	FRONT_DESK_MANAGER,
)
