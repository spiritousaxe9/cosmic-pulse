"""
data_generator.py — Cosmic Pulse LLM-Powered Signal Generator

Purpose:
    Generates realistic synthetic customer complaint signals on demand using
    the AI Refinery LLM. Every run produces fresh, varied, contextually
    accurate complaint messages instead of the same hardcoded strings, making
    every demo feel live and every test meaningful.

    Generated signal dicts use the exact keys that main.py expects:
        label, market, source, category, urgency_score, query

    The "query" value is a raw, unstructured customer message string —
    identical in format to the hardcoded SIGNAL_1/2/3 strings in main.py —
    and is passed directly to the Cosmic Pulse orchestrator pipeline.

Public API:
    generate_signal(market, source, category, urgency_score) -> dict
        Generate one signal with explicit parameters.

    generate_batch(n) -> list[dict]
        Generate n signals with randomised parameters and variety guarantee.

    generate_demo_set() -> list[dict]
        Generate exactly 5 curated signals that exercise every routing path.

    print_signal(signal) -> None
        Print a formatted preview of a signal for team review.

Usage:
    python data_generator.py
    → Generates and prints one demo set of 5 signals for preview.
"""

import asyncio
import os
import random
from typing import Optional
from air import AsyncAIRefinery
from dotenv import load_dotenv

# Load API key from .env at module import time
load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Allowed parameter values — these match signal_detection.py exactly
# ──────────────────────────────────────────────────────────────────────────────

MARKETS = [
    "North America",
    "Europe",
    "Asia",
    "South America",
]

SOURCES = [
    "support_ticket",
    "social_media",
    "app_review",
]

CATEGORIES = [
    "service_delay",
    "return_friction",
    "price_dissatisfaction",
    "product_quality",
    "other",
]

# ──────────────────────────────────────────────────────────────────────────────
# Tone and format guidance tables injected into the LLM system prompt
# Each entry is a plain-English instruction block for the model
# ──────────────────────────────────────────────────────────────────────────────

# Per-market: controls vocabulary, city references, currency, and emotional register
_MARKET_TONE = {
    "North America": (
        "Write in a casual, direct American tone. "
        "Reference a real US city (e.g. Chicago, Houston, Atlanta, Denver, Seattle). "
        "Use USD for any price references (e.g. '$49.99'). "
        "The customer is assertive and expects a fast, no-nonsense resolution."
    ),
    "Europe": (
        "Write in a formal, measured European tone. "
        "Reference a real UK or EU city (e.g. London, Manchester, Berlin, Paris, Amsterdam). "
        "Use GBP (£) or EUR (€) for prices. "
        "The customer may briefly reference consumer rights, EU return law, or GDPR. "
        "Tone is composed but firm — unhappy, not explosive."
    ),
    "Asia": (
        "Write in a polite but firm tone appropriate for urban Asia. "
        "Reference a real Asian city (e.g. Singapore, Tokyo, Seoul, Bangkok, Mumbai). "
        "Use USD or a local currency reference (e.g. SGD, JPY, THB, INR). "
        "The customer is respectful in phrasing but clearly disappointed and wants action."
    ),
    "South America": (
        "Write in a warm but frustrated South American tone. "
        "Reference a real South American city (e.g. São Paulo, Buenos Aires, Bogotá, Lima). "
        "Use USD or a local currency reference (e.g. BRL, ARS, COP, PEN). "
        "The customer is expressive and may compare Cosmic Mart unfavourably to local brands."
    ),
}

# Per-source: controls message format, length, and structural conventions
_SOURCE_FORMAT = {
    "support_ticket": (
        "Format this as a formal support ticket submitted through the Cosmic Mart app "
        "or website form. Use complete, grammatically correct sentences. "
        "Include an invented order number in the format CM-XX-YYYY-NNNNN "
        "(e.g. CM-US-2024-558821 for North America, CM-UK-2024-338412 for Europe). "
        "Include a rough date or timeframe. The message should be 4–8 sentences. "
        "Begin the message with exactly: 'Support ticket submitted via app:'"
    ),
    "social_media": (
        "Format this as a real tweet or Instagram comment. "
        "Keep it short: 1–3 sentences maximum. "
        "Tag @CosmicMart at least once. "
        "Use ALL CAPS on the single most frustrating word or phrase for emphasis. "
        "May include one relevant hashtag (e.g. #CosmicMart, #WorstExperience). "
        "Do NOT start with 'Support ticket'. The tone should feel spontaneous."
    ),
    "app_review": (
        "Format this as a customer review posted on the Cosmic Mart mobile app store listing. "
        "3–5 sentences. More detailed than social media, less formal than a support ticket. "
        "Reference the star rating context — begin with exactly: 'App review ({star_rating} stars):' "
        "and make the body match that rating (1–2 stars: very unhappy; 3 stars: mixed; "
        "4–5 stars would not be a complaint so treat 3 as the minimum here). "
        "May mention a specific product, market, or feature."
    ),
}

# Per-category: controls the substance of the complaint
_CATEGORY_CONTENT = {
    "service_delay": (
        "The complaint is about a late or missing order. "
        "Include: the tracking not updating for several days, "
        "the expected delivery date being missed, and at least one failed attempt "
        "to get help from customer support or a store associate. "
        "The customer's frustration is directed at both the delay and the lack of "
        "information or resolution from staff."
    ),
    "return_friction": (
        "The complaint is about difficulty making a return or getting a refund. "
        "Include one specific obstacle: the returns portal crashing, the policy being "
        "confusing or not clearly communicated, a store refusing to accept an online "
        "return, or the refund taking far too long. "
        "The customer should mention at least one failed attempt to resolve it. "
        "They feel the process is broken or unfair."
    ),
    "price_dissatisfaction": (
        "The complaint is about prices being too high, unexpected price increases, "
        "or poor value for money. "
        "Include a specific price comparison or percentage increase. "
        "The customer may reference a competitor offering the same item for less. "
        "They feel the quality does not justify the price they paid or are being asked to pay."
    ),
    "product_quality": (
        "The complaint is about a faulty, broken, or misrepresented product. "
        "Specify a product type: clothing (e.g. jacket, trainers), "
        "an electronics accessory (e.g. phone case, charger cable), "
        "or a home goods item (e.g. storage box, kitchen utensil). "
        "The item either arrived damaged, stopped working very quickly, "
        "or looked nothing like the product photos. "
        "Include a product or order reference."
    ),
    "other": (
        "The complaint is about something outside the main categories. "
        "Choose exactly one of these topics: "
        "(a) store layout being confusing or inaccessible, "
        "(b) staff behaviour being unhelpful or rude, "
        "(c) an app bug unrelated to returns, "
        "(d) a loyalty programme issue (points not credited, redemption failing). "
        "The customer must explicitly mention that frontline staff — either a store "
        "associate or a contact centre agent — were unable to explain the correct "
        "policy or process, making clear that a frontline knowledge gap exists."
    ),
}

# ROOT FIX 1 — calibrated complaint generation
# Per-urgency: exact tone and phrase guidance matched to urgency score.
# These calibrate the generated text so Signal Detection Agent scores correctly.
# The phrases mirror the explicit scoring rules in signal_detection.py exactly.
URGENCY_LANGUAGE = {
    1: (
        "The customer is barely bothered. Very calm tone. "
        "Uses words like 'just wanted to flag', 'not a big deal', "
        "'whenever you get a chance'. No demands. No threats. "
        "One short paragraph maximum. "
        "Example phrases: 'I noticed', 'might be worth looking at', "
        "'no rush but'."
    ),
    2: (
        "The customer is mildly disappointed. Measured tone. "
        "Uses words like 'unfortunately', 'a bit frustrating', "
        "'I was expecting better'. No threats. No urgency. "
        "Does NOT mention bank disputes, legal action, or "
        "posting on social media. Patient and polite. "
        "Example phrases: 'I was disappointed to find', "
        "'I hope this can be looked into', 'I would appreciate'."
    ),
    3: (
        "The customer is clearly frustrated but composed. "
        "Uses words like 'unacceptable', 'very disappointed', "
        "'I need this resolved'. May mention leaving a review "
        "but does not threaten legal action or bank disputes. "
        "Firm but not aggressive. "
        "Example phrases: 'I expect a response', "
        "'this needs to be fixed', 'I am not satisfied'."
    ),
    4: (
        "The customer is angry and demanding. "
        "Uses words like 'completely unacceptable', 'disgusted', "
        "'I demand', 'immediate action'. May threaten to post "
        "on social media or tell friends. Does NOT mention "
        "legal action or bank disputes yet. "
        "Example phrases: 'I will be posting about this', "
        "'I expect a resolution today', 'this is outrageous'."
    ),
    5: (
        "The customer is furious and making concrete threats. "
        "Uses words like 'legal action', 'bank dispute', "
        "'consumer protection bureau', 'lawyer', 'lawsuit'. "
        "Very aggressive tone. Demands specific action within "
        "a tight timeframe (24 hours or less). "
        "Example phrases: 'I will dispute this charge', "
        "'I am consulting a lawyer', 'I will sue'."
    ),
}

# ROOT FIX 1 — calibrated complaint generation
# Per-pattern-risk: controls whether customer mentions other affected customers.
# These calibrate the generated text so Signal Detection scores pattern_risk correctly.
# The phrases mirror the explicit pattern_risk scoring rules in signal_detection.py.
PATTERN_LANGUAGE = {
    "low": (
        "This is clearly an isolated incident. The customer "
        "does NOT mention other customers or a wider problem. "
        "No references to forums, social media complaints from "
        "others, Trustpilot, Reddit, or any community reports. "
        "It reads as a one-off personal experience. "
        "The customer says things like 'my order' not 'many orders'."
    ),
    "medium": (
        "The customer hints this might not be unique to them. "
        "May mention seeing one or two other complaints. "
        "Phrases like 'I saw someone else had this issue' or "
        "'a friend told me the same thing happened'. "
        "Not confirmed widespread but suggests a pattern."
    ),
    "high": (
        "The customer explicitly references a widespread problem. "
        "Mentions forums, Trustpilot, Reddit, community posts, "
        "or multiple other customers. Uses phrases like "
        "'hundreds of customers are reporting', 'I saw dozens "
        "of complaints on Trustpilot this week', 'the forum is "
        "full of this issue', 'many people are affected'. "
        "The customer knows this is systemic, not personal. "
        "This language is ESSENTIAL — the Signal Detection "
        "Agent must pick up on it to score pattern_risk high."
    ),
}


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _star_rating(urgency_score: int) -> int:
    """
    Convert an urgency score to an app store star rating.

    Higher urgency = lower star rating. Clamped to [1, 3] because a complaint
    at urgency 1 is still negative enough to merit no more than 3 stars.

    Args:
        urgency_score: Integer 1–5.

    Returns:
        Integer star rating 1–3.
    """
    # urgency 5 → 1 star, urgency 4 → 1 star, urgency 3 → 2 stars,
    # urgency 2 → 2 stars, urgency 1 → 3 stars
    mapping = {5: 1, 4: 1, 3: 2, 2: 2, 1: 3}
    return mapping.get(urgency_score, 2)


def _build_system_prompt(
    market: str,
    source: str,
    category: str,
    urgency_score: int,
    pattern_risk: str = "low",
    extra_hint: str = "",
) -> str:
    """
    Build the complete LLM system prompt for generating a customer complaint.

    ROOT FIX 1 — calibrated complaint generation.
    Embeds urgency and pattern_risk calibration signals directly in the prompt
    so the generated text contains the exact language patterns that signal_detection.py
    uses to score urgency_score and pattern_risk. This closes the loop between
    generator intent and detector output.

    Args:
        market:        One of the four Cosmic Mart markets.
        source:        Complaint source channel.
        category:      Complaint category (must match signal_detection.py values).
        urgency_score: Integer 1–5.
        pattern_risk:  One of ["low", "medium", "high"]. Controls whether the
                       customer mentions other affected customers / forums.
        extra_hint:    Optional additional context for curated demo signals.

    Returns:
        A complete system prompt string ready to pass to the LLM.
    """
    stars = _star_rating(urgency_score)

    # Resolve the {star_rating} placeholder in the app_review format block
    source_format_text = _SOURCE_FORMAT[source].replace("{star_rating}", str(stars))

    # ROOT FIX 1 — build calibration rules block that shapes exact wording
    calibration = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CALIBRATION REQUIREMENTS — these are mandatory, not suggestions:

Urgency level {urgency_score}/5 — the complaint text MUST reflect this tone exactly:
{URGENCY_LANGUAGE[urgency_score]}

Pattern risk "{pattern_risk}" — the complaint text MUST reflect this exactly:
{PATTERN_LANGUAGE[pattern_risk]}

MANDATORY RULES:
- If urgency_score is 1 or 2: do NOT use threatening language. No bank disputes.
  No legal threats. No "I will post about this." Patient and measured tone only.
- If urgency_score is 5: the customer MUST mention at least one of: bank dispute,
  legal action, lawyer, lawsuit, consumer protection bureau, or a 24-hour deadline.
- If pattern_risk is "high": the customer MUST explicitly mention forums, Trustpilot,
  Reddit, or multiple other customers reporting the same issue. This phrase is required.
- If pattern_risk is "low": the customer MUST NOT mention any other customers,
  forums, or wider problems. Only their own personal experience.
- If pattern_risk is "medium": the customer may hint at one other person affected
  but does NOT confirm a widespread problem.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    prompt = f"""You are generating realistic synthetic customer complaint data for Cosmic Mart,
a global retail brand with 144 million customers. Your output will be used to test
an AI-powered customer experience system.

Write ONE realistic customer complaint message with EXACTLY these characteristics:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARKET: {market}
{_MARKET_TONE[market]}

SOURCE FORMAT: {source}
{source_format_text}

COMPLAINT TOPIC: {category}
{_CATEGORY_CONTENT[category]}

URGENCY LEVEL: {urgency_score} / 5
{URGENCY_LANGUAGE[urgency_score]}

PATTERN RISK: {pattern_risk}
{PATTERN_LANGUAGE[pattern_risk]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    # Inject optional extra context for curated demo signals
    if extra_hint:
        prompt += f"\n\nADDITIONAL CONTEXT (important — incorporate this):\n{extra_hint}"

    prompt += calibration

    prompt += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT RULES:
1. Write ONLY the raw customer message text. Nothing else.
2. Do NOT include JSON, labels, headers, bullet points, or any explanation.
3. Do NOT begin with phrases like "Here is the complaint:", "Customer message:", or similar.
4. Make it sound like a real person wrote it — imperfect grammar is fine, emotions should feel genuine.
5. Include at least one concrete detail: order number, city name, price, product name, or date.
6. Respect the required length: short (1–3 sentences) for social_media;
   medium (3–5 sentences) for app_review; longer (4–8 sentences) for support_ticket.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    return prompt


async def _generate_signal_internal(
    market: str,
    source: str,
    category: str,
    urgency_score: int,
    extra_hint: str = "",
    label: str = "",
    expected_path: str = "",
    pattern_risk: str = "low",
) -> dict:
    """
    Core implementation of signal generation — supports optional extra_hint,
    label override, and expected_path metadata used by generate_demo_set.

    ROOT FIX 1 — now accepts pattern_risk so the generator embeds calibration
    signals in the complaint text that match Signal Detection's scoring rules.

    Args:
        market:        Market name.
        source:        Source channel.
        category:      Complaint category.
        urgency_score: Urgency 1–5.
        extra_hint:    Optional extra context for demo-curated signals.
        label:         Optional label override; defaults to auto-generated.
        expected_path: Optional expected routing path string for demo metadata.
        pattern_risk:  One of ["low", "medium", "high"]. Controls whether
                       generated text mentions other customers / forums.

    Returns:
        Dict with keys: label, market, source, category, urgency_score,
        query, pattern_risk, and (if provided) expected_path.
    """
    # HOSTING — works locally (.env) and on Streamlit Cloud (st.secrets)
    try:
        import streamlit as st
        api_key = st.secrets["API_KEY"]
    except Exception:
        api_key = str(os.getenv("API_KEY"))
    client = AsyncAIRefinery(api_key=api_key)

    system_prompt = _build_system_prompt(
        market=market,
        source=source,
        category=category,
        urgency_score=urgency_score,
        pattern_risk=pattern_risk,
        extra_hint=extra_hint,
    )

    response = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            # The user turn is a neutral trigger — all real instructions are in the system prompt
            {"role": "user", "content": "Generate the customer complaint message now."},
        ],
        model="openai/gpt-oss-120b",
    )

    # Strip any accidental whitespace the model may have added
    query = response.choices[0].message.content.strip()

    result = {
        "label":         label or f"{market} {category} urgency {urgency_score}",
        "market":        market,
        "source":        source,
        "category":      category,
        "urgency_score": urgency_score,
        "pattern_risk":  pattern_risk,
        "query":         query,
    }
    if expected_path:
        result["expected_path"] = expected_path
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

async def generate_signal(
    market: str,
    source: str,
    category: str,
    urgency_score: int,
    pattern_risk: str = "low",
) -> dict:
    """
    Generate a single realistic customer complaint signal using the LLM.

    ROOT FIX 1 — now accepts pattern_risk so generated text is calibrated to
    contain the exact language signals that signal_detection.py uses to score
    urgency_score and pattern_risk correctly.

    Calls the AI Refinery LLM with a carefully constructed prompt that
    combines market tone, source format, complaint category, urgency level,
    and pattern risk calibration. Every call produces a fresh, unique message.

    Args:
        market:        One of ["North America", "Europe", "Asia", "South America"].
        source:        One of ["support_ticket", "social_media", "app_review"].
        category:      One of ["service_delay", "return_friction",
                                "price_dissatisfaction", "product_quality", "other"].
                       These values match the output of signal_detection.py exactly.
        urgency_score: Integer 1–5.
                       1 = minor inconvenience, 5 = urgent reputational risk.
        pattern_risk:  One of ["low", "medium", "high"].
                       Controls whether the generated text mentions forums /
                       community reports so Signal Detection scores it correctly.

    Returns:
        A dict with exactly these keys (matching main.py's expected format):
            label        (str)  — "<market> <category> urgency <urgency_score>"
            market       (str)  — the market passed in
            source       (str)  — the source passed in
            category     (str)  — the category passed in
            urgency_score (int) — the urgency_score passed in
            pattern_risk  (str) — the pattern_risk passed in
            query        (str)  — the raw LLM-generated customer complaint text
    """
    return await _generate_signal_internal(
        market=market,
        source=source,
        category=category,
        urgency_score=urgency_score,
        pattern_risk=pattern_risk,
        extra_hint="",
    )


async def generate_batch(n: int) -> list:
    """
    Generate n signals with fully randomised parameters.

    Uses asyncio.gather to generate all signals concurrently — much faster
    than sequential calls when n is large.

    Variety guarantee:
        No two consecutive signals in the returned list will have the same
        category AND the same market simultaneously. This prevents monotonous
        batches where, for example, all signals are "Asia service_delay".
        Parameters are planned first (with this constraint enforced), then
        all LLM calls fire in parallel.

    Args:
        n: Number of signals to generate. Must be a positive integer.

    Returns:
        A list of n signal dicts, each with keys:
        label, market, source, category, urgency_score, query.

    Example:
        signals = await generate_batch(10)
        for s in signals:
            print_signal(s)
    """
    params_list = []
    last_market: Optional[str] = None
    last_category: Optional[str] = None

    for _ in range(n):
        attempts = 0
        while True:
            market = random.choice(MARKETS)
            source = random.choice(SOURCES)
            category = random.choice(CATEGORIES)
            urgency_score = random.randint(1, 5)

            # Enforce variety: reject if consecutive market+category pair is identical.
            # After 50 attempts (near-impossible with 4 markets × 5 categories),
            # allow the duplicate to avoid an infinite loop on tiny parameter spaces.
            same_pair = (market == last_market and category == last_category)
            if not same_pair or attempts >= 50:
                break
            attempts += 1

        # ROOT FIX 1 — randomize pattern_risk for calibrated generation
        pattern_risk = random.choice(["low", "medium", "high"])
        params_list.append((market, source, category, urgency_score, pattern_risk))
        last_market = market
        last_category = category

    # Fire all LLM calls concurrently — order is preserved by asyncio.gather
    signals = await asyncio.gather(
        *[
            _generate_signal_internal(m, s, c, u, pattern_risk=pr)
            for m, s, c, u, pr in params_list
        ]
    )

    return list(signals)


async def generate_demo_set() -> list:
    """
    Generate exactly 5 curated signals covering the two mutually exclusive routing
    paths in the Cosmic Pulse architecture diagram. Each signal reliably triggers
    its intended route based on urgency_score and pattern_risk.

    Routing logic (strict if/else):
        Route 1 — Resolution path  : urgency_score >= 4
        Route 2 — Insight-only path: pattern_risk in ("medium","high") AND urgency <= 3

    Signal coverage:
        Signal 1 — Route 1 — Resolution only
            market: North America | source: support_ticket | category: service_delay
            urgency: 5 | pattern_risk: low (isolated incident)
            expected: Detection → Resolution → Learning

        Signal 2 — Route 2 — Insight Routing ONLY
            market: Europe | source: app_review | category: return_friction
            urgency: 2 (LOW) | pattern_risk: high (systemic portal outage)
            expected: Detection → Insight Routing ONLY → Learning
            Key: urgency ≤ 3 AND pattern_risk == "high" → Insight Routing; Resolution never runs

        Signal 3 — Route 1 — Resolution + Employee Enablement
            market: Asia | source: social_media | category: price_dissatisfaction
            urgency: 4 | pattern_risk: high (regional pattern)
            expected: Detection → Resolution → Employee Enablement → Learning
            Key: urgency 4 → Route 1; store associate gave wrong price match info
                 → frontline_gap_detected: true → EEA fires as sub-route of Resolution

        Signal 4 — Route 1 — Resolution + HITL governance
            market: South America | source: support_ticket | category: product_quality
            urgency: 5 | pattern_risk: low (isolated defect)
            expected: Detection → Resolution → HITL pause → Learning
            Key: R$800 BRL value + explicit legal threat → requires_human: true

        Signal 5 — Route 2 — Insight Routing ONLY
            market: Europe | source: app_review | category: other
            urgency: 3 | pattern_risk: medium (loyalty policy confusion pattern)
            expected: Detection → Insight Routing ONLY → Learning
            Key: urgency ≤ 3 AND pattern_risk "medium" → Route 2; Resolution/EEA never run

    Returns:
        A list of exactly 5 signal dicts in demo-ready order.
        Each dict includes an 'expected_path' field for display purposes.
    """
    # ROOT FIX 4 — signal 2 and 5 extra hints calibrated with explicit phrase guidance
    # Each tuple: (market, source, category, urgency_score, pattern_risk,
    #              extra_hint, label, expected_path)
    demo_params = [
        # ── SIGNAL 1 — Route 1: Resolution only ────────────────────────────────
        (
            "North America",
            "support_ticket",
            "service_delay",
            5,
            "low",                          # urgency 5 → Route 1; isolated incident
            (
                "Single customer, isolated incident — this is NOT a widespread pattern. "
                "Do NOT mention other customers, forums, or community reports at all. "
                "Order tracking stuck for one customer in Chicago. No other complaints "
                "about this order batch. Support agents could not locate the order in "
                "their system — make it clear the frontline staff were helpless. "
                "CRITICAL: The customer explicitly threatens to dispute the charge with "
                "their bank (use the phrase 'bank dispute' or 'dispute this charge') "
                "and mentions contacting consumer protection. This is a Score 5 urgency — "
                "the threat of bank dispute or legal action must be explicit in the text. "
                "Mention a specific order number like CM-US-2024-558821."
            ),
            "North America · service delay · urgency 5 · isolated",
            "Detection → Resolution → Learning",
        ),
        # ── SIGNAL 2 — Route 2: Insight Routing ONLY (no Resolution) ──────────
        # ROOT FIX 4 — calibrated hint: urgency 2 tone + high pattern language
        (
            "Europe",
            "app_review",
            "return_friction",
            2,
            "high",                         # urgency 2 + pattern high → Route 2
            (
                "Write a MILD 2-star app review from a European customer "
                "who is disappointed but patient. The customer MUST: "
                "- Use calm, measured language matching urgency 2 tone: "
                "  words like 'disappointed', 'I was hoping', 'I would appreciate', "
                "  'unfortunately'. Absolutely NO threatening language. "
                "  NO bank disputes, NO legal threats, NO 'I will post about this'. "
                "- EXPLICITLY mention seeing the same portal issue reported by "
                "  hundreds of customers on Trustpilot and in the Cosmic Mart community "
                "  forum this week — use phrases like 'hundreds of customers are reporting "
                "  this', 'I saw dozens of complaints on Trustpilot', 'the forum is full "
                "  of this issue'. This Trustpilot/forum reference is MANDATORY. "
                "- Mention EU consumer rights politely as a note, not as a threat. "
                "- Sound like someone who expects it to be fixed eventually, "
                "  not someone who needs it fixed today. "
                "The forum/Trustpilot reference with 'hundreds of customers' or 'many "
                "people' is required — without it the pattern will not be detected."
            ),
            "Europe · return portal outage · pattern HIGH · low urgency",
            "Detection → Insight Routing ONLY → Learning",
        ),
        # ── SIGNAL 3 — Route 1: Resolution + Employee Enablement ───────────────
        (
            "Asia",
            "social_media",
            "price_dissatisfaction",
            4,
            "high",                         # urgency 4 → Route 1 (EEA via frontline gap)
            (
                "Angry individual customer in Singapore furious about a price discrepancy. "
                "They visited the Cosmic Mart store and a store associate PROMISED them the "
                "price would be matched to a competitor (Lazada). But when they checked the "
                "Cosmic Mart app, the price was different — higher than what the associate "
                "quoted. The store associate gave WRONG information about the price match "
                "policy. Now the customer doesn't know which price is correct and feels misled "
                "by staff. They are demanding the price they were verbally promised. "
                "The staff clearly did not know the correct policy — make the frontline "
                "knowledge gap very obvious. Also mention the pattern: they have seen dozens "
                "of posts on regional Facebook groups confirming Cosmic Mart prices are "
                "30-40% above Lazada across Southeast Asia. "
                "Urgency 4 language: use 'completely unacceptable' and 'I demand', "
                "threaten to post on social media — but NO bank dispute or legal threat. "
                "Tag @CosmicMart and use CAPS on the key frustration word."
            ),
            "Asia · price mismatch · urgency 4 · EEA",
            "Detection → Resolution → Employee Enablement → Learning",
        ),
        # ── SIGNAL 4 — Route 1: Resolution + HITL governance ───────────────────
        (
            "South America",
            "support_ticket",
            "product_quality",
            5,
            "low",                          # urgency 5 → Route 1; isolated → HITL
            (
                "Defective product requiring large compensation — a specific item "
                "(e.g. a blender, jacket, or phone accessory) arrived broken or "
                "completely non-functional. The replacement or refund value is over "
                "R$800 BRL (well above the $200 USD auto-approval threshold). "
                "CRITICAL: The customer explicitly threatens legal action and mentions "
                "they will contact a consumer protection agency (Procon in Brazil). "
                "Use the phrase 'legal action' explicitly in the text. "
                "This is an isolated incident — do NOT mention other customers, "
                "forums, or community reports at all. "
                "Include a specific order number like CM-BR-2024-334871 and city "
                "(São Paulo or Buenos Aires). The high monetary value (R$800+) and "
                "explicit legal threat require human approval before any action."
            ),
            "South America · product defect · urgency 5 · HITL required",
            "Detection → Resolution → HITL pause → Learning",
        ),
        # ── SIGNAL 5 — Route 2: Insight Routing ONLY (no Resolution) ──────────
        # ROOT FIX 4 — calibrated hint: urgency 3 tone + medium pattern language
        (
            "Europe",
            "app_review",
            "other",
            3,
            "medium",                       # urgency 3 + pattern medium → Route 2
            (
                "Write a CALM app review from a European customer who is "
                "confused and frustrated about the Cosmic Mart loyalty points "
                "redemption policy. The customer MUST: "
                "- Use firm but composed language matching urgency 3 tone: "
                "  words like 'unacceptable', 'very disappointed', 'I need this "
                "  resolved', 'I am not satisfied'. Firm but NOT aggressive. "
                "  NO legal threats, NO bank disputes, NO urgent demands. "
                "- EXPLICITLY mention seeing another customer or two with the "
                "  same loyalty policy confusion — use phrases like 'a friend "
                "  told me the same thing happened to them' or 'I saw someone "
                "  else had this issue on a forum'. This community hint is MANDATORY. "
                "- Reference trying to redeem points in Berlin or another EU city "
                "  and being given unclear or contradictory information about the policy. "
                "- Ask for policy clarification and compensation for the points issue. "
                "- Sound patient and reasonable, not furious. "
                "The 'friend/someone else' community reference is required to signal "
                "pattern_risk medium — without it the pattern will not be detected."
            ),
            "Europe · loyalty policy confusion · pattern MEDIUM · insight only",
            "Detection → Insight Routing ONLY → Learning",
        ),
    ]

    # Fire all 5 LLM calls concurrently — order is preserved by asyncio.gather
    signals = await asyncio.gather(
        *[
            _generate_signal_internal(
                market, source, category, urgency,
                extra_hint=hint,
                label=label,
                expected_path=expected_path,
                pattern_risk=pattern_risk,
            )
            for market, source, category, urgency, pattern_risk, hint, label, expected_path
            in demo_params
        ]
    )

    return list(signals)


def print_signal(signal: dict) -> None:
    """
    Print a formatted preview of a generated signal for team review.

    Displays the signal's metadata header and full query text in a clearly
    demarcated block. Use this before running the pipeline to confirm the
    generated message looks realistic and will trigger the expected agents.

    Args:
        signal: A signal dict with keys label, market, source,
                category, urgency_score, and query.

    Output format:
        ============================================================
        SIGNAL: <label>
        Market: <market> | Source: <source> | Urgency: <urgency_score>
        Category: <category>
        ------------------------------------------------------------
        <query>
        ============================================================
    """
    border = "=" * 60
    divider = "-" * 60
    print(border)
    print(f"SIGNAL: {signal['label']}")
    print(
        f"Market: {signal['market']} | "
        f"Source: {signal['source']} | "
        f"Urgency: {signal['urgency_score']}"
    )
    print(f"Category: {signal['category']}")
    print(divider)
    print(signal["query"])
    print(border)


# ──────────────────────────────────────────────────────────────────────────────
# HOW TO UPDATE main.py TO USE THE GENERATOR
#
# Replace the hardcoded test_signals list with:
#
# from data_generator import generate_demo_set, print_signal
#
# async def run():
#     test_signals = await generate_demo_set()
#     for signal in test_signals:
#         print_signal(signal)
#         # then pass signal["query"] to the pipeline
#         responses = await dc.query(query=signal["query"])
# ──────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    async def _preview() -> None:
        """
        Standalone preview: generate and print the full demo set of 5 signals.
        Run with: python data_generator.py
        """
        print("\nCosmic Pulse — Data Generator Preview")
        print("Generating demo set of 5 signals (this may take a few seconds)...\n")

        signals = await generate_demo_set()

        for i, signal in enumerate(signals, start=1):
            print(f"\n[{i} of {len(signals)}]")
            print_signal(signal)

        print(
            f"\n✓ {len(signals)} signals generated successfully. "
            "Ready to pass to the Cosmic Pulse pipeline."
        )

    asyncio.run(_preview())
