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

# System prompt that instructs the model to act as a signal classifier
SYSTEM_PROMPT = """You are the Signal Detection Agent for Cosmic Pulse, the customer
experience intelligence platform for Cosmic Mart.

Your job is to read a raw customer message and classify it into a structured signal.

Output a single JSON object with exactly these fields:
- "source": one of ["support_ticket", "social_media", "app_review", "unknown"]
  Infer from context clues (e.g. hashtags → social_media, star ratings → app_review).
- "sentiment": one of ["positive", "neutral", "negative", "urgent"]
  "urgent" means the customer is threatening to leave, demanding immediate action,
  or the tone is escalating.
- "category": one of ["service_delay", "return_friction", "price_dissatisfaction",
  "product_quality", "other"]
  Choose the single most dominant theme.
- "urgency_score": integer 1 to 5
  1 = minor inconvenience, no action needed
  2 = mild frustration, low risk
  3 = clear complaint, warrants monitoring
  4 = angry customer, action needed soon
  5 = urgent reputational risk, act immediately
- "summary": one plain-language sentence describing the core issue.
- "pattern_risk": one of ["low", "medium", "high"]
  low  = likely an isolated incident
  medium = could be a wider issue, needs monitoring
  high = likely affects many customers, escalate for pattern analysis

Return ONLY valid JSON. No preamble. No markdown. No explanation."""


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
