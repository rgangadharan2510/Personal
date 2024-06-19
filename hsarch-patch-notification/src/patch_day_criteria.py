from datetime import datetime, timedelta


def nth_weekday_of_month(day_of_week, nth_occurrence):
    """
    Determine the nth occurrence of a day_of_week in the current month.
    day_of_week is an integer where Monday = 0, ..., Sunday = 6.
    nth_occurrence is 1 for the 1st occurrence, 2 for the 2nd, etc.
    """

    # Check what is the month/year after 3 days from today. Use that for calculation logic
    post_day = datetime.today() + timedelta(days=3)

    start_of_month = datetime(post_day.year, post_day.month, 1)

    # Find the first day_of_week in the month
    first_day = (day_of_week - start_of_month.weekday() + 7) % 7 + 1

    # Calculate the nth occurrence of the day_of_week
    target_day = first_day + (nth_occurrence - 1) * 7

    # Calculate the date for this occurrence
    if target_day <= 31:  # Ensure it's within a valid day range for any month
        result_date = datetime(post_day.year, post_day.month, target_day)
    else:
        return None  # If it exceeds 31, it means there are not enough occurrences in this month

    return result_date


# Function to check if 3 days after is the nth weekday of the month
def is_nth_weekday_of_month(day_of_week, nth_occurrence):
    post_day = datetime.today() + timedelta(days=3)
    nth_day = nth_weekday_of_month(day_of_week, nth_occurrence)
    return post_day.date() == nth_day.date() if nth_day else False
