"""
This module computes the next weekly expiry (Tuesday) and formats it
to match Angel One's option symbol format (e.g., '27JUN25').
"""

from datetime import datetime, timedelta


def get_next_tuesday(from_date=None):
    """
    Returns the next Tuesday date from the given date.
    If from_date is None, uses today.
    """
    if from_date is None:
        from_date = datetime.now()

    days_ahead = (1 - from_date.weekday() + 7) % 7  # 1 = Tuesday
    days_ahead = 7 if days_ahead == 0 else days_ahead  # skip today if already Tuesday
    next_tuesday = from_date + timedelta(days=days_ahead)
    return next_tuesday


def format_expiry(expiry_date: datetime) -> str:
    """
    Formats the expiry date as '27JUN25' for option symbols.

    Args:
        expiry_date (datetime): The expiry date.

    Returns:
        str: Formatted expiry string.
    """
    return expiry_date.strftime("%d%b%y").upper()


def get_weekly_expiry_str():
    now = datetime.now()
    today = now.date()
    weekday = today.weekday()  # Monday = 0 ... Tuesday = 1

    # Find upcoming Tuesday
    days_ahead = (1 - weekday) % 7
    expiry_date = today + timedelta(days=days_ahead)

    # If today is Tuesday and time is before 3:30 PM → use today
    if weekday == 1 and now.time() < datetime.strptime("15:30", "%H:%M").time():
        expiry_date = today
    elif weekday == 1 and now.time() >= datetime.strptime("15:30", "%H:%M").time():
        expiry_date = today + timedelta(days=7)

    return expiry_date.strftime("%d%b%y").upper()


def get_monthly_expiry_date():
    """
    Returns the expiry date (last Tuesday) of the current or next month,
    depending on today's date.
    """
    today = datetime.today()

    # Find the last day of the current month
    if today.month < 12:
        last_day_current = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
    else:
        last_day_current = datetime(today.year + 1, 1, 1) - timedelta(days=1)

    # Find last Tuesday of the current month
    last_tuesday_current = last_day_current
    while last_tuesday_current.weekday() != 1:  # 0=Mon, 1=Tue, ...
        last_tuesday_current -= timedelta(days=1)

    # If we've already passed this month's expiry, go to next month
    if today > last_tuesday_current:
        # Move to next month
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        last_day_next = datetime(next_year, next_month + 1, 1) - timedelta(days=1) if next_month < 12 else datetime(
            next_year + 1, 1, 1) - timedelta(days=1)

        last_tuesday_next = last_day_next
        while last_tuesday_next.weekday() != 1:
            last_tuesday_next -= timedelta(days=1)
        expiry = last_tuesday_next
    else:
        expiry = last_tuesday_current

    return expiry.strftime("%d%b%y").upper()  # Format like 26NOV25


# Example usage
if __name__ == "__main__":
    print("Next Weekly Expiry:", get_weekly_expiry_str())
    print("Next Weekly Expiry Tuesday:", get_monthly_expiry_date())
