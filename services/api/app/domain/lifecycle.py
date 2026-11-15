"""Lifecycle classification rules shared by promotion, the API and tests."""
from dataclasses import dataclass

LIFECYCLE_STATUSES = (
    "operational", "still_travelling", "mission_completed_hardware_left_behind",
    "decommissioned_or_dormant", "lost_contact_or_failed", "crashed_or_impacted", "unknown_or_unverified",
)
VERIFICATION_STATUSES = ("unverified", "verified", "rejected", "conflicting_evidence")

# Statuses for which a documented "why it was left behind / retired / lost / impacted" makes sense.
REASON_ALLOWED = {
    "mission_completed_hardware_left_behind", "decommissioned_or_dormant",
    "lost_contact_or_failed", "crashed_or_impacted",
}
ACTIVE = {"operational", "still_travelling"}


class LifecycleError(ValueError):
    pass


@dataclass
class LifecycleInput:
    status: str
    left_behind_reason: str | None = None
    has_surface_location: bool = False
    has_supporting_source: bool = False
    verification_status: str = "unverified"
    mission_status: str | None = None


def validate_lifecycle(x: LifecycleInput) -> None:
    """Raise LifecycleError describing the first inconsistency."""
    if x.status not in LIFECYCLE_STATUSES:
        raise LifecycleError(f"Unknown lifecycle status '{x.status}'.")
    if x.verification_status not in VERIFICATION_STATUSES:
        raise LifecycleError(f"Unknown verification status '{x.verification_status}'.")
    if x.status in ACTIVE and x.left_behind_reason:
        raise LifecycleError("An operational or still-travelling artifact cannot have a left-behind/retired reason.")
    if x.left_behind_reason and x.status not in REASON_ALLOWED:
        raise LifecycleError("A reason may only be recorded for left-behind, dormant, lost or impacted artifacts.")
    if x.left_behind_reason and not x.has_supporting_source:
        raise LifecycleError("A documented reason requires at least one supporting source; reasons are never invented.")
    if x.status == "still_travelling" and x.has_surface_location:
        raise LifecycleError("A still-travelling artifact cannot have a fixed surface location.")
    if x.status != "unknown_or_unverified" and x.verification_status == "verified" and not x.has_supporting_source:
        raise LifecycleError("A verified lifecycle status needs at least one supporting source.")
    if x.mission_status in ("operational", "still_travelling") and x.status == "mission_completed_hardware_left_behind":
        raise LifecycleError("Artifact is marked left behind but its mission is still active; check both statuses.")
