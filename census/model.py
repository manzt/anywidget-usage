"""Domain types for committed census snapshots."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

import msgspec


class ImplementationSignal(StrEnum):
    ANYWIDGET = "anywidget"
    TRADITIONAL = "traditional_custom_widget"


class ReviewStatus(StrEnum):
    SOURCE_SUPPORTED = "source_supported_candidate"
    ASSISTANT_REVIEWED = "accepted_after_assistant_review"


class PackageRole(StrEnum):
    CANDIDATE = "custom_widget_candidate"
    REVIEWED_PACKAGE = "custom_widget_package"


class MigrationReview(StrEnum):
    NOT_ESTABLISHED = "not_established"
    REVIEW_CONTINUITY = "review_component_continuity"
    COMPONENT_TRANSITION = "component_transition_supported"


class RepositoryImplementation(StrEnum):
    ANYWIDGET = "anywidget"
    WITHOUT_ANYWIDGET = "without anywidget"


def _date(value: str) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


class WidgetPackage(msgspec.Struct, frozen=True, forbid_unknown_fields=True):
    package: str
    summary: str | None
    pypi_url: str
    repositories: tuple[str, ...]
    known_in_legacy: bool
    review_status: ReviewStatus
    role: PackageRole
    current_implementation_signals: tuple[ImplementationSignal, ...]
    historical_implementation_signals: tuple[ImplementationSignal, ...]
    first_package_release: str
    first_widget_observed_by: str
    first_widget_evidence_version: str
    first_anywidget_observed_by: str
    first_anywidget_evidence_version: str
    first_anywidget_evidence_is_prerelease: bool | None
    first_stable_anywidget_observed_by: str
    first_stable_anywidget_evidence_version: str
    first_anywidget_dependency_observed: str
    earliest_extant_release_has_widget_evidence: bool
    traditional_before_anywidget_observed: bool
    migration_review: MigrationReview
    first_widget_artifact_url: str
    first_anywidget_artifact_url: str
    review_note: str

    @property
    def widget_observed_by(self) -> date | None:
        return _date(self.first_widget_observed_by)


class WidgetRepository(msgspec.Struct, frozen=True, forbid_unknown_fields=True):
    repo: str
    url: str | None
    description: str | None
    stars: int
    created: date
    last_push: date | None
    implementation: RepositoryImplementation
    name: str
    hidive: bool
    widget_created: date | None
    kind: str | None
    in_package_census: bool
    packages: tuple[str, ...]
