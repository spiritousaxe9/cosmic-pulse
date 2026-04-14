"""
Insight Routing Agent — Cosmic Pulse

Purpose:
    Triggered when the Signal Detection Agent returns pattern_risk = "high"
    or when the same category appears repeatedly across multiple signals.
    Synthesises the pattern into a targeted insight brief and routes it to
    the correct business team for action.

Receives:
    query (str): The JSON string produced by Signal Detection Agent (or a
                 combined summary of multiple signals), containing source,
                 sentiment, category, urgency_score, summary, and pattern_risk.

Returns:
    str: A JSON string with the following fields:
        - pattern_summary          : Plain-language description of the
                                     pattern observed across signals
        - affected_volume_estimate : Estimated number or percentage of
                                     customers likely affected
        - root_cause_hypothesis    : Most probable underlying cause
        - recommended_action       : Specific action the routed team should
                                     take to address the root cause
        - routed_to_team           : The business team receiving this brief
                                     (Pricing and Promotions |
                                      Store Operations |
                                      Merchandising and Assortment |
                                      Returns and Policy Owners |
                                      Support Leadership)
        - priority                 : Urgency of the brief (high | medium | low)
        - insight_brief            : 2–3 sentence plain-language brief ready
                                     to send to the receiving team
"""

import os
import asyncio
from dotenv import load_dotenv
from air import AsyncAIRefinery

# Load API key from .env at module import time
load_dotenv()

# Routing map encoded in the system prompt — category drives team assignment
SYSTEM_PROMPT = """You are the Insight Routing Agent for Cosmic Pulse,
Cosmic Mart's customer experience orchestration platform.

You are triggered when a customer signal has pattern_risk "high" or when
a category is repeated across multiple signals — meaning this is not an
isolated complaint but a systemic issue that a business team must address.

Your job is to synthesise the signal into a targeted insight brief and
route it to exactly the right team.

Routing rules (use the category field from the input JSON):
- "price_dissatisfaction"              → "Pricing and Promotions"
- "product_quality"                    → "Merchandising and Assortment"
- "return_friction"                    → "Returns and Policy Owners"
- "service_delay"                      → "Support Leadership"
- category contains "store" or source is "store_feedback"
                                       → "Store Operations"
- "other" or ambiguous                 → "Support Leadership"

Priority rules:
- urgency_score 5 → "high"
- urgency_score 3 or 4 → "medium"
- urgency_score 1 or 2 → "low"
- pattern_risk "high" always escalates priority one level (low → medium,
  medium → high, high stays high)

Output a single JSON object with exactly these fields:
- "pattern_summary": 1–2 sentences describing the pattern across customers
- "affected_volume_estimate": a reasoned estimate, e.g. "~2–5% of customers
  in the affected market" or "potentially 50,000+ customers"
- "root_cause_hypothesis": the single most likely root cause in one sentence
- "recommended_action": one concrete action the receiving team should take
  within 48 hours
- "routed_to_team": one of ["Pricing and Promotions", "Store Operations",
  "Merchandising and Assortment", "Returns and Policy Owners",
  "Support Leadership"]
- "priority": one of ["high", "medium", "low"]
- "insight_brief": 2–3 sentences written in plain English, suitable to paste
  directly into a Slack message or email to the team. No jargon. Include
  the pattern, the impact estimate, and the recommended action.

Return ONLY valid JSON. No preamble. No markdown. No explanation."""


async def insight_routing_agent(query: str) -> str:
    """
    Synthesise a high-risk customer signal pattern into a routed insight brief.

    Args:
        query: The JSON string output from Signal Detection Agent, representing
               a high pattern_risk signal or a repeated-category signal batch.

    Returns:
        A JSON-formatted string containing pattern_summary, affected_volume_estimate,
        root_cause_hypothesis, recommended_action, routed_to_team, priority,
        and insight_brief.
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
