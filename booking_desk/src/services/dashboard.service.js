import { fetchDashboardAppointmentsForDate } from "@/api/dashboard.api";

const asDate = (dateValue) => {
	const [year, month, day] = String(dateValue).split("-").map(Number);
	return new Date(year, month - 1, day);
};

const isTodayIso = (dateValue) => {
	const now = new Date();
	const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
		now.getDate()
	).padStart(2, "0")}`;
	return dateValue === today;
};

const getStatus = (row) =>
	String(row.status || "")
		.trim()
		.toLowerCase();

const isCheckedIn = (row) => {
	const status = getStatus(row);
	return ["checked-in", "checked in"].includes(status);
};

const isOngoing = (row, selectedDate) => {
	const status = getStatus(row);
	return ["ongoing", "in progress"].includes(status);
};

const isDelayed = (row, selectedDate) => {
	if (!isTodayIso(selectedDate)) {
		return false;
	}
	if (getStatus(row) !== "checked-in") {
		return false;
	}
	if (row.actual_start_time) {
		return false;
	}

	const now = new Date();
	const start = row.start_time ? String(row.start_time).slice(0, 5) : "00:00";
	const [hour, minute] = start.split(":").map(Number);
	const startAt = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hour, minute);

	return now > startAt;
};

const hasPendingPayment = (row) => {
	if (getStatus(row) === "pending payment") {
		return true;
	}
	const paymentStatus = String(row.payment_status || "").toLowerCase();
	if (["unpaid", "partly paid"].includes(paymentStatus)) {
		return true;
	}
	return Number(row.outstanding_amount || 0) > 0;
};

const isNoShow = (row) => getStatus(row) === "no show";

const isCancelled = (row) => getStatus(row) === "cancelled";

export function mapDashboardMetrics(appointments, selectedDate) {
	return {
		todayAppointments: appointments.length,
		checkedIn: appointments.filter(isCheckedIn).length,
		ongoing: appointments.filter((item) => isOngoing(item, selectedDate)).length,
		completed: appointments.filter((item) => getStatus(item) === "completed").length,
		pendingPayment: appointments.filter(hasPendingPayment).length,
		cancelled: appointments.filter(isCancelled).length,
		delayed: appointments.filter((item) => isDelayed(item, selectedDate)).length,
		noShow: appointments.filter(isNoShow).length,
	};
}

export async function fetchDashboardMetrics(date) {
	const appointments = await fetchDashboardAppointmentsForDate(date);
	return mapDashboardMetrics(appointments, date);
}

export function getDateRangeByView(selectedDate, view) {
	const baseDate = asDate(selectedDate);

	if (view === "day") {
		return { fromDate: selectedDate, toDate: selectedDate };
	}

	if (view === "week") {
		const day = baseDate.getDay();
		const diff = day === 0 ? -6 : 1 - day;
		const start = new Date(baseDate);
		start.setDate(baseDate.getDate() + diff);
		const end = new Date(start);
		end.setDate(start.getDate() + 6);
		return {
			fromDate: toIsoDate(start),
			toDate: toIsoDate(end),
		};
	}

	const monthStart = new Date(baseDate.getFullYear(), baseDate.getMonth(), 1);
	const monthEnd = new Date(baseDate.getFullYear(), baseDate.getMonth() + 1, 0);
	return {
		fromDate: toIsoDate(monthStart),
		toDate: toIsoDate(monthEnd),
	};
}

export function toIsoDate(date) {
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
		date.getDate()
	).padStart(2, "0")}`;
}
