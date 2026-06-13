import json
import os
import time
from typing import Any, Callable, Dict, Optional
from dataclasses import replace
from .core import TestBlock


class PostToolHarness:
    """
    Harness for verifying state changes after a tool call.
    Zero-Fat implementation of the Action-Verification loop.
    """

    @staticmethod
    def execute(
        trace_id: str,
        action_name: str,
        action_fn: Callable[..., Any],
        action_args: Dict[str, Any],
        expected_state: Dict[str, Any],
        verifier_fn: Callable[[Any, Dict[str, Any]], Dict[str, Any]],
        pre_state_fn: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> TestBlock:
        """
        Executes an action and immediately verifies its result.
        """
        # 1. Capture Pre-state
        pre_state = pre_state_fn() if pre_state_fn else {}

        # 2. Execute Action (Crash-Driven: No try-catch here)
        start_time = time.time()
        action_result = action_fn(**action_args)
        elapsed = time.time() - start_time

        # 3. Capture and Verify Post-state
        actual_state = verifier_fn(action_result, action_args)

        # 4. Calculate Diff
        diff = {}
        for k, v in expected_state.items():
            if actual_state.get(k) != v:
                diff[k] = {"expected": v, "actual": actual_state.get(k)}

        result_status = "SUCCESS" if not diff else "FAILURE"

        block = TestBlock(
            trace_id=trace_id,
            input=action_args,
            pre_state=pre_state,
            action=action_name,
            expected_state=expected_state,
            actual_state={**actual_state, "elapsed_ms": int(elapsed * 1000)},
            diff=diff,
            result=result_status,
        )

        # Evidence-Based: Log the block
        os.makedirs(".cache/harness", exist_ok=True)
        log_path = f".cache/harness/{trace_id}_{action_name}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            # Helper to handle non-serializable objects in blocks
            def _serial(obj):
                if hasattr(obj, "__dict__"):
                    return obj.__dict__
                return str(obj)

            json.dump(block.__dict__, f, ensure_ascii=False, indent=2, default=_serial)

        return block


class CICDHarness:
    """
    Harness for orchestrating agent verification in CI/CD environments.
    """

    @staticmethod
    def run_suite(suite_name: str, blocks: list[TestBlock]):
        """
        Evaluates a suite of TestBlocks and generates a CI-friendly report.
        """
        total = len(blocks)
        passed = sum(1 for b in blocks if b.result == "SUCCESS")
        failed = total - passed

        report = {
            "suite": suite_name,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": f"{(passed / total) * 100:.2f}%" if total > 0 else "0%",
            },
            "failures": [
                {"action": b.action, "trace_id": b.trace_id, "diff": b.diff}
                for b in blocks
                if b.result != "SUCCESS"
            ],
        }

        print(f"\n--- CI/CD Report: {suite_name} ---")
        print(json.dumps(report, indent=2, ensure_ascii=False))

        if failed > 0:
            print(f"\n❌ SUITE FAILED: {failed} blocks failed verification.")
            # In real CI, we might exit 1 here, but we'll return the report for the caller to decide.
        else:
            print(f"\n✅ SUITE PASSED: All {total} blocks verified.")

        return report
