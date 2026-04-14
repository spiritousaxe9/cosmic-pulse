# ════════════════════════════════════════════════════
#  HOSTING ON STREAMLIT COMMUNITY CLOUD
#  (Free — takes ~10 minutes)
#
#  Step 1: Push project to GitHub
#    git init
#    git add .
#    git commit -m "Cosmic Pulse demo"
#    gh repo create cosmic-pulse --public --push
#
#  Step 2: Add secrets to GitHub repo
#    Go to repo Settings > Secrets > Actions
#    Add secret: API_KEY = your_airefinery_key
#
#  Step 3: Create requirements.txt in project root:
#    streamlit>=1.32.0
#    airefinery-sdk
#    python-dotenv
#
#  Step 4: Create .streamlit/secrets.toml locally:
#    API_KEY = "your_airefinery_key"
#
#  Step 5: Deploy on Streamlit Cloud
#    Go to share.streamlit.io
#    Connect GitHub account
#    Select repo: cosmic-pulse  |  Main file: app.py
#    Click Deploy
#
#  Step 6: Get your public URL
#    Format: https://yourname-cosmic-pulse.streamlit.app
#
#  Step 7: Update .env usage for cloud — already handled
#    below via try/except st.secrets pattern.
#
#  NOTE: Make sure .env and .streamlit/secrets.toml
#  are both in .gitignore — never push API keys.
# ════════════════════════════════════════════════════

# Install: pip install -r requirements.txt
# Run:     streamlit run app.py
"""
Cosmic Pulse — Streamlit Demo App

Multi-agent customer experience orchestration for Cosmic Mart.
Five specialised agents handle classification, resolution, employee
enablement, insight routing, and continuous learning.

Modes:
  Live Demo      — auto-runs 5 pre-built signals (judge presentation)
  Quick Generate — pick parameters, run one signal
  Manual Input   — paste your own signal text
"""

import streamlit as st
import asyncio
import json
import os

# HOSTING — works both locally (.env) and on Streamlit Cloud (st.secrets)
try:
    _api_key_global = st.secrets["API_KEY"]
    os.environ.setdefault("API_KEY", _api_key_global)
except Exception:
    from dotenv import load_dotenv
    load_dotenv()

from py_scripts.signal_detection import signal_detection_agent
from py_scripts.resolution import resolution_agent
from py_scripts.employee_enablement import employee_enablement_agent
from py_scripts.insight_routing import insight_routing_agent
from py_scripts.learning_insights import learning_insights_agent
from data_generator import generate_signal, generate_demo_set

# ─────────────────────────────────────────────────────────────────────────────
# Page config — must be first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cosmic Pulse",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# MODERN UI — Global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Reset / base ─────────────────────────────────────────────────────────── */
#MainMenu {visibility: hidden;}
footer    {visibility: hidden;}
header    {visibility: hidden;}
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.main .block-container {
    padding-top: 1.25rem;
    max-width: 1400px;
}

/* ── Tag pill ──────────────────────────────────────────────────────────────── */
.tag-pill {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 0.72rem;
    margin: 2px;
    background: rgba(255,255,255,0.2);
    color: white;
}

/* ── Primary button ────────────────────────────────────────────────────────── */
div.stButton > button[kind="primary"] {
    background-color: #6D28D9;
    color: white;
    border: none;
    font-weight: 600;
    font-size: 0.875rem;
    border-radius: 8px;
    padding: 0.5rem 1rem;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #5B21B6;
    border: none;
}
div.stButton > button[kind="primary"]:disabled {
    background-color: #C4B5FD;
    border: none;
}

/* ── Tab bar ───────────────────────────────────────────────────────────────── */
button[data-baseweb="tab"] {
    font-weight: 600;
    font-size: 0.875rem;
}

/* ── Step indicator pulse animation ───────────────────────────────────────── */
@keyframes pulse-ring {
    0%   { box-shadow: 0 0 0 0   rgba(109,40,217,0.45); }
    70%  { box-shadow: 0 0 0 7px rgba(109,40,217,0); }
    100% { box-shadow: 0 0 0 0   rgba(109,40,217,0); }
}
.step-active { animation: pulse-ring 1.5s ease-out infinite; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
MARKETS    = ["North America", "Europe", "Asia", "South America"]
SOURCES    = ["support_ticket", "social_media", "app_review"]
CATEGORIES = ["service_delay", "return_friction", "price_dissatisfaction",
              "product_quality", "other"]

AGENT_COLORS = {
    "Signal Detection Agent":     {"border": "#3B82F6", "text": "#1D4ED8",
                                   "bg": "#EFF6FF",  "light": "#DBEAFE"},
    "Resolution Agent":           {"border": "#10B981", "text": "#059669",
                                   "bg": "#F0FDF4",  "light": "#DCFCE7"},
    "Employee Enablement Agent":  {"border": "#14B8A6", "text": "#0F766E",
                                   "bg": "#F0FDFA",  "light": "#CCFBF1"},
    "Insight Routing Agent":      {"border": "#6366F1", "text": "#4338CA",
                                   "bg": "#EEF2FF",  "light": "#E0E7FF"},
    "Learning and Insights Agent":{"border": "#8B5CF6", "text": "#6D28D9",
                                   "bg": "#F5F3FF",  "light": "#EDE9FE"},
    "Human Governance":           {"border": "#F59E0B", "text": "#B45309",
                                   "bg": "#FFFBEB",  "light": "#FEF3C7"},
}

# Live Demo signal metadata (used for the intro table)
DEMO_SIGNALS_META = [
    (1, "North America", "service_delay",         5),
    (2, "Europe",        "return_friction",        3),
    (3, "Asia",          "price_dissatisfaction",  4),
    (4, "South America", "product_quality",        4),
    (5, "Europe",        "other",                  3),
]

# ─────────────────────────────────────────────────────────────────────────────
# Async runner
# ─────────────────────────────────────────────────────────────────────────────
def run_async(coro):
    """Run an async coroutine safely from Streamlit's synchronous context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ─────────────────────────────────────────────────────────────────────────────
# MODERN UI — Rendering helpers
# ─────────────────────────────────────────────────────────────────────────────

def urgency_color(score: int) -> tuple:
    """Return (text_color, bg_color) for an urgency score."""
    if score <= 2:   return "#059669", "#DCFCE7"
    elif score == 3: return "#D97706", "#FEF3C7"
    else:            return "#DC2626", "#FEE2E2"


def render_kv_table_html(data: dict) -> str:
    """Render a dict as clean HTML key-value rows."""
    rows = []
    for key, value in data.items():
        key_td = (
            f'<td style="padding:3px 12px 3px 0;color:#64748B;font-weight:600;'
            f'vertical-align:top;white-space:nowrap;font-size:0.78rem;">{key}</td>'
        )
        if isinstance(value, dict):
            rows.append(
                f'<tr><td colspan="2" style="padding:6px 0 2px 0;font-weight:700;'
                f'color:#334155;font-size:0.78rem;border-top:1px solid #E2E8F0;">{key}</td></tr>'
            )
            for sk, sv in value.items():
                rows.append(
                    f'<tr>'
                    f'<td style="padding:2px 10px 2px 16px;color:#64748B;font-size:0.75rem;">{sk}</td>'
                    f'<td style="padding:2px 8px;color:#0F172A;font-size:0.75rem;">{sv}</td>'
                    f'</tr>'
                )
        elif isinstance(value, list):
            pills = " ".join(
                f'<span style="background:#EDE9FE;color:#4C1D95;padding:1px 8px;'
                f'border-radius:999px;font-size:0.72rem;margin:1px;display:inline-block;">{v}</span>'
                for v in value
            )
            rows.append(f'<tr>{key_td}<td style="padding:3px 8px;">{pills}</td></tr>')
        elif value is None:
            rows.append(
                f'<tr>{key_td}'
                f'<td style="padding:3px 8px;color:#94A3B8;font-size:0.78rem;font-style:italic;">'
                f'not triggered</td></tr>'
            )
        else:
            rows.append(
                f'<tr>{key_td}'
                f'<td style="padding:3px 8px;color:#0F172A;font-size:0.78rem;">{str(value)}</td>'
                f'</tr>'
            )
    return f'<table style="width:100%;border-collapse:collapse;">{"".join(rows)}</table>'


def agent_card_html(name: str, result_str, triggered: bool = True) -> str:
    """Modernized agent card with pill label and status badge."""
    colors = AGENT_COLORS.get(name, {"border": "#E2E8F0", "text": "#64748B",
                                      "bg": "#F8FAFC", "light": "#F1F5F9"})
    if not triggered or not result_str:
        body = ('<p style="color:#94A3B8;font-size:0.78rem;margin:0;font-style:italic;">'
                'This agent was not invoked for this signal.</p>')
        badge_color, badge_bg, badge_text = "#94A3B8", "#F1F5F9", "⬜ Not triggered"
    else:
        try:
            body = render_kv_table_html(json.loads(result_str))
        except (json.JSONDecodeError, TypeError):
            safe = result_str.replace("<", "&lt;").replace(">", "&gt;")
            body = f'<code style="font-size:0.72rem;color:#334155;word-break:break-all;">{safe}</code>'
        badge_color, badge_bg, badge_text = "#059669", "#DCFCE7", "✅ Triggered"

    return (
        f'<div style="border-left:3px solid {colors["border"]};border-radius:10px;'
        f'padding:1.1rem 1.25rem;margin-bottom:0.75rem;background:#FFFFFF;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.06),0 1px 2px rgba(0,0,0,0.04);">'
        f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.65rem;">'
        f'<span style="background:{colors["light"]};color:{colors["text"]};padding:3px 10px;'
        f'border-radius:999px;font-size:0.72rem;font-weight:600;letter-spacing:0.02em;">{name}</span>'
        f'<span style="margin-left:auto;color:{badge_color};background:{badge_bg};'
        f'padding:2px 9px;border-radius:999px;font-size:0.7rem;font-weight:600;">{badge_text}</span>'
        f'</div>'
        f'{body}'
        f'</div>'
    )


def pending_card_html(name: str) -> str:
    return (
        f'<div style="border-left:3px solid #E2E8F0;border-radius:10px;'
        f'padding:0.8rem 1.25rem;margin-bottom:0.75rem;background:#F8FAFC;opacity:0.45;">'
        f'<span style="font-weight:600;color:#94A3B8;font-size:0.85rem;">⏳ {name} — waiting</span>'
        f'</div>'
    )


def running_card_html(name: str) -> str:
    colors = AGENT_COLORS.get(name, {"border": "#E2E8F0", "text": "#64748B",
                                      "bg": "#F8FAFC", "light": "#F1F5F9"})
    return (
        f'<div style="border-left:3px solid {colors["border"]};border-radius:10px;'
        f'padding:0.8rem 1.25rem;margin-bottom:0.75rem;background:{colors["bg"]};'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
        f'<span style="background:{colors["light"]};color:{colors["text"]};padding:3px 10px;'
        f'border-radius:999px;font-size:0.72rem;font-weight:600;">'
        f'🔄 {name} — running…</span>'
        f'</div>'
    )


# LIVE DEMO MODE — step indicator
def step_indicator_html(current: int, total: int = 5) -> str:
    """
    Render Signal 1 > Signal 2 > ... progress row.
    current = 1-5 means that signal is active; current > total means all done.
    """
    parts = []
    for i in range(1, total + 1):
        if i < current:
            circle = (
                f'<div style="width:28px;height:28px;border-radius:50%;background:#6D28D9;'
                f'color:white;display:flex;align-items:center;justify-content:center;'
                f'margin:0 auto;font-size:0.7rem;font-weight:700;">✓</div>'
            )
            lc = "#6D28D9"
        elif i == current:
            circle = (
                f'<div class="step-active" style="width:28px;height:28px;border-radius:50%;'
                f'border:2.5px solid #6D28D9;color:#6D28D9;display:flex;align-items:center;'
                f'justify-content:center;margin:0 auto;font-size:0.7rem;font-weight:700;">{i}</div>'
            )
            lc = "#6D28D9"
        else:
            circle = (
                f'<div style="width:28px;height:28px;border-radius:50%;border:2px solid #E2E8F0;'
                f'color:#94A3B8;display:flex;align-items:center;justify-content:center;'
                f'margin:0 auto;font-size:0.7rem;font-weight:700;">{i}</div>'
            )
            lc = "#94A3B8"

        parts.append(
            f'<div style="text-align:center;flex:1;">'
            f'{circle}'
            f'<div style="font-size:0.65rem;color:{lc};font-weight:600;margin-top:4px;">'
            f'Signal {i}</div></div>'
        )
        if i < total:
            lcolor = "#6D28D9" if i < current else "#E2E8F0"
            parts.append(
                f'<div style="height:2px;background:{lcolor};flex:2;margin-bottom:18px;"></div>'
            )

    return (
        f'<div style="display:flex;align-items:center;margin-bottom:1.25rem;">'
        + "".join(parts)
        + "</div>"
    )


def hitl_governance_card_html(action_taken: str, customer_message: str, signal: dict) -> str:
    urgency  = signal.get("urgency_score", 3)
    category = signal.get("category", "other").replace("_", " ").title()
    market   = signal.get("market", "Unknown")
    act_safe = str(action_taken).replace("<", "&lt;").replace(">", "&gt;")
    msg_safe = str(customer_message).replace("<", "&lt;").replace(">", "&gt;")
    msg_prev = (msg_safe[:140] + "…") if len(msg_safe) > 140 else msg_safe

    return (
        f'<div style="border-left:3px solid #F59E0B;border-radius:10px;'
        f'padding:1.1rem 1.25rem;margin-bottom:0.5rem;background:#FFFBEB;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
        f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.6rem;">'
        f'<span style="background:#FEF3C7;color:#B45309;padding:3px 10px;border-radius:999px;'
        f'font-size:0.72rem;font-weight:600;">⚠️ Human Governance</span>'
        f'<span style="margin-left:auto;background:#FEF3C7;color:#B45309;padding:2px 9px;'
        f'border-radius:999px;font-size:0.7rem;font-weight:600;">🔒 Awaiting Decision</span>'
        f'</div>'
        f'<p style="color:#78350F;font-size:0.78rem;margin:0 0 0.6rem 0;">'
        f'The Resolution Agent flagged this case as high-impact. A human must approve or '
        f'reject the proposed action before the pipeline continues.</p>'
        f'<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
        f'<tr><td style="padding:3px 12px 3px 0;color:#92400E;font-weight:600;white-space:nowrap;">'
        f'Proposed action</td>'
        f'<td style="padding:3px 8px;color:#0F172A;font-weight:700;">{act_safe}</td></tr>'
        f'<tr><td style="padding:3px 12px 3px 0;color:#92400E;font-weight:600;vertical-align:top;">'
        f'Customer message</td>'
        f'<td style="padding:3px 8px;color:#0F172A;">{msg_prev}</td></tr>'
        f'<tr><td style="padding:3px 12px 3px 0;color:#92400E;font-weight:600;">Urgency</td>'
        f'<td style="padding:3px 8px;color:#0F172A;">{urgency} / 5</td></tr>'
        f'<tr><td style="padding:3px 12px 3px 0;color:#92400E;font-weight:600;">Category</td>'
        f'<td style="padding:3px 8px;color:#0F172A;">{category}</td></tr>'
        f'<tr><td style="padding:3px 12px 3px 0;color:#92400E;font-weight:600;">Market</td>'
        f'<td style="padding:3px 8px;color:#0F172A;">{market}</td></tr>'
        f'</table></div>'
    )


def hitl_result_card_html(decision: str, action_taken: str) -> str:
    if decision == "approved":
        border, bg, title = "#10B981", "#F0FDF4", "#059669"
        badge_bg, badge_color = "#DCFCE7", "#059669"
        badge_text = "✅ Action Approved"
        msg = "The human reviewer approved the action. Pipeline resumed."
    elif decision == "rejected":
        border, bg, title = "#F59E0B", "#FFFBEB", "#B45309"
        badge_bg, badge_color = "#FEF3C7", "#B45309"
        badge_text = "⚠️ Rejected — Escalated"
        msg = "Case escalated to a human representative. Automated action not executed."
    else:
        return ""

    act_safe = str(action_taken).replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<div style="border-left:3px solid {border};border-radius:10px;'
        f'padding:1.1rem 1.25rem;margin-bottom:0.75rem;background:{bg};'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
        f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">'
        f'<span style="background:{badge_bg};color:{badge_color};padding:3px 10px;'
        f'border-radius:999px;font-size:0.72rem;font-weight:600;">'
        f'⚖️ Human Governance — Decision Recorded</span>'
        f'<span style="margin-left:auto;background:{badge_bg};color:{badge_color};'
        f'padding:2px 9px;border-radius:999px;font-size:0.7rem;font-weight:600;">{badge_text}</span>'
        f'</div>'
        f'<p style="color:{title};font-size:0.78rem;margin:0 0 0.2rem 0;">{msg}</p>'
        f'<p style="color:#64748B;font-size:0.75rem;margin:0;">'
        f'Proposed action: <strong>{act_safe}</strong></p>'
        f'</div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────────────────────
_defaults = {
    "mode":              "Live Demo",
    # Single-signal pipeline state
    "signal":            None,
    "pipeline_complete": False,
    "pipeline_results":  {},
    "pipeline_status":   "idle",
    "hitl_triggered":    False,
    "hitl_approved":     None,
    "hitl_decision":     "not_triggered",
    "pipeline_paused":   False,
    # Live Demo state
    "demo_running":      False,
    "demo_complete":     False,
    "demo_results":      [],
    "demo_progress":     0,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline execution — single-signal (Quick Generate / Manual Input)
# ─────────────────────────────────────────────────────────────────────────────

def _run_post_hitl_agents(signal, detection_result, resolution_result,
                          pattern_risk, frontline_gap, hitl_decision,
                          slot_eea, slot_ir, slot_ln):
    """EEA → Insight Routing → Learning. Shared by normal path and post-HITL path."""
    eea_result = None
    if frontline_gap:
        slot_eea.markdown(running_card_html("Employee Enablement Agent"), unsafe_allow_html=True)
        with st.spinner("Employee Enablement Agent running…"):
            eea_result = run_async(employee_enablement_agent(resolution_result))
        slot_eea.markdown(agent_card_html("Employee Enablement Agent", eea_result, True),
                          unsafe_allow_html=True)
    else:
        slot_eea.markdown(agent_card_html("Employee Enablement Agent", None, False),
                          unsafe_allow_html=True)

    insight_result = None
    if pattern_risk in ("medium", "high"):
        slot_ir.markdown(running_card_html("Insight Routing Agent"), unsafe_allow_html=True)
        with st.spinner("Insight Routing Agent running…"):
            insight_result = run_async(insight_routing_agent(detection_result))
        slot_ir.markdown(agent_card_html("Insight Routing Agent", insight_result, True),
                         unsafe_allow_html=True)
    else:
        slot_ir.markdown(agent_card_html("Insight Routing Agent", None, False),
                         unsafe_allow_html=True)

    hitl_triggered_flag = (hitl_decision != "not_triggered")
    learning_input = json.dumps({
        "market":                     signal.get("market", "Unknown"),
        "source":                     signal.get("source", "unknown"),
        "category":                   signal.get("category", "other"),
        "urgency_score":              signal.get("urgency_score", 3),
        "original_signal":            signal["query"],
        "signal_detection_output":    detection_result,
        "resolution_output":          resolution_result,
        "employee_enablement_output": eea_result,
        "insight_routing_output":     insight_result,
        "hitl_triggered":             hitl_triggered_flag,
        "hitl_decision":              hitl_decision,
        "hitl_action_proposed":       st.session_state.get("_partial_action", ""),
        **({"hitl_override_note":
            "Human reviewer rejected the automated action. Case escalated to human rep."}
           if hitl_decision == "rejected" else {}),
    })

    slot_ln.markdown(running_card_html("Learning and Insights Agent"), unsafe_allow_html=True)
    with st.spinner("Learning and Insights Agent running…"):
        learning_result = run_async(learning_insights_agent(learning_input))
    slot_ln.markdown(agent_card_html("Learning and Insights Agent", learning_result, True),
                     unsafe_allow_html=True)

    return eea_result, insight_result, learning_result


def run_pipeline_ui(signal: dict) -> None:
    """
    Phase 1 of the single-signal pipeline. Runs Signal Detection → Resolution.
    If requires_human=true, stores partial state and calls st.rerun() to show
    the HITL governance card. Otherwise, continues to EEA → IR → Learning.
    """
    st.markdown(
        '<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:0.75rem;">'
        '🤖 Agent Pipeline</h3>', unsafe_allow_html=True)

    slot_sd   = st.empty()
    slot_res  = st.empty()
    slot_hitl = st.empty()
    slot_eea  = st.empty()
    slot_ir   = st.empty()
    slot_ln   = st.empty()

    for slot, name in [(slot_sd,  "Signal Detection Agent"),
                       (slot_res, "Resolution Agent"),
                       (slot_eea, "Employee Enablement Agent"),
                       (slot_ir,  "Insight Routing Agent"),
                       (slot_ln,  "Learning and Insights Agent")]:
        slot.markdown(pending_card_html(name), unsafe_allow_html=True)

    # Step 1 — Signal Detection
    slot_sd.markdown(running_card_html("Signal Detection Agent"), unsafe_allow_html=True)
    with st.spinner("Signal Detection Agent running…"):
        detection_result = run_async(signal_detection_agent(signal["query"]))
    slot_sd.markdown(agent_card_html("Signal Detection Agent", detection_result, True),
                     unsafe_allow_html=True)

    try:
        det_json     = json.loads(detection_result)
        pattern_risk = str(det_json.get("pattern_risk", "low")).lower().strip()
    except (json.JSONDecodeError, AttributeError):
        pattern_risk = "low"

    # Step 2 — Resolution
    slot_res.markdown(running_card_html("Resolution Agent"), unsafe_allow_html=True)
    with st.spinner("Resolution Agent running…"):
        resolution_result = run_async(resolution_agent(detection_result))
    slot_res.markdown(agent_card_html("Resolution Agent", resolution_result, True),
                      unsafe_allow_html=True)

    try:
        res_json       = json.loads(resolution_result)
        frontline_gap  = bool(res_json.get("frontline_gap_detected", False))
        requires_human = bool(res_json.get("requires_human", False))
        action_taken   = res_json.get("action_taken", "unknown")
        customer_msg   = res_json.get("customer_message", "N/A")
    except (json.JSONDecodeError, AttributeError):
        frontline_gap  = False
        requires_human = False
        action_taken   = "unknown"
        customer_msg   = "N/A"

    # HITL check
    if requires_human:
        slot_hitl.markdown(
            '<div style="padding:0.6rem 1rem;background:#FEF3C7;border-radius:8px;'
            'color:#B45309;font-size:0.82rem;font-weight:600;">⏳ Awaiting human approval…</div>',
            unsafe_allow_html=True,
        )
        st.session_state._partial_detection     = detection_result
        st.session_state._partial_resolution    = resolution_result
        st.session_state._partial_pattern_risk  = pattern_risk
        st.session_state._partial_frontline_gap = frontline_gap
        st.session_state._partial_action        = action_taken
        st.session_state._partial_customer_msg  = customer_msg
        st.session_state.hitl_triggered         = True
        st.session_state.pipeline_paused        = True
        st.session_state.hitl_decision          = "not_triggered"
        st.session_state.pipeline_status        = "paused_hitl"
        st.rerun()
        return

    # Non-HITL path
    eea_result, insight_result, learning_result = _run_post_hitl_agents(
        signal, detection_result, resolution_result,
        pattern_risk, frontline_gap, "not_triggered",
        slot_eea, slot_ir, slot_ln,
    )

    st.session_state.pipeline_results = {
        "signal_detection_output":    detection_result,
        "resolution_output":          resolution_result,
        "employee_enablement_output": eea_result,
        "insight_routing_output":     insight_result,
        "learning_output":            learning_result,
        "_meta_pattern_risk":         pattern_risk,
        "_meta_frontline_gap":        frontline_gap,
        "_meta_hitl_triggered":       False,
        "_meta_hitl_decision":        "not_triggered",
        "_meta_hitl_action":          "",
    }
    st.session_state.pipeline_complete = True
    st.session_state.pipeline_status   = "complete"


def render_hitl_paused_ui() -> None:
    """Show HITL governance card with Approve / Reject buttons."""
    st.markdown(
        '<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:0.75rem;">'
        '🤖 Agent Pipeline</h3>', unsafe_allow_html=True)

    st.markdown(agent_card_html("Signal Detection Agent",
                                st.session_state._partial_detection, True),
                unsafe_allow_html=True)
    st.markdown(agent_card_html("Resolution Agent",
                                st.session_state._partial_resolution, True),
                unsafe_allow_html=True)
    st.markdown(
        hitl_governance_card_html(
            st.session_state._partial_action,
            st.session_state._partial_customer_msg,
            st.session_state.signal,
        ),
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(
            '<div style="background:#DCFCE7;border-radius:6px;padding:4px 8px;'
            'font-size:0.7rem;color:#059669;font-weight:600;margin-bottom:4px;">'
            '✅ Execute the proposed action</div>', unsafe_allow_html=True)
        approve = st.button("Approve Action", key="hitl_approve_btn",
                            use_container_width=True, type="primary")
    with col2:
        st.markdown(
            '<div style="background:#FEF3C7;border-radius:6px;padding:4px 8px;'
            'font-size:0.7rem;color:#B45309;font-weight:600;margin-bottom:4px;">'
            '⚠️ Escalate to human rep</div>', unsafe_allow_html=True)
        reject = st.button("Reject / Escalate", key="hitl_reject_btn",
                           use_container_width=True)

    if approve:
        st.session_state.hitl_decision   = "approved"
        st.session_state.hitl_approved   = True
        st.session_state.pipeline_paused = False
        st.session_state.pipeline_status = "idle"
    if reject:
        st.session_state.hitl_decision   = "rejected"
        st.session_state.hitl_approved   = False
        st.session_state.pipeline_paused = False
        st.session_state.pipeline_status = "idle"

    for name in ("Employee Enablement Agent", "Insight Routing Agent",
                 "Learning and Insights Agent"):
        st.markdown(pending_card_html(name), unsafe_allow_html=True)


def run_pipeline_phase2(signal: dict) -> None:
    """Phase 2: continue pipeline after HITL decision."""
    st.markdown(
        '<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:0.75rem;">'
        '🤖 Agent Pipeline</h3>', unsafe_allow_html=True)

    decision          = st.session_state.hitl_decision
    detection_result  = st.session_state._partial_detection
    resolution_result = st.session_state._partial_resolution
    pattern_risk      = st.session_state._partial_pattern_risk
    frontline_gap     = st.session_state._partial_frontline_gap
    action_taken      = st.session_state._partial_action

    st.markdown(agent_card_html("Signal Detection Agent", detection_result, True),
                unsafe_allow_html=True)
    st.markdown(agent_card_html("Resolution Agent", resolution_result, True),
                unsafe_allow_html=True)
    st.markdown(hitl_result_card_html(decision, action_taken), unsafe_allow_html=True)

    if decision == "approved":
        st.success("✅ Action approved. Continuing pipeline…")
    else:
        st.warning(
            "⚠️ Case escalated to a human representative. "
            "The Learning Agent will record this override to improve future routing."
        )

    slot_eea = st.empty()
    slot_ir  = st.empty()
    slot_ln  = st.empty()
    for slot, name in [(slot_eea, "Employee Enablement Agent"),
                       (slot_ir,  "Insight Routing Agent"),
                       (slot_ln,  "Learning and Insights Agent")]:
        slot.markdown(pending_card_html(name), unsafe_allow_html=True)

    eea_result, insight_result, learning_result = _run_post_hitl_agents(
        signal, detection_result, resolution_result,
        pattern_risk, frontline_gap, decision,
        slot_eea, slot_ir, slot_ln,
    )

    st.session_state.pipeline_results = {
        "signal_detection_output":    detection_result,
        "resolution_output":          resolution_result,
        "employee_enablement_output": eea_result,
        "insight_routing_output":     insight_result,
        "learning_output":            learning_result,
        "_meta_pattern_risk":         pattern_risk,
        "_meta_frontline_gap":        frontline_gap,
        "_meta_hitl_triggered":       True,
        "_meta_hitl_decision":        decision,
        "_meta_hitl_action":          action_taken,
    }
    st.session_state.pipeline_complete = True
    st.session_state.pipeline_status   = "complete"


def display_pipeline_from_state(results: dict) -> None:
    """Re-render all agent cards from stored session state."""
    st.markdown(
        '<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:0.75rem;">'
        '🤖 Agent Pipeline</h3>', unsafe_allow_html=True)

    st.markdown(agent_card_html("Signal Detection Agent",
                                results.get("signal_detection_output"), True),
                unsafe_allow_html=True)
    st.markdown(agent_card_html("Resolution Agent",
                                results.get("resolution_output"), True),
                unsafe_allow_html=True)

    if results.get("_meta_hitl_triggered"):
        st.markdown(
            hitl_result_card_html(
                results.get("_meta_hitl_decision", ""),
                results.get("_meta_hitl_action", ""),
            ),
            unsafe_allow_html=True,
        )

    for name, key in [("Employee Enablement Agent", "employee_enablement_output"),
                      ("Insight Routing Agent",      "insight_routing_output")]:
        r = results.get(key)
        st.markdown(agent_card_html(name, r, triggered=(r is not None)),
                    unsafe_allow_html=True)

    st.markdown(agent_card_html("Learning and Insights Agent",
                                results.get("learning_output"), True),
                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# LIVE DEMO MODE — pipeline runner (no HITL pause, fully automatic)
# ─────────────────────────────────────────────────────────────────────────────

def _run_live_demo() -> None:
    """
    Generate 5 signals via generate_demo_set() and run each fully through
    the pipeline. HITL is not paused — requires_human is noted but the
    pipeline continues automatically (appropriate for a presentation).
    """
    st.markdown("---")

    with st.spinner("Generating 5 demo signals via AI…"):
        signals = run_async(generate_demo_set())

    progress_bar = st.progress(0)
    step_slot    = st.empty()
    all_results  = []

    for i, signal in enumerate(signals, 1):
        # Update step indicator and progress bar
        step_slot.markdown(step_indicator_html(i, 5), unsafe_allow_html=True)
        progress_bar.progress(i / 5)

        # Signal header
        st.markdown(
            f'<div style="background:#F5F3FF;border-radius:8px;padding:0.65rem 1rem;'
            f'margin-bottom:0.75rem;display:flex;align-items:center;gap:0.75rem;">'
            f'<span style="background:#6D28D9;color:white;padding:2px 10px;border-radius:999px;'
            f'font-size:0.75rem;font-weight:700;">Signal {i} of 5</span>'
            f'<span style="color:#64748B;font-size:0.82rem;">{signal.get("label","")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Compact signal preview
        urg = signal.get("urgency_score", 3)
        ut, ubg = urgency_color(urg)
        q = signal.get("query", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        q_short = (q[:200] + "…") if len(q) > 200 else q
        st.markdown(
            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;'
            f'padding:0.65rem 1rem;margin-bottom:0.75rem;">'
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:0.4rem;">'
            f'<span style="background:#DBEAFE;color:#1D4ED8;padding:2px 9px;border-radius:999px;font-size:0.7rem;font-weight:600;">🌍 {signal.get("market","")}</span>'
            f'<span style="background:#EDE9FE;color:#6D28D9;padding:2px 9px;border-radius:999px;font-size:0.7rem;font-weight:600;">🏷️ {signal.get("category","").replace("_"," ").title()}</span>'
            f'<span style="background:{ubg};color:{ut};padding:2px 9px;border-radius:999px;font-size:0.7rem;font-weight:700;">⚡ Urgency {urg}</span>'
            f'</div>'
            f'<p style="color:#334155;font-size:0.78rem;margin:0;line-height:1.5;">{q_short}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Agent slots
        slot_sd  = st.empty()
        slot_res = st.empty()
        slot_eea = st.empty()
        slot_ir  = st.empty()
        slot_ln  = st.empty()
        for slot, name in [(slot_sd,  "Signal Detection Agent"),
                           (slot_res, "Resolution Agent"),
                           (slot_eea, "Employee Enablement Agent"),
                           (slot_ir,  "Insight Routing Agent"),
                           (slot_ln,  "Learning and Insights Agent")]:
            slot.markdown(pending_card_html(name), unsafe_allow_html=True)

        # Signal Detection
        slot_sd.markdown(running_card_html("Signal Detection Agent"), unsafe_allow_html=True)
        detection_result = run_async(signal_detection_agent(signal["query"]))
        slot_sd.markdown(agent_card_html("Signal Detection Agent", detection_result, True),
                         unsafe_allow_html=True)

        try:
            pattern_risk = str(json.loads(detection_result).get("pattern_risk", "low")).lower()
        except Exception:
            pattern_risk = "low"

        # Resolution
        slot_res.markdown(running_card_html("Resolution Agent"), unsafe_allow_html=True)
        resolution_result = run_async(resolution_agent(detection_result))
        slot_res.markdown(agent_card_html("Resolution Agent", resolution_result, True),
                          unsafe_allow_html=True)

        try:
            res_json       = json.loads(resolution_result)
            frontline_gap  = bool(res_json.get("frontline_gap_detected", False))
            requires_human = bool(res_json.get("requires_human", False))
            action_taken   = res_json.get("action_taken", "")
        except Exception:
            frontline_gap  = False
            requires_human = False
            action_taken   = ""

        # Employee Enablement
        eea_result = None
        if frontline_gap:
            slot_eea.markdown(running_card_html("Employee Enablement Agent"),
                              unsafe_allow_html=True)
            eea_result = run_async(employee_enablement_agent(resolution_result))
            slot_eea.markdown(agent_card_html("Employee Enablement Agent", eea_result, True),
                              unsafe_allow_html=True)
        else:
            slot_eea.markdown(agent_card_html("Employee Enablement Agent", None, False),
                              unsafe_allow_html=True)

        # Insight Routing
        insight_result = None
        if pattern_risk in ("medium", "high"):
            slot_ir.markdown(running_card_html("Insight Routing Agent"), unsafe_allow_html=True)
            insight_result = run_async(insight_routing_agent(detection_result))
            slot_ir.markdown(agent_card_html("Insight Routing Agent", insight_result, True),
                             unsafe_allow_html=True)
        else:
            slot_ir.markdown(agent_card_html("Insight Routing Agent", None, False),
                             unsafe_allow_html=True)

        # Learning
        learning_input = json.dumps({
            "market":                     signal.get("market", "Unknown"),
            "source":                     signal.get("source", "unknown"),
            "category":                   signal.get("category", "other"),
            "urgency_score":              signal.get("urgency_score", 3),
            "original_signal":            signal["query"],
            "signal_detection_output":    detection_result,
            "resolution_output":          resolution_result,
            "employee_enablement_output": eea_result,
            "insight_routing_output":     insight_result,
            "hitl_triggered":             requires_human,
            "hitl_decision":              "auto_approved_demo" if requires_human else "not_triggered",
            "hitl_action_proposed":       action_taken,
        })
        slot_ln.markdown(running_card_html("Learning and Insights Agent"), unsafe_allow_html=True)
        learning_result = run_async(learning_insights_agent(learning_input))
        slot_ln.markdown(agent_card_html("Learning and Insights Agent", learning_result, True),
                         unsafe_allow_html=True)

        all_results.append({
            "signal":                      signal,
            "signal_detection_output":     detection_result,
            "resolution_output":           resolution_result,
            "employee_enablement_output":  eea_result,
            "insight_routing_output":      insight_result,
            "learning_output":             learning_result,
            "_meta_pattern_risk":          pattern_risk,
            "_meta_frontline_gap":         frontline_gap,
            "_meta_hitl_triggered":        requires_human,
            "_meta_hitl_decision":         "auto_approved" if requires_human else "not_triggered",
            "_meta_hitl_action":           action_taken,
        })

        if i < len(signals):
            st.markdown(
                '<hr style="border:none;border-top:2px solid #EDE9FE;margin:1.25rem 0;">',
                unsafe_allow_html=True,
            )

    # All done
    step_slot.markdown(step_indicator_html(6, 5), unsafe_allow_html=True)  # current>total = all ✓
    progress_bar.progress(1.0)
    st.session_state.demo_results  = all_results
    st.session_state.demo_complete = True
    st.rerun()


def render_live_demo_ui() -> None:
    """Render Live Demo mode — intro card, signal table, start button, or completion state."""
    # Intro header card
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1E1B4B 0%,#4C1D95 100%);'
        'border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;">'
        '<h2 style="color:white;margin:0 0 0.2rem 0;font-size:1.05rem;font-weight:700;">'
        '🎬 Live Demo — Cosmic Pulse in Action</h2>'
        '<p style="color:#C4B5FD;margin:0;font-size:0.82rem;">'
        '5 pre-built signals covering all routing paths. '
        'Runs automatically from start to finish.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Signal preview table
    urgency_cell = lambda u: (
        f'<span style="background:{"#FEE2E2" if u>=4 else "#FEF3C7" if u==3 else "#DCFCE7"};'
        f'color:{"#DC2626" if u>=4 else "#D97706" if u==3 else "#059669"};'
        f'padding:2px 9px;border-radius:999px;font-size:0.72rem;font-weight:700;">{u}</span>'
    )
    rows_html = "".join(
        f'<tr style="border-top:1px solid #E2E8F0;">'
        f'<td style="padding:7px 12px;color:#64748B;font-weight:600;">{n}</td>'
        f'<td style="padding:7px 12px;color:#0F172A;font-weight:500;">{m}</td>'
        f'<td style="padding:7px 12px;color:#0F172A;">{c.replace("_"," ").title()}</td>'
        f'<td style="padding:7px 12px;">{urgency_cell(u)}</td>'
        f'</tr>'
        for n, m, c, u in DEMO_SIGNALS_META
    )
    st.markdown(
        '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;'
        'background:white;border-radius:10px;overflow:hidden;'
        'box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-bottom:1rem;">'
        '<thead><tr style="background:#F5F3FF;">'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">#</th>'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">Market</th>'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">Category</th>'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">Urgency</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody></table>',
        unsafe_allow_html=True,
    )

    if not st.session_state.demo_complete:
        if st.button("🚀 Start Live Demo", use_container_width=True,
                     type="primary", key="start_demo_btn"):
            _run_live_demo()
    else:
        # Completion banner
        st.markdown(
            '<div style="background:#F0FDF4;border:1px solid #10B981;border-radius:10px;'
            'padding:1rem 1.5rem;margin-bottom:1rem;display:flex;align-items:center;gap:0.75rem;">'
            '<span style="font-size:1.4rem;">🎉</span>'
            '<div>'
            '<div style="font-weight:700;color:#059669;font-size:0.95rem;">'
            'Live Demo Complete — 5 signals processed</div>'
            '<div style="font-size:0.78rem;color:#64748B;margin-top:2px;">'
            'Switch to the Results tab to browse all outputs.</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        # Summary table
        results = st.session_state.demo_results
        if results:
            sum_rows = ""
            for idx, r in enumerate(results, 1):
                sig = r.get("signal", {})
                agents = sum([
                    1,
                    1,
                    1 if r.get("employee_enablement_output") else 0,
                    1 if r.get("insight_routing_output") else 0,
                    1,
                ])
                hitl = "Yes" if r.get("_meta_hitl_triggered") else "No"
                sum_rows += (
                    f'<tr style="border-top:1px solid #E2E8F0;">'
                    f'<td style="padding:7px 12px;color:#64748B;">{idx}</td>'
                    f'<td style="padding:7px 12px;color:#0F172A;">{sig.get("market","—")}</td>'
                    f'<td style="padding:7px 12px;color:#0F172A;">'
                    f'{sig.get("category","—").replace("_"," ").title()}</td>'
                    f'<td style="padding:7px 12px;text-align:center;">'
                    f'<span style="background:#EDE9FE;color:#6D28D9;padding:2px 9px;'
                    f'border-radius:999px;font-size:0.72rem;font-weight:600;">{agents}</span></td>'
                    f'<td style="padding:7px 12px;">'
                    f'<span style="background:{"#FEF3C7" if hitl=="Yes" else "#F1F5F9"};'
                    f'color:{"#B45309" if hitl=="Yes" else "#64748B"};padding:2px 9px;'
                    f'border-radius:999px;font-size:0.72rem;font-weight:600;">{hitl}</span>'
                    f'</td></tr>'
                )
            st.markdown(
                '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;'
                'background:white;border-radius:10px;overflow:hidden;'
                'box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-bottom:1rem;">'
                '<thead><tr style="background:#F5F3FF;">'
                '<th style="padding:8px 12px;text-align:left;color:#6D28D9;">#</th>'
                '<th style="padding:8px 12px;text-align:left;color:#6D28D9;">Market</th>'
                '<th style="padding:8px 12px;text-align:left;color:#6D28D9;">Category</th>'
                '<th style="padding:8px 12px;text-align:center;color:#6D28D9;">Agents</th>'
                '<th style="padding:8px 12px;text-align:left;color:#6D28D9;">HITL</th>'
                '</tr></thead>'
                f'<tbody>{sum_rows}</tbody></table>',
                unsafe_allow_html=True,
            )

        if st.button("🔄 Run Demo Again", use_container_width=True, key="run_demo_again_btn"):
            st.session_state.demo_complete = False
            st.session_state.demo_results  = []
            st.session_state.demo_progress = 0
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def render_signal_preview(signal: dict) -> None:
    st.markdown(
        '<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:0.65rem;">'
        '📡 Signal Preview</h3>', unsafe_allow_html=True)

    urg = signal.get("urgency_score", 3)
    urg_text, urg_bg = urgency_color(urg)
    src = signal.get("source", "unknown").replace("_", " ").title()
    cat = signal.get("category", "other").replace("_", " ").title()
    mkt = signal.get("market", "Unknown")
    q   = (signal.get("query", "")
           .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    st.markdown(
        f'<div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:0.65rem;">'
        f'<span style="background:#DBEAFE;color:#1D4ED8;padding:3px 11px;border-radius:999px;font-size:0.75rem;font-weight:600;">🌍 {mkt}</span>'
        f'<span style="background:#EDE9FE;color:#6D28D9;padding:3px 11px;border-radius:999px;font-size:0.75rem;font-weight:600;">📡 {src}</span>'
        f'<span style="background:#F0FDF4;color:#059669;padding:3px 11px;border-radius:999px;font-size:0.75rem;font-weight:600;">🏷️ {cat}</span>'
        f'<span style="background:{urg_bg};color:{urg_text};padding:3px 11px;border-radius:999px;font-size:0.75rem;font-weight:700;">⚡ Urgency {urg}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;'
        f'padding:0.9rem 1.1rem;font-size:0.875rem;line-height:1.75;color:#0F172A;">{q}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)


def render_cxo_dashboard(learning_result_str: str) -> None:
    """MODERN UI — gradient CXO dashboard card."""
    try:
        data = json.loads(learning_result_str) if learning_result_str else {}
    except json.JSONDecodeError:
        st.warning("⚠️ Could not parse Learning Agent output.")
        st.code(learning_result_str or "", language="json")
        return

    cxo = data.get("cxo_insight", {})
    if isinstance(cxo, str):
        try:
            cxo = json.loads(cxo)
        except Exception:
            cxo = {}

    sentiment = str(cxo.get("sentiment_trend", "stable")).lower().strip()
    cost      = str(cxo.get("cost_trend", "stable")).lower().strip()
    demand    = str(cxo.get("demand_signal", "No demand signal available"))
    dd        = (demand[:120] + "…") if len(demand) > 123 else demand

    sp = {"deteriorating": ("#DC2626", "📉"), "improving": ("#059669", "📈"),
          "stable": ("#D97706", "➡️")}
    cp = {"increasing": ("#DC2626", "💸"), "decreasing": ("#059669", "💰"),
          "stable": ("#D97706", "💵")}
    sc, si = sp.get(sentiment, ("#64748B", "📊"))
    cc, ci = cp.get(cost,      ("#64748B", "💵"))

    def _metric(icon, label, value, color):
        return (
            f'<div style="background:rgba(255,255,255,0.95);border-radius:8px;'
            f'padding:1rem;text-align:center;">'
            f'<div style="font-size:1.5rem;margin-bottom:0.25rem;">{icon}</div>'
            f'<div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:0.25rem;">{label}</div>'
            f'<div style="font-size:0.85rem;font-weight:600;color:{color};">{value}</div>'
            f'</div>'
        )

    tags   = data.get("tags", [])
    risk   = str(data.get("repeat_risk", "low")).lower()
    rc_map = {"high": ("#DC2626", "rgba(254,226,226,0.9)"),
              "medium": ("#D97706", "rgba(254,243,199,0.9)"),
              "low": ("#059669", "rgba(220,252,231,0.9)")}
    rc, rbg = rc_map.get(risk, ("#64748B", "rgba(241,245,249,0.9)"))

    tags_html = "".join(
        f'<span style="background:rgba(255,255,255,0.18);color:white;padding:2px 9px;'
        f'border-radius:999px;font-size:0.7rem;margin:2px;display:inline-block;">{t}</span>'
        for t in (tags if isinstance(tags, list) else [])
    )

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1E1B4B 0%,#4C1D95 100%);'
        f'border-radius:12px;padding:1.5rem;margin-top:1.25rem;">'
        f'<h3 style="color:white;margin:0 0 1rem 0;font-size:0.78rem;font-weight:600;'
        f'letter-spacing:0.1em;text-transform:uppercase;">📊 CXO Visibility Dashboard</h3>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.75rem;">'
        + _metric(si, "Customer Sentiment", sentiment.title(), sc)
        + _metric(ci, "Cost to Serve", cost.title(), cc)
        + _metric("📊", "Demand Signal", dd, "#0F172A")
        + f'</div>'
        f'<div style="margin-top:1rem;display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">'
        f'<span style="background:{rbg};color:{rc};padding:3px 12px;border-radius:999px;'
        f'font-size:0.75rem;font-weight:700;">Repeat Risk: {risk.upper()}</span>'
        f'{tags_html}'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)


def render_results_tab(results, demo_results=None) -> None:
    """Results tab — handles both single-signal and Live Demo (all 5) results."""
    if demo_results:
        st.markdown(
            '<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:1rem;">'
            '📋 Live Demo — All 5 Signal Outputs</h3>', unsafe_allow_html=True)

        for i, r in enumerate(demo_results, 1):
            sig   = r.get("signal", {})
            label = (
                f"Signal {i} — {sig.get('market','?')} / "
                f"{sig.get('category','?').replace('_',' ').title()} / "
                f"Urgency {sig.get('urgency_score','?')}"
            )
            with st.expander(label, expanded=(i == 1)):
                for lbl, key in [
                    ("🔵 Signal Detection Agent",     "signal_detection_output"),
                    ("🟢 Resolution Agent",            "resolution_output"),
                    ("🩵 Employee Enablement Agent",   "employee_enablement_output"),
                    ("🔷 Insight Routing Agent",       "insight_routing_output"),
                    ("🟣 Learning and Insights Agent", "learning_output"),
                ]:
                    raw = r.get(key)
                    if raw:
                        with st.expander(lbl, expanded=False):
                            try:
                                st.json(json.loads(raw))
                            except Exception:
                                st.code(raw)
                    else:
                        with st.expander(f"{lbl} — not triggered", expanded=False):
                            st.caption("Not triggered for this signal.")
        return

    if not results:
        st.info("Run the pipeline first to see full agent outputs here.", icon="📋")
        return

    st.markdown(
        '<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:1rem;">'
        '📋 Full Agent Outputs</h3>', unsafe_allow_html=True)

    for label, key in [
        ("🔵 Signal Detection Agent",     "signal_detection_output"),
        ("🟢 Resolution Agent",            "resolution_output"),
        ("🩵 Employee Enablement Agent",   "employee_enablement_output"),
        ("🔷 Insight Routing Agent",       "insight_routing_output"),
        ("🟣 Learning and Insights Agent", "learning_output"),
    ]:
        raw = results.get(key)
        if raw:
            with st.expander(label, expanded=False):
                try:
                    st.json(json.loads(raw))
                except Exception:
                    st.code(raw)
        else:
            with st.expander(f"{label} — not triggered", expanded=False):
                st.caption("This agent was not invoked for this signal.")

    if results.get("_meta_hitl_triggered"):
        st.markdown("---")
        st.markdown("**⚖️ Human Governance Record**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Decision",
                  results.get("_meta_hitl_decision", "—").replace("_", " ").title())
        c2.metric("Action Proposed", results.get("_meta_hitl_action", "—"))
        c3.metric("HITL Triggered", "Yes")


def render_about_tab() -> None:
    st.markdown(
        '<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:1rem;">'
        '🌌 About Cosmic Pulse</h3>', unsafe_allow_html=True)
    st.markdown("""
Cosmic Pulse is a multi-agent AI system that orchestrates customer experience
signals for **Cosmic Mart**, a global retail brand with **144 million customers**
across 10 markets. Built with the **Accenture AI Refinery SDK**.

---

#### Agent Pipeline
| Agent | Trigger | Purpose |
|---|---|---|
| 🔵 Signal Detection | Always | Classifies signal: source, sentiment, category, urgency, pattern risk |
| 🟢 Resolution | Always | Determines action, writes customer message, detects frontline gaps |
| ⚖️ Human Governance | `requires_human = true` | Pauses pipeline for human Approve / Reject |
| 🩵 Employee Enablement | `frontline_gap_detected = true` | Just-in-time policy guidance for frontline staff |
| 🔷 Insight Routing | `pattern_risk = medium/high` | Routes pattern brief to correct business team |
| 🟣 Learning & Insights | Always last | Updates playbooks, produces CXO dashboard signals |

---

#### Demo Modes
- **🎬 Live Demo** — Auto-runs 5 pre-built signals. Best for judge presentations. No HITL pause.
- **⚡ Quick Generate** — Pick parameters, generate one signal. HITL triggers if `requires_human=true`.
- **✏️ Manual Input** — Paste real customer feedback and run the full pipeline.

---

#### HITL Demo Tips *(Quick Generate mode)*
Set **North America / service_delay / Urgency 5** to reliably trigger `requires_human: true`.
Click **Approve** → pipeline resumes. Click **Reject** → escalation path + Learning Agent records override.

---

#### Routing Rules
```
urgency_score 4 or 5          → Resolution Agent (always in this build)
requires_human = true          → Human Governance pause (Quick/Manual only)
frontline_gap_detected = true  → Employee Enablement Agent
pattern_risk = medium or high  → Insight Routing Agent
Always last                    → Learning and Insights Agent
```
    """)


# ─────────────────────────────────────────────────────────────────────────────
# MODERN UI — Page header bar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:linear-gradient(135deg,#1E1B4B 0%,#6D28D9 100%);'
    'padding:1.1rem 1.5rem;border-radius:12px;margin-bottom:1.25rem;'
    'display:flex;align-items:center;gap:1rem;">'
    '<div style="width:42px;height:42px;background:rgba(255,255,255,0.15);border-radius:10px;'
    'display:flex;align-items:center;justify-content:center;'
    'font-size:1.3rem;flex-shrink:0;">🌌</div>'
    '<div>'
    '<h1 style="color:white;margin:0;font-size:1.35rem;font-weight:700;'
    'letter-spacing:-0.02em;">Cosmic Pulse</h1>'
    '<p style="color:#C4B5FD;margin:0;font-size:0.78rem;">'
    'Customer Experience Orchestration — Cosmic Mart</p>'
    '</div>'
    '<div style="margin-left:auto;flex-shrink:0;">'
    '<span style="background:rgba(255,255,255,0.12);color:white;padding:4px 12px;'
    'border-radius:999px;font-size:0.7rem;font-weight:500;">'
    'Powered by Accenture AI Refinery</span>'
    '</div></div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Two-column layout: control panel | tabs
# ─────────────────────────────────────────────────────────────────────────────
col_ctrl, col_main = st.columns([1, 2.6], gap="large")

# ── Left column — control panel ───────────────────────────────────────────────
with col_ctrl:
    st.markdown(
        '<div style="background:#1E1B4B;border-radius:12px;padding:1rem 0.9rem 0.25rem 0.9rem;">'
        '<p style="color:#C4B5FD;font-size:0.65rem;font-weight:700;'
        'text-transform:uppercase;letter-spacing:0.1em;margin:0 0 0.6rem 0;">MODE</p>',
        unsafe_allow_html=True,
    )

    # MODERN UI — pill mode selector
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        if st.button("🎬 Live", use_container_width=True, key="mode_live",
                     type="primary" if st.session_state.mode == "Live Demo" else "secondary"):
            if st.session_state.mode != "Live Demo":
                st.session_state.mode = "Live Demo"
                st.rerun()
    with mc2:
        if st.button("⚡ Quick", use_container_width=True, key="mode_quick",
                     type="primary" if st.session_state.mode == "Quick Generate" else "secondary"):
            if st.session_state.mode != "Quick Generate":
                st.session_state.mode = "Quick Generate"
                st.rerun()
    with mc3:
        if st.button("✏️ Manual", use_container_width=True, key="mode_manual",
                     type="primary" if st.session_state.mode == "Manual Input" else "secondary"):
            if st.session_state.mode != "Manual Input":
                st.session_state.mode = "Manual Input"
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")

    run_clicked = False

    # ── Mode-specific controls ────────────────────────────────────────────────
    if st.session_state.mode == "Live Demo":
        st.markdown(
            '<p style="font-size:0.8rem;color:#64748B;line-height:1.6;margin:0;">'
            'Runs 5 pre-built signals automatically. '
            'Perfect for judge presentations — no manual steps needed.</p>',
            unsafe_allow_html=True,
        )

    elif st.session_state.mode == "Quick Generate":
        market   = st.selectbox("Market",   MARKETS,    key="ld_market")
        source   = st.selectbox("Source",   SOURCES,    key="ld_source")
        category = st.selectbox("Category", CATEGORIES, key="ld_category")
        urgency  = st.slider("Urgency", 1, 5, 3, key="ld_urgency")

        if st.button("🎲 Generate Signal", use_container_width=True, key="gen_btn"):
            with st.spinner("Generating…"):
                gen = run_async(generate_signal(market, source, category, urgency))
            st.session_state.signal            = gen
            st.session_state.pipeline_complete = False
            st.session_state.pipeline_results  = {}
            st.session_state.hitl_triggered    = False
            st.session_state.hitl_approved     = None
            st.session_state.hitl_decision     = "not_triggered"
            st.session_state.pipeline_paused   = False
            st.session_state.pipeline_status   = "idle"
            st.success("✓ Signal ready")

        st.markdown("---")
        run_clicked = st.button(
            "🚀 Run Pipeline",
            use_container_width=True,
            type="primary",
            disabled=(st.session_state.signal is None),
            key="run_btn_quick",
        )

    else:  # Manual Input
        manual_text = st.text_area(
            "Customer signal",
            height=120,
            placeholder="e.g. My order still hasn't arrived…",
            key="manual_text_input",
        )
        mi_market = st.selectbox("Market", MARKETS, key="mi_market")

        if manual_text and manual_text.strip():
            new_sig = {
                "label":         f"Manual — {mi_market}",
                "market":        mi_market,
                "source":        "support_ticket",
                "category":      "other",
                "urgency_score": 3,
                "query":         manual_text.strip(),
            }
            prev = st.session_state.signal
            if (prev is None
                    or prev.get("query") != new_sig["query"]
                    or prev.get("market") != new_sig["market"]):
                st.session_state.signal            = new_sig
                st.session_state.pipeline_complete = False
                st.session_state.pipeline_results  = {}
                st.session_state.hitl_triggered    = False
                st.session_state.hitl_approved     = None
                st.session_state.hitl_decision     = "not_triggered"
                st.session_state.pipeline_paused   = False
                st.session_state.pipeline_status   = "idle"
        elif not (manual_text or "").strip():
            if st.session_state.signal and str(
                    st.session_state.signal.get("label", "")).startswith("Manual"):
                st.session_state.signal            = None
                st.session_state.pipeline_complete = False
                st.session_state.pipeline_results  = {}

        st.markdown("---")
        run_clicked = st.button(
            "🚀 Run Pipeline",
            use_container_width=True,
            type="primary",
            disabled=(st.session_state.signal is None),
            key="run_btn_manual",
        )

    st.markdown("---")

    # Status badge
    _status = st.session_state.pipeline_status
    if _status == "paused_hitl":
        st.markdown(
            '<div style="background:#FEF3C7;border:1px solid #F59E0B;border-radius:8px;'
            'padding:0.5rem 0.75rem;">'
            '<span style="font-weight:700;font-size:0.8rem;color:#B45309;">'
            '⚠️ Awaiting approval</span></div>',
            unsafe_allow_html=True,
        )
    elif _status == "complete" or st.session_state.demo_complete:
        st.markdown(
            '<div style="background:#DCFCE7;border:1px solid #10B981;border-radius:8px;'
            'padding:0.5rem 0.75rem;">'
            '<span style="font-weight:700;font-size:0.8rem;color:#059669;">'
            '✓ Complete</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if st.button("🔄 Reset", use_container_width=True, key="reset_btn"):
        for _k in list(st.session_state.keys()):
            del st.session_state[_k]
        st.rerun()

    # Download buttons
    if (st.session_state.pipeline_complete
            and st.session_state.pipeline_results
            and st.session_state.mode != "Live Demo"):
        st.download_button(
            "📥 Download Results",
            data=json.dumps({"signal": st.session_state.signal,
                             "pipeline_results": st.session_state.pipeline_results},
                            indent=2),
            file_name="cosmic_pulse_results.json",
            mime="application/json",
            use_container_width=True,
        )
    elif st.session_state.demo_complete and st.session_state.demo_results:
        st.download_button(
            "📥 Download All 5 Results",
            data=json.dumps(
                {"demo_results": st.session_state.demo_results}, indent=2,
                default=str,
            ),
            file_name="cosmic_pulse_demo_results.json",
            mime="application/json",
            use_container_width=True,
        )


# ── Right column — tabs ───────────────────────────────────────────────────────
with col_main:
    tab_pipeline, tab_results, tab_about = st.tabs(["🤖 Pipeline", "📋 Results", "ℹ️ About"])

    # ── Pipeline tab ──────────────────────────────────────────────────────────
    with tab_pipeline:

        if st.session_state.mode == "Live Demo":
            # LIVE DEMO MODE — all rendering handled in render_live_demo_ui()
            render_live_demo_ui()

        else:
            # QUICK GENERATE / MANUAL INPUT modes
            if st.session_state.signal:
                render_signal_preview(st.session_state.signal)
            else:
                st.markdown(
                    '<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;'
                    'padding:2.5rem 2rem;text-align:center;margin-top:0.5rem;">'
                    '<div style="font-size:2.75rem;margin-bottom:0.75rem;">🌌</div>'
                    '<h3 style="color:#6D28D9;margin-bottom:0.5rem;font-size:1rem;">'
                    'Welcome to Cosmic Pulse</h3>'
                    '<p style="color:#64748B;max-width:420px;margin:0 auto;'
                    'line-height:1.7;font-size:0.875rem;">'
                    'Use the control panel on the left — generate or paste a signal, '
                    'then click <strong>Run Pipeline</strong>.</p>'
                    '</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("---")

            # Pipeline state machine
            if run_clicked and st.session_state.signal:
                for _k in ["_partial_detection", "_partial_resolution",
                           "_partial_pattern_risk", "_partial_frontline_gap",
                           "_partial_action", "_partial_customer_msg"]:
                    st.session_state.pop(_k, None)
                st.session_state.pipeline_complete = False
                st.session_state.pipeline_results  = {}
                st.session_state.hitl_triggered    = False
                st.session_state.hitl_approved     = None
                st.session_state.hitl_decision     = "not_triggered"
                st.session_state.pipeline_paused   = False
                st.session_state.pipeline_status   = "idle"

                run_pipeline_ui(st.session_state.signal)
                if st.session_state.pipeline_complete:
                    render_cxo_dashboard(
                        st.session_state.pipeline_results.get("learning_output", ""))

            elif (st.session_state.pipeline_paused
                  and st.session_state.hitl_decision == "not_triggered"):
                render_hitl_paused_ui()

            elif (st.session_state.hitl_triggered
                  and not st.session_state.pipeline_paused
                  and st.session_state.hitl_decision != "not_triggered"
                  and not st.session_state.pipeline_complete):
                run_pipeline_phase2(st.session_state.signal)
                if st.session_state.pipeline_complete:
                    render_cxo_dashboard(
                        st.session_state.pipeline_results.get("learning_output", ""))

            elif st.session_state.pipeline_complete and st.session_state.pipeline_results:
                display_pipeline_from_state(st.session_state.pipeline_results)
                render_cxo_dashboard(
                    st.session_state.pipeline_results.get("learning_output", ""))

    # ── Results tab ───────────────────────────────────────────────────────────
    with tab_results:
        if st.session_state.mode == "Live Demo" and st.session_state.demo_complete:
            render_results_tab(None, demo_results=st.session_state.demo_results)
        elif st.session_state.pipeline_complete and st.session_state.pipeline_results:
            render_results_tab(st.session_state.pipeline_results)
        else:
            st.info("Run the pipeline first to see full agent outputs here.", icon="📋")

    # ── About tab ─────────────────────────────────────────────────────────────
    with tab_about:
        render_about_tab()
