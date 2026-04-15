"""
Signal Detection Agent — Cosmic Pulse

Purpose:
    Reads raw customer messages sourced from support tickets, social media,
    app reviews, or store feedback and converts them into a structured JSON
    signal for downstream orchestration.

Receives:
    query (str): A raw, unstructured customer message or feedback snippet.

Returns:
    str: A JSON string with the following fields:
        - source        : Where the signal originated
                          (support_ticket | social_media | app_review | unknown)
        - sentiment     : Emotional tone of the message
                          (positive | neutral | negative | urgent)
        - category      : Primary friction topic
                          (service_delay | return_friction | price_dissatisfaction |
                           product_quality | other)
        - urgency_score : Integer 1–5 (1=minor, 5=urgent reputational risk)
        - summary       : One-sentence plain-language summary of the complaint
        - pattern_risk  : Likelihood the issue affects many customers
                          (low | medium | high)
"""

import os
import asyncio
from dotenv import load_dotenv
from air import AsyncAIRefinery

# Load API key from .env at module import time
load_dotenv()

# ROOT FIX 2 — signal detection explicit scoring rules
# System prompt that instructs the model to score based on SPECIFIC LANGUAGE SIGNALS,
# not general tone or subjective interpretation.
SYSTEM_PROMPT = """You are the Signal Detection Agent for Cosmic Pulse,
Cosmic Mart's customer experience AI system.

Your job is to read a raw customer message and return
a structured JSON signal. You must score urgency and
pattern_risk based on SPECIFIC LANGUAGE in the text,
not general tone or your own judgment.

## Urgency scoring rules — follow exactly

Score 1 — ONLY if the text contains phrases like:
  "no rush", "whenever you get a chance", "just wanted
  to flag", "not a big deal", "minor issue"

Score 2 — ONLY if the text:
  - Shows mild disappointment with NO threats
  - Contains words like "disappointed", "frustrated",
    "I was expecting better", "I would appreciate"
  - Does NOT mention bank disputes, legal action,
    social media threats, or contacting authorities

Score 3 — ONLY if the text:
  - Shows clear frustration with firm language
  - Contains words like "unacceptable", "I need this
    resolved", "I expect a response", "not satisfied"
  - May mention leaving a review but NO threats of
    bank disputes or legal action

Score 4 — ONLY if the text:
  - Shows anger with specific demands
  - Contains words like "I demand", "disgusted",
    "completely unacceptable", "I will post about this",
    threats to tell friends or post on social media
  - Does NOT mention bank disputes or legal action

Score 5 — ONLY if the text EXPLICITLY mentions:
  - "dispute", "bank dispute", "chargeback"
  - "legal action", "lawyer", "lawsuit", "sue"
  - "consumer protection", "trading standards",
    "regulatory body", "BBB", "ombudsman", "Procon"
  - A specific deadline like "within 24 hours or I will"

If the text does not contain these specific signals,
do NOT score 5. Score based on what is written,
not what you think the customer might do.

## Pattern risk scoring rules — follow exactly

Score "low" if:
  - Customer only talks about their own experience
  - No mention of other customers, forums, or reports
  - Language like "my order", "my account", "I was"

Score "medium" if:
  - Customer mentions ONE other person or hints at
    a wider issue without confirming it
  - Language like "I saw someone else", "a friend told
    me", "I think this might be happening to others"

Score "high" ONLY if the text EXPLICITLY mentions:
  - Multiple other customers affected
  - Forums, Trustpilot, Reddit, community reports
  - Language like "hundreds of customers", "the forum
    is full of complaints", "I saw dozens of reviews",
    "many people are reporting this", "systemic issue"

Do not score "high" unless these explicit signals exist.

## Output format

Return ONLY valid JSON. No preamble. No markdown. No explanation.

{
  "source": "support_ticket | social_media | app_review | unknown",
  "sentiment": "positive | neutral | negative | urgent",
  "category": "service_delay | return_friction | price_dissatisfaction | product_quality | other",
  "urgency_score": <integer 1-5 based on rules above>,
  "summary": "<one sentence>",
  "pattern_risk": "low | medium | high based on rules above"
}"""


async def signal_detection_agent(query: str) -> str:
    """
    Classify a raw customer message into a structured Cosmic Pulse signal.

    Args:
        query: The raw customer feedback or support message text.

    Returns:
        A JSON-formatted string containing source, sentiment, category,
        urgency_score, summary, and pattern_risk.
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
