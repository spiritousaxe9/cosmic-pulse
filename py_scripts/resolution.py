"""
Resolution Agent — Cosmic Pulse

Purpose:
    Receives the structured JSON output from the Signal Detection Agent and
    determines the appropriate resolution action for the customer case.
    Generates a warm, personalised customer-facing message and flags whether
    human escalation or frontline guidance is required.

Receives:
    query (str): The JSON string produced by Signal Detection Agent, containing
                 source, sentiment, category, urgency_score, summary, and
                 pattern_risk fields.

Returns:
    str: A JSON string with the following fields:
        - customer_id          : A synthetic reference ID for the case
        - action_taken         : Resolution action selected
                                 (auto_refund | simplify_return | personalised_offer |
                                  human_escalation | frontline_support)
        - customer_message     : Warm, apologetic, solution-focused message for
                                 the customer. Must never mention AI or internal
                                 systems.
        - requires_human       : bool — true if the case needs a human agent
        - frontline_gap_detected: bool — true if the signal suggests frontline
                                  staff need guidance
        - resolution_status    : One of ["resolved", "escalated", "pending_human",
                                  "guidance_issued"]
"""

import os
import asyncio
from dotenv import load_dotenv
from air import AsyncAIRefinery

# Load API key from .env at module import time
load_dotenv()

# System prompt defining resolution decision logic and output contract
SYSTEM_PROMPT = """You are the Resolution Agent for Cosmic Pulse, Cosmic Mart's
customer experience orchestration platform.

You receive a structured JSON signal from the Signal Detection Agent. Your job
is to determine the right resolution action and craft a personalised response.

Resolution action rules:
- urgency_score 5 OR sentiment "urgent" → "human_escalation"
- category "return_friction" AND urgency_score >= 3 → "simplify_return"
- category "service_delay" AND urgency_score <= 3 → "personalised_offer"
- category "price_dissatisfaction" → "personalised_offer"
- category "product_quality" AND urgency_score >= 4 → "human_escalation"
- requires_human true → "human_escalation"
- If the signal indicates frontline staff could not help the customer or the
  customer explicitly mentioned store staff or call center agents being unable
  to assist → set frontline_gap_detected to true and action_taken to
  "frontline_support"
- All other cases → "personalised_offer"

Output a single JSON object with exactly these fields:
- "customer_id": a plausible synthetic ID, e.g. "CM-NA-2024-00847"
- "action_taken": one of ["auto_refund", "simplify_return", "personalised_offer",
  "human_escalation", "frontline_support"]
- "customer_message": a warm, apologetic, solution-focused message addressed
  directly to the customer. Write in first-person plural (we/our). Never mention
  AI, bots, machine learning, or any internal system name. Keep it under 80 words.
- "requires_human": boolean — true only if human_escalation is the action
- "frontline_gap_detected": boolean — true if staff guidance is needed
- "resolution_status": one of ["resolved", "escalated", "pending_human",
  "guidance_issued"]

Tone guidelines for customer_message:
- Lead with a genuine apology
- Acknowledge the specific issue from the signal summary
- State clearly what action has been or will be taken
- End with a reassurance line

Return ONLY valid JSON. No preamble. No markdown. No explanation."""


async def resolution_agent(query: str) -> str:
    """
    Determine and execute the resolution action for a classified customer signal.

    Args:
        query: The JSON string output from Signal Detection Agent.

    Returns:
        A JSON-formatted string containing customer_id, action_taken,
        customer_message, requires_human, frontline_gap_detected, and
        resolution_status.
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
