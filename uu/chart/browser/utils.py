from datetime import date, datetime

import pytz
from tzlocal import get_localzone as system_timezone

try:
    from plone.app.event.base import default_timezone
    HAS_PAE = True
except ImportError:
    HAS_PAE = False


def withtz(dt):
    if HAS_PAE:
        tz = default_timezone()  # site-specific or user-specific
        if isinstance(tz, str):
            tz = pytz.timezone(tz)
    else:
        # fallback to system tz if site-specific local time is not available:
        tz = system_timezone()
    if isinstance(dt, date):
        return tz.localize(datetime(*dt.timetuple()[:7]))
    if dt.tzinfo is not None:
        return dt
    return tz.localize(dt)

