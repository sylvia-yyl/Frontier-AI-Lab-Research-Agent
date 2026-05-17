import json
from datetime import date
from pathlib import Path
from agent import run_agent
from critic import run_critic


MAX_CRITIC_RETRIES = 2


def build_brief(lab: str, findings: list) -> str:
    findings_text = ""
    for f in findings:
        findings_text += f"""
Step {f['step']} | Query: {f['query']}
Tier: {f['tier']} | Gate: {f['gate']}
Sources: {', '.join(f['sources'][:3])}
Content: {f['content'][:400]}
---"""

    prompt = f"""
You are a buy-side research analyst.
Based ONLY on the findings below, write a structured research brief for {lab}.

Rules:
- Never invent numbers not present in the findings
- Every claim must reference which source it came from
- Include a Limitations section for anything uncertain
- Format: Key Developments, Investment Implications, Limitations

Findings:
{findings_text}
"""
    from google import genai
    from google.genai import types
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3)
    )
    return response.text


def save_output(lab: str, brief: str, critic_result: dict,
                agent_result: dict) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    filename = f"{lab.lower()}_{date.today().isoformat()}.json"
    filepath = output_dir / filename

    output = {
        "lab": lab,
        "date": date.today().isoformat(),
        "status": agent_result["status"],
        "steps_taken": agent_result["steps_taken"],
        "registry_summary": agent_result["registry_summary"],
        "critic_scores": critic_result["scores"],
        "critic_total": critic_result["total"],
        "verdict": critic_result["verdict"],
        "quality_flag": "HUMAN_REVIEW_REQUIRED" if critic_result["verdict"] == "RETRY" else "OK",
        "weak_areas": critic_result.get("weak_areas", []),
        "brief": brief,
        "data_registry": agent_result["usable_data"]
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n[Output saved] {filepath}")
    return filepath


def run(lab: str):
    print(f"\n{'='*60}")
    print(f"PIPELINE START: {lab}")
    print(f"{'='*60}")

    agent_result = run_agent(lab)

    if agent_result["status"] == "INSUFFICIENT_DATA":
        print(f"\n[Pipeline] Aborted: {agent_result['reason']}")
        return

    print(f"\n[Pipeline] Building brief from {len(agent_result['findings'])} findings...")
    brief = build_brief(lab, agent_result["findings"])
    print(f"\n[Brief Preview]\n{brief[:500]}...")

    critic_retries = 0
    while critic_retries <= MAX_CRITIC_RETRIES:
        print(f"\n[Pipeline] Running critic (attempt {critic_retries + 1})...")
        critic_result = run_critic(brief)

        if critic_result["verdict"] == "PASS":
            print(f"\n[Pipeline] Critic PASSED with {critic_result['total']}/40")
            break

        print(f"\n[Pipeline] Critic RETRY — focus: {critic_result['retry_focus']}")
        critic_retries += 1

        if critic_retries > MAX_CRITIC_RETRIES:
            print(f"[Pipeline] Max retries reached, saving with RETRY verdict")
            break

        retry_query = critic_result["retry_focus"][:100]
        print(f"[Pipeline] Searching: '{retry_query}'")

        from tools import search_web
        from checkpoint1 import classify_tier
        from registry import make_datapoint

        text, sources, source_urls = search_web(f"{lab} {retry_query}")
        tier = classify_tier(sources)
        dp = make_datapoint(content=text[:1500], tier=tier,
                            sources=sources or ["source_unverified"],
                            source_urls=source_urls)

        agent_result["findings"].append({
            "step": f"retry_{critic_retries}",
            "query": retry_query,
            "tier": tier,
            "gate": "PASS",
            "sources": sources[:5],
            "source_urls": source_urls[:5],
            "content": text[:500],
        })

        brief = build_brief(lab, agent_result["findings"])

    save_output(lab, brief, critic_result, agent_result)
    print(f"\n[Pipeline Complete]")
    print(f"Verdict: {critic_result['verdict']} | Score: {critic_result['total']}/40")


if __name__ == "__main__":
    run("DeepSeek")
