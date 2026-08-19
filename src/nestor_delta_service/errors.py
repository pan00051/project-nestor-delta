"""Website API error types for the Delta adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

SCHEMA_VERSION = "delta.report.v1"


@dataclass(frozen=True)
class ServiceError(Exception):
    """Structured API error that maps to a stable HTTP status."""

    http_status: int
    outcome: str
    code: str
    message: str
    field: str | None = None
    detail: Mapping[str, Any] | None = None
    report_fields: Mapping[str, Any] | None = None

    def to_report(self) -> dict[str, Any]:
        report = {
            "schema_version": SCHEMA_VERSION,
            "outcome": self.outcome,
            "error": {
                "code": self.code,
                "message": self.message,
                "field": self.field,
                "detail": self.detail,
            },
        }
        if self.report_fields:
            report.update(self.report_fields)
        return report


def validation_error(
    code: str,
    message: str,
    *,
    field: str | None = None,
    detail: Mapping[str, Any] | None = None,
    report_fields: Mapping[str, Any] | None = None,
) -> ServiceError:
    return ServiceError(422, "validation_error", code, message, field, detail, report_fields)


def not_found(
    code: str,
    message: str,
    *,
    field: str | None = None,
    detail: Mapping[str, Any] | None = None,
) -> ServiceError:
    return ServiceError(404, "not_found", code, message, field, detail)


def analysis_failure(
    code: str,
    message: str,
    *,
    field: str | None = None,
    detail: Mapping[str, Any] | None = None,
) -> ServiceError:
    return ServiceError(500, "analysis_failure", code, message, field, detail)
