from google import genai
from google.genai import types
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

CRITIC_PROMPT = """
You are a senior buy-side portfolio manager with 15 years experience.
Review this research brief and score it on 4 dimensions (0-10 each).
Be strict. Output ONLY valid JSON, no preamble, no markdown.

Scoring criteria:
1. claim_coverage: Are all key claims backed by a named source? 
   Deduct for vague phrases like "reportedly", "analysts say" with no source.
2. counter_evidence: Does the brief acknowledge opposing views or risks?
   Deduct if conclusions are one-sided with no caveats.
3. logic_chain: Is the reasoning from facts to investment implications clear?
   Deduct for logical jumps longer than 2 steps.
4. staleness_risk: Are data points clearly dated?
   Deduct for undated claims or data older than 30 days presented as current.

Output format:
{{
  "scores": {{
    "claim_coverage": <0-10>,
    "counter_evidence": <0-10>,
    "logic_chain": <0-10>,
    "staleness_risk": <0-10>
  }},
  "total": <sum>,
  "weak_areas": ["list of specific problems found"],
  "verdict": "PASS" or "RETRY",
  "retry_focus": "what the agent should re-search if RETRY"
}}

PASS if total >= 28. RETRY if total < 28.

Brief to review:
{brief}
"""


def run_critic(brief_text: str) -> dict:
    """
    Critic agent: independently scores the research brief.
    Returns structured feedback.
    If verdict is RETRY, agent must re-search the specified focus area.
    """
    prompt = CRITIC_PROMPT.format(brief=brief_text)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            # No search tool — critic reasons only on what it receives
            temperature=0.2
        )
    )

    raw = response.text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = __import__("json").loads(raw)
    except Exception as e:
        # If JSON parse fails, return a safe default requesting retry
        return {
            "scores": {},
            "total": 0,
            "weak_areas": [f"Critic failed to parse response: {e}"],
            "verdict": "RETRY",
            "retry_focus": "all areas — critic could not evaluate"
        }

    print(f"\n[Critic Scores]")
    for k, v in result.get("scores", {}).items():
        print(f"  {k}: {v}/10")
    print(f"  Total: {result.get('total')}/40")
    print(f"  Verdict: {result.get('verdict')}")
    if result.get("weak_areas"):
        print(f"  Weak areas: {result['weak_areas']}")

    return result


if __name__ == "__main__":
    # Test with a sample brief
    sample_brief = """
    DeepSeek Research Brief — May 2026

    Key Developments:
    - DeepSeek released V4 series on April 24, 2026, including Pro and Flash 
      variants (MoE architecture). Source: deepseek.com
    - Inference efficiency improved significantly vs V3. Independent benchmarks 
      show cost reduction but methodology disputed by some researchers.
    - No major funding announcements found this week.

    Investment Implications:
    - Improved inference efficiency may reduce per-query GPU demand.
    - V4 release signals continued Chinese lab competitiveness.

    Limitations:
    - Benchmark independence not fully verified.
    - No T1 source confirming exact efficiency numbers.
    """

    result = run_critic(sample_brief)
    print(f"\nFull result: {result}")