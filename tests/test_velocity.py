from datetime import date

from sprint_planning_automator.velocity import Resource, compute_adjusted_velocity

WINDOW_START = date(2026, 8, 25)
WINDOW_END = date(2026, 9, 8)


def test_no_ooo_leaves_velocity_unchanged():
    resources = [
        Resource("t1", "Eng A"),
        Resource("t1", "Eng B"),
        Resource("t1", "Eng C"),
        Resource("t1", "Eng D"),
    ]
    result = compute_adjusted_velocity("t1", 24, resources, WINDOW_START, WINDOW_END)
    assert result.adjusted_velocity == 24
    assert result.ooo_engineers == []
    assert result.data_missing is False


def test_ooo_engineer_reduces_velocity_by_even_share():
    resources = [
        Resource("t1", "Eng A"),
        Resource("t1", "Eng B", ooo_start="2026-08-20", ooo_end="2026-09-01"),
        Resource("t1", "Eng C"),
        Resource("t1", "Eng D"),
    ]
    result = compute_adjusted_velocity("t1", 32, resources, WINDOW_START, WINDOW_END)
    assert result.adjusted_velocity == 24  # 32 * 3/4
    assert result.ooo_engineers == ["Eng B"]
    assert result.total_engineers == 4


def test_uneven_division_rounds_down():
    resources = [
        Resource("t1", "Eng A"),
        Resource("t1", "Eng B", ooo_start="2026-08-27", ooo_end="2026-09-05"),
        Resource("t1", "Eng C"),
        Resource("t1", "Eng D"),
    ]
    result = compute_adjusted_velocity("t1", 18, resources, WINDOW_START, WINDOW_END)
    assert result.adjusted_velocity == 13  # floor(18 * 3/4) = floor(13.5)


def test_multiple_ooo_engineers_stack():
    resources = [
        Resource("t1", "Eng A", ooo_start="2026-08-26", ooo_end="2026-08-30"),
        Resource("t1", "Eng B", ooo_start="2026-09-01", ooo_end="2026-09-03"),
        Resource("t1", "Eng C"),
        Resource("t1", "Eng D"),
    ]
    result = compute_adjusted_velocity("t1", 32, resources, WINDOW_START, WINDOW_END)
    assert result.adjusted_velocity == 16  # 32 * 2/4
    assert set(result.ooo_engineers) == {"Eng A", "Eng B"}


def test_ooo_before_window_does_not_count():
    resources = [
        Resource("t1", "Eng A", ooo_start="2026-07-01", ooo_end="2026-07-10"),
        Resource("t1", "Eng B"),
    ]
    result = compute_adjusted_velocity("t1", 20, resources, WINDOW_START, WINDOW_END)
    assert result.adjusted_velocity == 20
    assert result.ooo_engineers == []


def test_ooo_partially_overlapping_window_counts():
    resources = [
        Resource("t1", "Eng A", ooo_start="2026-09-05", ooo_end="2026-09-20"),
        Resource("t1", "Eng B"),
    ]
    result = compute_adjusted_velocity("t1", 20, resources, WINDOW_START, WINDOW_END)
    assert result.adjusted_velocity == 10
    assert result.ooo_engineers == ["Eng A"]


def test_missing_resource_data_falls_back_to_baseline():
    result = compute_adjusted_velocity("t1", 32, [], WINDOW_START, WINDOW_END)
    assert result.adjusted_velocity == 32
    assert result.data_missing is True
    assert result.total_engineers == 0


def test_resources_for_other_teams_are_ignored():
    resources = [
        Resource("t2", "Eng X", ooo_start="2026-08-26", ooo_end="2026-08-30"),
    ]
    result = compute_adjusted_velocity("t1", 10, resources, WINDOW_START, WINDOW_END)
    assert result.data_missing is True  # no resources match team t1


def test_incomplete_ooo_dates_treated_as_not_ooo():
    resources = [
        Resource("t1", "Eng A", ooo_start="2026-08-26", ooo_end=None),
        Resource("t1", "Eng B", ooo_start=None, ooo_end="2026-08-30"),
        Resource("t1", "Eng C"),
    ]
    result = compute_adjusted_velocity("t1", 30, resources, WINDOW_START, WINDOW_END)
    assert result.adjusted_velocity == 30
    assert result.ooo_engineers == []
