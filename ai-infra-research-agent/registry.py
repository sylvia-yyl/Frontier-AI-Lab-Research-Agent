from dataclasses import dataclass, field
from typing import Literal, Optional
from data_models import DataPoint, gate_check
import uuid


@dataclass
class Registry:
    lab: str
    entries: list[dict] = field(default_factory=list)  # PASS/FLAG entries
    appendix: list[dict] = field(default_factory=list)  # BLOCK entries

    def add(self, dp: DataPoint) -> Literal["PASS", "FLAG", "BLOCK"]:
        result = gate_check(dp)
        entry = {
            "id": dp.id,
            "content": dp.content,
            "tier": dp.tier,
            "sources": dp.sources,
            "source_urls": dp.source_urls,
            "gate": result,
            "caveat": self._assign_caveat(result)
        }

        if result == "BLOCK":
            self.appendix.append(entry)
        else:
            self.entries.append(entry)

        return result

    def _assign_caveat(self, gate: str) -> str | None:
        if gate == "BLOCK":
            return "Blocked: single weak source (T3), insufficient for analysis"
        if gate == "FLAG":
            return "Single source only — definition or scope may differ across reports"
        return None

    def get_usable(self) -> list[dict]:
        return self.entries

    def summary(self) -> dict:
        passed = [e for e in self.entries if e["gate"] == "PASS"]
        flagged = [e for e in self.entries if e["gate"] == "FLAG"]
        return {
            "lab": self.lab,
            "total_collected": len(self.entries) + len(self.appendix),
            "passed": len(passed),
            "flagged": len(flagged),
            "blocked": len(self.appendix),
            "has_t1_source": any(e["tier"] == "T1" for e in self.entries)
        }


def make_datapoint(content: str, tier: str, sources: list[str],
                   source_urls: Optional[list[str]] = None) -> DataPoint:
    return DataPoint(
        id=str(uuid.uuid4())[:8],
        content=content,
        tier=tier,
        sources=sources,
        source_urls=source_urls or [],
    )


if __name__ == "__main__":
    reg = Registry(lab="DeepSeek")

    dp1 = make_datapoint(
        content="DeepSeek releases new MoE architecture paper",
        tier="T1",
        sources=["arxiv.org/abs/2026.11111"]
    )
    print(f"dp1 gate: {reg.add(dp1)}")

    dp2 = make_datapoint(
        content="DeepSeek rumored to raise $5B",
        tier="T3",
        sources=["somesite.com/article"]
    )
    print(f"dp2 gate: {reg.add(dp2)}")

    dp3 = make_datapoint(
        content="DeepSeek inference cost 10x cheaper than GPT-4",
        tier="T2",
        sources=["arstechnica.com/article", "theverge.com/article"]
    )
    print(f"dp3 gate: {reg.add(dp3)}")

    print(f"\nRegistry summary: {reg.summary()}")
    print(f"\nUsable entries: {len(reg.get_usable())}")
    print(f"Appendix (blocked): {len(reg.appendix)}")
