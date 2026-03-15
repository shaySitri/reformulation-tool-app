"""
stats_reader.py
---------------
Reads logs/feedback.jsonl and returns aggregated statistics.

read_stats() is the single entry point. It handles a missing log file
gracefully and skips any malformed lines.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LOG_PATH = _REPO_ROOT / "logs" / "feedback.jsonl"


def read_stats() -> Dict[str, Any]:
    """
    Parse feedback.jsonl and return aggregated stats.

    Returns a dict with keys:
        total         int
        siri_understood  dict  {yes, no, unanswered} counts + pct
        by_intent     dict  intent_label → {total, yes, no, unanswered}
        recent        list  last 20 records, newest first
    """
    records: List[Dict[str, Any]] = []

    if _LOG_PATH.exists():
        with _LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    total = len(records)

    # siri_understood counts
    yes_count = sum(1 for r in records if r.get("siri_understood") is True)
    no_count = sum(1 for r in records if r.get("siri_understood") is False)
    unanswered_count = sum(1 for r in records if r.get("siri_understood") is None)

    def pct(n: int) -> float:
        return round(n / total * 100, 1) if total > 0 else 0.0

    siri_understood = {
        "yes": yes_count,
        "no": no_count,
        "unanswered": unanswered_count,
        "yes_pct": pct(yes_count),
        "no_pct": pct(no_count),
        "unanswered_pct": pct(unanswered_count),
    }

    # breakdown by intent
    by_intent: Dict[str, Dict[str, int]] = {}
    for r in records:
        label = r.get("intent_label") or "unknown"
        if label not in by_intent:
            by_intent[label] = {"total": 0, "yes": 0, "no": 0, "unanswered": 0}
        by_intent[label]["total"] += 1
        understood = r.get("siri_understood")
        if understood is True:
            by_intent[label]["yes"] += 1
        elif understood is False:
            by_intent[label]["no"] += 1
        else:
            by_intent[label]["unanswered"] += 1

    # sort by total descending
    by_intent = dict(
        sorted(by_intent.items(), key=lambda x: x[1]["total"], reverse=True)
    )

    # all records, newest first
    all_records = list(reversed(records))

    return {
        "total": total,
        "siri_understood": siri_understood,
        "by_intent": by_intent,
        "records": all_records,
    }
