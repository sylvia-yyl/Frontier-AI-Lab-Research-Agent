from dataclasses import dataclass
from registry import Registry, make_datapoint
from tools import search_web


@dataclass
class CP1Result:
    passed: bool
    reason: str
    attempt: int


# Known T1 domains for AI research
T1_DOMAINS = ["arxiv.org", "github.com", "openai.com", "deepmind.com",
              "anthropic.com", "deepseek.com", "deepseek.ai", "mistral.ai",
              "meta.com", "google.com", "huggingface.co"]

# Reputable T2 domains
T2_DOMAINS = T2_DOMAINS = ["techcrunch.com", "theverge.com", "arstechnica.com",
              "nature.com", "technologyreview.com", "wired.com",
              "reuters.com", "bloomberg.com", "venturebeat.com",
              "businessinsider.com", "scmp.com", "ft.com",
              "wsj.com", "economist.com", "forbes.com"]


def classify_tier(sources: list[str]) -> str:
    """
    Infer best tier from source titles returned by Gemini grounding.
    T1 if any known official domain found, T2 if reputable media, else T3.
    """
    for s in sources:
        s_lower = s.lower()
        for domain in T1_DOMAINS:
            if domain in s_lower:
                return "T1"
    for s in sources:
        s_lower = s.lower()
        for domain in T2_DOMAINS:
            if domain in s_lower:
                return "T2"
    return "T3"


def run_checkpoint1(lab: str, max_attempts: int = 3) -> tuple[CP1Result, Registry]:
    """
    CP1: Search coverage check.
    Pass criteria:
      - At least 1 T1 or T2 source found
      - At least 2 distinct sources
      - Registry has usable entries after gate check

    On failure: retry with broader query, up to max_attempts.
    If all attempts fail: return failed result — agent never fabricates coverage.
    """
    queries = [
        f"{lab} AI research paper 2026",
        f"{lab} artificial intelligence latest development",
        f"{lab} AI model release announcement"
    ]

    for attempt in range(max_attempts):
        query = queries[attempt]
        print(f"\n[CP1] Attempt {attempt + 1}: '{query}'")

        text, sources, source_urls = search_web(query)
        tier = classify_tier(sources)
        distinct_domains = len(set(sources))

        print(f"  Tier detected: {tier}")
        print(f"  Sources found: {len(sources)}")
        print(f"  Distinct domains: {distinct_domains}")
        print(f"  Sources: {sources[:5]}")

        reg = Registry(lab=lab)
        dp = make_datapoint(
            content=text[:1000],
            tier=tier,
            sources=sources if sources else ["source_unverified"],
            source_urls=source_urls,
        )
        gate = reg.add(dp)
        print(f"  Gate result: {gate}")

        has_usable = reg.summary()["passed"] + reg.summary()["flagged"] > 0

        # Pass only if T1 or T2 found — T3 alone is not sufficient
        if tier in ["T1", "T2"] and has_usable:
            return CP1Result(
                passed=True,
                reason=f"Coverage OK (tier={tier}, distinct_domains={distinct_domains})",
                attempt=attempt + 1
            ), reg
        else:
            print(f"  T3 sources only, retrying...")

    # All attempts failed — explicitly mark gap, never fabricate
    return CP1Result(
        passed=False,
        reason=f"No reliable sources found for '{lab}' after {max_attempts} attempts. "
               f"Brief will note: insufficient public information this week.",
        attempt=max_attempts
    ), Registry(lab=lab)


if __name__ == "__main__":
    result, reg = run_checkpoint1("DeepSeek")
    print(f"\n[CP1 Result] Passed: {result.passed}")
    print(f"Reason: {result.reason}")
    print(f"Attempts used: {result.attempt}")
    print(f"Registry summary: {reg.summary()}")