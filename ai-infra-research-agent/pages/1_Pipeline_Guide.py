import streamlit as st

st.set_page_config(page_title="Pipeline Guide", layout="wide", page_icon="📖")

st.title("📖 Pipeline Guide")
st.caption("How the research agent works — every step explained")

# ── Overall architecture ──────────────────────────────────────────────────────
st.markdown("## Overall Architecture")

st.markdown("""
```
User selects lab
       │
       ▼
┌─────────────────┐
│  CP1 Checkpoint │  ← Must find ≥1 T1/T2 source and ≥2 distinct domains
│  (Coverage)     │    Retries up to 3× with broader queries before aborting
└────────┬────────┘
         │ PASS
         ▼
┌─────────────────┐
│   ReAct Agent   │  ← Loop: Thought → Search → Observe → decide next step
│   (max 8 steps) │    Stops early when ≥3 PASS-grade data points collected
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Registry  │  ← Every data point gets a Tier + Gate check
│  (T1/T2/T3)     │    BLOCK entries go to appendix, never used in brief
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Brief Builder  │  ← LLM synthesises findings into structured report
│                 │    Rules: no invented numbers, every claim needs a source
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Critic (CP4)   │  ← Independent LLM scores brief on 4 dimensions (0–40)
│                 │    PASS ≥28  |  RETRY <28  |  max 2 retries
└────────┬────────┘
         │
         ▼
    JSON output
  + quality flag
```
""")

st.divider()

# ── ReAct agent ───────────────────────────────────────────────────────────────
st.markdown("## 🔍 ReAct Search Agent")

st.markdown("""
**ReAct = Reason + Act.** Instead of a fixed list of queries, the agent reads
each result and *decides* what to search next.
""")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**The loop**")
    st.markdown("""
| Step | What happens |
|------|-------------|
| **Thought** | Agent picks the next search query |
| **Action** | Calls Gemini + Google Search grounding |
| **Observation** | Reads result, checks tier and gate |
| **Decide** | Picks the next query based on what it found |
""")

with col2:
    st.markdown("**Adaptive branching**")
    st.markdown("""
| Signal found | Next action |
|-------------|------------|
| Efficiency / benchmark claim | Queue independent verification search |
| Funding / billion-dollar figure | Queue cross-validation search |
| Product release | Queue technical deep-dive |
| Gate = BLOCK | Queue stronger-source search on same topic |
| ≥3 PASS data points | Stop early, proceed to brief |
""")

st.divider()

# ── Data trust model ──────────────────────────────────────────────────────────
st.markdown("## 🗂️ Data Trust Model — T1 / T2 / T3")

st.markdown("""
Every data point is evaluated on **two dimensions: source quality and cross-validation.**
""")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### 🟢 T1 — Official")
    st.markdown("""
**What qualifies**
- Lab's own website / blog
- arXiv papers
- Official GitHub releases
- Lab press releases

**Examples**
`deepseek.com`, `arxiv.org`, `github.com/openai`
""")

with c2:
    st.markdown("### 🟡 T2 — Reputable Media")
    st.markdown("""
**What qualifies**
- Bloomberg, Reuters, FT
- MIT Technology Review
- Ars Technica, The Verge
- Nature, Science

**Examples**
`bloomberg.com`, `arstechnica.com`, `technologyreview.mit.edu`
""")

with c3:
    st.markdown("### 🔴 T3 — Weak Signal")
    st.markdown("""
**What qualifies**
- Single news site
- Social media posts
- Unverified reports
- Anonymous blog posts

**Examples**
`randomtech.blog`, Reddit posts, unverified tweets
""")

st.divider()

# ── Gate check ────────────────────────────────────────────────────────────────
st.markdown("## 🚦 Gate Check — PASS / FLAG / BLOCK")

st.markdown("""
Every data point must pass a gate before entering the registry.
**BLOCK entries are quarantined** — they go to an appendix and are never used in the brief.
""")

st.markdown("""
| Gate | Condition | Effect |
|------|-----------|--------|
| ✅ **PASS** | T1/T2 with multiple sources | Full confidence, used in analysis |
| ⚠️ **FLAG** | Single T1 source | Accepted with caveat: "single source only — scope may differ" |
| 🚫 **BLOCK** | T3 single source | Quarantined to appendix, never used |
""")

st.markdown("""
> **Why block T3 single-source?**
> A single unverified report is worse than no data — it can mislead the brief
> with a confident-sounding but unreliable claim.
""")

st.divider()

# ── CP1 checkpoint ────────────────────────────────────────────────────────────
st.markdown("## ✅ CP1 — Search Coverage Checkpoint")

st.markdown("""
Run **before** the main agent loop. The pipeline aborts early if minimum
coverage cannot be established — better to return nothing than a hallucinated brief.

| Requirement | Threshold |
|-------------|-----------|
| At least one T1 or T2 source found | Required |
| At least 2 distinct domains | Required |
| Retries with broader queries | Up to 3× |

If CP1 fails → pipeline returns `INSUFFICIENT_DATA`, no brief is generated.
""")

st.divider()

# ── Brief builder ─────────────────────────────────────────────────────────────
st.markdown("## 📝 Brief Builder")

st.markdown("""
After the agent finishes collecting data, a separate LLM call synthesises
the findings into a structured report.

**Hard rules the LLM must follow:**
- Never invent or extrapolate numerical values — only transcribe from source text
- Every claim must name which source it came from
- Data conflicts must be surfaced explicitly, not silently resolved
- A **Limitations** section is mandatory

**Output sections:**
1. Key Developments
2. Investment Implications
3. Limitations
""")

st.divider()

# ── Critic scoring ────────────────────────────────────────────────────────────
st.markdown("## ⚖️ Critic Scoring — 0 to 40")

st.markdown("""
An **independent** LLM (no access to search tools) reads the brief and scores
it on four dimensions. It cannot see the original sources — it judges only
what the brief itself says.
""")

st.markdown("""
| Dimension | Max | What gets deducted |
|-----------|-----|--------------------|
| **Claim Coverage** | 10 | Vague phrases like "reportedly" or "analysts say" with no named source |
| **Counter Evidence** | 10 | One-sided conclusions with no caveats or opposing views |
| **Logic Chain** | 10 | Reasoning jumps longer than 2 steps from evidence to conclusion |
| **Staleness Risk** | 10 | Undated claims, or data older than 30 days presented as current |
""")

col_a, col_b = st.columns(2)
with col_a:
    st.success("**PASS** — total ≥ 28 / 40\n\nBrief is accepted and saved.")
with col_b:
    st.warning("**RETRY** — total < 28 / 40\n\nCritic specifies a weak area. Agent re-searches that topic, rebuilds the brief, and re-scores. Maximum **2 retries**.")

st.markdown("""
If the brief still fails after 2 retries, it is saved with
`quality_flag: HUMAN_REVIEW_REQUIRED`.
""")

st.divider()

# ── Quality flag ──────────────────────────────────────────────────────────────
st.markdown("## 🏷️ Quality Flag")

st.markdown("""
| Flag | Meaning |
|------|---------|
| `OK` | Critic passed (≥28/40) — brief can be used as-is |
| `HUMAN_REVIEW_REQUIRED` | Critic failed after max retries — treat conclusions with caution |
""")
