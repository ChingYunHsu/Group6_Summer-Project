export const REPORTS = [
    {
        "report_id": "r_501",
        "venue_id": "v_1002",
        "issue_type": "wheelchair_lift_broken",
        "latitude": 40.706086,
        "longitude": -73.996864,
        "status": "active",
        "confirmation_count": 2,
        "expires_in_minutes": 95,
        "created_at": "2026-05-28T10:00:00Z",
        "reported_by": "anonymous",
        "badge_text": "Multiple users confirm",
    },
    {
        "report_id": "r_502",
        "venue_id": "v_1003",
        "issue_type": "large_crowd",
        "latitude": 40.749825,
        "longitude": -73.797634,
        "status": "active",
        "confirmation_count": 0,
        "expires_in_minutes": 120,
        "created_at": "2026-05-28T10:30:00Z",
        "reported_by": "anonymous",
        "badge_text": "Live report",
    },
]

export const REPORT_TEMPLATE = {
    "status": "accepted",
    "report_id": "r_new",
    "message": "Report queued for validation.",
};