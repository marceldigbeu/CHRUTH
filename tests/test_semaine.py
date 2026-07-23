from datetime import date

from ao_semaine import iso_week_bounds, iso_week_label


def test_bounds_midweek():
    monday, sunday = iso_week_bounds(date(2026, 6, 10))  # mercredi
    assert monday == date(2026, 6, 8)
    assert sunday == date(2026, 6, 14)


def test_bounds_on_monday():
    monday, sunday = iso_week_bounds(date(2026, 6, 8))
    assert monday == date(2026, 6, 8)
    assert sunday == date(2026, 6, 14)


def test_bounds_on_sunday():
    monday, sunday = iso_week_bounds(date(2026, 6, 14))
    assert monday == date(2026, 6, 8)
    assert sunday == date(2026, 6, 14)


def test_label():
    assert iso_week_label(date(2026, 6, 10)) == "2026-W24"
