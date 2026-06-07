VENUES = [
    {
        "venue_id": "v_1001",
        "name": "Central Park Urgent Care",
        "venue_type": "clinic",
        "latitude": 40.785091,
        "longitude": -73.968285,
        "borough": "Manhattan",
        "language_tags": ["EN", "FR"],
        "primary_language": "EN",
        "secondary_language": "FR",
        "accessible_status": "full_access",
        "accessibility_features": ["ramp", "lift", "automatic_door", "disabled_toilet"],
        "active_warning": False,
        "live_report_count": 0,
        "busyness_level": "quiet",
        "busyness_percent": 24,
        "avg_wait_minutes": 5,
        "open_now": True,
        "address": "150 E 42nd St, New York, NY 10017",
        "phone": "+1 (212) 661-8139",
        "opening_hours": "Mon-Sun: 08:00 AM - 10:00 PM",
        "distance_km": 0.8,
        "supported_services": ["Bilingual Staff (French)", "First-Aid Kit"],
        "live_status_badge": "Open Now",
        "forecast_mode": "live",
        "busyness_forecast_12h": [
            {"offset_hours": 0, "percent": 20, "level": "quiet"},
            {"offset_hours": 3, "percent": 35, "level": "moderate"},
            {"offset_hours": 6, "percent": 60, "level": "moderate"},
            {"offset_hours": 9, "percent": 80, "level": "busy"},
            {"offset_hours": 12, "percent": 40, "level": "moderate"},
        ],
        "is_favourite": True,
    },
    {
        "venue_id": "v_1002",
        "name": "Brooklyn Bridge Pharmacy",
        "venue_type": "pharmacy",
        "latitude": 40.706086,
        "longitude": -73.996864,
        "borough": "Brooklyn",
        "language_tags": ["EN", "ES"],
        "primary_language": "EN",
        "secondary_language": "ES",
        "accessible_status": "partial",
        "accessibility_features": ["ramp", "disabled_toilet"],
        "active_warning": True,
        "live_report_count": 2,
        "busyness_level": "moderate",
        "busyness_percent": 53,
        "avg_wait_minutes": 12,
        "open_now": True,
        "address": "10 Brooklyn Bridge Blvd, Brooklyn, NY 11201",
        "phone": "+1 (718) 555-0102",
        "opening_hours": "Mon-Fri: 09:00 AM - 09:00 PM",
        "distance_km": 3.2,
        "supported_services": ["Bilingual Staff (Spanish)", "First-Aid Kit"],
        "live_status_badge": "Open Now - Closes 10:00 PM",
        "forecast_mode": "live",
        "busyness_forecast_12h": [
            {"offset_hours": 0, "percent": 40, "level": "moderate"},
            {"offset_hours": 3, "percent": 55, "level": "moderate"},
            {"offset_hours": 6, "percent": 75, "level": "busy"},
            {"offset_hours": 9, "percent": 65, "level": "busy"},
            {"offset_hours": 12, "percent": 35, "level": "moderate"},
        ],
        "is_favourite": True,
    },
    {
        "venue_id": "v_1003",
        "name": "Queens Transit Hub",
        "venue_type": "clinic",
        "latitude": 40.749825,
        "longitude": -73.797634,
        "borough": "Queens",
        "language_tags": ["EN", "ZH"],
        "primary_language": "EN",
        "secondary_language": "ZH",
        "accessible_status": "step_free_route_only",
        "accessibility_features": ["step_free_route"],
        "active_warning": True,
        "live_report_count": 1,
        "busyness_level": "busy",
        "busyness_percent": 81,
        "avg_wait_minutes": 7,
        "open_now": False,
        "address": "Queens Transit Hub, Queens, NY 11373",
        "phone": "+1 (718) 555-0144",
        "opening_hours": "Mon-Sun: 06:00 AM - 11:30 PM",
        "distance_km": 5.4,
        "supported_services": ["First-Aid Kit"],
        "live_status_badge": "Closed - Opens 06:00 AM",
        "forecast_mode": "predicted",
        "busyness_forecast_12h": [
            {"offset_hours": 0, "percent": 75, "level": "busy"},
            {"offset_hours": 3, "percent": 60, "level": "moderate"},
            {"offset_hours": 6, "percent": 45, "level": "moderate"},
            {"offset_hours": 9, "percent": 25, "level": "quiet"},
            {"offset_hours": 12, "percent": 20, "level": "quiet"},
        ],
        "is_favourite": False,
    },
]

REPORTS = [
    {
        "report_id": "r_501",
        "venue_id": "v_1002",
        "issue_type": "wheelchair_lift_broken",
        "latitude": 40.706086,
        "longitude": -73.996864,
        "status": "active",
        "confirmation_count": 8,
        "expires_in_minutes": 95,
        "created_at": "2026-05-28T10:00:00Z",
        "reported_by": "anonymous",
        "badge_text": "8 users confirmed",
    },
    {
        "report_id": "r_502",
        "venue_id": "v_1003",
        "issue_type": "large_crowd",
        "latitude": 40.749825,
        "longitude": -73.797634,
        "status": "active",
        "confirmation_count": 12,
        "expires_in_minutes": 120,
        "created_at": "2026-05-28T10:30:00Z",
        "reported_by": "anonymous",
        "badge_text": "12 users confirmed",
    },
]

REPORT_TEMPLATE = {
    "status": "accepted",
    "report_id": "r_new",
    "message": "Report queued for validation.",
}

USER_PROFILE = {
    "user_id": "u_1001",
    "account_state": "logged_in",
    "full_name": "Amelia Rivera",
    "email": "amelia.rivera@example.com",
    "phone": "+1 (917) 555-0118",
    "date_of_birth": "1998-04-12",
    "gender": "Female",
    "nationality": "Spanish",
    "address": "245 W 46th St, New York, NY 10036",
    "spoken_languages": ["English", "Spanish", "French"],
    "guest_prompt_title": "Secure Your Medical ID",
    "avatar_initials": "AR",
}

MEDICAL_ID = {
    "blood_type": "O+",
    "severe_allergies": ["Penicillin", "Peanuts"],
    "conditions": ["Asthma"],
    "medications": ["Salbutamol Inhaler"],
    "emergency_notes": "Prefers communication in Spanish during emergencies.",
    "medical_pass_title": "MEDICAL ALERT / ALERTA MÉDICA",
}

EMERGENCY_CONTACTS = [
    {
        "contact_id": "ec_001",
        "name": "Lucia Rivera",
        "relationship": "Mother",
        "phone": "+34 612 345 678",
    },
    {
        "contact_id": "ec_002",
        "name": "Daniel Ortiz",
        "relationship": "Friend",
        "phone": "+1 (646) 555-0191",
    },
]

USER_SETTINGS = {
    "selected_language": "English",
    "selected_language_native": "English",
    "location_access_enabled": True,
    "notifications_enabled": True,
    "privacy_mode": "standard",
    "guest_mode_enabled": False,
    "show_medical_id_on_sos": True,
    "data_export_available": True,
    "delete_account_enabled": True,
}

LANGUAGE_OPTIONS = [
    {"code": "en", "native_name": "English", "english_name": "English"},
    {"code": "fr", "native_name": "Français", "english_name": "French"},
    {"code": "es", "native_name": "Español", "english_name": "Spanish"},
    {"code": "zh", "native_name": "中文", "english_name": "Chinese"},
    {"code": "ar", "native_name": "العربية", "english_name": "Arabic"},
]

FAVOURITES = [
    {
        "favourite_id": "fav_001",
        "venue_id": "v_1001",
        "saved_at": "2026-06-01T09:15:00Z",
        "display_status": "OPTIMAL FLOW",
    },
    {
        "favourite_id": "fav_002",
        "venue_id": "v_1002",
        "saved_at": "2026-06-02T14:40:00Z",
        "display_status": "MODERATE",
    },
]

INSIGHTS_DASHBOARD = {
    "district": "Midtown East",
    "real_time_density": {
        "percent": 84,
        "trend_label": "+4% vs last hour",
    },
    "quick_triage": {
        "wait_minutes": 12,
        "venue_name": "Central Park Urgent Care",
    },
    "best_travel_window": {
        "start": "2:30 PM",
        "end": "4:00 PM",
        "cta_label": "Plan Route",
    },
    "chart_mode": "12_hour_predicted",
    "prediction_series": [42, 38, 35, 33, 40, 52, 61, 68, 73, 64, 51, 39],
    "history_series_7d": [58, 62, 49, 71, 66, 54, 47],
    "fastest_hubs": [
        {
            "rank": 1,
            "venue_id": "v_1001",
            "venue_name": "Central Park Urgent Care",
            "travel_minutes": 5,
            "wait_minutes": 5,
            "language_flags": ["EN", "FR"],
            "flow_status": "OPTIMAL FLOW",
        },
        {
            "rank": 2,
            "venue_id": "v_1002",
            "venue_name": "Brooklyn Bridge Pharmacy",
            "travel_minutes": 8,
            "wait_minutes": 12,
            "language_flags": ["EN", "ES"],
            "flow_status": "MODERATE",
        },
        {
            "rank": 3,
            "venue_id": "v_1003",
            "venue_name": "Queens Transit Hub",
            "travel_minutes": 10,
            "wait_minutes": 7,
            "language_flags": ["EN", "ZH"],
            "flow_status": "DIVERTING",
        },
    ],
}

ROUTE_OPTIONS = {
    "origin_label": "Current Location",
    "destination_venue_id": "v_1002",
    "departure_time_label": "Leave Now",
    "options": [
        {
            "mode": "walk",
            "duration_minutes": 18,
            "status": "available",
            "summary": "Fastest walking route",
        },
        {
            "mode": "transit",
            "duration_minutes": 12,
            "status": "available",
            "summary": "Subway 6 + 4 min walk",
        },
        {
            "mode": "drive",
            "duration_minutes": 9,
            "status": "moderate_traffic",
            "summary": "Moderate congestion",
        },
    ],
}

ROUTE_DETAIL = {
    "destination_venue_id": "v_1002",
    "polyline_preview": [
        {"latitude": 40.7580, "longitude": -73.9855},
        {"latitude": 40.7482, "longitude": -73.9874},
        {"latitude": 40.7061, "longitude": -73.9969},
    ],
    "steps": [
        "Start at Current Location.",
        "Walk 4 minutes to the nearest subway entrance.",
        "Take Subway 6 downtown for 2 stops.",
        "Exit and walk 3 minutes to Brooklyn Bridge Pharmacy.",
    ],
    "start_navigation_label": "Start Navigation",
}

APP_STATE = {
    "is_guest": False,
    "is_authenticated": True,
    "has_accepted_terms": True,
    "has_accepted_privacy_policy": True,
    "location_permission": "granted",
    "show_finish_profile_prompt": False,
}