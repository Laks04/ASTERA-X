import pytest

from app.domain.lifecycle import LIFECYCLE_STATUSES, LifecycleError, LifecycleInput as L, validate_lifecycle


def ok(**kw):
    validate_lifecycle(L(**kw))


def bad(match, **kw):
    with pytest.raises(LifecycleError, match=match):
        validate_lifecycle(L(**kw))


def test_all_seven_statuses_exist():
    assert set(LIFECYCLE_STATUSES) == {"operational", "still_travelling", "mission_completed_hardware_left_behind",
                                       "decommissioned_or_dormant", "lost_contact_or_failed", "crashed_or_impacted", "unknown_or_unverified"}


def test_voyager_style_record_is_valid_as_still_travelling_without_reason():
    ok(status="still_travelling", has_supporting_source=True, verification_status="verified")


def test_active_artifacts_cannot_have_left_behind_reasons():
    bad("cannot have", status="still_travelling", left_behind_reason="abandoned", has_supporting_source=True)
    bad("cannot have", status="operational", left_behind_reason="x", has_supporting_source=True)


def test_still_travelling_cannot_sit_at_a_surface_location():
    bad("surface location", status="still_travelling", has_surface_location=True)


def test_reasons_require_a_source_and_a_compatible_status():
    bad("supporting source", status="mission_completed_hardware_left_behind", left_behind_reason="mission ended")
    bad("only be recorded", status="unknown_or_unverified", left_behind_reason="mission ended", has_supporting_source=True)
    ok(status="mission_completed_hardware_left_behind", left_behind_reason="documented in source", has_supporting_source=True)


def test_verified_status_needs_a_source_and_unknown_is_exempt():
    bad("needs at least one", status="crashed_or_impacted", verification_status="verified")
    ok(status="unknown_or_unverified", verification_status="verified")


def test_artifact_and_mission_status_must_agree():
    bad("mission is still active", status="mission_completed_hardware_left_behind", mission_status="operational")


def test_unknown_values_rejected():
    bad("Unknown lifecycle", status="abandoned")
    bad("Unknown verification", status="operational", verification_status="maybe")
