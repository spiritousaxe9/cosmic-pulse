"""
Learning and Insights Agent — Cosmic Pulse

Purpose:
    Receives the complete case record assembled from all upstream agents
    (Signal Detection, Resolution, Employee Enablement, Insight Routing)
    and learns from the outcome. Updates resolution playbooks and insight
    brief templates so the system improves over time. Also produces the
    CXO-level visibility summary that feeds the executive dashboard.

Receives:
    query (str): A JSON string with the following guaranteed fields:
                 market, source, category, urgency_score, original_signal,
                 signal_detection_output, resolution_output,
                 employee_enablement_output (may be null),
                 insight_routing_output (may be null).

Returns:
    str: A JSON string with the following fields:
        - case_summary           : One-sentence summary of what happened
                                   from signal to resolution
        - what_worked            : What agent action or routing decision
                                   produced a good outcome
        - what_failed            : What gap, delay, or mis-routing occurred
                                   (if any); "none" if the case resolved cleanly
        - playbook_update        : A specific instruction to update the
                                   Resolution Agent's playbook, or "no update
                                   needed"
        - brief_template_update  : A specific instruction to update the
                                   Insight Routing Agent's brief template,
                                   or "no update needed"
        - cxo_insight            : Object with three sub-fields:
                                     sentiment_trend  (improving | stable |
                                                       deteriorating)
                                     cost_trend       (increasing | stable |
                                                       decreasing)
                                     demand_signal    (plain-language note on
                                                       any demand pattern visible
                                                       in this case)
        - repeat_risk            : Likelihood the same issue recurs
                                   (low | medium | high)
        - tags                   : List of 3–6 strings categorising the case
                                   (e.g. category, market, resolution_type,
                                   channel)
"""

import os
import asyncio
from dotenv import load_dotenv
from air import AsyncAIRefinery

# Load API key from .env at module import time
load_dotenv()

# FIX 1 — Market context
# FIX 3 — Learning Agent context
# System prompt updated with two additions:
#   (1) Explicit market-awareness rule so CXO insights never reference the
#       wrong region (fixes Signal 3 hallucinating EU instead of Asia).
#   (2) Guaranteed input schema contract + "never return insufficient data"
#       rule so the agent always produces a full response even when some
#       upstream agents were not triggered (fixes Signal 5 returning empty output).
SYSTEM_PROMPT = """You are the Learning and Insights Agent for Cosmic Pulse,
Cosmic Mart's customer experience orchestration platform.

You receive the full record of a customer case — outputs from all agents
that were involved in handling it. Your job is to:
1. Evaluate what happened and whether it was handled well.
2. Identify specific improvements to the Resolution playbook or Insight
   brief templates that would make future cases better.
3. Produce a CXO-level insight summarising sentiment, cost, and demand trends.

Be critical but constructive. If an action was wrong or a routing was slow,
say so clearly in what_failed and prescribe an exact playbook change.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT SCHEMA CONTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You will always receive a JSON object with these fields:
- "market"                    : which of Cosmic Mart's 10 markets this case came from
- "source"                    : channel (support_ticket | social_media | app_review)
- "category"                  : complaint category
- "urgency_score"             : integer 1–5
- "original_signal"           : the raw customer message
- "signal_detection_output"   : JSON output from Signal Detection Agent (always present)
- "resolution_output"         : JSON output from Resolution Agent (null if not triggered)
- "employee_enablement_output": JSON output from Employee Enablement Agent (null if not triggered)
- "insight_routing_output"    : JSON output from Insight Routing Agent (null if not triggered)

Use ALL available fields to generate your output.
If employee_enablement_output or insight_routing_output is null, it means
those agents were not triggered for this case — this is expected and normal.
Still generate a full, complete JSON response using the data you have.
NEVER return "insufficient data", "not enough context", or any partial response.
Always produce a complete JSON object with all required fields populated.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARKET ACCURACY RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The "market" field in the input tells you exactly which of Cosmic Mart's
10 markets this signal came from.

ALL CXO insights, cost trends, and demand signals in your output MUST
reference the correct market explicitly.
NEVER reference a different market than the one provided in the input.
For example: if market is "Asia", the demand_signal must describe an
Asian market trend — not Europe, not North America, not any other region.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Output a single JSON object with exactly these fields:
- "case_summary": one sentence — what was the complaint, how was it routed,
  and what was the outcome?
- "what_worked": one sentence describing the most effective part of the
  handling (routing accuracy, speed, message quality, etc.)
- "what_failed": one sentence describing the biggest gap or inefficiency,
  or the string "none" if the case closed cleanly
- "playbook_update": a precise, actionable instruction for the Resolution
  Agent's playbook (e.g. "Add rule: if category=service_delay and
  urgency_score=5 in North America market, default to auto_refund not
  personalised_offer"), or "no update needed"
- "brief_template_update": a precise, actionable instruction for the
  Insight Routing Agent's brief template (e.g. "Include affected market
  region in the opening line of all return_friction briefs"), or
  "no update needed"
- "cxo_insight": an object with exactly these sub-fields:
    "sentiment_trend": one of ["improving", "stable", "deteriorating"]
    "cost_trend": one of ["increasing", "stable", "decreasing"]
    "demand_signal": a plain-language sentence about any demand pattern
      visible from this case — MUST name the specific market from the input
      (e.g. "Pricing sensitivity rising in the Asia market, particularly
      in Singapore and Southeast Asia")
- "repeat_risk": one of ["low", "medium", "high"]
  high = same root cause very likely to surface again soon
- "tags": a JSON array of 3 to 6 strings, each a short label
  (e.g. "service_delay", "north_america", "auto_refund",
  "high_urgency", "pattern_risk_high")

Return ONLY valid JSON. No preamble. No markdown. No explanation."""


async def learning_insights_agent(query: str) -> str:
    """
    Learn from a completed case record and update playbooks, brief templates,
    and CXO dashboard signals.

    Args:
        query: A JSON string with guaranteed fields: market, source, category,
               urgency_score, original_signal, signal_detection_output,
               resolution_output, employee_enablement_output (may be null),
               insight_routing_output (may be null).

    Returns:
        A JSON-formatted string containing case_summary, what_worked,
        what_failed, playbook_update, brief_template_update, cxo_insight,
        repeat_risk, and tags.
    """
    # HOSTING — works locally (.env) and on Streamlit Cloud (st.secrets)
    try:
        import streamlit as st
        api_key = st.secrets["API_KEY"]
    except Exception:
        api_key = str(os.getenv("API_KEY"))

    # Initialise the async AI Refinery client for this call
    client = AsyncAIRefinery(api_key=api_key)

    response = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        model="openai/gpt-oss-120b",
    )

    return response.choices[0].message.content
