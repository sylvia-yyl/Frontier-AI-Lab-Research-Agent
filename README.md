# Frontier AI Lab Research Agent

An agent that autonomously researches AI labs, validates sources, and critiques its own output.

Given a lab name, the agent independently plans its search strategy, collects and validates data, synthesises findings into a brief, and self-evaluates quality — without human intervention at each step.

---

## The Problem It Solves

Tracking frontier AI labs (DeepSeek, Anthropic, Mistral, xAI, etc.) requires monitoring arXiv, GitHub, and news simultaneously. Manual research takes hours and is prone to missing weak signals or accepting unreliable sources.

Most AI tools either hallucinate citations or treat all sources as equally trustworthy. This agent solves both problems.

---

## Key Design Decisions

### 1. ReAct Architecture (not a fixed workflow)
The agent decides its next search query based on what it finds — not a hardcoded sequence. If it detects an efficiency claim, it queues a verification search. If a source is blocked, it searches for a stronger one. The research plan emerges from the data.

### 2. 2-Dimensional Data Trust Model
Every data point is evaluated on two independent dimensions:

| Dimension | What It Measures | Example Failure |
|-----------|-----------------|-----------------|
| **Tier** | Source quality (T1/T2/T3) | Agent accepts a Reddit post as fact |
| **Cross-validation** | Number of corroborating sources | Single T3 source with no corroboration |

**Tier classification:**
- 🟢 **T1** — Official sources: lab websites, arXiv, GitHub releases
- 🟡 **T2** — Reputable media: Bloomberg, Reuters, MIT Tech Review, Ars Technica
- 🔴 **T3** — Weak signal: single blogs, unverified reports, social media

**Gate results:**
- ✅ **PASS** — T1/T2 with multiple sources — used in analysis
- ⚠️ **FLAG** — Single T1 source — accepted with caveat
- 🚫 **BLOCK** — T3 single source — quarantined to appendix, never used in brief

### 3. Auditable Data Registry
Every data point is logged with its tier, sources, clickable source URLs, gate result, and caveat. Nothing enters the brief without passing `gate_check()`. Blocked data moves to appendix — it never silently disappears.

### 4. Critic-in-the-Loop (CP4)
Before saving output, an independent LLM scores the brief on 4 dimensions (0–10 each):

| Dimension | What Gets Deducted |
|-----------|-------------------|
| **claim_coverage** | Vague phrases like "reportedly" with no named source |
| **counter_evidence** | One-sided conclusions with no caveats |
| **logic_chain** | Reasoning jumps longer than 2 steps |
| **staleness_risk** | Undated claims presented as current |

Pass threshold: **28/40**. On failure, the agent re-searches the critic's specified focus area and rebuilds the brief. Max 2 retries. If still failing, output is saved with `HUMAN_REVIEW_REQUIRED` flag.

---

## Architecture

```
Input: lab name (e.g. "DeepSeek")
       │
       ▼
┌─────────────────┐
│  CP1 Checkpoint │  Must find ≥1 T1/T2 source + ≥2 distinct domains
│                 │  Retries up to 3× with broader queries before aborting
└────────┬────────┘
         │ PASS
         ▼
┌─────────────────┐
│   ReAct Agent   │  Thought → Search → Observe → decide next step
│   (agent.py)    │  Stops early when ≥3 PASS-grade data points collected
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Registry  │  gate_check() on every data point
│  (registry.py)  │  PASS / FLAG (caveat) / BLOCK (appendix)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Brief Builder  │  LLM synthesises — never generates numbers
│  (main.py)      │  All values transcribed from registry entries
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Critic (CP4)   │  Independent LLM scores brief (0–40)
│  (critic.py)    │  PASS ≥28  |  RETRY <28  |  max 2 retries
└────────┬────────┘
         │
         ▼
  JSON output + quality flag
```

---

## Output Example

```json
{
  "lab": "DeepSeek",
  "date": "2026-05-17",
  "status": "OK",
  "quality_flag": "OK",
  "critic_total": 30,
  "verdict": "PASS",
  "brief": "...",
  "data_registry": [
    {
      "id": "a1b2c3d4",
      "content": "DeepSeek V4 launched April 2026...",
      "tier": "T1",
      "sources": ["deepseek.com", "arstechnica.com"],
      "source_urls": ["https://deepseek.com/...", "https://arstechnica.com/..."],
      "gate": "PASS",
      "caveat": null
    }
  ]
}
```

---

## Setup

```bash
git clone https://github.com/your-username/Frontier-AI-Lab-Weekly-Digest
cd Frontier-AI-Lab-Weekly-Digest/ai-infra-research-agent

pip install google-genai python-dotenv streamlit
```

Create `ai-infra-research-agent/.env`:
```
GEMINI_API_KEY=your_key_here
```

**Run the UI (recommended):**
```bash
streamlit run ai-infra-research-agent/ui.py
```

**Run from the command line:**
```bash
cd ai-infra-research-agent
python main.py
```

---

## File Structure

```
ai-infra-research-agent/
├── CLAUDE.md                    # agent behaviour spec
├── main.py                      # pipeline entry point
├── agent.py                     # ReAct loop
├── critic.py                    # independent quality scoring (CP4)
├── checkpoint1.py               # CP1 coverage validation + tier classification
├── registry.py                  # data trust registry + gate_check
├── data_models.py               # DataPoint schema
├── tools.py                     # search_web (Gemini + Google Search grounding)
├── ui.py                        # Streamlit UI
├── pages/
│   └── 1_Pipeline_Guide.py      # in-app documentation page
└── output/                      # generated briefs saved as JSON
```

---

## Limitations

- Source tier classification is heuristic-based (domain name matching), not guaranteed accurate for all sources
- Gemini grounding may return redirect URIs — these still navigate to the correct article when clicked
- Agent stops at 3 PASS data points to control API costs; increase the threshold in `agent.py` for deeper research
- Critic scoring is LLM-based and may vary slightly between runs
