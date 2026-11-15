"""Parser regression tests (pure functions, no database)."""
from app.ingestion import moon_catalogue as mc
from tests.conftest import TEXT

recs = mc.parse_catalogue(TEXT)
get = lambda n, sec=None: next(r for r in recs if r.object_name == n and (sec is None or r.section == sec))


def test_numeric_coordinates_page_and_raw_preserved():
    r = get("Surveyor 1")
    assert (r.lat, r.lon, r.page, r.status) == (-2.474, -43.339, 1, "coordinates_stated")
    assert r.raw_line == "Surveyor 1 -2.474 ˚ N, -43.339 ˚ E" and r.flags == []


def test_ranger9_impossible_latitude_preserved_and_flagged():
    r = get("Ranger 9")
    assert r.lat == 112.828 and r.lon == -2.387
    assert r.status == "invalid_coordinate_needs_review" and "invalid_coordinate_needs_review" in r.flags
    assert "stored as printed" in " ".join(r.notes)


def test_unknown_impact_and_missing_coordinates():
    s4, lo4 = get("Surveyor 4"), get("Lunar Orbiter 4")
    assert s4.lat is None and s4.status == "unknown_in_source" and "missing_coordinates" in s4.flags
    assert lo4.lat is None and lo4.status == "impact_noted" and "missing_coordinates" in lo4.flags


def test_luna13_coordinates_are_layout_inferred_and_need_review():
    r = get("Luna 13")
    assert (r.lat, r.lon) == (18.87, -62.05)
    assert "layout_inferred_association" in r.flags and r.confidence == 0.5
    assert r.raw_line == "Luna 13 / 18.87 ˚ N, -62.05 ˚ E"
    assert "Luna 10" in " ".join(r.notes)


def test_luna10_has_no_location_and_luna20_inferred_with_luna19_noted():
    l10 = get("Luna 10")
    assert l10.lat is None and l10.status == "none_listed" and "missing_coordinates" in l10.flags
    l20 = get("Luna 20 descent stage")
    assert (l20.lat, l20.lon) == (3.787, 56.625) and "layout_inferred_association" in l20.flags
    assert "Luna 19" in " ".join(l20.notes)


def test_region_only_entries():
    r = get("Chandrayaan-1 Lunar Orbiter")
    assert r.status == "region_only" and "region_only" in r.flags and r.lat is None
    assert get("Apollo 16 Subsatellite (PFS-2)").status == "region_only"


def test_equipment_categories_from_printed_names_only():
    assert get("LM Descent Stage (plaque attached)", "Apollo 12").category == "descent_stage"
    assert get("Central Station", "Apollo 14").category == "central_station"
    assert get("Laser Range Reflector", "Apollo 14").category == "retroreflector"
    assert get("S-IVB", "Apollo 13").category == "launch_vehicle_stage"
    assert get("Lunokhod 1").category == "rover"
    assert get("Apollo 11 landing site").category == "landing_site"
    assert get("Surveyor 1").category is None  # the catalogue line does not say what kind of craft it is


def test_stray_minus_space_is_read_and_noted_with_raw_kept():
    r = get("SMART-1 (controlled crash)")
    assert r.lon == -46.2 and "stray space" in " ".join(r.notes) and "- 46.2" in r.raw_line


def test_duplicate_entries_are_both_kept_and_flagged():
    text = "=== PAGE 1 ===\nU.S. Material (Non-Apollo)\nSurveyor 1 -2.474 ˚ N, -43.339 ˚ E\nSurveyor 1 -2.474 ˚ N, -43.339 ˚ E\n"
    a, b = mc.parse_catalogue(text)
    assert (a.occurrence, b.occurrence) == (1, 2) and "duplicate_in_source" in b.flags and "duplicate_in_source" not in a.flags


def test_conflicting_coordinates_for_same_object_flag_all_occurrences():
    text = "=== PAGE 1 ===\nU.S. Material (Non-Apollo)\nSurveyor 1 -2.474 ˚ N, -43.339 ˚ E\n=== PAGE 2 ===\nSurveyor 1 -2.5 ˚ N, -43.0 ˚ E\n"
    a, b = mc.parse_catalogue(text)
    assert "conflicting_entry" in a.flags and "conflicting_entry" in b.flags and (a.page, b.page) == (1, 2)


def test_entry_before_any_section_is_flagged_uncertain_attribution():
    (r,) = mc.parse_catalogue("=== PAGE 1 ===\nSurveyor 1 -2.474 ˚ N, -43.339 ˚ E\n")
    assert r.section == "Unsectioned" and "uncertain_mission_attribution" in r.flags
