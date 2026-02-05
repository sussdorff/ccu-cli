"""Thermostat schedule (Heizprofil/Wochenprogramm) handling.

Supports legacy HomeMatic thermostats like HM-TC-IT-WM-W-EU and HM-CC-RT-DN.

Schedule structure:
- 3 profiles (P1, P2, P3), selected via WEEK_PROGRAM_POINTER (0, 1, 2)
- Each profile has 13 time slots per day
- Each slot has ENDTIME (minutes since midnight) and TEMPERATURE
- Slots are sequential: slot N runs from slot N-1's ENDTIME to slot N's ENDTIME
"""

from dataclasses import dataclass, field
from typing import Any

# Days in HomeMatic parameter naming order
WEEKDAYS = [
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
]

# Short names for CLI
WEEKDAY_SHORT = {
    "mon": "MONDAY",
    "tue": "TUESDAY",
    "wed": "WEDNESDAY",
    "thu": "THURSDAY",
    "fri": "FRIDAY",
    "sat": "SATURDAY",
    "sun": "SUNDAY",
    "monday": "MONDAY",
    "tuesday": "TUESDAY",
    "wednesday": "WEDNESDAY",
    "thursday": "THURSDAY",
    "friday": "FRIDAY",
    "saturday": "SATURDAY",
    "sunday": "SUNDAY",
}

MAX_SLOTS = 13
END_OF_DAY = 1440  # 24:00 in minutes


@dataclass
class TimeSlot:
    """A single time slot in a heating schedule."""

    slot_number: int  # 1-13
    end_minutes: int  # Minutes since midnight (0-1440)
    temperature: float  # Target temperature in °C

    @property
    def end_time(self) -> str:
        """Return end time as HH:MM string."""
        hours = self.end_minutes // 60
        minutes = self.end_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    @property
    def is_active(self) -> bool:
        """Check if this slot is active (not set to end-of-day placeholder)."""
        # Slots with end_minutes == 1440 after the first real slot are inactive
        return self.end_minutes < END_OF_DAY or self.slot_number == 1


@dataclass
class DaySchedule:
    """Schedule for a single day."""

    day: str  # MONDAY, TUESDAY, etc.
    slots: list[TimeSlot] = field(default_factory=list)

    def get_active_slots(self) -> list[TimeSlot]:
        """Return only the active (non-placeholder) slots."""
        active = []
        for slot in self.slots:
            active.append(slot)
            # Once we hit end-of-day, remaining slots are placeholders
            if slot.end_minutes >= END_OF_DAY:
                break
        return active


@dataclass
class WeekSchedule:
    """Complete weekly heating schedule (one profile)."""

    profile_number: int  # 1, 2, or 3
    days: dict[str, DaySchedule] = field(default_factory=dict)
    comfort_temp: float = 21.0
    lowering_temp: float = 17.0

    def __post_init__(self) -> None:
        # Initialize empty days if not provided
        for day in WEEKDAYS:
            if day not in self.days:
                self.days[day] = DaySchedule(day=day)


def parse_time(time_str: str) -> int:
    """Parse time string (HH:MM) to minutes since midnight.

    Args:
        time_str: Time in HH:MM format (e.g., "05:00", "21:30")

    Returns:
        Minutes since midnight

    Raises:
        ValueError: If format is invalid
    """
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {time_str} (expected HH:MM)")

    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str} (expected HH:MM)")

    if not (0 <= hours <= 24) or not (0 <= minutes < 60):
        raise ValueError(f"Invalid time: {time_str}")

    if hours == 24 and minutes > 0:
        raise ValueError(f"Invalid time: {time_str} (use 24:00 for end of day)")

    return hours * 60 + minutes


def format_time(minutes: int) -> str:
    """Format minutes since midnight as HH:MM.

    Args:
        minutes: Minutes since midnight (0-1440)

    Returns:
        Time string in HH:MM format
    """
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def parse_schedule_from_paramset(
    params: dict[str, Any], profile: int = 1
) -> WeekSchedule:
    """Parse a weekly schedule from device MASTER paramset.

    Args:
        params: MASTER paramset dictionary from device
        profile: Profile number (1, 2, or 3)

    Returns:
        WeekSchedule object
    """
    prefix = f"P{profile}_"

    schedule = WeekSchedule(
        profile_number=profile,
        comfort_temp=params.get("TEMPERATURE_COMFORT", 21.0),
        lowering_temp=params.get("TEMPERATURE_LOWERING", 17.0),
    )

    for day in WEEKDAYS:
        day_schedule = DaySchedule(day=day)

        for slot_num in range(1, MAX_SLOTS + 1):
            endtime_key = f"{prefix}ENDTIME_{day}_{slot_num}"
            temp_key = f"{prefix}TEMPERATURE_{day}_{slot_num}"

            end_minutes = params.get(endtime_key, END_OF_DAY)
            temperature = params.get(temp_key, schedule.lowering_temp)

            day_schedule.slots.append(
                TimeSlot(
                    slot_number=slot_num,
                    end_minutes=end_minutes,
                    temperature=temperature,
                )
            )

        schedule.days[day] = day_schedule

    return schedule


def build_schedule_params(
    schedule: WeekSchedule,
) -> dict[str, Any]:
    """Build MASTER paramset dictionary from a WeekSchedule.

    Args:
        schedule: WeekSchedule to convert

    Returns:
        Dictionary of parameters to set via putParamset
    """
    prefix = f"P{schedule.profile_number}_"
    params: dict[str, Any] = {}

    for day, day_schedule in schedule.days.items():
        for slot in day_schedule.slots:
            endtime_key = f"{prefix}ENDTIME_{day}_{slot.slot_number}"
            temp_key = f"{prefix}TEMPERATURE_{day}_{slot.slot_number}"

            params[endtime_key] = slot.end_minutes
            params[temp_key] = slot.temperature

    return params


def create_simple_schedule(
    profile: int,
    heat_start: str,
    heat_end: str,
    comfort_temp: float,
    lowering_temp: float,
    days: list[str] | None = None,
) -> WeekSchedule:
    """Create a simple schedule with one heating period per day.

    Args:
        profile: Profile number (1, 2, or 3)
        heat_start: Start of heating period (HH:MM)
        heat_end: End of heating period (HH:MM)
        comfort_temp: Temperature during heating period
        lowering_temp: Temperature outside heating period
        days: Days to apply to (default: all days)

    Returns:
        WeekSchedule with the specified heating period
    """
    start_minutes = parse_time(heat_start)
    end_minutes = parse_time(heat_end)

    if days is None:
        target_days = WEEKDAYS
    else:
        target_days = [WEEKDAY_SHORT.get(d.lower(), d.upper()) for d in days]

    schedule = WeekSchedule(
        profile_number=profile,
        comfort_temp=comfort_temp,
        lowering_temp=lowering_temp,
    )

    for day in WEEKDAYS:
        day_schedule = DaySchedule(day=day)

        if day in target_days:
            # Slot 1: lowering until heat_start
            # Slot 2: comfort until heat_end
            # Slot 3: lowering until end of day
            # Remaining slots: end-of-day placeholders

            day_schedule.slots = [
                TimeSlot(1, start_minutes, lowering_temp),
                TimeSlot(2, end_minutes, comfort_temp),
                TimeSlot(3, END_OF_DAY, lowering_temp),
            ]

            # Fill remaining slots with placeholders
            for i in range(4, MAX_SLOTS + 1):
                day_schedule.slots.append(TimeSlot(i, END_OF_DAY, lowering_temp))
        else:
            # Keep existing schedule or use defaults
            for i in range(1, MAX_SLOTS + 1):
                day_schedule.slots.append(TimeSlot(i, END_OF_DAY, lowering_temp))

        schedule.days[day] = day_schedule

    return schedule


def create_constant_schedule(
    profile: int,
    temperature: float,
    days: list[str] | None = None,
) -> WeekSchedule:
    """Create a schedule with constant temperature (no night setback).

    Args:
        profile: Profile number (1, 2, or 3)
        temperature: Constant target temperature
        days: Days to apply to (default: all days)

    Returns:
        WeekSchedule with constant temperature
    """
    if days is None:
        target_days = WEEKDAYS
    else:
        target_days = [WEEKDAY_SHORT.get(d.lower(), d.upper()) for d in days]

    schedule = WeekSchedule(
        profile_number=profile,
        comfort_temp=temperature,
        lowering_temp=temperature,
    )

    for day in WEEKDAYS:
        day_schedule = DaySchedule(day=day)

        if day in target_days:
            # Single slot covering entire day at constant temperature
            day_schedule.slots = [TimeSlot(1, END_OF_DAY, temperature)]

            # Fill remaining slots with placeholders
            for i in range(2, MAX_SLOTS + 1):
                day_schedule.slots.append(TimeSlot(i, END_OF_DAY, temperature))
        else:
            # Placeholder slots
            for i in range(1, MAX_SLOTS + 1):
                day_schedule.slots.append(TimeSlot(i, END_OF_DAY, temperature))

        schedule.days[day] = day_schedule

    return schedule
