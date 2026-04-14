"""
Cosmic Pulse — Main Orchestration Entry Point

System overview:
    Cosmic Pulse is a multi-agent AI system that orchestrates customer
    experience signals for Cosmic Mart, a global retail brand with 144 million
    customers across 10 markets.

    The system processes raw customer feedback through a pipeline of five
    specialised agents:

    1. Signal Detection Agent  — always runs first on every signal
    2. Resolution Agent        — triggered when urgency_score >= 4
    3. Employee Enablement Agent — triggered when Resolution output contains
                                   frontline_gap_detected: true
    4. Insight Routing Agent   — triggered when pattern_risk is medium or high
    5. Learning and Insights Agent — always runs last; receives all outputs

Routing is handled explicitly in run_signal() rather than delegated
entirely to the DistillerClient orchestrator. This prevents three
categories of orchestrator mis-routing observed in live tests:
    - Bug 1: Learning Agent using wrong market in CXO insight
    - Bug 2: Employee Enablement Agent not triggering on Signal 4
    - Bug 3: Learning Agent receiving insufficient context on Signal 5

Signals are generated fresh on every run via data_generator.py.

Usage:
    Set API_KEY in .env, then run:
        python main.py
"""

import os
import asyncio
import json
from dotenv import load_dotenv
from air import DistillerClient

# Import all five agent functions from py_scripts
from py_scripts.signal_detection import signal_detection_agent
from py_scripts.resolution import resolution_agent
from py_scripts.employee_enablement import employee_enablement_agent
from py_scripts.insight_routing import insight_routing_agent
from py_scripts.learning_insights import learning_insights_agent

# Import the live signal generator and preview printer
from data_generator import generate_demo_set, print_signal

# Load environment variables from .env
load_dotenv()


def print_agent_response(agent_name: str, response: str) -> None:
    """Pretty-print a single agent's JSON response with its name header."""
    print(f"\n--- {agent_name} ---")
    try:
        # Attempt to pretty-print valid JSON for readability
        parsed = json.loads(response)
        print(json.dumps(parsed, indent=2))
    except json.JSONDecodeError:
        # Fall back to raw string if the model returned non-JSON
        print(response)


async def run_signal(signal: dict) -> None:
    """
    Run a single generated signal through the explicit Cosmic Pulse pipeline.

    All routing decisions are made in Python here rather than delegated
    to the DistillerClient orchestrator. This guarantees:
        - Employee Enablement is always triggered when frontline_gap_detected
          is true in the Resolution output (Fix 2).
        - The Learning Agent always receives the correct market field and the
          full output from every agent that ran in this case (Fixes 1 & 3).
        - pattern_risk medium OR high both trigger Insight Routing.

    Pipeline order:
        1. Signal Detection  (always)
        2. Resolution        (if urgency_score >= 4)
        3. Employee Enable.  (if Resolution returned frontline_gap_detected=true)
        4. Insight Routing   (if pattern_risk is "medium" or "high")
        5. Learning          (always, with all outputs + market metadata)

    Args:
        signal: Signal dict from data_generator with keys:
                label, market, source, category, urgency_score, query.
    """
    # Print the generated signal preview before running the pipeline
    print_signal(signal)
    print("\nRouting signal into Cosmic Pulse pipeline...\n")

    # ── Step 1: Signal Detection Agent ───────────────────────────────────
    # Always runs first on every signal — classifies the raw message
    signal_detection_result = await signal_detection_agent(signal["query"])
    print_agent_response("Signal Detection Agent", signal_detection_result)

    # Parse the detection output to drive routing decisions.
    # Fall back to the generator's metadata if the JSON is malformed.
    try:
        detection_json = json.loads(signal_detection_result)
        detected_urgency = int(detection_json.get("urgency_score", signal["urgency_score"]))
        pattern_risk = str(detection_json.get("pattern_risk", "low")).lower()
    except (json.JSONDecodeError, AttributeError, ValueError):
        detected_urgency = signal["urgency_score"]
        pattern_risk = "low"

    # ── Step 2: Resolution Agent ──────────────────────────────────────────
    # Triggered when urgency_score is 4 or 5
    resolution_result = None

    if detected_urgency >= 4:
        resolution_result = await resolution_agent(signal_detection_result)
        print_agent_response("Resolution Agent", resolution_result)

    # ── Step 3: Employee Enablement Agent ────────────────────────────────
    # FIX 2 — EEA trigger
    # Do NOT rely on the orchestrator to route this. Explicitly parse the
    # Resolution output and call EEA whenever frontline_gap_detected is true.
    employee_enablement_result = None

    if resolution_result is not None:
        try:
            resolution_json = json.loads(resolution_result)
            frontline_gap = bool(resolution_json.get("frontline_gap_detected", False))
        except (json.JSONDecodeError, AttributeError):
            frontline_gap = False

        if frontline_gap:
            # Pass the full Resolution JSON so EEA has action context
            employee_enablement_result = await employee_enablement_agent(resolution_result)
            print_agent_response("Employee Enablement Agent", employee_enablement_result)

    # ── Step 4: Insight Routing Agent ────────────────────────────────────
    # Triggered when pattern_risk is "medium" OR "high" (not just high).
    # Both can run in the same pipeline alongside Resolution Agent.
    insight_routing_result = None

    if pattern_risk in ("medium", "high"):
        # Pass the Signal Detection output — Insight Routing synthesises patterns
        insight_routing_result = await insight_routing_agent(signal_detection_result)
        print_agent_response("Insight Routing Agent", insight_routing_result)

    # ── Step 5: Learning and Insights Agent ──────────────────────────────
    # FIX 1 — Market context
    # FIX 3 — Learning Agent context
    # Always runs last. Receives a comprehensive JSON object that explicitly
    # includes:
    #   - market: prevents the agent from hallucinating a different region
    #     in its CXO insight (Fix 1 — e.g. Signal 3 was Asia, not EU)
    #   - source, category, urgency_score, original_signal: full case metadata
    #   - all four agent outputs, with null for agents that did not run
    #     (Fix 3 — prevents "insufficient data" response on low-urgency cases)
    learning_input = json.dumps({
        "market": signal["market"],
        "source": signal["source"],
        "category": signal["category"],
        "urgency_score": signal["urgency_score"],
        "original_signal": signal["query"],
        "signal_detection_output": signal_detection_result,
        "resolution_output": resolution_result,
        "employee_enablement_output": employee_enablement_result,
        "insight_routing_output": insight_routing_result,
    })

    learning_result = await learning_insights_agent(learning_input)
    print_agent_response("Learning and Insights Agent", learning_result)


async def main() -> None:
    """
    Entry point for the Cosmic Pulse demonstration run.

    Registers the project with the DistillerClient (for SDK compliance and
    team.yaml agent registration), then generates a fresh set of 5 curated
    signals and runs each one through the explicit pipeline in run_signal().

    Signal coverage guaranteed by generate_demo_set():
        - At least one urgency 4 or 5   → triggers Resolution Agent
        - At least one high pattern_risk → triggers Insight Routing Agent
        - At least one frontline gap     → triggers Employee Enablement Agent
        - At least 3 different markets
        - All 3 source types represented
    """
    api_key = str(os.getenv("API_KEY"))

    # Register the project with the DistillerClient so the SDK is aware of
    # the team configuration even though routing is handled explicitly below
    distiller_client = DistillerClient(api_key=api_key)
    distiller_client.create_project(
        config_path="core/team.yaml",
        project="cosmic-pulse",
    )

    # Generate fresh signals for this run — every execution produces new data
    print("\n" + "=" * 60)
    print("  Cosmic Pulse — Starting up")
    print("=" * 60)
    print("\nGenerating live signals via data_generator...\n")

    test_signals = await generate_demo_set()

    print(f"✓ {len(test_signals)} signals generated. Starting pipeline.\n")

    # Process each signal sequentially so console output stays readable
    for i, signal in enumerate(test_signals, start=1):
        print(f"\n{'=' * 60}")
        print(f"  PROCESSING SIGNAL {i} OF {len(test_signals)}")
        print(f"{'=' * 60}")
        await run_signal(signal)

    print("\n" + "=" * 60)
    print("  Cosmic Pulse — All signals processed.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
