#!/usr/bin/env python3
"""
HDH-Bench Runner

Runs the 12-task benchmark:
1. Loads tasks from benchmark/tasks.json
2. Sends task prompts to agent via Anthropic/OpenAI APIs
3. Collects responses
4. Scores with benchmark/scorer.py against ground_truth.json
5. Outputs results to results/benchmark_runs/<run_id>/

Usage:
    python scripts/run.py --agent anthropic
    python scripts/run.py --agent openai --tasks T04,T05,T06
    python scripts/run.py --agent anthropic --all-tasks
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import httpx

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from benchmark.scorer import score_all

BENCHMARK_DIR = ROOT_DIR / "data" / "benchmark"
TASKS_FILE = ROOT_DIR / "benchmark" / "tasks.json"
GT_FILE = BENCHMARK_DIR / "ground_truth" / "ground_truth.json"
AGENT_PROMPT_FILE = BENCHMARK_DIR / "agent_prompt.md"


FHIR_TOOL_DESCRIPTION = """Make a GET request to a FHIR R4 API endpoint.

Available systems:
- EHR (localhost:8001): Patient, Condition
- LIS (localhost:8002): Patient, ServiceRequest, Observation
- Pharmacy (localhost:8005): Patient, MedicationRequest
- PAS (localhost:8006): Patient, Encounter
- Billing (localhost:8007): Patient, Claim, Coverage

Search tips:
- Use _count=200 and _offset for pagination
- Condition code search needs EXACT codes: ?code=E11.9
- MedicationRequest does NOT support code search; fetch all with ?_count=200 and filter
- Observation supports code search: ?code=4548-4
- Match patients across systems by name: ?name=Smith
"""


def fhir_request(url: str) -> str:
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return json.dumps(resp.json())[:15000]
    except Exception as e:
        return json.dumps({"error": str(e)})


def parse_json_response(text: str) -> Dict:
    if not text:
        return {}
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return {"raw": text[:1000]}


def load_tasks() -> List[Dict]:
    with open(TASKS_FILE) as f:
        data = json.load(f)
    return data["tasks"]


def load_ground_truth() -> Dict:
    with open(GT_FILE) as f:
        return json.load(f)


def load_agent_prompt() -> str:
    with open(AGENT_PROMPT_FILE) as f:
        return f.read()


def build_task_prompt(task: Dict, gt: Dict) -> str:
    """Build the prompt for a specific task, filling in patient IDs from GT."""
    desc = task["description"]
    task_gt = gt["tasks"].get(task["task_id"], {})

    # Fill in patient_ehr_id placeholder if present
    patient_ehr_id = task_gt.get("patient_ehr_id", "")
    if "{patient_ehr_id}" in desc and patient_ehr_id:
        desc = desc.replace("{patient_ehr_id}", patient_ehr_id)

    response_schema = json.dumps(task["expected_response_schema"], indent=2)
    return f"""## Task: {task['title']}

{desc}

Return your answer as a JSON object matching this schema:
```json
{response_schema}
```

Return ONLY the JSON object, no markdown wrapping."""


# ── Agent runners ────────────────────────────────────────────────────────

async def run_anthropic(task_prompt: str, context: str, max_turns: int = 20) -> Dict:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    messages = [{"role": "user", "content": f"{context}\n\n{task_prompt}"}]
    tools = [{
        "name": "fhir_request",
        "description": FHIR_TOOL_DESCRIPTION,
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"]
        }
    }]

    start = time.time()
    turns = 0
    tokens = 0

    while turns < max_turns:
        turns += 1
        resp = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )
        tokens += resp.usage.input_tokens + resp.usage.output_tokens

        if resp.stop_reason == "tool_use":
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    url = block.input.get("url", "")
                    print(f"      [Turn {turns}] GET {url[:80]}", flush=True)
                    result = fhir_request(url)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            text = ""
            for block in resp.content:
                if hasattr(block, "text"):
                    text = block.text
                    break
            return {
                "response": parse_json_response(text),
                "turns": turns,
                "time_seconds": time.time() - start,
                "tokens": tokens,
            }

    return {"response": {}, "turns": turns, "time_seconds": time.time() - start, "tokens": tokens}


async def run_openai(task_prompt: str, context: str, max_turns: int = 20) -> Dict:
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": task_prompt},
    ]
    tools = [{
        "type": "function",
        "function": {
            "name": "fhir_request",
            "description": FHIR_TOOL_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            }
        }
    }]

    start = time.time()
    turns = 0
    tokens = 0

    while turns < max_turns:
        turns += 1
        resp = client.chat.completions.create(
            model="gpt-4o", messages=messages, tools=tools,
            tool_choice="auto" if turns < max_turns - 1 else "none",
        )
        tokens += resp.usage.total_tokens if resp.usage else 0
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                url = args.get("url", "")
                print(f"      [Turn {turns}] GET {url[:80]}", flush=True)
                result = fhir_request(url)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            return {
                "response": parse_json_response(msg.content or ""),
                "turns": turns,
                "time_seconds": time.time() - start,
                "tokens": tokens,
            }

    return {"response": {}, "turns": turns, "time_seconds": time.time() - start, "tokens": tokens}


AGENT_RUNNERS = {
    "anthropic": run_anthropic,
    "openai": run_openai,
}


# ── Main ─────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="HDH-Bench runner")
    parser.add_argument("--agent", "-a", default="anthropic", choices=list(AGENT_RUNNERS.keys()))
    parser.add_argument("--tasks", "-t", help="Comma-separated task IDs (e.g. T04,T05)")
    parser.add_argument("--all-tasks", action="store_true")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    tasks = load_tasks()
    gt = load_ground_truth()
    context = load_agent_prompt()

    if not args.all_tasks and args.tasks:
        selected = set(args.tasks.split(","))
        tasks = [t for t in tasks if t["task_id"] in selected]
    elif not args.all_tasks:
        tasks = tasks[:6]  # Default: first 6 tasks

    runner = AGENT_RUNNERS[args.agent]

    # Create run directory
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = ROOT_DIR / "results" / "benchmark_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"HDH-BENCH")
    print(f"{'='*60}")
    print(f"Run ID:  {run_id}")
    print(f"Agent:   {args.agent}")
    print(f"Tasks:   {len(tasks)}")
    print(f"Output:  {run_dir}")
    print(f"{'='*60}\n")

    # Run each task
    responses: Dict[str, Dict] = {}
    raw_results = []

    for task in tasks:
        tid = task["task_id"]
        print(f"\n--- {tid}: {task['title']} ---")

        prompt = build_task_prompt(task, gt)
        try:
            result = await runner(prompt, context, args.max_turns)
            responses[tid] = result["response"]
            raw_results.append({
                "task_id": tid,
                "response": result["response"],
                "turns": result["turns"],
                "time_seconds": round(result["time_seconds"], 2),
                "tokens": result["tokens"],
            })
            print(f"  Done: {result['turns']} turns, {result['time_seconds']:.1f}s")
            if args.verbose:
                print(f"  Response: {json.dumps(result['response'])[:200]}...")
        except Exception as e:
            print(f"  ERROR: {e}")
            responses[tid] = {}
            raw_results.append({"task_id": tid, "error": str(e)})

    # Score
    print(f"\n{'='*60}")
    print("SCORING")
    print(f"{'='*60}")

    scored = score_all(responses, gt)

    for r in scored["task_results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {r['task_id']}: {r['score']:.2f} [{status}]")

    print(f"\n  Overall: {scored['overall_score']:.1%}")
    print(f"  Passed:  {scored['tasks_passed']}/{scored['tasks_total']}")
    print(f"{'='*60}")

    # Save outputs
    with open(run_dir / "raw_results.json", "w") as f:
        json.dump(raw_results, f, indent=2)

    with open(run_dir / "scored_results.json", "w") as f:
        json.dump(scored, f, indent=2)

    metadata = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "agent": args.agent,
        "tasks": [t["task_id"] for t in tasks],
        "overall_score": scored["overall_score"],
        "tasks_passed": scored["tasks_passed"],
        "tasks_total": scored["tasks_total"],
    }
    with open(run_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Generate report
    report = f"""# HDH-Bench Results
**Run ID**: {run_id}
**Agent**: {args.agent}
**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Score: {scored['overall_score']:.1%}
**Passed**: {scored['tasks_passed']}/{scored['tasks_total']} tasks

## Task Results

| Task | Title | Score | Pass |
|------|-------|-------|------|
"""
    task_lookup = {t["task_id"]: t for t in load_tasks()}
    for r in scored["task_results"]:
        title = task_lookup.get(r["task_id"], {}).get("title", "")
        status = "PASS" if r["passed"] else "FAIL"
        report += f"| {r['task_id']} | {title} | {r['score']:.2f} | {status} |\n"

    with open(run_dir / "REPORT.md", "w") as f:
        f.write(report)

    print(f"\nResults saved to: {run_dir}")


if __name__ == "__main__":
    asyncio.run(main())
