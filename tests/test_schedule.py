"""Tests for thermostat schedule handling."""

import pytest

from ccu_cli.schedule import (
    WEEKDAYS,
    TimeSlot,
    DaySchedule,
    WeekSchedule,
    parse_time,
    format_time,
    parse_schedule_from_paramset,
    build_schedule_params,
    create_simple_schedule,
    create_constant_schedule,
)


class TestParseTime:
    """Tests for parse_time function."""

    def test_parses_midnight(self) -> None:
        assert parse_time("00:00") == 0

    def test_parses_end_of_day(self) -> None:
        assert parse_time("24:00") == 1440

    def test_parses_morning(self) -> None:
        assert parse_time("05:00") == 300

    def test_parses_with_minutes(self) -> None:
        assert parse_time("06:30") == 390

    def test_parses_afternoon(self) -> None:
        assert parse_time("14:45") == 885

    def test_accepts_single_digit_hour(self) -> None:
        # Single digit hour is valid
        assert parse_time("5:00") == 300
        assert parse_time("9:30") == 570

    def test_rejects_no_colon(self) -> None:
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time("0530")

    def test_rejects_invalid_hour(self) -> None:
        with pytest.raises(ValueError, match="Invalid time"):
            parse_time("25:00")

    def test_rejects_invalid_minute(self) -> None:
        with pytest.raises(ValueError, match="Invalid time"):
            parse_time("12:60")


class TestFormatTime:
    """Tests for format_time function."""

    def test_formats_midnight(self) -> None:
        assert format_time(0) == "00:00"

    def test_formats_end_of_day(self) -> None:
        assert format_time(1440) == "24:00"

    def test_formats_morning(self) -> None:
        assert format_time(300) == "05:00"

    def test_formats_with_minutes(self) -> None:
        assert format_time(390) == "06:30"


class TestTimeSlot:
    """Tests for TimeSlot dataclass."""

    def test_end_time_property(self) -> None:
        slot = TimeSlot(slot_number=1, end_minutes=360, temperature=17.0)
        assert slot.end_time == "06:00"

    def test_is_active_when_before_end_of_day(self) -> None:
        slot = TimeSlot(slot_number=1, end_minutes=360, temperature=17.0)
        assert slot.is_active is True

    def test_is_active_first_slot_at_end_of_day(self) -> None:
        # First slot is always active even if end_minutes is 1440
        slot = TimeSlot(slot_number=1, end_minutes=1440, temperature=21.0)
        assert slot.is_active is True

    def test_not_active_placeholder_slot(self) -> None:
        slot = TimeSlot(slot_number=5, end_minutes=1440, temperature=17.0)
        assert slot.is_active is False


class TestDaySchedule:
    """Tests for DaySchedule dataclass."""

    def test_get_active_slots_filters_placeholders(self) -> None:
        day = DaySchedule(
            day="MONDAY",
            slots=[
                TimeSlot(1, 360, 17.0),
                TimeSlot(2, 1200, 21.0),
                TimeSlot(3, 1440, 17.0),  # End of day marker
                TimeSlot(4, 1440, 17.0),  # Placeholder
                TimeSlot(5, 1440, 17.0),  # Placeholder
            ],
        )
        active = day.get_active_slots()
        assert len(active) == 3
        assert active[0].slot_number == 1
        assert active[1].slot_number == 2
        assert active[2].slot_number == 3


class TestParseScheduleFromParamset:
    """Tests for parse_schedule_from_paramset function."""

    def test_parses_basic_schedule(self) -> None:
        params = {
            "TEMPERATURE_COMFORT": 21.0,
            "TEMPERATURE_LOWERING": 17.0,
            "WEEK_PROGRAM_POINTER": 0,
            "P1_ENDTIME_MONDAY_1": 360,
            "P1_TEMPERATURE_MONDAY_1": 17.0,
            "P1_ENDTIME_MONDAY_2": 1200,
            "P1_TEMPERATURE_MONDAY_2": 21.0,
            "P1_ENDTIME_MONDAY_3": 1440,
            "P1_TEMPERATURE_MONDAY_3": 17.0,
        }
        # Add remaining slots as placeholders
        for i in range(4, 14):
            params[f"P1_ENDTIME_MONDAY_{i}"] = 1440
            params[f"P1_TEMPERATURE_MONDAY_{i}"] = 17.0

        schedule = parse_schedule_from_paramset(params, profile=1)

        assert schedule.profile_number == 1
        assert schedule.comfort_temp == 21.0
        assert schedule.lowering_temp == 17.0

        monday = schedule.days["MONDAY"]
        active = monday.get_active_slots()
        assert len(active) == 3
        assert active[0].end_minutes == 360
        assert active[0].temperature == 17.0
        assert active[1].end_minutes == 1200
        assert active[1].temperature == 21.0


class TestBuildScheduleParams:
    """Tests for build_schedule_params function."""

    def test_builds_correct_keys(self) -> None:
        schedule = WeekSchedule(profile_number=1)
        schedule.days["MONDAY"] = DaySchedule(
            day="MONDAY",
            slots=[
                TimeSlot(1, 300, 17.0),
                TimeSlot(2, 1320, 21.0),
                TimeSlot(3, 1440, 17.0),
            ],
        )

        params = build_schedule_params(schedule)

        assert params["P1_ENDTIME_MONDAY_1"] == 300
        assert params["P1_TEMPERATURE_MONDAY_1"] == 17.0
        assert params["P1_ENDTIME_MONDAY_2"] == 1320
        assert params["P1_TEMPERATURE_MONDAY_2"] == 21.0


class TestCreateSimpleSchedule:
    """Tests for create_simple_schedule function."""

    def test_creates_three_slot_schedule(self) -> None:
        schedule = create_simple_schedule(
            profile=1,
            heat_start="05:00",
            heat_end="22:00",
            comfort_temp=21.0,
            lowering_temp=17.0,
        )

        monday = schedule.days["MONDAY"]
        active = monday.get_active_slots()

        # Should have 3 active slots
        assert len(active) == 3

        # Slot 1: lowering until 05:00
        assert active[0].end_minutes == 300
        assert active[0].temperature == 17.0

        # Slot 2: comfort until 22:00
        assert active[1].end_minutes == 1320
        assert active[1].temperature == 21.0

        # Slot 3: lowering until 24:00
        assert active[2].end_minutes == 1440
        assert active[2].temperature == 17.0

    def test_applies_to_all_days_by_default(self) -> None:
        schedule = create_simple_schedule(
            profile=1,
            heat_start="06:00",
            heat_end="20:00",
            comfort_temp=21.0,
            lowering_temp=17.0,
        )

        for day in WEEKDAYS:
            active = schedule.days[day].get_active_slots()
            assert len(active) == 3

    def test_applies_to_specific_days(self) -> None:
        schedule = create_simple_schedule(
            profile=1,
            heat_start="06:00",
            heat_end="20:00",
            comfort_temp=21.0,
            lowering_temp=17.0,
            days=["mon", "tue", "wed", "thu", "fri"],
        )

        # Weekdays should have schedule
        for day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
            active = schedule.days[day].get_active_slots()
            assert active[0].end_minutes == 360

        # Weekend should have default (all 1440)
        for day in ["SATURDAY", "SUNDAY"]:
            active = schedule.days[day].get_active_slots()
            assert active[0].end_minutes == 1440


class TestCreateConstantSchedule:
    """Tests for create_constant_schedule function."""

    def test_creates_single_slot_schedule(self) -> None:
        schedule = create_constant_schedule(
            profile=1,
            temperature=21.0,
        )

        monday = schedule.days["MONDAY"]
        active = monday.get_active_slots()

        # Should have 1 active slot covering entire day
        assert len(active) == 1
        assert active[0].end_minutes == 1440
        assert active[0].temperature == 21.0

    def test_applies_to_specific_days(self) -> None:
        schedule = create_constant_schedule(
            profile=2,
            temperature=22.0,
            days=["sat", "sun"],
        )

        # Weekend should have constant temp
        for day in ["SATURDAY", "SUNDAY"]:
            active = schedule.days[day].get_active_slots()
            assert active[0].temperature == 22.0

        # Weekdays should have default
        for day in ["MONDAY", "TUESDAY"]:
            active = schedule.days[day].get_active_slots()
            # Default is also 1440 but at the default temp
            assert active[0].end_minutes == 1440
