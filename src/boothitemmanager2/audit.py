from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AuditItem:
    description: str
    status: Literal["PASS", "FAIL"]
    message: str | None = None


@dataclass(frozen=True)
class AuditChecklistResult:
    trace_id: str
    category: str
    items: list[AuditItem]
    final_status: Literal["PASS", "FAIL"]
    reject_reason: str | None = None


class AuditEngine:
    @staticmethod
    def evaluate_category(
        trace_id: str, category: str, items: list[AuditItem]
    ) -> AuditChecklistResult:
        failed_items = [item for item in items if item.status == "FAIL"]
        final_status: Literal["PASS", "FAIL"] = "FAIL" if failed_items else "PASS"
        reject_reason = None
        if final_status == "FAIL":
            reject_reason = f"Audit failed in category '{category}': " + "; ".join(
                [f"{i.description} ({i.message})" for i in failed_items]
            )
        return AuditChecklistResult(
            trace_id=trace_id,
            category=category,
            items=items,
            final_status=final_status,
            reject_reason=reject_reason,
        )

    @staticmethod
    def final_decision(results: list[AuditChecklistResult]) -> Literal["ACCEPT", "REJECT"]:
        for res in results:
            if res.final_status == "FAIL":
                return "REJECT"
        return "ACCEPT"
