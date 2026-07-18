// Mock live report feed. Read-only — the web viewport only ever displays
// these, it never lets a user submit, confirm, or resolve a report.
// "landmark_bound" reports are tied to a specific venue_id and render as the
// red-tinted banner inside the Left Detail Drawer.
// "standalone" reports are not tied to an existing venue and render as the
// gray pill floating card on the map.

export const REPORTS = [
  {
    report_id: "r_2001",
    type: "landmark_bound",
    venue_id: "v_1002",
    icon: "/",
    message: "Elevator Broken",
    confirmations: 8,
    reported_at: "2026-06-08T08:42:00Z",
    source: "mobile_app",
  },
  {
    report_id: "r_2002",
    type: "standalone",
    venue_id: null,
    latitude: 40.758,
    longitude: -73.9855,
    icon: "!",
    message: "Ramp Blocked",
    confirmations: 12,
    reported_at: "2026-06-08T08:55:00Z",
    source: "mobile_app",
  },
  {
    report_id: "r_2003",
    type: "landmark_bound",
    venue_id: "v_1003",
    icon: "!",
    message: "Large crowd near entrance",
    confirmations: 5,
    reported_at: "2026-06-08T09:01:00Z",
    source: "mobile_app",
  },
];

export function getLandmarkAlertForVenue(venueId) {
  return REPORTS.find(
    (r) => r.type === "landmark_bound" && r.venue_id === venueId
  );
}

export function getStandaloneAlerts() {
  return REPORTS.filter((r) => r.type === "standalone");
}
