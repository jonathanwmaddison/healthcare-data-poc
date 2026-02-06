#!/usr/bin/env python3
"""Score all 50 tasks for the Claude Code Opus 4.6 benchmark run using the HDH scorer."""

import json
import sys
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from benchmark.evaluation.scorer import HDHScorer

def main():
    # Load raw results
    raw_path = root_dir / "results/benchmark_runs/20260205_claude_code_opus/raw_results.json"
    with open(raw_path) as f:
        raw_data = json.load(f)

    # Transform results to scorer format: list of dicts with task_id and response
    responses = []
    for task_id, task_data in raw_data["results"].items():
        responses.append({
            "task_id": task_id,
            "response": task_data.get("result", {}),
            "turns_used": 0,
            "time_seconds": 0
        })

    # Create scorer
    tasks_dir = root_dir / "benchmark/tasks"
    scorer = HDHScorer(tasks_dir)

    # Score all
    result = scorer.score_all(
        responses,
        model_info={"name": "claude-opus-4-6", "agent": "Claude Code"},
        verbose=True
    )

    # Convert to dict for JSON output
    from dataclasses import asdict
    output = asdict(result)
    print(json.dumps(output, indent=2, default=str))

if __name__ == "__main__":
    main()
