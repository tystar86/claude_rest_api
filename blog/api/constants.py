"""Shared API constants (import-light; safe for routers without circular imports)."""

AUTHENTICATION_REQUIRED_DETAIL = "Authentication credentials were not provided."

DASHBOARD_CACHE_KEY = "dashboard_data"
DASHBOARD_CACHE_TTL = 60  # seconds

ACTIVITY_CACHE_KEY = "activity_data"
ACTIVITY_CACHE_TTL = 300  # seconds (5 minutes) — header ticker; short DB/query load
