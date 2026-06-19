from datetime import datetime, time

from django.utils import timezone


def day_start(value):
    return timezone.make_aware(
        datetime.combine(value, time.min),
        timezone.get_current_timezone(),
    )
