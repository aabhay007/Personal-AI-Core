"""Timezone-aware Date & Time Tool."""
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.tools.base import BaseTool


class DateTimeInput(BaseModel):
    timezone_name: Optional[str] = Field(
        "UTC",
        description="IANA timezone name, such as 'UTC', 'America/New_York', 'Europe/London', 'Asia/Kolkata', or 'Asia/Tokyo'."
    )


class DateTimeTool(BaseTool):
    name = "get_current_datetime"
    description = (
        "Get the current server-side date, time, and day of week for a specified timezone. "
        "Defaults to 'UTC' if no timezone is provided."
    )
    args_schema = DateTimeInput
    timeout_seconds = 2.0

    async def execute(self, timezone_name: Optional[str] = "UTC") -> Dict[str, Any]:
        """Compute the current date and time in the requested timezone."""
        target_tz = (timezone_name or "UTC").strip()
        try:
            tz = ZoneInfo(target_tz)
        except Exception:
            # Fallback to standard timezone.utc if invalid or missing tz database
            from datetime import timezone as dt_timezone
            tz = dt_timezone.utc
            target_tz = "UTC (fallback)"

        now = datetime.now(tz)

        return {
            "timezone": target_tz,
            "iso_timestamp": now.isoformat(),
            "formatted": now.strftime("%A, %B %d, %Y %I:%M:%S %p"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "utc_offset": now.strftime("%z"),
        }
