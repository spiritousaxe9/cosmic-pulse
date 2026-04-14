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

# Per-urgency: controls emotional intensity and language register
_URGENCY_TONE = {
    1: (
        "The customer is mildly inconvenienced. Tone is calm and almost polite. "
        "They are reporting a problem but not demanding immediate action. No threats."
    ),
    2: (
        "The customer is frustrated but composed. "
        "They want an answer but their language stays measured. "
        "They may express disappointment but do not threaten consequences."
    ),
    3: (
        "The customer is clearly unhappy. Tone is firm and pointed. "
        "They state what they want to happen. "
        "They may say they are 'very disappointed' or 'not impressed'. "
        "No explicit threats yet but the implication is there."
    ),
    4: (
        "The customer is angry. Language is sharp and demanding. "
        "They use strong phrasing like 'completely unacceptable' or 'absolutely disgusted'. "
        "They may threaten to leave Cosmic Mart, post a negative review, "
        "or tell friends to avoid the brand. "
        "Capitalise one or two key phrases for emphasis."
    ),
    5: (
        "The customer is furious. This is an urgent, reputational-risk message. "
        "They explicitly threaten to dispute the charge with their bank, "
        "contact a consumer rights body, go to media, post publicly, "
        "or have already told others to avoid Cosmic Mart. "
        "Maximum emotional intensity — the brand is at immediate risk."
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
    extra_hint: str = "",
) -> str:
    """
    Build the complete LLM system prompt for generating a customer complaint.

    Combines market tone, source format, category content, urgency guidance,
    and an optional extra hint into a single coherent instruction block.
    The model is explicitly told to return ONLY the raw customer message —
    no JSON, no labels, no preamble.

    Args:
        market:        One of the four Cosmic Mart markets.
        source:        Complaint source channel.
        category:      Complaint category (must match signal_detection.py values).
        urgency_score: Integer 1–5.
        extra_hint:    Optional additional context for curated demo signals.

    Returns:
        A complete system prompt string ready to pass to the LLM.
    """
    stars = _star_rating(urgency_score)

    # Resolve the {star_rating} placeholder in the app_review format block
    source_format_text = _SOURCE_FORMAT[source].replace("{star_rating}", str(stars))

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
{_URGENCY_TONE[urgency_score]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    # Inject optional extra context for curated demo signals
    if extra_hint:
        prompt += f"\n\nADDITIONAL CONTEXT (important — incorporate this):\n{extra_hint}"

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
) -> dict:
    """
    Core implementation of signal generation — supports an optional extra_hint
    parameter used by generate_demo_set to inject curated context that ensures
    specific routing paths are triggered in the orchestrator.

    Calls the AI Refinery LLM and wraps the generated text in a signal dict
    with the exact keys that main.py expects.

    Args:
        market:        Market name.
        source:        Source channel.
        category:      Complaint category.
        urgency_score: Urgency 1–5.
        extra_hint:    Optional extra context for demo-curated signals.

    Returns:
        Dict with keys: label, market, source, category, urgency_score, query.
    """
    api_key = str(os.getenv("API_KEY"))
    client = AsyncAIRefinery(api_key=api_key)

    system_prompt = _build_system_prompt(
        market=market,
        source=source,
        category=category,
        urgency_score=urgency_score,
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

    return {
        "label": f"{market} {category} urgency {urgency_score}",
        "market": market,
        "source": source,
        "category": category,
        "urgency_score": urgency_score,
        "query": query,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

async def generate_signal(
    market: str,
    source: str,
    category: str,
    urgency_score: int,
) -> dict:
    """
    Generate a single realistic customer complaint signal using the LLM.

    Calls the AI Refinery LLM with a carefully constructed prompt that
    combines market tone, source format, complaint category, and urgency
    level. Every call produces a fresh, unique message — no two runs will
    return the same text.

    Args:
        market:        One of ["North America", "Europe", "Asia", "South America"].
        source:        One of ["support_ticket", "social_media", "app_review"].
        category:      One of ["service_delay", "return_friction",
                                "price_dissatisfaction", "product_quality", "other"].
                       These values match the output of signal_detection.py exactly.
        urgency_score: Integer 1–5.
                       1 = minor inconvenience, 5 = urgent reputational risk.

    Returns:
        A dict with exactly these keys (matching main.py's expected format):
            label        (str)  — "<market> <category> urgency <urgency_score>"
            market       (str)  — the market passed in
            source       (str)  — the source passed in
            category     (str)  — the category passed in
            urgency_score (int) — the urgency_score passed in
            query        (str)  — the raw LLM-generated customer complaint text
    """
    return await _generate_signal_internal(
        market=market,
        source=source,
        category=category,
        urgency_score=urgency_score,
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

        params_list.append((market, source, category, urgency_score))
        last_market = market
        last_category = category

    # Fire all LLM calls concurrently — order is preserved by asyncio.gather
    signals = await asyncio.gather(
        *[
            _generate_signal_internal(m, s, c, u)
            for m, s, c, u in params_list
        ]
    )

    return list(signals)


async def generate_demo_set() -> list:
    """
    Generate exactly 5 curated signals designed to exercise every routing
    path in the Cosmic Pulse orchestration system.

    Each signal is crafted with a specific context hint so the LLM generates
    a message that reliably triggers the intended agent(s):

        Signal 1 — North America | support_ticket | service_delay | urgency 5
            Triggers: Resolution Agent (urgency >= 4)
                      Employee Enablement Agent (frontline staff unable to help)
            Context:  Customer called support twice with no resolution.
                      Threatening bank dispute. Staff explicitly unhelpful.

        Signal 2 — Europe | app_review | return_friction | urgency 3
            Triggers: Insight Routing Agent (pattern_risk high — many customers affected)
                      Resolution Agent (return friction, urgency 3)
            Context:  Customer found community forum posts showing many UK/EU customers
                      have the same portal issue. References EU consumer rights.

        Signal 3 — Asia | social_media | price_dissatisfaction | urgency 4
            Triggers: Resolution Agent (urgency >= 4)
                      Insight Routing Agent (pattern_risk high — regional pattern)
            Context:  Price rise across Singapore, Malaysia, Thailand.
                      Regional Facebook groups and Reddit threads confirming pattern.

        Signal 4 — South America | support_ticket | product_quality | urgency 4
            Triggers: Resolution Agent (urgency >= 4, faulty product)
            Context:  Specific item arrived visibly damaged.
                      Store staff couldn't help with online orders — policy unknown.

        Signal 5 — Europe | social_media | other | urgency 3
            Triggers: Employee Enablement Agent (frontline knowledge gap)
            Context:  Two staff members gave contradictory loyalty programme answers.
                      Classic frontline gap — staff have no consistent policy guidance.

    Coverage summary:
        ✓ At least one urgency 4 or 5     → Resolution Agent       (signals 1, 3, 4)
        ✓ At least one pattern_risk high  → Insight Routing Agent  (signals 2, 3)
        ✓ At least one frontline gap      → Employee Enablement    (signals 1, 4, 5)
        ✓ At least 3 different markets    → NA, Europe, Asia, SA   (all 4 used)
        ✓ At least 3 different sources    → ticket, review, social (all 3 used)

    Returns:
        A list of exactly 5 signal dicts in demo-ready order.
    """
    # Each tuple: (market, source, category, urgency_score, extra_hint)
    demo_params = [
        (
            "North America",
            "support_ticket",
            "service_delay",
            5,
            # Hint: failed support contacts + frontline gap + bank dispute threat
            (
                "The customer has already called Cosmic Mart support twice. "
                "Both times the agent said they would escalate but nothing was ever "
                "followed up and the order is still missing. Make it very explicit "
                "that the frontline staff were completely unable to help and did not "
                "know how to locate the order in their system. "
                "The customer is now threatening to dispute the charge with their "
                "bank and share the experience on social media."
            ),
        ),
        (
            "Europe",
            "app_review",
            "return_friction",
            3,
            # Hint: widespread pattern — community forum evidence + EU rights
            (
                "The customer discovered on the Cosmic Mart community forum and "
                "Trustpilot that many other UK and EU customers have been hitting "
                "the exact same return portal failure this week — it is clearly a "
                "systemic platform issue, not just their device. "
                "Mention EU consumer rights or the 14-day return law briefly. "
                "The customer is frustrated that a known issue hasn't been fixed."
            ),
        ),
        (
            "Asia",
            "social_media",
            "price_dissatisfaction",
            4,
            # Hint: regional price pattern across multiple Asian markets
            (
                "Prices have risen noticeably across Singapore, Malaysia, and Thailand "
                "over the past few months with no quality improvement. "
                "The customer has seen hundreds of posts in regional Facebook groups "
                "and Reddit threads from other customers across Southeast Asia "
                "saying the same thing. "
                "Tag @CosmicMart and use CAPS on the price increase figure or "
                "the word that expresses peak frustration."
            ),
        ),
        (
            "South America",
            "support_ticket",
            "product_quality",
            4,
            # Hint: damaged item + store staff couldn't help = frontline gap
            (
                "A specific item — either a jacket, a pair of trainers, or a small "
                "kitchen appliance — arrived visibly damaged with a cracked seam or "
                "broken component that was clearly a manufacturing defect. "
                "The customer went to the local São Paulo or Buenos Aires store to "
                "resolve it but the store associate said they have no way to handle "
                "online order defects in-store and did not know the correct policy. "
                "Include a specific order number and product name."
            ),
        ),
        (
            "Europe",
            "social_media",
            "other",
            3,
            # Hint: explicit frontline knowledge gap — contradictory staff answers
            (
                "The complaint is specifically about Cosmic Mart staff giving "
                "completely contradictory information about the loyalty points "
                "redemption policy. A store associate in the London Oxford Street "
                "store said one thing; a contact centre agent said the opposite. "
                "Neither could point to a written policy. "
                "This is a textbook frontline knowledge gap. "
                "Tag @CosmicMart and keep it short and punchy."
            ),
        ),
    ]

    # Fire all 5 LLM calls concurrently — order is preserved by asyncio.gather
    signals = await asyncio.gather(
        *[
            _generate_signal_internal(market, source, category, urgency, hint)
            for market, source, category, urgency, hint in demo_params
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
