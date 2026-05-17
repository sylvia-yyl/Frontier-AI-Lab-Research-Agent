import streamlit as st
import sys
import json
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="Frontier AI Lab Research Agent",
    layout="wide",
    page_icon="🔬",
)

st.title("🔬 Frontier AI Lab Research Agent")
st.caption("An agent that autonomously researches AI labs, validates sources, and critiques its own output.")

# ── Sidebar ───────────────────────────────────────────────────────────────────
LABS = ["DeepSeek", "OpenAI", "Anthropic", "Google DeepMind", "Meta AI", "Mistral", "xAI", "Cohere"]

with st.sidebar:
    st.header("Target Lab")
    choice = st.radio("", LABS + ["Custom..."], label_visibility="collapsed")
    if choice == "Custom...":
        lab_name = st.text_input("Lab name", placeholder="e.g. Cohere")
    else:
        lab_name = choice

    st.divider()
    run_btn = st.button(
        "▶ Run Research",
        type="primary",
        use_container_width=True,
        disabled=not lab_name,
    )

    st.divider()
    st.markdown("📖 **[Pipeline Guide →](Pipeline_Guide)**")
    st.caption("Explains T1/T2/T3 tiers, gate checks, critic scoring, and the full agent architecture.")

if not run_btn:
    st.info("Select a lab in the sidebar and click **Run Research**.")
    st.stop()

# ── Pipeline execution ────────────────────────────────────────────────────────

def _fmt(line: str) -> str:
    """Format an agent trace line for display."""
    if not line or set(line) <= {"=", "-", " "}:
        return "---"
    for t, b in [("T1", "🟢 **T1**"), ("T2", "🟡 **T2**"), ("T3", "🔴 **T3**")]:
        line = line.replace(f"tier={t}", f"tier={b}")
    for g, b in [("PASS", "✅ PASS"), ("FLAG", "⚠️ FLAG"), ("BLOCK", "🚫 BLOCK")]:
        line = line.replace(f"Gate: {g}", f"Gate: {b}")
    if "[Step" in line and "Thought:" in line:
        return f"**🔍 {line}**"
    if "Observation:" in line:
        return f"&nbsp;&nbsp;👁️ {line}"
    if "Content preview:" in line:
        return f"&nbsp;&nbsp;&nbsp;&nbsp;_{line}_"
    if "AGENT START" in line or "PIPELINE START" in line:
        return f"#### {line}"
    if "AGENT COMPLETE" in line or "Pipeline Complete" in line:
        return f"✅ **{line}**"
    if "CP1 PASSED" in line:
        return f"✅ {line}"
    if "Critic Scores" in line:
        return f"**⚖️ {line}**"
    if "Verdict:" in line:
        return f"**{line}**"
    if "Sufficient PASS-grade" in line:
        return f"✅ {line}"
    return line


trace_lines: list[str] = []

# Placeholder shown while running; replaced by expander after completion
running_placeholder = st.empty()

with running_placeholder:
    st.info(f"🤖 Researching **{lab_name}**… please wait.")

# Live trace display (updates during run)
live_trace = st.empty()

class _Capture:
    def write(self, text):
        for raw in text.split("\n"):
            raw = raw.strip()
            if raw:
                trace_lines.append(_fmt(raw))
                live_trace.markdown("\n\n".join(trace_lines))

    def flush(self):
        pass

_orig = sys.stdout
sys.stdout = _Capture()
_err = None
try:
    from main import run as _run  # noqa: PLC0415
    _run(lab_name)
except Exception as e:
    _err = e
finally:
    sys.stdout = _orig

# Replace live trace with a permanent expander containing the full history
live_trace.empty()
running_placeholder.empty()

if _err:
    st.error(f"Pipeline error: {_err}")
    with st.expander("🤖 Agent trace (failed)", expanded=True):
        st.markdown("\n\n".join(trace_lines))
    st.stop()

with st.expander("🤖 Agent trace — click to expand", expanded=False):
    st.markdown("\n\n".join(trace_lines))

if _err:
    st.error(f"Pipeline error: {_err}")
    st.stop()

# ── Load output JSON ──────────────────────────────────────────────────────────
output_dir = Path("output")
today = date.today().isoformat()
candidates = list(output_dir.glob(f"*{today}.json")) if output_dir.exists() else []
if not candidates:
    st.warning("Output file not found — pipeline may have aborted early.")
    st.stop()

output_path = max(candidates, key=lambda p: p.stat().st_mtime)
with open(output_path, encoding="utf-8") as f:
    data = json.load(f)

# ── Critic scores ─────────────────────────────────────────────────────────────
st.divider()
st.markdown("## ⚖️ Critic Review")

scores = data.get("critic_scores", {})
total = data.get("critic_total", 0)
verdict = data.get("verdict", "?")

c1, c2, c3, c4, c5 = st.columns(5)
for col, (key, label) in zip(
    [c1, c2, c3, c4],
    [
        ("claim_coverage", "Claim Coverage"),
        ("counter_evidence", "Counter Evidence"),
        ("logic_chain", "Logic Chain"),
        ("staleness_risk", "Staleness Risk"),
    ],
):
    col.metric(label, f"{scores.get(key, 0)}/10")

if verdict == "PASS":
    c5.metric("Total", f"{total}/40", delta="PASS ✅")
else:
    c5.metric("Total", f"{total}/40", delta="RETRY ⚠️", delta_color="inverse")

if data.get("quality_flag") == "HUMAN_REVIEW_REQUIRED":
    st.warning("⚠️ **Human review required** — critic score below threshold after max retries.")

if data.get("weak_areas"):
    with st.expander("Weak areas identified by critic"):
        for area in data["weak_areas"]:
            st.markdown(f"• {area}")

# ── Research brief ────────────────────────────────────────────────────────────
st.divider()
st.markdown("## 📄 Research Brief")
st.markdown(data.get("brief", "_No brief generated._"))

# ── Data registry ─────────────────────────────────────────────────────────────
st.divider()
st.markdown("## 🗂️ Data Registry")

registry = data.get("data_registry", [])
if registry:
    tier_map = {"T1": "🟢 T1", "T2": "🟡 T2", "T3": "🔴 T3"}
    gate_map = {"PASS": "✅ PASS", "FLAG": "⚠️ FLAG", "BLOCK": "🚫 BLOCK"}

    for e in registry:
        tier = tier_map.get(e.get("tier", ""), e.get("tier", ""))
        gate = gate_map.get(e.get("gate", ""), e.get("gate", ""))
        labels = e.get("sources", [])
        urls = e.get("source_urls", [])

        # Build clickable source links
        link_parts = []
        for i, label in enumerate(labels[:4]):
            url = urls[i] if i < len(urls) and urls[i] else None
            link_parts.append(f"[{label}]({url})" if url else label)
        sources_md = " · ".join(link_parts) if link_parts else "—"

        caveat = e.get("caveat")
        preview = (e.get("content") or "")[:150] + "…"

        with st.container(border=True):
            col1, col2 = st.columns([1, 3])
            col1.markdown(f"**{tier}** &nbsp; {gate}")
            col2.markdown(sources_md)
            st.caption(preview)
            if caveat:
                st.warning(caveat, icon="⚠️")

    summary = data.get("registry_summary", {})
    if summary:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total collected", summary.get("total_collected", 0))
        m2.metric("Passed", summary.get("passed", 0))
        m3.metric("Flagged", summary.get("flagged", 0))
        m4.metric("Blocked", summary.get("blocked", 0))
else:
    st.info("No registry entries found.")

# ── Export ────────────────────────────────────────────────────────────────────
st.divider()
with open(output_path, encoding="utf-8") as f:
    raw_json = f.read()

st.download_button(
    "⬇️ Download JSON report",
    data=raw_json,
    file_name=output_path.name,
    mime="application/json",
)
