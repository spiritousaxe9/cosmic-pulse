# ════════════════════════════════════════════════════
#  HOSTING ON STREAMLIT COMMUNITY CLOUD
#  (Free — takes ~10 minutes)
#
#  Step 1: Push project to GitHub
#    git init && git add . && git commit -m "Cosmic Pulse demo"
#    Then push to https://github.com/spiritousaxe9/cosmic-pulse
#
#  Step 2: Deploy on Streamlit Cloud
#    Go to share.streamlit.io → Create app
#    Repo: spiritousaxe9/cosmic-pulse | File: app.py
#    Advanced settings → Secrets:
#      API_KEY = "your_airefinery_key"
#    Click Deploy
#
#  NOTE: .env and .streamlit/secrets.toml are in .gitignore
# ════════════════════════════════════════════════════

# Install: pip install -r requirements.txt
# Run:     streamlit run app.py
"""
Cosmic Pulse — Streamlit Demo App
Multi-agent CX orchestration for Cosmic Mart (144M customers, 10 markets).
Modes: Live Demo | Quick Generate | Manual Input
"""

import streamlit as st
import asyncio
import json
import os
from datetime import datetime

# HOSTING — works locally (.env) and on Streamlit Cloud (st.secrets)
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

# ABOUT FIX — live mermaid diagram
try:
    from streamlit_mermaid import st_mermaid  # type: ignore
    MERMAID_AVAILABLE = True
except ImportError:
    MERMAID_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cosmic Pulse",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu{visibility:hidden;}footer{visibility:hidden;}header{visibility:hidden;}
*{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
.main .block-container{padding-top:1rem;max-width:1400px;}

div.stButton>button[kind="primary"]{background:#6D28D9;color:white;border:none;
  font-weight:600;font-size:.875rem;border-radius:8px;padding:.5rem 1rem;}
div.stButton>button[kind="primary"]:hover{background:#5B21B6;border:none;}
div.stButton>button[kind="primary"]:disabled{background:#C4B5FD;border:none;}
button[data-baseweb="tab"]{font-weight:600;font-size:.875rem;}

/* FIX 3 — HITL pulsing border */
@keyframes pulse-border{
  0%  {border-color:#D97706;box-shadow:0 0 0 0 rgba(217,119,6,.4);}
  70% {border-color:#F59E0B;box-shadow:0 0 0 8px rgba(217,119,6,0);}
  100%{border-color:#D97706;box-shadow:0 0 0 0 rgba(217,119,6,0);}
}
.hitl-card{animation:pulse-border 2s ease-in-out infinite;
  border:3px solid #D97706;border-radius:12px;padding:1.5rem;background:#FFFBEB;}

/* Step indicator pulse */
@keyframes pulse-ring{
  0%  {box-shadow:0 0 0 0 rgba(109,40,217,.45);}
  70% {box-shadow:0 0 0 7px rgba(109,40,217,0);}
  100%{box-shadow:0 0 0 0 rgba(109,40,217,0);}
}
.step-active{animation:pulse-ring 1.5s ease-out infinite;}

/* POLISH 1 — thin top progress bar */
.progress-bar-top{position:fixed;top:0;left:0;z-index:9999;height:3px;
  background:linear-gradient(90deg,#6D28D9,#8B5CF6);transition:width .4s ease;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
MARKETS    = ["North America","Europe","Asia","South America"]
SOURCES    = ["support_ticket","social_media","app_review"]
CATEGORIES = ["service_delay","return_friction","price_dissatisfaction","product_quality","other"]

AGENT_COLORS = {
    "Signal Detection Agent":     {"border":"#3B82F6","text":"#1D4ED8","bg":"#EFF6FF","light":"#DBEAFE"},
    "Resolution Agent":           {"border":"#10B981","text":"#059669","bg":"#F0FDF4","light":"#DCFCE7"},
    "Employee Enablement Agent":  {"border":"#14B8A6","text":"#0F766E","bg":"#F0FDFA","light":"#CCFBF1"},
    "Insight Routing Agent":      {"border":"#6366F1","text":"#4338CA","bg":"#EEF2FF","light":"#E0E7FF"},
    "Learning and Insights Agent":{"border":"#8B5CF6","text":"#6D28D9","bg":"#F5F3FF","light":"#EDE9FE"},
    "Human Governance":           {"border":"#F59E0B","text":"#B45309","bg":"#FFFBEB","light":"#FEF3C7"},
}

# ROUTING FIX — mutually exclusive ORC branches: one row per path
# (n, market, category, urgency, pattern, route_label)
DEMO_SIGNALS_META = [
    (1, "North America", "service_delay",        5, "low",    "Route 1 — Resolution"),      # SIGNAL PATH — Route 1 Resolution
    (2, "Europe",        "return_friction",       2, "high",   "Route 2 — Insight only"),    # SIGNAL PATH — Route 2 Insight only
    (3, "Asia",          "price_dissatisfaction", 4, "high",   "Route 1 — Resolution + EEA"),# SIGNAL PATH — Route 1 Resolution
    (4, "South America", "product_quality",       5, "low",    "Route 1 — Resolution + HITL"),# SIGNAL PATH — Route 1 Resolution
    (5, "Europe",        "other",                 3, "medium", "Route 2 — Insight only"),    # SIGNAL PATH — Route 2 Insight only
]

# ABOUT FIX — full detailed diagram with labels, subgraph legend, and rich node text
COSMIC_PULSE_DIAGRAM = """flowchart TD

  SIG[Experience Signals<br/>VoC + Ops Data<br/>- Support interactions<br/>- Social sentiment and topics<br/>- Reviews and feedback<br/>- Store feedback]:::ext
  PII[PII Masking and Responsible AI<br/>Remove personal data<br/>Privacy controls across markets]:::ext
  ENT[Enterprise Systems<br/>CRM - Contact Center - Commerce and Returns]:::ext

  DET["[Signal Detection Agent<br/>Detect friction and trends<br/>Tag topic: returns, support, price, store, product]"]:::agent
  ORC["[Cosmic Pulse Orchestrator<br/>Choose workflow: Resolution or Insight Routing]"]:::agent
  RES["[Resolution Agent<br/>Run Resolution Playbooks<br/>- Case routing and escalation<br/>- Returns and refunds where allowed]"]:::agent
  EEA["[Employee Enablement Agent optional<br/>Just in time policy guidance<br/>Triggered by complexity or frontline strain]"]:::agent
  INS["[Insight Routing Agent<br/>Run Insight Brief Templates<br/>Synthesize patterns and send briefs]"]:::agent
  LRN["[Learning Agent<br/>Improve agent knowledge<br/>Update playbooks and brief templates]"]:::agent

  GOV["[Human in the Loop Governance<br/>Approve high impact actions]"]:::gov

  T1(Pricing and Promotions):::stake
  T2(Store Operations):::stake
  T3(Merchandising and Assortment):::stake
  T4(Returns and Policy Owners):::stake
  T5(Support Leadership):::stake
  OUT(Outcome Signals<br/>- Sentiment and topic shifts<br/>- Repeat complaint patterns<br/>- Team action taken):::stake
  CXO(CXO Visibility<br/>Sentiment - Cost to serve - Demand trends):::stake

  SIG -->|Collect signals for analysis| PII
  PII -->|Anonymize for safe processing| DET
  DET -->|Structured themes and trend flags| ORC

  ORC -->|Single urgent customer case| RES
  ORC -->|Repeated pattern across customers| INS

  RES -->|Execute low risk actions in systems| ENT
  RES -->|High impact action needs approval| GOV
  GOV -->|Approved action executed in systems| ENT

  RES -->|Complex case or frontline strain| EEA
  EEA -->|Guidance applied in frontline workflow| ENT

  INS -->|Pricing and value complaints| T1
  INS -->|Store experience complaints| T2
  INS -->|Product and selection complaints| T3
  INS -->|Returns and policy friction| T4
  INS -->|Support responsiveness themes| T5

  ENT -->|Service outcomes and repeat contact signals| OUT
  INS -->|Insights sent and prioritization metadata| OUT
  T1 -.->|Team action status| OUT
  T2 -.->|Team action status| OUT
  T3 -.->|Team action status| OUT
  T4 -.->|Team action status| OUT
  T5 -.->|Team action status| OUT

  OUT -->|What worked vs what did not| LRN
  LRN -->|Update resolution playbooks| RES
  LRN -->|Update insight brief templates| INS
  LRN -->|Trends and drivers for leadership| CXO

  classDef ext fill:#F3F4F6,stroke:#6B7280,color:#111827
  classDef agent fill:#DBEAFE,stroke:#2563EB,color:#0F172A
  classDef stake fill:#DCFCE7,stroke:#16A34A,color:#052E16
  classDef gov fill:#FEF3C7,stroke:#D97706,color:#7C2D12

  subgraph LEGEND["Legend"]
    direction LR
    LEXT[External Data / Systems]:::ext
    LAGENT["[Agentic Component]"]:::agent
    LSTAKE(Stakeholder / Outcome):::stake
    LGOV["[Human Governance]"]:::gov
  end
"""

# ─────────────────────────────────────────────────────────────────────────────
# Async runner
# ─────────────────────────────────────────────────────────────────────────────
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")

# ─────────────────────────────────────────────────────────────────────────────
# ROOT FIX 3 — routing uses Signal Detection output directly, no lock
# The Orchestrator chooses ONE route: Resolution OR Insight Routing, never both.
# Works correctly for all modes (Live Demo, Quick Generate, Manual Input)
# because the generator now writes calibrated text that Signal Detection scores correctly.
# ─────────────────────────────────────────────────────────────────────────────

# ROUTING TEST STRINGS — paste into Manual Input to verify routing is correct
# Test A (should route to INSIGHT ROUTING — urgency 2, pattern high):
#   "I tried to return my headphones using the app portal but it keeps crashing.
#    I'm not in a rush but I saw hundreds of other customers reporting the exact
#    same crash on Trustpilot this week and on the community forum. Seems like a
#    systemic issue. Would appreciate a fix when possible."
#   Expected: urgency 2, pattern_risk high → Insight Routing
#
# Test B (should route to RESOLUTION — urgency 5, pattern low):
#   "My order hasn't arrived and the tracking hasn't updated in 4 days. I've
#    called twice and nobody can find my order. If this isn't resolved by tomorrow
#    I will dispute the charge with my bank and contact the consumer protection
#    bureau immediately."
#   Expected: urgency 5, pattern_risk low → Resolution

def compute_routing(urgency: int, pattern_risk: str) -> tuple:
    """
    ROOT FIX 3 — routing from Signal Detection output, no intended_route lock.
    Strictly follows the two diagram arrows:
        ORC -->|Single urgent customer case| RES
        ORC -->|Repeated pattern across customers| INS
    Returns (route, routing_label, routing_reason).
    route == "resolution"  OR  "insight" — never both simultaneously.

    Route 1 — Resolution    : urgency >= 4
    Route 2 — Insight (high): pattern_risk "high"  AND urgency <= 3
    Route 2 — Insight (med) : pattern_risk "medium" AND urgency <= 3
    Default                 : Resolution (low urgency + low pattern)
    """
    # Route 1 — Single urgent customer case
    if urgency >= 4:
        return (
            "resolution",
            "Single urgent customer case",
            (f"urgency_score {urgency} detected in signal — indicates an urgent "
             f"individual customer case. Routing to Resolution Agent. "
             f"Insight Routing Agent: not triggered."),
        )

    # Route 2 — Repeated pattern (high confidence)
    if pattern_risk == "high" and urgency <= 3:
        return (
            "insight",
            "Repeated pattern across customers",
            (f"pattern_risk '{pattern_risk}' with urgency_score {urgency} — "
             f"multiple customers affected, confirmed widespread issue. "
             f"Routing to Insight Routing Agent. "
             f"Resolution Agent: not triggered."),
        )

    # Route 2 — Emerging pattern (medium confidence)
    if pattern_risk == "medium" and urgency <= 3:
        return (
            "insight",
            "Emerging pattern across customers",
            (f"pattern_risk '{pattern_risk}' with urgency_score {urgency} — "
             f"pattern is emerging across customers, not an urgent individual case. "
             f"Routing to Insight Routing Agent. "
             f"Resolution Agent: not triggered."),
        )

    # Default — low urgency, low pattern → Resolution (standard individual case)
    return (
        "resolution",
        "Standard customer case",
        (f"urgency_score {urgency}, pattern_risk '{pattern_risk}'. "
         f"Standard individual case. Routing to Resolution Agent."),
    )

# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers
# ─────────────────────────────────────────────────────────────────────────────
def urgency_color(score: int) -> tuple:
    if score <= 2:   return "#059669","#DCFCE7"
    elif score == 3: return "#D97706","#FEF3C7"
    else:            return "#DC2626","#FEE2E2"

def render_kv_table_html(data: dict) -> str:
    rows = []
    for key, value in data.items():
        key_td = (f'<td style="padding:3px 12px 3px 0;color:#64748B;font-weight:600;'
                  f'vertical-align:top;white-space:nowrap;font-size:.78rem;">{key}</td>')
        if isinstance(value, dict):
            rows.append(f'<tr><td colspan="2" style="padding:6px 0 2px 0;font-weight:700;'
                        f'color:#334155;font-size:.78rem;border-top:1px solid #E2E8F0;">{key}</td></tr>')
            for sk,sv in value.items():
                rows.append(f'<tr><td style="padding:2px 10px 2px 16px;color:#64748B;font-size:.75rem;">{sk}</td>'
                            f'<td style="padding:2px 8px;color:#0F172A;font-size:.75rem;">{sv}</td></tr>')
        elif isinstance(value, list):
            pills = " ".join(f'<span style="background:#EDE9FE;color:#4C1D95;padding:1px 8px;'
                             f'border-radius:999px;font-size:.72rem;margin:1px;display:inline-block;">{v}</span>'
                             for v in value)
            rows.append(f'<tr>{key_td}<td style="padding:3px 8px;">{pills}</td></tr>')
        elif value is None:
            rows.append(f'<tr>{key_td}<td style="padding:3px 8px;color:#94A3B8;font-size:.78rem;'
                        f'font-style:italic;">not triggered</td></tr>')
        else:
            rows.append(f'<tr>{key_td}<td style="padding:3px 8px;color:#0F172A;font-size:.78rem;">'
                        f'{str(value)}</td></tr>')
    return f'<table style="width:100%;border-collapse:collapse;">{"".join(rows)}</table>'

def agent_card_html(name: str, result_str, triggered: bool = True, timestamp: str = None) -> str:
    """POLISH 5 — timestamp shown in top-right corner."""
    colors = AGENT_COLORS.get(name, {"border":"#E2E8F0","text":"#64748B","bg":"#F8FAFC","light":"#F1F5F9"})
    ts_html = (f'<span style="font-size:.65rem;color:#94A3B8;margin-left:auto;">{timestamp}</span>'
               if timestamp else "")
    if not triggered or not result_str:
        body = ('<p style="color:#94A3B8;font-size:.78rem;margin:0;font-style:italic;">'
                'This agent was not invoked for this signal.</p>')
        badge_color,badge_bg,badge_text = "#94A3B8","#F1F5F9","⬜ Not triggered"
    else:
        try:    body = render_kv_table_html(json.loads(result_str))
        except: body = f'<code style="font-size:.72rem;color:#334155;word-break:break-all;">{result_str[:500]}</code>'
        badge_color,badge_bg,badge_text = "#059669","#DCFCE7","✅ Triggered"
    return (f'<div style="border-left:3px solid {colors["border"]};border-radius:10px;'
            f'padding:1rem 1.25rem;margin-bottom:.75rem;background:#FFFFFF;'
            f'box-shadow:0 1px 3px rgba(0,0,0,.06);">'
            f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.65rem;">'
            f'<span style="background:{colors["light"]};color:{colors["text"]};padding:3px 10px;'
            f'border-radius:999px;font-size:.72rem;font-weight:600;">{name}</span>'
            f'<span style="margin-left:auto;color:{badge_color};background:{badge_bg};'
            f'padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:600;">{badge_text}</span>'
            f'{ts_html}</div>{body}</div>')

def pending_card_html(name: str) -> str:
    return (f'<div style="border-left:3px solid #E2E8F0;border-radius:10px;'
            f'padding:.8rem 1.25rem;margin-bottom:.75rem;background:#F8FAFC;opacity:.45;">'
            f'<span style="font-weight:600;color:#94A3B8;font-size:.85rem;">⏳ {name} — waiting</span></div>')

def running_card_html(name: str) -> str:
    c = AGENT_COLORS.get(name,{"border":"#E2E8F0","text":"#64748B","bg":"#F8FAFC","light":"#F1F5F9"})
    return (f'<div style="border-left:3px solid {c["border"]};border-radius:10px;'
            f'padding:.8rem 1.25rem;margin-bottom:.75rem;background:{c["bg"]};'
            f'box-shadow:0 1px 3px rgba(0,0,0,.06);">'
            f'<span style="background:{c["light"]};color:{c["text"]};padding:3px 10px;'
            f'border-radius:999px;font-size:.72rem;font-weight:600;">🔄 {name} — running…</span></div>')

def step_indicator_html(current: int, total: int = 5) -> str:
    parts = []
    for i in range(1, total+1):
        if i < current:
            circle = (f'<div style="width:28px;height:28px;border-radius:50%;background:#6D28D9;'
                      f'color:white;display:flex;align-items:center;justify-content:center;'
                      f'margin:0 auto;font-size:.7rem;font-weight:700;">✓</div>')
            lc = "#6D28D9"
        elif i == current:
            circle = (f'<div class="step-active" style="width:28px;height:28px;border-radius:50%;'
                      f'border:2.5px solid #6D28D9;color:#6D28D9;display:flex;align-items:center;'
                      f'justify-content:center;margin:0 auto;font-size:.7rem;font-weight:700;">{i}</div>')
            lc = "#6D28D9"
        else:
            circle = (f'<div style="width:28px;height:28px;border-radius:50%;border:2px solid #E2E8F0;'
                      f'color:#94A3B8;display:flex;align-items:center;justify-content:center;'
                      f'margin:0 auto;font-size:.7rem;font-weight:700;">{i}</div>')
            lc = "#94A3B8"
        parts.append(f'<div style="text-align:center;flex:1;">{circle}'
                     f'<div style="font-size:.65rem;color:{lc};font-weight:600;margin-top:4px;">Signal {i}</div></div>')
        if i < total:
            lcolor = "#6D28D9" if i < current else "#E2E8F0"
            parts.append(f'<div style="height:2px;background:{lcolor};flex:2;margin-bottom:18px;"></div>')
    return f'<div style="display:flex;align-items:center;margin-bottom:1.25rem;">{"".join(parts)}</div>'


# ROUTING FIX — mutually exclusive ORC branches: routing pathway card
def routing_pathway_card_html(route: str, routing_label: str, routing_reason: str,
                               urgency: int, pattern_risk: str) -> str:
    """
    Shows ONLY the active route. The inactive route is shown in gray as 'not triggered'.
    Strictly mirrors the diagram's two mutually exclusive ORC arrows.
    """
    urg_t, urg_bg = urgency_color(urgency)
    pr_bg  = "#FEE2E2" if pattern_risk=="high" else "#FEF3C7" if pattern_risk=="medium" else "#DCFCE7"
    pr_col = "#DC2626" if pattern_risk=="high" else "#D97706" if pattern_risk=="medium" else "#059669"

    def active_node(label):
        return (f'<span style="background:#EDE9FE;color:#6D28D9;border:1.5px solid #8B5CF6;'
                f'padding:4px 10px;border-radius:8px;font-size:.72rem;font-weight:600;'
                f'white-space:nowrap;">{label}</span>')

    def not_triggered(label):
        return (f'<span style="color:#9CA3AF;font-size:.75rem;font-style:italic;">'
                f'{label}: not triggered</span>')

    arrow = '<span style="color:#6D28D9;font-weight:700;margin:0 4px;">→</span>'

    if route == "resolution":
        # SIGNAL PATH — Route 1 Resolution
        path_html = (active_node("Signal Detection")
                     + arrow + active_node("Resolution Agent")
                     + arrow + active_node("Enterprise Systems")
                     + arrow + active_node("Learning Agent"))
        inactive_html = not_triggered("Insight Routing Agent")
        note = "EEA fires after Resolution if frontline_gap_detected = true. HITL fires if requires_human = true."
    else:
        # SIGNAL PATH — Route 2 Insight only
        path_html = (active_node("Signal Detection")
                     + arrow + active_node("Insight Routing Agent")
                     + arrow + active_node("T1–T5 Teams")
                     + arrow + active_node("Learning Agent"))
        inactive_html = (not_triggered("Resolution Agent")
                         + ' <span style="color:#9CA3AF;font-size:.75rem;">&nbsp;·&nbsp;</span> '
                         + not_triggered("Employee Enablement Agent"))
        note = "Resolution Agent and EEA are not called on this path."

    return (
        f'<div style="border-left:3px solid #8B5CF6;border-radius:10px;padding:1rem 1.25rem;'
        f'margin-bottom:.75rem;background:#FAFAFF;box-shadow:0 1px 3px rgba(0,0,0,.05);">'
        f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem;">'
        f'<span style="font-weight:700;color:#6D28D9;font-size:.82rem;">📐 Routing Decision</span>'
        f'<span style="background:{urg_bg};color:{urg_t};padding:2px 9px;border-radius:999px;'
        f'font-size:.7rem;font-weight:700;margin-left:auto;">Urgency {urgency}</span>'
        f'<span style="background:{pr_bg};color:{pr_col};padding:2px 9px;border-radius:999px;'
        f'font-size:.7rem;font-weight:600;">risk: {pattern_risk}</span>'
        f'</div>'
        f'<div style="font-size:.82rem;font-weight:700;color:#1E1B4B;margin-bottom:.5rem;">'
        f'Orchestrator → {routing_label}</div>'
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:.45rem;">'
        f'{path_html}</div>'
        f'<div style="margin-bottom:.4rem;">{inactive_html}</div>'
        f'<p style="color:#64748B;font-size:.75rem;margin:0;line-height:1.6;">'
        f'{routing_reason}</p>'
        f'<p style="color:#94A3B8;font-size:.7rem;margin:.25rem 0 0 0;font-style:italic;">{note}</p>'
        f'</div>'
    )


# FIX 5 — Case journey summary card
def case_journey_summary_html(signal: dict, result: dict) -> str:
    """Purple summary card shown at the end of each signal's output."""
    sig_mkt = signal.get("market","?")
    sig_cat = signal.get("category","?").replace("_"," ").title()
    sig_urg = signal.get("urgency_score","?")

    ran_res  = result.get("_meta_run_resolution", True)
    ran_eea  = result.get("employee_enablement_output") is not None
    ran_ir   = result.get("insight_routing_output") is not None
    hitl_dec = result.get("_meta_hitl_decision","not_triggered")
    hitl_trig= result.get("_meta_hitl_triggered", False)
    action   = result.get("_meta_hitl_action","")

    # Build path string
    path_parts = ["Detection"]
    if ran_res:  path_parts.append("Resolution")
    if ran_eea:  path_parts.append("EEA")
    if ran_ir:   path_parts.append("Insight Routing")
    path_parts.append("Learning")
    path_str = " → ".join(path_parts)

    # HITL row
    if hitl_trig:
        hitl_color = "#059669" if hitl_dec=="approved" else "#D97706"
        hitl_label = f"Triggered · {hitl_dec.title()}"
    else:
        hitl_color = "#94A3B8"
        hitl_label = "Not triggered"

    # Repeat risk from learning output
    repeat_risk = "—"
    lr = result.get("learning_output","")
    if lr:
        try:
            repeat_risk = json.loads(lr).get("repeat_risk","—").upper()
        except Exception:
            pass
    rr_color = "#DC2626" if repeat_risk=="HIGH" else "#D97706" if repeat_risk=="MEDIUM" else "#059669"

    def row(label, value, vcolor="#0F172A"):
        return (f'<tr><td style="padding:3px 12px 3px 0;color:#7C3AED;font-weight:600;'
                f'font-size:.75rem;white-space:nowrap;">{label}</td>'
                f'<td style="padding:3px 0;color:{vcolor};font-size:.75rem;">{value}</td></tr>')

    return (
        f'<div style="border-left:4px solid #6D28D9;border-radius:10px;padding:1rem 1.25rem;'
        f'margin-top:.75rem;margin-bottom:.5rem;background:#F5F3FF;">'
        f'<div style="font-weight:700;color:#6D28D9;font-size:.82rem;margin-bottom:.6rem;">'
        f'📋 Case Journey Summary</div>'
        f'<table style="width:100%;border-collapse:collapse;">'
        + row("Signal",    f"{sig_mkt} · {sig_cat} · Urgency {sig_urg}")
        + row("Path",      path_str)
        + row("HITL",      hitl_label, hitl_color)
        + row("Action",    action or "—")
        + row("Repeat risk", repeat_risk, rr_color)
        + f'</table></div>'
    )


def hitl_governance_card_html(action_taken: str, customer_message: str, signal: dict) -> str:
    """FIX 3 — uses .hitl-card CSS class for pulsing amber animation."""
    urgency  = signal.get("urgency_score", 3)
    category = signal.get("category","other").replace("_"," ").title()
    market   = signal.get("market","Unknown")
    act_safe = str(action_taken).replace("<","&lt;").replace(">","&gt;")
    msg_safe = str(customer_message).replace("<","&lt;").replace(">","&gt;")
    msg_prev = (msg_safe[:140]+"…") if len(msg_safe)>140 else msg_safe
    return (
        f'<div class="hitl-card">'
        f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.75rem;">'
        f'<span style="background:#FEF3C7;color:#B45309;padding:3px 10px;border-radius:999px;'
        f'font-size:.72rem;font-weight:600;">⚠️ Human Governance — Approval Required</span>'
        f'<span style="margin-left:auto;background:#FEF3C7;color:#B45309;padding:2px 9px;'
        f'border-radius:999px;font-size:.7rem;font-weight:700;">🔒 AWAITING DECISION</span>'
        f'</div>'
        f'<p style="color:#78350F;font-size:.8rem;margin:0 0 .75rem 0;">'
        f'The Resolution Agent flagged this case as high-impact. A human must approve or '
        f'reject the proposed action before the pipeline continues.</p>'
        f'<table style="width:100%;border-collapse:collapse;font-size:.8rem;">'
        f'<tr><td style="padding:3px 12px 3px 0;color:#92400E;font-weight:600;white-space:nowrap;">Proposed action</td>'
        f'<td style="padding:3px 8px;color:#0F172A;font-weight:700;">{act_safe}</td></tr>'
        f'<tr><td style="padding:3px 12px 3px 0;color:#92400E;font-weight:600;vertical-align:top;">Customer message</td>'
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
    """FIX 3 — persists as green/amber banner after pipeline completes."""
    if decision == "approved":
        border,bg,tc = "#10B981","#F0FDF4","#059669"
        badge_bg,badge_color,badge_text = "#DCFCE7","#059669","✅ Action Approved"
        msg = "✅ Human approved — pipeline continuing."
    elif decision in ("rejected","auto_approved","auto_approved_demo"):
        if decision == "approved": pass
        border,bg,tc = "#F59E0B","#FFFBEB","#B45309"
        badge_bg,badge_color = "#FEF3C7","#B45309"
        if "auto" in decision:
            badge_text = "⚡ Auto-approved (Live Demo)"
            msg = "⚡ Live Demo mode: HITL auto-approved to keep presentation flowing."
        else:
            badge_text = "⚠️ Rejected — Escalated"
            msg = "⚠️ Human rejected — case escalated to human representative."
    else:
        return ""
    act_safe = str(action_taken).replace("<","&lt;").replace(">","&gt;")
    return (
        f'<div style="border-left:3px solid {border};border-radius:10px;'
        f'padding:1rem 1.25rem;margin-bottom:.75rem;background:{bg};">'
        f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem;">'
        f'<span style="background:{badge_bg};color:{badge_color};padding:3px 10px;'
        f'border-radius:999px;font-size:.72rem;font-weight:600;">'
        f'⚖️ Human Governance — Decision Recorded</span>'
        f'<span style="margin-left:auto;background:{badge_bg};color:{badge_color};'
        f'padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:600;">{badge_text}</span>'
        f'</div>'
        f'<p style="color:{tc};font-size:.8rem;margin:0 0 .2rem 0;font-weight:600;">{msg}</p>'
        f'<p style="color:#64748B;font-size:.75rem;margin:0;">Action: <strong>{act_safe}</strong></p>'
        f'</div>'
    )

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
_defaults = {
    "mode":                  "Live Demo",
    "signal":                None,
    "pipeline_complete":     False,
    "pipeline_results":      {},
    "pipeline_status":       "idle",
    "hitl_triggered":        False,
    "hitl_approved":         None,
    "hitl_decision":         "not_triggered",  # not_triggered|pending|approved|rejected
    "pipeline_paused":       False,
    "current_signal":        None,
    "demo_running":          False,
    "demo_complete":         False,
    "demo_results":          [],
    "demo_progress":         0,
    "demo_balloons_shown":   False,            # POLISH 2
    "pipeline_progress":     0.0,              # POLISH 1
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run_post_hitl_agents(signal, detection_result, resolution_result,
                          frontline_gap, hitl_decision,
                          slot_eea, slot_ln):
    """
    ROUTING FIX — mutually exclusive ORC branches.
    Post-Resolution phase: EEA (if frontline gap) + Learning Agent.
    Insight Routing is NEVER called here — it belongs to Route 2 only,
    and this function is only reached on Route 1 (Resolution path).
    Returns (eea_result, learning_result, ts_eea, ts_ln).
    """
    # Employee Enablement: triggered only if Resolution detected a frontline gap
    eea_result = None; ts_eea = None
    if frontline_gap:
        slot_eea.markdown(running_card_html("Employee Enablement Agent"), unsafe_allow_html=True)
        with st.spinner("Employee Enablement Agent running…"):
            eea_result = run_async(employee_enablement_agent(resolution_result or "{}"))
        ts_eea = _ts()
        slot_eea.markdown(agent_card_html("Employee Enablement Agent", eea_result, True, ts_eea), unsafe_allow_html=True)
    else:
        slot_eea.markdown(agent_card_html("Employee Enablement Agent", None, False), unsafe_allow_html=True)

    # Learning always runs last; Insight Routing output is always None on Route 1
    hitl_flag = hitl_decision not in ("not_triggered","")
    learning_input = json.dumps({
        "market":                     signal.get("market","Unknown"),
        "source":                     signal.get("source","unknown"),
        "category":                   signal.get("category","other"),
        "urgency_score":              signal.get("urgency_score",3),
        "original_signal":            signal.get("query",""),
        "signal_detection_output":    detection_result,
        "resolution_output":          resolution_result,
        "employee_enablement_output": eea_result,
        "insight_routing_output":     None,
        "hitl_triggered":             hitl_flag,
        "hitl_decision":              hitl_decision,
        "hitl_action_proposed":       st.session_state.get("_partial_action",""),
        **({"hitl_override_note":"Human reviewer rejected. Case escalated to human rep."}
           if hitl_decision=="rejected" else {}),
    })
    slot_ln.markdown(running_card_html("Learning and Insights Agent"), unsafe_allow_html=True)
    with st.spinner("Learning and Insights Agent running…"):
        learning_result = run_async(learning_insights_agent(learning_input))
    ts_ln = _ts()
    slot_ln.markdown(agent_card_html("Learning and Insights Agent", learning_result, True, ts_ln), unsafe_allow_html=True)

    st.session_state.pipeline_progress = 1.0
    return eea_result, learning_result, ts_eea, ts_ln


def run_pipeline_ui(signal: dict) -> None:
    """
    ROUTING FIX — mutually exclusive ORC branches.
    Orchestrator chooses ONE route: Resolution OR Insight Routing, never both.
    """
    st.session_state.pipeline_progress = 0.1
    st.markdown('<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:.75rem;">'
                '🤖 Agent Pipeline</h3>', unsafe_allow_html=True)

    slot_sd     = st.empty()
    slot_route  = st.empty()
    slot_res    = st.empty()
    slot_hitl   = st.empty()
    slot_eea    = st.empty()
    slot_ir     = st.empty()
    slot_ln     = st.empty()
    slot_journey= st.empty()

    for slot, name in [(slot_sd,"Signal Detection Agent"),(slot_res,"Resolution Agent"),
                       (slot_eea,"Employee Enablement Agent"),(slot_ir,"Insight Routing Agent"),
                       (slot_ln,"Learning and Insights Agent")]:
        slot.markdown(pending_card_html(name), unsafe_allow_html=True)

    # ── Step 1: Signal Detection (always runs first) ───────────────────────
    slot_sd.markdown(running_card_html("Signal Detection Agent"), unsafe_allow_html=True)
    with st.spinner("Signal Detection Agent running…"):
        detection_result = run_async(signal_detection_agent(signal["query"]))
    ts_sd = _ts()
    slot_sd.markdown(agent_card_html("Signal Detection Agent", detection_result, True, ts_sd), unsafe_allow_html=True)
    st.session_state.pipeline_progress = 0.25

    try:
        det_json     = json.loads(detection_result)
        pattern_risk = str(det_json.get("pattern_risk","low")).lower().strip()
        urgency      = int(det_json.get("urgency_score", signal.get("urgency_score",3)))
    except Exception:
        pattern_risk = "low"
        urgency      = signal.get("urgency_score",3)

    # ROUTING FIX — mutually exclusive ORC branches
    route, routing_label, routing_reason = compute_routing(urgency, pattern_risk)

    # Show routing decision card before any agent runs
    slot_route.markdown(
        routing_pathway_card_html(route, routing_label, routing_reason, urgency, pattern_risk),
        unsafe_allow_html=True)

    # ── Step 2: Execute EXACTLY ONE route ─────────────────────────────────
    resolution_result = None; ts_res = None
    insight_result    = None; ts_ir  = None
    eea_result        = None; ts_eea = None
    frontline_gap = False; requires_human = False
    action_taken = "N/A"; customer_msg = "N/A"

    if route == "resolution":
        # SIGNAL PATH — Route 1 Resolution
        slot_res.markdown(running_card_html("Resolution Agent"), unsafe_allow_html=True)
        with st.spinner("Resolution Agent running…"):
            resolution_result = run_async(resolution_agent(detection_result))
        ts_res = _ts()
        slot_res.markdown(agent_card_html("Resolution Agent", resolution_result, True, ts_res), unsafe_allow_html=True)
        st.session_state.pipeline_progress = 0.5

        try:
            res_json       = json.loads(resolution_result)
            frontline_gap  = bool(res_json.get("frontline_gap_detected", False))
            requires_human = bool(res_json.get("requires_human", False))
            action_taken   = res_json.get("action_taken","N/A")
            customer_msg   = res_json.get("customer_message","N/A")
        except Exception:
            pass

        # HITL: genuine pause via st.rerun() + st.stop()
        if requires_human:
            slot_hitl.markdown(
                '<div style="padding:.6rem 1rem;background:#FEF3C7;border-radius:8px;'
                'color:#B45309;font-size:.82rem;font-weight:600;">⏳ Awaiting human approval…</div>',
                unsafe_allow_html=True)
            st.session_state._partial_detection      = detection_result
            st.session_state._partial_resolution     = resolution_result
            st.session_state._partial_route          = route
            st.session_state._partial_routing_label  = routing_label
            st.session_state._partial_routing_reason = routing_reason
            st.session_state._partial_frontline_gap  = frontline_gap
            st.session_state._partial_action         = action_taken
            st.session_state._partial_customer_msg   = customer_msg
            st.session_state._partial_urgency        = urgency
            st.session_state._partial_pattern_risk   = pattern_risk
            st.session_state._partial_ts_sd          = ts_sd
            st.session_state._partial_ts_res         = ts_res
            st.session_state.hitl_triggered          = True
            st.session_state.pipeline_paused         = True
            st.session_state.hitl_decision           = "pending"
            st.session_state.pipeline_status         = "paused_hitl"
            st.session_state.current_signal          = signal
            st.rerun()
            return

        # Insight Routing is not triggered on Route 1
        slot_ir.markdown(agent_card_html("Insight Routing Agent", None, False), unsafe_allow_html=True)

        # EEA + Learning
        eea_result, learning_result, ts_eea, ts_ln = _run_post_hitl_agents(
            signal, detection_result, resolution_result,
            frontline_gap, "not_triggered",
            slot_eea, slot_ln,
        )

    else:
        # SIGNAL PATH — Route 2 Insight only
        # Resolution Agent is NOT called on this route
        slot_res.markdown(agent_card_html("Resolution Agent", None, False), unsafe_allow_html=True)
        slot_eea.markdown(agent_card_html("Employee Enablement Agent", None, False), unsafe_allow_html=True)

        slot_ir.markdown(running_card_html("Insight Routing Agent"), unsafe_allow_html=True)
        with st.spinner("Insight Routing Agent running…"):
            insight_result = run_async(insight_routing_agent(detection_result))
        ts_ir = _ts()
        slot_ir.markdown(agent_card_html("Insight Routing Agent", insight_result, True, ts_ir), unsafe_allow_html=True)
        st.session_state.pipeline_progress = 0.5

        learning_input = json.dumps({
            "market":                     signal.get("market","Unknown"),
            "source":                     signal.get("source","unknown"),
            "category":                   signal.get("category","other"),
            "urgency_score":              signal.get("urgency_score",3),
            "original_signal":            signal.get("query",""),
            "signal_detection_output":    detection_result,
            "resolution_output":          None,
            "employee_enablement_output": None,
            "insight_routing_output":     insight_result,
        })
        slot_ln.markdown(running_card_html("Learning and Insights Agent"), unsafe_allow_html=True)
        with st.spinner("Learning and Insights Agent running…"):
            learning_result = run_async(learning_insights_agent(learning_input))
        ts_ln = _ts()
        slot_ln.markdown(agent_card_html("Learning and Insights Agent", learning_result, True, ts_ln), unsafe_allow_html=True)
        st.session_state.pipeline_progress = 1.0

    results = {
        "signal_detection_output":    detection_result,
        "resolution_output":          resolution_result,
        "employee_enablement_output": eea_result,
        "insight_routing_output":     insight_result,
        "learning_output":            learning_result,
        "_meta_route":                route,
        "_meta_routing_label":        routing_label,
        "_meta_routing_reason":       routing_reason,
        "_meta_urgency":              urgency,
        "_meta_pattern_risk":         pattern_risk,
        "_meta_run_resolution":       (route == "resolution"),
        "_meta_run_insight_routing":  (route == "insight"),
        "_meta_frontline_gap":        frontline_gap,
        "_meta_hitl_triggered":       False,
        "_meta_hitl_decision":        "not_triggered",
        "_meta_hitl_action":          "",
        "_meta_ts_sd": ts_sd, "_meta_ts_res": ts_res,
        "_meta_ts_eea": ts_eea, "_meta_ts_ir": ts_ir, "_meta_ts_ln": ts_ln,
    }
    st.session_state.pipeline_results  = results
    st.session_state.pipeline_complete = True
    st.session_state.pipeline_status   = "complete"

    slot_journey.markdown(case_journey_summary_html(signal, results), unsafe_allow_html=True)


# FIX 3 — HITL paused UI with st.stop()
def render_hitl_paused_ui() -> None:
    """
    FIX 3 — Show HITL governance card with pulsing animation.
    st.stop() is called in the main render loop after this returns.
    """
    st.markdown('<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:.75rem;">'
                '🤖 Agent Pipeline</h3>', unsafe_allow_html=True)

    ts_sd          = st.session_state.get("_partial_ts_sd")
    ts_res         = st.session_state.get("_partial_ts_res")
    urgency        = st.session_state.get("_partial_urgency", 3)
    pattern_risk   = st.session_state.get("_partial_pattern_risk","low")
    route          = st.session_state.get("_partial_route", "resolution")
    routing_label  = st.session_state.get("_partial_routing_label", "Single urgent customer case")
    routing_reason = st.session_state.get("_partial_routing_reason", "")

    # ROUTING FIX — use stored route from Phase 1
    st.markdown(routing_pathway_card_html(route, routing_label, routing_reason, urgency, pattern_risk),
                unsafe_allow_html=True)
    st.markdown(agent_card_html("Signal Detection Agent",
                                st.session_state._partial_detection, True, ts_sd), unsafe_allow_html=True)
    st.markdown(agent_card_html("Resolution Agent",
                                st.session_state._partial_resolution, True, ts_res), unsafe_allow_html=True)

    # FIX 3 — pulsing amber governance card
    st.markdown(hitl_governance_card_html(
        st.session_state._partial_action,
        st.session_state._partial_customer_msg,
        st.session_state.get("current_signal") or st.session_state.signal,
    ), unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div style="background:#DCFCE7;border-radius:6px;padding:4px 8px;'
                    'font-size:.7rem;color:#059669;font-weight:600;margin-bottom:4px;">'
                    '✅ Execute the proposed action</div>', unsafe_allow_html=True)
        approve = st.button("Approve Action", key="hitl_approve_btn",
                            use_container_width=True, type="primary")
    with col2:
        st.markdown('<div style="background:#FEF3C7;border-radius:6px;padding:4px 8px;'
                    'font-size:.7rem;color:#B45309;font-weight:600;margin-bottom:4px;">'
                    '⚠️ Escalate to human representative</div>', unsafe_allow_html=True)
        reject = st.button("Reject / Escalate", key="hitl_reject_btn", use_container_width=True)

    # FIX 3 — button handlers set state and rerun
    if approve:
        st.session_state.hitl_decision   = "approved"
        st.session_state.hitl_approved   = True
        st.session_state.pipeline_paused = False
        st.session_state.pipeline_status = "idle"
        st.rerun()
    if reject:
        st.session_state.hitl_decision   = "rejected"
        st.session_state.hitl_approved   = False
        st.session_state.pipeline_paused = False
        st.session_state.pipeline_status = "idle"
        st.rerun()

    for name in ("Employee Enablement Agent","Insight Routing Agent","Learning and Insights Agent"):
        st.markdown(pending_card_html(name), unsafe_allow_html=True)


def run_pipeline_phase2(signal: dict) -> None:
    """Resume pipeline after HITL decision (always Route 1 — Resolution path)."""
    st.markdown('<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:.75rem;">'
                '🤖 Agent Pipeline</h3>', unsafe_allow_html=True)

    decision          = st.session_state.hitl_decision
    detection_result  = st.session_state._partial_detection
    resolution_result = st.session_state._partial_resolution
    frontline_gap     = st.session_state._partial_frontline_gap
    action_taken      = st.session_state._partial_action
    urgency           = st.session_state.get("_partial_urgency", signal.get("urgency_score",3))
    pattern_risk      = st.session_state.get("_partial_pattern_risk","low")
    route             = st.session_state.get("_partial_route", "resolution")
    routing_label     = st.session_state.get("_partial_routing_label", "Single urgent customer case")
    routing_reason    = st.session_state.get("_partial_routing_reason", "")
    ts_sd             = st.session_state.get("_partial_ts_sd")
    ts_res            = st.session_state.get("_partial_ts_res")

    # ROUTING FIX — always Route 1 here (HITL is a sub-route of Resolution)
    st.markdown(routing_pathway_card_html(route, routing_label, routing_reason, urgency, pattern_risk),
                unsafe_allow_html=True)
    st.markdown(agent_card_html("Signal Detection Agent", detection_result, True, ts_sd), unsafe_allow_html=True)
    st.markdown(agent_card_html("Resolution Agent", resolution_result, True, ts_res), unsafe_allow_html=True)
    st.markdown(hitl_result_card_html(decision, action_taken), unsafe_allow_html=True)

    if decision == "approved":
        st.success("✅ Human approved — pipeline continuing…")
    else:
        st.warning("⚠️ Human rejected — case escalated to human representative. "
                   "Learning Agent records this override.")

    # Insight Routing is never called after HITL (we are on Route 1)
    slot_ir = st.empty()
    slot_ir.markdown(agent_card_html("Insight Routing Agent", None, False), unsafe_allow_html=True)

    slot_eea = st.empty(); slot_ln = st.empty()
    for slot, name in [(slot_eea,"Employee Enablement Agent"),(slot_ln,"Learning and Insights Agent")]:
        slot.markdown(pending_card_html(name), unsafe_allow_html=True)

    eea_result, learning_result, ts_eea, ts_ln = _run_post_hitl_agents(
        signal, detection_result, resolution_result,
        frontline_gap, decision,
        slot_eea, slot_ln,
    )
    insight_result = None; ts_ir = None

    results = {
        "signal_detection_output":    detection_result,
        "resolution_output":          resolution_result,
        "employee_enablement_output": eea_result,
        "insight_routing_output":     insight_result,
        "learning_output":            learning_result,
        "_meta_route":                route,
        "_meta_routing_label":        routing_label,
        "_meta_routing_reason":       routing_reason,
        "_meta_urgency":              urgency,
        "_meta_pattern_risk":         pattern_risk,
        "_meta_run_resolution":       True,
        "_meta_run_insight_routing":  False,
        "_meta_frontline_gap":        frontline_gap,
        "_meta_hitl_triggered":       True,
        "_meta_hitl_decision":        decision,
        "_meta_hitl_action":          action_taken,
        "_meta_ts_sd": ts_sd, "_meta_ts_res": ts_res,
        "_meta_ts_eea": ts_eea, "_meta_ts_ir": ts_ir, "_meta_ts_ln": ts_ln,
    }
    st.session_state.pipeline_results  = results
    st.session_state.pipeline_complete = True
    st.session_state.pipeline_status   = "complete"
    st.markdown(case_journey_summary_html(signal, results), unsafe_allow_html=True)


def display_pipeline_from_state(results: dict) -> None:
    """Re-render pipeline cards from stored state. FIX 5 — includes journey summary."""
    st.markdown('<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:.75rem;">'
                '🤖 Agent Pipeline</h3>', unsafe_allow_html=True)

    urgency        = results.get("_meta_urgency",3)
    pattern_risk   = results.get("_meta_pattern_risk","low")
    # ROUTING FIX — derive route from stored _meta_route (backward compat fallback)
    route          = results.get("_meta_route") or ("resolution" if results.get("_meta_run_resolution", True) else "insight")
    routing_label  = results.get("_meta_routing_label", "Single urgent customer case")
    routing_reason = results.get("_meta_routing_reason", "")
    run_resolution = (route == "resolution")

    st.markdown(routing_pathway_card_html(route, routing_label, routing_reason, urgency, pattern_risk),
                unsafe_allow_html=True)
    st.markdown(agent_card_html("Signal Detection Agent",
                                results.get("signal_detection_output"), True,
                                results.get("_meta_ts_sd")), unsafe_allow_html=True)
    st.markdown(agent_card_html("Resolution Agent",
                                results.get("resolution_output"), run_resolution,
                                results.get("_meta_ts_res")), unsafe_allow_html=True)

    if results.get("_meta_hitl_triggered"):
        st.markdown(hitl_result_card_html(results.get("_meta_hitl_decision",""),
                                          results.get("_meta_hitl_action","")), unsafe_allow_html=True)

    r_eea = results.get("employee_enablement_output")
    r_ir  = results.get("insight_routing_output")
    st.markdown(agent_card_html("Employee Enablement Agent", r_eea,
                                r_eea is not None, results.get("_meta_ts_eea")), unsafe_allow_html=True)
    st.markdown(agent_card_html("Insight Routing Agent", r_ir,
                                r_ir is not None, results.get("_meta_ts_ir")), unsafe_allow_html=True)
    st.markdown(agent_card_html("Learning and Insights Agent",
                                results.get("learning_output"), True,
                                results.get("_meta_ts_ln")), unsafe_allow_html=True)
    # FIX 5
    if st.session_state.signal:
        st.markdown(case_journey_summary_html(st.session_state.signal, results), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FIX 2 — Live Demo: results persist after completion
# ─────────────────────────────────────────────────────────────────────────────

def display_demo_results_from_state() -> None:
    """FIX 2 — Re-render all demo signal outputs from session_state.demo_results."""
    for i, r in enumerate(st.session_state.demo_results, 1):
        sig = r.get("signal", {})
        urg = sig.get("urgency_score",3); ut,ubg = urgency_color(urg)
        q   = sig.get("query","").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        q_s = (q[:200]+"…") if len(q)>200 else q

        st.markdown(
            f'<div style="background:#F5F3FF;border-radius:8px;padding:.65rem 1rem;'
            f'margin-bottom:.5rem;display:flex;align-items:center;gap:.75rem;">'
            f'<span style="background:#6D28D9;color:white;padding:2px 10px;border-radius:999px;'
            f'font-size:.75rem;font-weight:700;">Signal {i} of 5</span>'
            f'<span style="color:#64748B;font-size:.82rem;">{sig.get("label","")}</span></div>',
            unsafe_allow_html=True)

        st.markdown(
            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;'
            f'padding:.65rem 1rem;margin-bottom:.65rem;">'
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:.4rem;">'
            f'<span style="background:#DBEAFE;color:#1D4ED8;padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:600;">🌍 {sig.get("market","")}</span>'
            f'<span style="background:#EDE9FE;color:#6D28D9;padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:600;">🏷️ {sig.get("category","").replace("_"," ").title()}</span>'
            f'<span style="background:{ubg};color:{ut};padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:700;">⚡ Urgency {urg}</span>'
            f'</div><p style="color:#334155;font-size:.78rem;margin:0;line-height:1.5;">{q_s}</p></div>',
            unsafe_allow_html=True)

        urgency_v      = r.get("_meta_urgency", urg)
        pattern_risk_v = r.get("_meta_pattern_risk","low")
        # ROUTING FIX — derive route for display
        route_v         = r.get("_meta_route") or ("resolution" if r.get("_meta_run_resolution", True) else "insight")
        routing_label_v = r.get("_meta_routing_label", "Single urgent customer case")
        routing_reason_v= r.get("_meta_routing_reason", "")
        run_res_v       = (route_v == "resolution")

        st.markdown(routing_pathway_card_html(route_v, routing_label_v, routing_reason_v, urgency_v, pattern_risk_v),
                    unsafe_allow_html=True)
        st.markdown(agent_card_html("Signal Detection Agent", r.get("signal_detection_output"), True, r.get("_meta_ts_sd")), unsafe_allow_html=True)
        st.markdown(agent_card_html("Resolution Agent", r.get("resolution_output"), run_res_v, r.get("_meta_ts_res")), unsafe_allow_html=True)

        if r.get("_meta_hitl_triggered"):
            st.markdown(hitl_result_card_html(r.get("_meta_hitl_decision",""), r.get("_meta_hitl_action","")), unsafe_allow_html=True)

        r_eea = r.get("employee_enablement_output")
        r_ir  = r.get("insight_routing_output")
        st.markdown(agent_card_html("Employee Enablement Agent", r_eea, r_eea is not None, r.get("_meta_ts_eea")), unsafe_allow_html=True)
        st.markdown(agent_card_html("Insight Routing Agent", r_ir, r_ir is not None, r.get("_meta_ts_ir")), unsafe_allow_html=True)
        st.markdown(agent_card_html("Learning and Insights Agent", r.get("learning_output"), True, r.get("_meta_ts_ln")), unsafe_allow_html=True)
        st.markdown(case_journey_summary_html(sig, r), unsafe_allow_html=True)  # FIX 5

        if i < len(st.session_state.demo_results):
            st.markdown('<hr style="border:none;border-top:2px solid #EDE9FE;margin:1.25rem 0;">',
                        unsafe_allow_html=True)


def _run_live_demo() -> None:
    """
    FIX 2 — Runs all 5 signals, stores results in session_state.demo_results as they complete.
    Does NOT call st.rerun() — completion banner shown inline, then on next rerun
    display_demo_results_from_state() re-renders everything from state.
    """
    st.markdown("---")
    with st.spinner("Generating 5 demo signals via AI…"):
        signals = run_async(generate_demo_set())

    progress_bar = st.progress(0)
    step_slot    = st.empty()

    for i, signal in enumerate(signals, 1):
        step_slot.markdown(step_indicator_html(i, 5), unsafe_allow_html=True)
        progress_bar.progress(i / 5)

        st.markdown(
            f'<div style="background:#F5F3FF;border-radius:8px;padding:.65rem 1rem;'
            f'margin-bottom:.75rem;display:flex;align-items:center;gap:.75rem;">'
            f'<span style="background:#6D28D9;color:white;padding:2px 10px;border-radius:999px;'
            f'font-size:.75rem;font-weight:700;">Signal {i} of 5</span>'
            f'<span style="color:#64748B;font-size:.82rem;">{signal.get("label","")}</span></div>',
            unsafe_allow_html=True)

        urg = signal.get("urgency_score",3); ut,ubg = urgency_color(urg)
        q   = signal.get("query","").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        q_s = (q[:200]+"…") if len(q)>200 else q
        st.markdown(
            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;'
            f'padding:.65rem 1rem;margin-bottom:.75rem;">'
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:.4rem;">'
            f'<span style="background:#DBEAFE;color:#1D4ED8;padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:600;">🌍 {signal.get("market","")}</span>'
            f'<span style="background:#EDE9FE;color:#6D28D9;padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:600;">🏷️ {signal.get("category","").replace("_"," ").title()}</span>'
            f'<span style="background:{ubg};color:{ut};padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:700;">⚡ Urgency {urg}</span>'
            f'</div><p style="color:#334155;font-size:.78rem;margin:0;line-height:1.5;">{q_s}</p></div>',
            unsafe_allow_html=True)

        # FIX 1 — compute routing
        slot_sd = st.empty(); slot_route = st.empty(); slot_res = st.empty()
        slot_eea = st.empty(); slot_ir = st.empty(); slot_ln = st.empty()
        slot_journey = st.empty()
        for slot, name in [(slot_sd,"Signal Detection Agent"),(slot_res,"Resolution Agent"),
                           (slot_eea,"Employee Enablement Agent"),(slot_ir,"Insight Routing Agent"),
                           (slot_ln,"Learning and Insights Agent")]:
            slot.markdown(pending_card_html(name), unsafe_allow_html=True)

        slot_sd.markdown(running_card_html("Signal Detection Agent"), unsafe_allow_html=True)
        detection_result = run_async(signal_detection_agent(signal["query"]))
        ts_sd = _ts()
        slot_sd.markdown(agent_card_html("Signal Detection Agent", detection_result, True, ts_sd), unsafe_allow_html=True)

        try:
            dj = json.loads(detection_result)
            pattern_risk = str(dj.get("pattern_risk","low")).lower()
            urgency_v    = int(dj.get("urgency_score", urg))
        except Exception:
            pattern_risk = "low"; urgency_v = urg

        # ROUTING FIX — mutually exclusive ORC branches
        route, routing_label, routing_reason = compute_routing(urgency_v, pattern_risk)
        slot_route.markdown(
            routing_pathway_card_html(route, routing_label, routing_reason, urgency_v, pattern_risk),
            unsafe_allow_html=True)

        resolution_result = None; ts_res = None
        insight_result    = None; ts_ir  = None
        eea_result        = None; ts_eea = None
        frontline_gap = False; requires_human = False; action_taken = ""

        if route == "resolution":
            # SIGNAL PATH — Route 1 Resolution
            slot_res.markdown(running_card_html("Resolution Agent"), unsafe_allow_html=True)
            resolution_result = run_async(resolution_agent(detection_result))
            ts_res = _ts()
            slot_res.markdown(agent_card_html("Resolution Agent", resolution_result, True, ts_res), unsafe_allow_html=True)
            try:
                rj = json.loads(resolution_result)
                frontline_gap  = bool(rj.get("frontline_gap_detected",False))
                requires_human = bool(rj.get("requires_human",False))
                action_taken   = rj.get("action_taken","")
            except Exception:
                pass

            # In Live Demo: HITL is auto-approved to keep presentation flowing
            if requires_human:
                st.markdown(hitl_result_card_html("auto_approved_demo", action_taken), unsafe_allow_html=True)

            # Insight Routing not triggered on Route 1
            slot_ir.markdown(agent_card_html("Insight Routing Agent", None, False), unsafe_allow_html=True)

            # EEA (if frontline gap)
            if frontline_gap:
                slot_eea.markdown(running_card_html("Employee Enablement Agent"), unsafe_allow_html=True)
                eea_result = run_async(employee_enablement_agent(resolution_result or "{}"))
                ts_eea = _ts()
                slot_eea.markdown(agent_card_html("Employee Enablement Agent", eea_result, True, ts_eea), unsafe_allow_html=True)
            else:
                slot_eea.markdown(agent_card_html("Employee Enablement Agent", None, False), unsafe_allow_html=True)

            learning_input = json.dumps({
                "market": signal.get("market","Unknown"), "source": signal.get("source","unknown"),
                "category": signal.get("category","other"), "urgency_score": signal.get("urgency_score",3),
                "original_signal": signal["query"], "signal_detection_output": detection_result,
                "resolution_output": resolution_result, "employee_enablement_output": eea_result,
                "insight_routing_output": None,
                "hitl_triggered": requires_human,
                "hitl_decision": "auto_approved_demo" if requires_human else "not_triggered",
                "hitl_action_proposed": action_taken,
            })

        else:
            # SIGNAL PATH — Route 2 Insight only
            slot_res.markdown(agent_card_html("Resolution Agent", None, False), unsafe_allow_html=True)
            slot_eea.markdown(agent_card_html("Employee Enablement Agent", None, False), unsafe_allow_html=True)

            slot_ir.markdown(running_card_html("Insight Routing Agent"), unsafe_allow_html=True)
            insight_result = run_async(insight_routing_agent(detection_result))
            ts_ir = _ts()
            slot_ir.markdown(agent_card_html("Insight Routing Agent", insight_result, True, ts_ir), unsafe_allow_html=True)

            learning_input = json.dumps({
                "market": signal.get("market","Unknown"), "source": signal.get("source","unknown"),
                "category": signal.get("category","other"), "urgency_score": signal.get("urgency_score",3),
                "original_signal": signal["query"], "signal_detection_output": detection_result,
                "resolution_output": None, "employee_enablement_output": None,
                "insight_routing_output": insight_result,
            })

        slot_ln.markdown(running_card_html("Learning and Insights Agent"), unsafe_allow_html=True)
        learning_result = run_async(learning_insights_agent(learning_input))
        ts_ln = _ts()
        slot_ln.markdown(agent_card_html("Learning and Insights Agent", learning_result, True, ts_ln), unsafe_allow_html=True)

        r = {
            "signal": signal,
            "signal_detection_output":    detection_result,
            "resolution_output":          resolution_result,
            "employee_enablement_output": eea_result,
            "insight_routing_output":     insight_result,
            "learning_output":            learning_result,
            "_meta_route":                route,
            "_meta_routing_label":        routing_label,
            "_meta_routing_reason":       routing_reason,
            "_meta_urgency":              urgency_v,
            "_meta_pattern_risk":         pattern_risk,
            "_meta_run_resolution":       (route == "resolution"),
            "_meta_run_insight_routing":  (route == "insight"),
            "_meta_frontline_gap":        frontline_gap,
            "_meta_hitl_triggered":       requires_human,
            "_meta_hitl_decision":        "auto_approved_demo" if requires_human else "not_triggered",
            "_meta_hitl_action":          action_taken,
            "_meta_ts_sd": ts_sd, "_meta_ts_res": ts_res,
            "_meta_ts_eea": ts_eea, "_meta_ts_ir": ts_ir, "_meta_ts_ln": ts_ln,
        }
        st.session_state.demo_results = st.session_state.demo_results + [r]
        slot_journey.markdown(case_journey_summary_html(signal, r), unsafe_allow_html=True)

        if i < len(signals):
            st.markdown('<hr style="border:none;border-top:2px solid #EDE9FE;margin:1.25rem 0;">',
                        unsafe_allow_html=True)

    step_slot.markdown(step_indicator_html(6, 5), unsafe_allow_html=True)
    progress_bar.progress(1.0)
    st.session_state.demo_complete = True
    st.session_state.pipeline_status = "complete"
    # POLISH 2 — balloons on completion
    st.balloons()
    st.session_state.demo_balloons_shown = True


def render_live_demo_ui() -> None:
    """FIX 2 — Intro card always shown. After completion, results re-render from state."""
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1E1B4B 0%,#4C1D95 100%);'
        'border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;">'
        '<h2 style="color:white;margin:0 0 .2rem 0;font-size:1.05rem;font-weight:700;">'
        '🎬 Live Demo — Cosmic Pulse in Action</h2>'
        '<p style="color:#C4B5FD;margin:0;font-size:.82rem;">'
        '5 pre-built signals covering all routing paths. '
        'Runs automatically — no manual steps needed.</p></div>',
        unsafe_allow_html=True)

    urgency_cell = lambda u: (
        f'<span style="background:{"#FEE2E2" if u>=4 else "#FEF3C7" if u==3 else "#DCFCE7"};'
        f'color:{"#DC2626" if u>=4 else "#D97706" if u==3 else "#059669"};'
        f'padding:2px 9px;border-radius:999px;font-size:.72rem;font-weight:700;">{u}</span>')
    pattern_cell = lambda p: (
        f'<span style="background:{"#FEE2E2" if p=="high" else "#FEF3C7" if p=="medium" else "#DCFCE7"};'
        f'color:{"#DC2626" if p=="high" else "#D97706" if p=="medium" else "#059669"};'
        f'padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:600;">{p}</span>')
    # Route column color coding: Route 1 = green family, Route 2 = indigo
    _path_style = {
        "Route 1 — Resolution":          ("#059669", "#DCFCE7"),   # green
        "Route 1 — Resolution + EEA":    ("#0F766E", "#CCFBF1"),   # teal
        "Route 1 — Resolution + HITL":   ("#B45309", "#FEF3C7"),   # amber
        "Route 2 — Insight only":        ("#4338CA", "#E0E7FF"),   # indigo
    }
    def path_cell(path):
        tc, bg = _path_style.get(path, ("#64748B", "#F1F5F9"))
        return (f'<span style="background:{bg};color:{tc};padding:2px 9px;'
                f'border-radius:999px;font-size:.7rem;font-weight:600;">{path}</span>')
    rows_html = "".join(
        f'<tr style="border-top:1px solid #E2E8F0;">'
        f'<td style="padding:7px 12px;color:#64748B;font-weight:600;">{n}</td>'
        f'<td style="padding:7px 12px;color:#0F172A;font-weight:500;">{m}</td>'
        f'<td style="padding:7px 12px;color:#0F172A;">{c.replace("_"," ").title()}</td>'
        f'<td style="padding:7px 12px;">{urgency_cell(u)}</td>'
        f'<td style="padding:7px 12px;">{pattern_cell(p)}</td>'
        f'<td style="padding:7px 12px;">{path_cell(path)}</td></tr>'
        for n, m, c, u, p, path in DEMO_SIGNALS_META)
    st.markdown(
        '<table style="width:100%;border-collapse:collapse;font-size:.82rem;background:white;'
        'border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:1rem;">'
        '<thead><tr style="background:#F5F3FF;">'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">#</th>'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">Market</th>'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">Category</th>'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">Urgency</th>'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">Pattern</th>'
        '<th style="padding:8px 12px;text-align:left;color:#6D28D9;font-weight:700;">Path</th>'
        f'</tr></thead><tbody>{rows_html}</tbody></table>',
        unsafe_allow_html=True)

    if st.session_state.demo_complete:
        # FIX 2 — green completion banner stays visible
        st.markdown(
            '<div style="background:#F0FDF4;border:1px solid #10B981;border-radius:10px;'
            'padding:1rem 1.5rem;margin-bottom:1rem;display:flex;align-items:center;gap:.75rem;">'
            '<span style="font-size:1.4rem;">🎉</span>'
            '<div><div style="font-weight:700;color:#059669;font-size:.95rem;">'
            'Live Demo Complete — 5 signals processed</div>'
            '<div style="font-size:.78rem;color:#64748B;margin-top:2px;">'
            'All results visible below and in the Results tab.</div></div></div>',
            unsafe_allow_html=True)

        # FIX 2 — re-render all 5 signal pipeline outputs from state
        display_demo_results_from_state()

        # Summary table
        results_list = st.session_state.demo_results
        if results_list:
            sum_rows = "".join(
                f'<tr style="border-top:1px solid #E2E8F0;">'
                f'<td style="padding:7px 12px;color:#64748B;">{idx}</td>'
                f'<td style="padding:7px 12px;color:#0F172A;">{r.get("signal",{}).get("market","—")}</td>'
                f'<td style="padding:7px 12px;color:#0F172A;">{r.get("signal",{}).get("category","—").replace("_"," ").title()}</td>'
                f'<td style="padding:7px 12px;text-align:center;">'
                f'<span style="background:#EDE9FE;color:#6D28D9;padding:2px 9px;border-radius:999px;font-size:.72rem;font-weight:600;">'
                f'{sum([1,1,1 if r.get("employee_enablement_output") else 0,1 if r.get("insight_routing_output") else 0,1])}</span></td>'
                f'<td style="padding:7px 12px;">'
                f'<span style="background:{"#FEF3C7" if r.get("_meta_hitl_triggered") else "#F1F5F9"};'
                f'color:{"#B45309" if r.get("_meta_hitl_triggered") else "#64748B"};'
                f'padding:2px 9px;border-radius:999px;font-size:.72rem;font-weight:600;">'
                f'{"Yes" if r.get("_meta_hitl_triggered") else "No"}</span></td></tr>'
                for idx, r in enumerate(results_list, 1))
            st.markdown(
                '<table style="width:100%;border-collapse:collapse;font-size:.82rem;background:white;'
                'border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-top:1rem;">'
                '<thead><tr style="background:#F5F3FF;">'
                '<th style="padding:8px 12px;text-align:left;color:#6D28D9;">#</th>'
                '<th style="padding:8px 12px;text-align:left;color:#6D28D9;">Market</th>'
                '<th style="padding:8px 12px;text-align:left;color:#6D28D9;">Category</th>'
                '<th style="padding:8px 12px;text-align:center;color:#6D28D9;">Agents</th>'
                '<th style="padding:8px 12px;text-align:left;color:#6D28D9;">HITL</th>'
                f'</tr></thead><tbody>{sum_rows}</tbody></table>',
                unsafe_allow_html=True)

        if st.button("🔄 Run Demo Again", use_container_width=True, key="run_demo_again_btn"):
            st.session_state.demo_complete        = False
            st.session_state.demo_results         = []
            st.session_state.demo_balloons_shown  = False
            st.session_state.pipeline_status      = "idle"
            st.rerun()
    else:
        if st.button("🚀 Start Live Demo", use_container_width=True, type="primary", key="start_demo_btn"):
            _run_live_demo()


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def render_signal_preview(signal: dict) -> None:
    st.markdown('<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:.65rem;">'
                '📡 Signal Preview</h3>', unsafe_allow_html=True)
    urg = signal.get("urgency_score",3); ut,ubg = urgency_color(urg)
    src = signal.get("source","unknown").replace("_"," ").title()
    cat = signal.get("category","other").replace("_"," ").title()
    mkt = signal.get("market","Unknown")
    q   = signal.get("query","").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    st.markdown(
        f'<div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:.65rem;">'
        f'<span style="background:#DBEAFE;color:#1D4ED8;padding:3px 11px;border-radius:999px;font-size:.75rem;font-weight:600;">🌍 {mkt}</span>'
        f'<span style="background:#EDE9FE;color:#6D28D9;padding:3px 11px;border-radius:999px;font-size:.75rem;font-weight:600;">📡 {src}</span>'
        f'<span style="background:#F0FDF4;color:#059669;padding:3px 11px;border-radius:999px;font-size:.75rem;font-weight:600;">🏷️ {cat}</span>'
        f'<span style="background:{ubg};color:{ut};padding:3px 11px;border-radius:999px;font-size:.75rem;font-weight:700;">⚡ Urgency {urg}</span>'
        f'</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;'
        f'padding:.9rem 1.1rem;font-size:.875rem;line-height:1.75;color:#0F172A;">{q}</div>',
        unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


def render_cxo_dashboard(learning_result_str: str) -> None:
    try:    data = json.loads(learning_result_str) if learning_result_str else {}
    except: st.warning("⚠️ Could not parse Learning Agent output."); return

    cxo = data.get("cxo_insight",{})
    if isinstance(cxo,str):
        try: cxo = json.loads(cxo)
        except: cxo = {}

    sentiment = str(cxo.get("sentiment_trend","stable")).lower().strip()
    cost      = str(cxo.get("cost_trend","stable")).lower().strip()
    demand    = str(cxo.get("demand_signal","No signal"))
    dd        = (demand[:120]+"…") if len(demand)>123 else demand

    sp = {"deteriorating":("#DC2626","📉"),"improving":("#059669","📈"),"stable":("#D97706","➡️")}
    cp = {"increasing":("#DC2626","💸"),"decreasing":("#059669","💰"),"stable":("#D97706","💵")}
    sc,si = sp.get(sentiment,("#64748B","📊"))
    cc,ci = cp.get(cost,("#64748B","💵"))

    def _m(icon,label,value,color):
        return (f'<div style="background:rgba(255,255,255,.95);border-radius:8px;padding:1rem;text-align:center;">'
                f'<div style="font-size:1.5rem;margin-bottom:.25rem;">{icon}</div>'
                f'<div style="font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.25rem;">{label}</div>'
                f'<div style="font-size:.85rem;font-weight:600;color:{color};">{value}</div></div>')

    tags = data.get("tags",[])
    risk = str(data.get("repeat_risk","low")).lower()
    rc_map = {"high":("#DC2626","rgba(254,226,226,.9)"),"medium":("#D97706","rgba(254,243,199,.9)"),"low":("#059669","rgba(220,252,231,.9)")}
    rc,rbg = rc_map.get(risk,("#64748B","rgba(241,245,249,.9)"))
    tags_html = "".join(
        f'<span style="background:rgba(255,255,255,.18);color:white;padding:2px 9px;'
        f'border-radius:999px;font-size:.7rem;margin:2px;display:inline-block;">{t}</span>'
        for t in (tags if isinstance(tags,list) else []))

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1E1B4B 0%,#4C1D95 100%);'
        f'border-radius:12px;padding:1.5rem;margin-top:1.25rem;">'
        f'<h3 style="color:white;margin:0 0 1rem 0;font-size:.78rem;font-weight:600;'
        f'letter-spacing:.1em;text-transform:uppercase;">📊 CXO Visibility Dashboard</h3>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.75rem;">'
        + _m(si,"Customer Sentiment",sentiment.title(),sc)
        + _m(ci,"Cost to Serve",cost.title(),cc)
        + _m("📊","Demand Signal",dd,"#0F172A")
        + f'</div><div style="margin-top:1rem;display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;">'
        f'<span style="background:{rbg};color:{rc};padding:3px 12px;border-radius:999px;'
        f'font-size:.75rem;font-weight:700;">Repeat Risk: {risk.upper()}</span>'
        f'{tags_html}</div></div>',
        unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


def render_results_tab(results, demo_results=None) -> None:
    """POLISH 4 — metrics row at the top."""
    all_results_list = demo_results if demo_results else ([results] if results else [])

    # POLISH 4 — metrics row
    if all_results_list:
        total    = len(all_results_list)
        hitl_ct  = sum(1 for r in all_results_list if r.get("_meta_hitl_triggered"))
        high_rr  = 0
        for r in all_results_list:
            lr = r.get("learning_output","")
            if lr:
                try:
                    rr = json.loads(lr).get("repeat_risk","").lower()
                    if rr == "high": high_rr += 1
                except Exception: pass
        markets  = len({r.get("signal",r).get("market","?") if isinstance(r.get("signal"), dict) else "?"
                        for r in all_results_list})
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Signals Processed", total)
        c2.metric("HITL Triggered",    hitl_ct)
        c3.metric("High Repeat Risk",  high_rr)
        c4.metric("Markets Covered",   markets)
        st.markdown("---")

    if demo_results:
        st.markdown('<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:1rem;">'
                    '📋 Live Demo — All 5 Signal Outputs</h3>', unsafe_allow_html=True)
        for i, r in enumerate(demo_results, 1):
            sig = r.get("signal",{})
            label = (f"Signal {i} — {sig.get('market','?')} / "
                     f"{sig.get('category','?').replace('_',' ').title()} / "
                     f"Urgency {sig.get('urgency_score','?')}")
            with st.expander(label, expanded=(i==1)):
                for lbl,key in [("🔵 Signal Detection Agent","signal_detection_output"),
                                 ("🟢 Resolution Agent","resolution_output"),
                                 ("🩵 Employee Enablement Agent","employee_enablement_output"),
                                 ("🔷 Insight Routing Agent","insight_routing_output"),
                                 ("🟣 Learning and Insights Agent","learning_output")]:
                    raw = r.get(key)
                    if raw:
                        with st.expander(lbl, expanded=False):
                            try: st.json(json.loads(raw))
                            except: st.code(raw)
                    else:
                        with st.expander(f"{lbl} — not triggered", expanded=False):
                            st.caption("Not triggered for this signal.")
        return

    if not results:
        st.info("Run the pipeline first to see full agent outputs here.", icon="📋")
        return

    st.markdown('<h3 style="color:#0F172A;font-size:1rem;font-weight:700;margin-bottom:1rem;">'
                '📋 Full Agent Outputs</h3>', unsafe_allow_html=True)
    for label, key in [("🔵 Signal Detection Agent","signal_detection_output"),
                        ("🟢 Resolution Agent","resolution_output"),
                        ("🩵 Employee Enablement Agent","employee_enablement_output"),
                        ("🔷 Insight Routing Agent","insight_routing_output"),
                        ("🟣 Learning and Insights Agent","learning_output")]:
        raw = results.get(key)
        if raw:
            with st.expander(label, expanded=False):
                try: st.json(json.loads(raw))
                except: st.code(raw)
        else:
            with st.expander(f"{label} — not triggered", expanded=False):
                st.caption("This agent was not invoked for this signal.")

    if results.get("_meta_hitl_triggered"):
        st.markdown("---"); st.markdown("**⚖️ Human Governance Record**")
        c1,c2,c3 = st.columns(3)
        c1.metric("Decision", results.get("_meta_hitl_decision","—").replace("_"," ").title())
        c2.metric("Action Proposed", results.get("_meta_hitl_action","—"))
        c3.metric("HITL Triggered","Yes")


# ABOUT FIX — live mermaid diagram and full rewrite
def render_about_tab() -> None:

    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1E1B4B, #6D28D9);
                border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
      <h2 style="color:white; margin:0; font-size:1.25rem; font-weight:700;">
        Cosmic Pulse — System Architecture
      </h2>
      <p style="color:#C4B5FD; margin:0.5rem 0 0; font-size:0.875rem;">
        Agentic AI Customer Experience Orchestration for Cosmic Mart
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Live Mermaid diagram
    st.markdown("#### System Diagram")
    if MERMAID_AVAILABLE:
        st_mermaid(COSMIC_PULSE_DIAGRAM, height=700)
    else:
        st.info(
            "Install streamlit-mermaid to render the interactive "
            "diagram: `pip install streamlit-mermaid`"
        )
        st.code(COSMIC_PULSE_DIAGRAM, language="text")

    st.divider()

    # Two columns: system overview + routing rules / agent descriptions
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### What Cosmic Pulse Does")
        st.markdown("""
        Cosmic Pulse is a **multi-agent AI system** that proactively
        manages customer experience for Cosmic Mart — a global retail
        brand serving 144 million customers across 10 markets.

        Instead of waiting for complaints to escalate, it continuously
        monitors signals, diagnoses root causes, and routes to the
        right resolution path automatically.
        """)

        st.markdown("#### The Two Routing Paths")
        st.markdown("""
        <div style="border-left: 3px solid #2563EB; padding: 0.75rem 1rem;
                    background:#EFF6FF; border-radius:0 8px 8px 0;
                    margin-bottom:0.75rem;">
          <div style="font-weight:600; color:#1D4ED8; font-size:0.875rem;">
            Route 1 — Single urgent customer case
          </div>
          <div style="color:#1E293B; font-size:0.8rem; margin-top:0.25rem;">
            urgency_score 4 or 5 → Resolution Agent<br/>
            Sub-routes triggered by Resolution output:<br/>
            &nbsp;&nbsp;· HITL: requires_human = true → Approve / Reject<br/>
            &nbsp;&nbsp;· EEA: frontline_gap_detected = true → Employee Enablement
          </div>
        </div>
        <div style="border-left: 3px solid #4F46E5; padding: 0.75rem 1rem;
                    background:#EEF2FF; border-radius:0 8px 8px 0;">
          <div style="font-weight:600; color:#4338CA; font-size:0.875rem;">
            Route 2 — Repeated pattern across customers
          </div>
          <div style="color:#1E293B; font-size:0.8rem; margin-top:0.25rem;">
            urgency ≤ 3 + pattern_risk medium or high<br/>
            → Insight Routing Agent only<br/>
            Resolution Agent: NOT called · EEA: NOT called
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### HITL Demo Tips")
        st.markdown("""
        In **Quick Generate** mode, set **North America / service_delay /
        Urgency 5 / Pattern low** — reliably triggers `requires_human: true`.

        Click **Approve** → watch pipeline resume and Learning Agent record
        the outcome. Click **Reject** → escalation path is recorded.
        """)

    with col2:
        st.markdown("#### Agent Descriptions")

        agents = [
            ("Signal Detection Agent", "#2563EB", "#DBEAFE",
             "Reads raw customer messages and classifies them into "
             "structured signals with sentiment, category, urgency "
             "score (1–5), and pattern risk. Scores are based on "
             "specific language signals in the text, not general tone."),
            ("Cosmic Pulse Orchestrator", "#6D28D9", "#EDE9FE",
             "Receives the structured signal and makes the routing "
             "decision — Resolution or Insight Routing — based on "
             "urgency and pattern risk. Strictly mutually exclusive."),
            ("Resolution Agent", "#059669", "#DCFCE7",
             "Runs resolution playbooks for urgent individual cases. "
             "Issues refunds, simplifies returns, escalates to humans "
             "for high-impact actions, detects frontline policy gaps."),
            ("Employee Enablement Agent", "#0F766E", "#CCFBF1",
             "Optional. Triggered when Resolution detects a frontline "
             "knowledge gap (frontline_gap_detected = true). Delivers "
             "just-in-time policy guidance to staff through their "
             "existing workflows."),
            ("Insight Routing Agent", "#3730A3", "#E0E7FF",
             "Synthesises repeated patterns across multiple customers "
             "and sends targeted insight briefs to the right business "
             "team — Pricing (T1), Store Ops (T2), Merchandising (T3), "
             "Returns (T4), or Support Leadership (T5)."),
            ("Learning Agent", "#334155", "#F1F5F9",
             "Runs after every case. Updates Resolution playbooks and "
             "Insight brief templates based on what worked and what "
             "failed. Feeds trends and drivers to the CXO dashboard."),
            ("Human-in-the-Loop Governance", "#B45309", "#FEF3C7",
             "Pauses the pipeline when Resolution flags a high-impact "
             "action (requires_human = true). A human must approve or "
             "reject before the action executes in Enterprise Systems."),
        ]

        for name, color, bg, desc in agents:
            st.markdown(f"""
            <div style="border-left: 3px solid {color};
                        background: {bg};
                        border-radius: 0 8px 8px 0;
                        padding: 0.6rem 0.875rem;
                        margin-bottom: 0.5rem;">
              <div style="font-weight: 600; color: {color};
                          font-size: 0.8rem;">
                {name}
              </div>
              <div style="color: #1E293B; font-size: 0.75rem;
                          margin-top: 0.2rem; line-height: 1.4;">
                {desc}
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Tech stack
    st.markdown("#### Tech Stack")
    cols = st.columns(4)
    stack = [
        ("Accenture AI Refinery SDK", "Agent orchestration + LLM calls"),
        ("openai/gpt-oss-120b", "Model for all five agents"),
        ("Python 3.12 + Streamlit", "Backend pipeline + demo UI"),
        ("streamlit-mermaid", "Interactive architecture diagram"),
    ]
    for col, (tech, role) in zip(cols, stack):
        with col:
            st.markdown(f"""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0;
                        border-radius:8px; padding:0.875rem;
                        text-align:center;">
              <div style="font-weight:600; color:#1E1B4B;
                          font-size:0.8rem;">{tech}</div>
              <div style="color:#64748B; font-size:0.7rem;
                          margin-top:0.2rem;">{role}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; color:#94A3B8;
                font-size:0.75rem; margin-top:1.5rem;">
      Team Chicago · Cosmic Mart Agentic AI Hackathon · Cohort 4 FY26 ·
      Accenture AI Intensive
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MODERN UI — Page header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:linear-gradient(135deg,#1E1B4B 0%,#6D28D9 100%);'
    'padding:1.1rem 1.5rem;border-radius:12px;margin-bottom:1.25rem;'
    'display:flex;align-items:center;gap:1rem;">'
    '<div style="width:42px;height:42px;background:rgba(255,255,255,.15);border-radius:10px;'
    'display:flex;align-items:center;justify-content:center;font-size:1.3rem;flex-shrink:0;">🌌</div>'
    '<div><h1 style="color:white;margin:0;font-size:1.35rem;font-weight:700;letter-spacing:-.02em;">'
    'Cosmic Pulse</h1>'
    '<p style="color:#C4B5FD;margin:0;font-size:.78rem;">Customer Experience Orchestration — Cosmic Mart</p></div>'
    '<div style="margin-left:auto;flex-shrink:0;">'
    '<span style="background:rgba(255,255,255,.12);color:white;padding:4px 12px;'
    'border-radius:999px;font-size:.7rem;font-weight:500;">Powered by Accenture AI Refinery</span>'
    '</div></div>',
    unsafe_allow_html=True)

# POLISH 1 — thin animated progress bar at the very top of the viewport
_pct = int(st.session_state.pipeline_progress * 100)
if _pct > 0:
    st.markdown(f'<div class="progress-bar-top" style="width:{_pct}%;"></div>',
                unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Two-column layout
# ─────────────────────────────────────────────────────────────────────────────
col_ctrl, col_main = st.columns([1, 2.6], gap="large")

# ── Left column — control panel ───────────────────────────────────────────────
with col_ctrl:
    st.markdown(
        '<div style="background:#1E1B4B;border-radius:12px;padding:1rem .9rem .25rem .9rem;">'
        '<p style="color:#C4B5FD;font-size:.65rem;font-weight:700;'
        'text-transform:uppercase;letter-spacing:.1em;margin:0 0 .6rem 0;">MODE</p>',
        unsafe_allow_html=True)

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        if st.button("🎬 Live", use_container_width=True, key="mode_live",
                     type="primary" if st.session_state.mode=="Live Demo" else "secondary"):
            if st.session_state.mode != "Live Demo":
                st.session_state.mode = "Live Demo"; st.rerun()
    with mc2:
        if st.button("⚡ Quick", use_container_width=True, key="mode_quick",
                     type="primary" if st.session_state.mode=="Quick Generate" else "secondary"):
            if st.session_state.mode != "Quick Generate":
                st.session_state.mode = "Quick Generate"; st.rerun()
    with mc3:
        if st.button("✏️ Manual", use_container_width=True, key="mode_manual",
                     type="primary" if st.session_state.mode=="Manual Input" else "secondary"):
            if st.session_state.mode != "Manual Input":
                st.session_state.mode = "Manual Input"; st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")

    run_clicked = False

    if st.session_state.mode == "Live Demo":
        st.markdown('<p style="font-size:.8rem;color:#64748B;line-height:1.6;margin:0;">'
                    'Runs 5 pre-built signals automatically. '
                    'Perfect for judge presentations — no manual steps needed.</p>',
                    unsafe_allow_html=True)

    elif st.session_state.mode == "Quick Generate":
        market       = st.selectbox("Market",       MARKETS,                    key="ld_market")
        source       = st.selectbox("Source",       SOURCES,                    key="ld_source")
        category     = st.selectbox("Category",     CATEGORIES,                 key="ld_category")
        urgency      = st.slider("Urgency", 1, 5, 3,                            key="ld_urgency")
        # ROOT FIX 3 — pattern_risk controls generated text calibration AND routing
        pattern_risk = st.selectbox("Pattern Risk", ["low", "medium", "high"],  key="ld_pattern")
        st.caption("low → Route 1 (Resolution) · medium/high + urgency ≤ 3 → Route 2 (Insight)")

        if st.button("🎲 Generate Signal", use_container_width=True, key="gen_btn"):
            with st.spinner("Generating…"):
                gen = run_async(generate_signal(market, source, category, urgency, pattern_risk))
            st.session_state.signal            = gen
            st.session_state.pipeline_complete = False
            st.session_state.pipeline_results  = {}
            st.session_state.hitl_triggered    = False
            st.session_state.hitl_approved     = None
            st.session_state.hitl_decision     = "not_triggered"
            st.session_state.pipeline_paused   = False
            st.session_state.pipeline_status   = "idle"
            st.session_state.pipeline_progress = 0.0
            st.success("✓ Signal ready")

        st.markdown("---")
        run_clicked = st.button("🚀 Run Pipeline", use_container_width=True, type="primary",
                                disabled=(st.session_state.signal is None), key="run_btn_quick")
        # POLISH 3 — keyboard shortcut hint
        st.markdown('<p style="font-size:.68rem;color:#94A3B8;text-align:center;margin-top:4px;">'
                    'Generate a signal first, then Run</p>', unsafe_allow_html=True)

    else:  # Manual Input
        manual_text = st.text_area("Customer signal", height=120,
                                   placeholder="e.g. My order still hasn't arrived…",
                                   key="manual_text_input")
        mi_market = st.selectbox("Market", MARKETS, key="mi_market")
        if manual_text and manual_text.strip():
            new_sig = {"label":f"Manual — {mi_market}","market":mi_market,
                       "source":"support_ticket","category":"other",
                       "urgency_score":3,"query":manual_text.strip()}
            prev = st.session_state.signal
            if (prev is None or prev.get("query")!=new_sig["query"]
                    or prev.get("market")!=new_sig["market"]):
                st.session_state.signal            = new_sig
                st.session_state.pipeline_complete = False
                st.session_state.pipeline_results  = {}
                st.session_state.hitl_triggered    = False
                st.session_state.hitl_approved     = None
                st.session_state.hitl_decision     = "not_triggered"
                st.session_state.pipeline_paused   = False
                st.session_state.pipeline_status   = "idle"
                st.session_state.pipeline_progress = 0.0
        elif not (manual_text or "").strip():
            if st.session_state.signal and str(st.session_state.signal.get("label","")).startswith("Manual"):
                st.session_state.signal = None
                st.session_state.pipeline_complete = False
                st.session_state.pipeline_results  = {}

        st.markdown("---")
        run_clicked = st.button("🚀 Run Pipeline", use_container_width=True, type="primary",
                                disabled=(st.session_state.signal is None), key="run_btn_manual")
        # POLISH 3 — keyboard shortcut hint
        st.markdown('<p style="font-size:.68rem;color:#94A3B8;text-align:center;margin-top:4px;">'
                    'Paste a signal above, then Run</p>', unsafe_allow_html=True)

    st.markdown("---")

    _status = st.session_state.pipeline_status
    if _status == "paused_hitl":
        st.markdown('<div style="background:#FEF3C7;border:1px solid #F59E0B;border-radius:8px;'
                    'padding:.5rem .75rem;"><span style="font-weight:700;font-size:.8rem;'
                    'color:#B45309;">⚠️ Awaiting approval</span></div>', unsafe_allow_html=True)
    elif _status == "complete" or st.session_state.demo_complete:
        st.markdown('<div style="background:#DCFCE7;border:1px solid #10B981;border-radius:8px;'
                    'padding:.5rem .75rem;"><span style="font-weight:700;font-size:.8rem;'
                    'color:#059669;">✓ Complete</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    if st.button("🔄 Reset", use_container_width=True, key="reset_btn"):
        for _k in list(st.session_state.keys()):
            del st.session_state[_k]
        st.rerun()

    if (st.session_state.pipeline_complete and st.session_state.pipeline_results
            and st.session_state.mode != "Live Demo"):
        st.download_button("📥 Download Results",
                           data=json.dumps({"signal": st.session_state.signal,
                                            "pipeline_results": st.session_state.pipeline_results}, indent=2),
                           file_name="cosmic_pulse_results.json", mime="application/json",
                           use_container_width=True)
    elif st.session_state.demo_complete and st.session_state.demo_results:
        st.download_button("📥 Download All 5 Results",
                           data=json.dumps({"demo_results": st.session_state.demo_results},
                                           indent=2, default=str),
                           file_name="cosmic_pulse_demo_results.json", mime="application/json",
                           use_container_width=True)

# ── Right column — tabs ───────────────────────────────────────────────────────
with col_main:
    tab_pipeline, tab_results, tab_about = st.tabs(["🤖 Pipeline","📋 Results","ℹ️ About"])

    with tab_pipeline:
        if st.session_state.mode == "Live Demo":
            render_live_demo_ui()

        else:
            if st.session_state.signal:
                render_signal_preview(st.session_state.signal)
            else:
                st.markdown(
                    '<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;'
                    'padding:2.5rem 2rem;text-align:center;margin-top:.5rem;">'
                    '<div style="font-size:2.75rem;margin-bottom:.75rem;">🌌</div>'
                    '<h3 style="color:#6D28D9;margin-bottom:.5rem;font-size:1rem;">Welcome to Cosmic Pulse</h3>'
                    '<p style="color:#64748B;max-width:420px;margin:0 auto;line-height:1.7;font-size:.875rem;">'
                    'Use the control panel on the left — generate or paste a signal, then click Run Pipeline.</p>'
                    '</div>', unsafe_allow_html=True)

            st.markdown("---")

            # FIX 3 — Pipeline state machine with genuine HITL pause
            if run_clicked and st.session_state.signal:
                for _k in ["_partial_detection","_partial_resolution","_partial_route",
                           "_partial_routing_label","_partial_routing_reason",
                           "_partial_frontline_gap","_partial_action","_partial_customer_msg",
                           "_partial_urgency","_partial_pattern_risk","_partial_ts_sd","_partial_ts_res"]:
                    st.session_state.pop(_k, None)
                st.session_state.pipeline_complete = False
                st.session_state.pipeline_results  = {}
                st.session_state.hitl_triggered    = False
                st.session_state.hitl_approved     = None
                st.session_state.hitl_decision     = "not_triggered"
                st.session_state.pipeline_paused   = False
                st.session_state.pipeline_status   = "idle"
                st.session_state.pipeline_progress = 0.0

                run_pipeline_ui(st.session_state.signal)
                if st.session_state.pipeline_complete:
                    render_cxo_dashboard(st.session_state.pipeline_results.get("learning_output",""))

            # FIX 3 — HITL pending: show governance card and STOP
            elif (st.session_state.pipeline_paused
                  and st.session_state.hitl_decision == "pending"):
                render_hitl_paused_ui()
                st.stop()  # FIX 3 — genuinely halt script execution here

            # FIX 3 — decision made: run phase 2
            elif (st.session_state.hitl_triggered
                  and not st.session_state.pipeline_paused
                  and st.session_state.hitl_decision in ("approved","rejected")
                  and not st.session_state.pipeline_complete):
                run_pipeline_phase2(st.session_state.signal or st.session_state.current_signal)
                if st.session_state.pipeline_complete:
                    render_cxo_dashboard(st.session_state.pipeline_results.get("learning_output",""))

            elif st.session_state.pipeline_complete and st.session_state.pipeline_results:
                display_pipeline_from_state(st.session_state.pipeline_results)
                render_cxo_dashboard(st.session_state.pipeline_results.get("learning_output",""))

    with tab_results:
        if st.session_state.mode == "Live Demo" and st.session_state.demo_complete:
            render_results_tab(None, demo_results=st.session_state.demo_results)
        elif st.session_state.pipeline_complete and st.session_state.pipeline_results:
            render_results_tab(st.session_state.pipeline_results)
        else:
            st.info("Run the pipeline first to see full agent outputs here.", icon="📋")

    with tab_about:
        render_about_tab()
