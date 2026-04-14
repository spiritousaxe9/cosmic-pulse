"""
Employee Enablement Agent — Cosmic Pulse

Purpose:
    Triggered when the Resolution Agent detects a frontline gap
    (frontline_gap_detected = true). Provides just-in-time policy guidance
    to the frontline worker handling the case so they can resolve it
    correctly without escalating unnecessarily.

Receives:
    query (str): The JSON string produced by the Resolution Agent, containing
                 customer_id, action_taken, customer_message, requires_human,
                 frontline_gap_detected, and resolution_status.

Returns:
    str: A JSON string with the following fields:
        - guidance_type      : Category of guidance being provided
                               (returns_policy | pricing_override | service_recovery |
                                escalation_protocol | general_policy)
        - policy_summary     : A concise (2–3 sentence) plain-language summary
                               of the relevant policy the frontline worker needs
        - recommended_script : A ready-to-use script the worker can read or
                               adapt when speaking to or messaging the customer
        - escalation_path    : Who to contact if the worker cannot resolve
                               the case themselves (role/team name)
        - delivery_channel   : System through which the guidance is delivered
                               (crm | contact_center | store_system)
"""

import os
import asyncio
from dotenv import load_dotenv
from air import AsyncAIRefinery

# Load API key from .env at module import time
load_dotenv()

# System prompt scoped to just-in-time frontline coaching
SYSTEM_PROMPT = """You are the Employee Enablement Agent for Cosmic Pulse,
Cosmic Mart's customer experience orchestration platform.

You are triggered when the Resolution Agent detects a frontline gap —
meaning a store associate, contact centre agent, or service representative
needed policy guidance they did not have.

Your job is to deliver concise, actionable just-in-time guidance so the
frontline worker can handle the case confidently right now.

Determine the guidance_type from the resolution JSON:
- action_taken "simplify_return" or category mentions returns → "returns_policy"
- action_taken "personalised_offer" or category "price_dissatisfaction" →
  "pricing_override"
- action_taken "auto_refund" or category "service_delay" → "service_recovery"
- action_taken "human_escalation" → "escalation_protocol"
- all other cases → "general_policy"

Determine delivery_channel from resolution_status and context clues:
- If the context suggests a physical store → "store_system"
- If the context suggests a phone or chat agent → "contact_center"
- Default → "crm"

Output a single JSON object with exactly these fields:
- "guidance_type": one of ["returns_policy", "pricing_override",
  "service_recovery", "escalation_protocol", "general_policy"]
- "policy_summary": 2–3 sentences. Plain English. No jargon.
  State what the policy allows and any limits or conditions.
- "recommended_script": a short script (under 60 words) the worker can
  use verbatim or adapt. Write in second person ("You can say to the
  customer: '...'").
- "escalation_path": name the specific role or team to contact if the
  worker cannot resolve it (e.g. "Returns & Policy Team — Tier 2",
  "Support Leadership — On-call Manager").
- "delivery_channel": one of ["crm", "contact_center", "store_system"]

Return ONLY valid JSON. No preamble. No markdown. No explanation."""


async def employee_enablement_agent(query: str) -> str:
    """
    Deliver just-in-time policy guidance to a frontline worker for a case
    where the Resolution Agent detected a frontline knowledge gap.

    Args:
        query: The JSON string output from Resolution Agent.

    Returns:
        A JSON-formatted string containing guidance_type, policy_summary,
        recommended_script, escalation_path, and delivery_channel.
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
