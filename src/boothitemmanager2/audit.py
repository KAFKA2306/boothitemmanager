from dataclasses import dataclass, field
from typing import List, Literal, Optional
from .core import TestBlock

@dataclass(frozen=True)
class AuditItem:
    description: str
    status: Literal["PASS", "FAIL"]
    message: Optional[str] = None

@dataclass(frozen=True)
class AuditChecklistResult:
    trace_id: str
    category: str
    items: List[AuditItem]
    final_status: Literal["PASS", "FAIL"]
    reject_reason: Optional[str] = None

class AuditEngine:
    """
    Mechanical Audit Engine based on DEFINE AUDIT CHECKLIST.
    Zero-Fat: Binary evaluation only.
    Crash-Driven: Any FAIL results in immediate REJECT intent.
    """
    
    @staticmethod
    def evaluate_category(trace_id: str, category: str, items: List[AuditItem]) -> AuditChecklistResult:
        # If even one item is FAIL, final_status is FAIL.
        # Mechanical: No weights, no scoring.
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
            reject_reason=reject_reason
        )

    @staticmethod
    def final_decision(results: List[AuditChecklistResult]) -> Literal["ACCEPT", "REJECT"]:
        # If even one category is FAIL, final decision is REJECT.
        for res in results:
            if res.final_status == "FAIL":
                return "REJECT"
        return "ACCEPT"
