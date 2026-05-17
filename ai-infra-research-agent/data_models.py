from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DataPoint:
    id: str
    content: str
    tier: Literal["T1", "T2", "T3"]
    sources: list[str]
    source_urls: list[str] = field(default_factory=list)
    is_derived: bool = False
    derived_from: list[str] = field(default_factory=list)

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def effective_tier(self) -> str:
        """Barrel Principle: Derived data inherits the lowest trust tier of its inputs."""
        return self.tier


def gate_check(dp: DataPoint) -> Literal["PASS", "FLAG", "BLOCK"]:
    if dp.tier == "T3" and dp.source_count < 2:
        return "BLOCK"
    if dp.source_count == 1 and dp.tier == "T1":
        return "FLAG"
    return "PASS"


if __name__ == "__main__":
    dp1 = DataPoint(
        id="dp_001",
        content="DeepSeek inference efficiency improved by 40%",
        tier="T1",
        sources=["arxiv.org/abs/2026.xxxxx"]
    )
    print(f"Tier: {dp1.tier}")
    print(f"Gate: {gate_check(dp1)}")

    dp2 = DataPoint(
        id="dp_002",
        content="Some rumor about DeepSeek funding",
        tier="T3",
        sources=["randomsite.com"]
    )
    print(f"\nTier: {dp2.tier}")
    print(f"Gate: {gate_check(dp2)}")
