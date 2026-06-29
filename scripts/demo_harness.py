from boothitemmanager2.agent_harness import CICDHarness, PostToolHarness


def run_demo_action(value: int) -> dict[str, int]:
    return {"result": value + 1}


def verify_demo(result: dict[str, int], args: dict[str, int]) -> dict[str, int]:
    return {"result": result["result"], "input": args["value"]}


block = PostToolHarness.execute(
    trace_id="ci_demo",
    action_name="increment_demo",
    action_fn=run_demo_action,
    action_args={"value": 1},
    expected_state={"result": 2, "input": 1},
    verifier_fn=verify_demo,
)

report = CICDHarness.run_suite("Agent Harness Smoke Suite", [block])
if report["summary"]["failed"] > 0:
    raise SystemExit(1)
