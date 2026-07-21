from datetime import datetime, time, timedelta, timezone as datetime_timezone

from django.utils import timezone


def day_start(value):
    return timezone.make_aware(
        datetime.combine(value, time.min),
        timezone.get_current_timezone(),
    )


def utc_week_bounds(value=None):
    """Return the Monday-inclusive, next-Monday-exclusive UTC week bounds."""
    value = value or timezone.now()
    value_utc = value.astimezone(datetime_timezone.utc)
    week_start = (value_utc - timedelta(days=value_utc.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return week_start, week_start + timedelta(days=7)
