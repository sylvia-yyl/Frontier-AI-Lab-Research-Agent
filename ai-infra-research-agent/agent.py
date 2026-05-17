from registry import Registry, make_datapoint
from tools import search_web
from checkpoint1 import run_checkpoint1, classify_tier


MAX_STEPS = 8


def run_agent(lab: str) -> dict:
    """
    ReAct loop: Thought → Action → Observation → repeat.
    Agent decides next search query based on what it finds.
    Stops when it has enough usable data or hits MAX_STEPS.
    """

    print(f"\n{'='*60}")
    print(f"AGENT START: Researching '{lab}'")
    print(f"{'='*60}")

    cp1_result, reg = run_checkpoint1(lab)
    if not cp1_result.passed:
        return {
            "lab": lab,
            "status": "INSUFFICIENT_DATA",
            "reason": cp1_result.reason,
            "data_registry": []
        }

    print(f"\n[CP1 PASSED] {cp1_result.reason}")

    searched_topics = set()
    findings = []

    pending_queries = [
        f"{lab} latest AI model release 2026",
        f"{lab} research breakthrough inference efficiency",
        f"{lab} funding investment news 2026",
    ]

    step = 0
    while step < MAX_STEPS and pending_queries:
        step += 1
        query = pending_queries.pop(0)

        query_key = query.lower()[:40]
        if query_key in searched_topics:
            print(f"\n[Step {step}] Skipping duplicate query")
            continue
        searched_topics.add(query_key)

        # ── Thought ──────────────────────────────────────────────
        print(f"\n[Step {step}] Thought: searching for → '{query}'")

        # ── Action ───────────────────────────────────────────────
        text, sources, source_urls = search_web(query)
        tier = classify_tier(sources)

        # ── Observation ──────────────────────────────────────────
        print(f"  Observation: tier={tier}, sources={sources[:3]}")
        print(f"  Content preview: {text[:200]}")

        dp = make_datapoint(
            content=text[:1500],
            tier=tier,
            sources=sources if sources else ["source_unverified"],
            source_urls=source_urls,
        )
        gate = reg.add(dp)
        print(f"  Gate: {gate}")

        findings.append({
            "step": step,
            "query": query,
            "tier": tier,
            "gate": gate,
            "sources": sources[:5],
            "source_urls": source_urls[:5],
            "content": text[:500],
        })

        # ── Agent decides next step based on observation ──────────
        if gate == "BLOCK":
            print(f"  → Source blocked, queuing stronger source search")
            pending_queries.insert(0, f"{lab} {query.split()[1]} arxiv OR github OR official")

        elif "efficiency" in text.lower() or "benchmark" in text.lower():
            print(f"  → Efficiency claim detected, queuing verification search")
            pending_queries.append(f"{lab} benchmark independent test comparison 2026")

        elif "funding" in text.lower() or "billion" in text.lower():
            print(f"  → Funding signal detected, queuing cross-check")
            pending_queries.append(f"{lab} funding round investors confirmed")

        elif "release" in text.lower() or "launch" in text.lower():
            print(f"  → Release detected, queuing technical deep-dive")
            pending_queries.append(f"{lab} model architecture technical details")

        summary = reg.summary()
        if summary["passed"] >= 3:
            print(f"\n[Agent] Sufficient PASS-grade data collected, stopping early")
            break

    summary = reg.summary()
    usable = reg.get_usable()

    print(f"\n{'='*60}")
    print(f"AGENT COMPLETE after {step} steps")
    print(f"Registry: {summary}")
    print(f"{'='*60}")

    return {
        "lab": lab,
        "status": "OK",
        "steps_taken": step,
        "registry_summary": summary,
        "findings": findings,
        "usable_data": usable
    }


if __name__ == "__main__":
    result = run_agent("DeepSeek")
    print(f"\nFinal status: {result['status']}")
    print(f"Steps taken: {result['steps_taken']}")
    print(f"Usable data points: {len(result['usable_data'])}")
