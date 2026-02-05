#!/usr/bin/env python3
"""
Run benchmark with full validation and results archiving.

Creates a timestamped directory with:
- Raw agent responses
- Ground truth validation
- Detailed scoring breakdown
- Execution logs
- Summary report

Usage:
    python scripts/run_validated_benchmark.py --agents claude,codex --all-tasks
    python scripts/run_validated_benchmark.py --agents claude --tasks Q001,Q002,Q005
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import asyncio

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the comparison runner
from scripts.run_agent_comparison import (
    run_benchmark, load_benchmark_context, get_agent
)


def validate_against_ground_truth(results: dict, mpi: dict) -> dict:
    """Validate agent results against ground truth."""

    validation = {
        "timestamp": datetime.now().isoformat(),
        "agents": {},
    }

    # Group results by agent
    agent_results = {}
    for r in results.get("results", []):
        agent_name = r.get("agent", "unknown")
        agent_results.setdefault(agent_name, []).append(r)

    # Validate each agent
    for agent_name, agent_tasks in agent_results.items():
        agent_validation = {
            "tasks": {},
            "summary": {
                "total_score": 0,
                "tasks_completed": 0,
                "total_time_seconds": 0,
                "total_turns": 0,
            }
        }

        for task_result in agent_tasks:
            task_id = task_result["task_id"]
            resp = task_result.get("response", {})
            turns = task_result.get("turns", 0)
            time_s = task_result.get("time_seconds", 0)

            task_validation = {
                "task_id": task_id,
                "turns": turns,
                "time_seconds": time_s,
                "tokens": task_result.get("tokens", 0),
                "score": 0.0,
                "details": {},
                "pass": False,
            }

            # Validate each task type
            if task_id == "Q001":
                p42 = next((p for p in mpi["patients"] if p["system_ids"]["ehr"] == "MRN-100042"), None)
                if p42:
                    true_ids = p42["system_ids"]
                    found_ids = resp.get("patient_ids", {})
                    correct = sum(1 for sys, tid in true_ids.items() if found_ids.get(sys) == tid)
                    score = correct / len(true_ids)

                    task_validation["score"] = score
                    task_validation["pass"] = score >= 0.8
                    task_validation["details"] = {
                        "expected_systems": 6,
                        "matched_systems": correct,
                        "system_matches": {
                            sys: {
                                "expected": tid,
                                "found": found_ids.get(sys),
                                "match": found_ids.get(sys) == tid
                            }
                            for sys, tid in true_ids.items()
                        }
                    }

            elif task_id == "Q002":
                count = resp.get("total_count", len(resp.get("patient_ids", [])))
                expected_range = [92, 154]
                in_range = expected_range[0] <= count <= expected_range[1]
                score = 1.0 if in_range else max(0, 1 - abs(count - 123) / 123)

                task_validation["score"] = score
                task_validation["pass"] = in_range
                task_validation["details"] = {
                    "found_count": count,
                    "expected_range": expected_range,
                    "in_range": in_range,
                }

            elif task_id == "Q003":
                count = resp.get("total_count", 0)
                expected = 71
                score = max(0, 1 - abs(count - expected) / expected)

                task_validation["score"] = score
                task_validation["pass"] = score >= 0.7
                task_validation["details"] = {
                    "found_count": count,
                    "expected": expected,
                    "deviation": abs(count - expected),
                }

            elif task_id == "Q004":
                groups = len(resp.get("duplicate_groups", []))
                expected_range = [39, 59]
                in_range = expected_range[0] <= groups <= expected_range[1]
                score = 0.8 if in_range else max(0, 0.8 - abs(groups - 49) / 49)

                task_validation["score"] = score
                task_validation["pass"] = in_range
                task_validation["details"] = {
                    "found_groups": groups,
                    "expected_range": expected_range,
                    "in_range": in_range,
                }

            elif task_id == "Q005":
                pts = resp.get("patients", [])
                valid = 0
                invalid_matches = []

                for p in pts:
                    ehr_id = p.get("ehr_id", "")
                    m = next((x for x in mpi["patients"] if x["system_ids"]["ehr"] == ehr_id), None)
                    if m:
                        pharm_match = p.get("pharmacy_id") == m["system_ids"]["pharmacy"]
                        lis_match = p.get("lis_id") == m["system_ids"]["lis"]
                        if pharm_match and lis_match:
                            valid += 1
                        else:
                            invalid_matches.append({
                                "ehr_id": ehr_id,
                                "found_pharmacy": p.get("pharmacy_id"),
                                "expected_pharmacy": m["system_ids"]["pharmacy"],
                                "found_lis": p.get("lis_id"),
                                "expected_lis": m["system_ids"]["lis"],
                            })

                match_rate = valid / len(pts) if pts else 0
                count_score = min(1.0, len(pts) / 50) if pts else 0
                score = (match_rate * 0.7) + (count_score * 0.3)

                task_validation["score"] = score
                task_validation["pass"] = score >= 0.5
                task_validation["details"] = {
                    "total_patients": len(pts),
                    "valid_matches": valid,
                    "match_rate": match_rate,
                    "invalid_matches": invalid_matches[:5],  # First 5 errors
                }

            elif task_id == "Q006":
                o = resp.get("orphaned_results", {}).get("count", 0)
                a = resp.get("abandoned_orders", {}).get("count", 0)
                exp_o = [113, 123]
                exp_a = [15, 25]

                o_score = 1.0 if exp_o[0] <= o <= exp_o[1] else max(0, 1 - abs(o - 118) / 118)
                a_score = 1.0 if exp_a[0] <= a <= exp_a[1] else max(0, 1 - abs(a - 20) / 20)
                score = (o_score + a_score) / 2

                task_validation["score"] = score
                task_validation["pass"] = score >= 0.7
                task_validation["details"] = {
                    "orphaned_results": {
                        "found": o,
                        "expected_range": exp_o,
                        "score": o_score,
                    },
                    "abandoned_orders": {
                        "found": a,
                        "expected_range": exp_a,
                        "score": a_score,
                    }
                }

            agent_validation["tasks"][task_id] = task_validation
            agent_validation["summary"]["total_score"] += task_validation["score"]
            agent_validation["summary"]["tasks_completed"] += 1
            agent_validation["summary"]["total_time_seconds"] += time_s
            agent_validation["summary"]["total_turns"] += turns

        # Calculate averages
        if agent_validation["summary"]["tasks_completed"] > 0:
            agent_validation["summary"]["average_score"] = (
                agent_validation["summary"]["total_score"] /
                agent_validation["summary"]["tasks_completed"]
            )
        else:
            agent_validation["summary"]["average_score"] = 0.0

        validation["agents"][agent_name] = agent_validation

    return validation


def generate_summary_report(validation: dict, results: dict) -> str:
    """Generate markdown summary report."""

    report = f"""# HDH-Bench Results
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Benchmark Version**: 1.0.0

## Agents Tested
{', '.join(validation['agents'].keys())}

## Overall Scores

| Agent | Avg Score | Tasks | Time | Turns |
|-------|-----------|-------|------|-------|
"""

    for agent_name, agent_data in validation["agents"].items():
        summary = agent_data["summary"]
        report += f"| {agent_name} | {summary['average_score']:.1%} | {summary['tasks_completed']} | {summary['total_time_seconds']:.0f}s | {summary['total_turns']} |\n"

    report += "\n## Task-by-Task Results\n\n"

    # Task descriptions
    task_names = {
        "Q001": "Patient 360 View (Cross-System Matching)",
        "Q002": "Diabetic Cohort Building",
        "Q003": "Abnormal Glucose Detection",
        "Q004": "Duplicate Patient Detection",
        "Q005": "Cross-System Cohort with Validation",
        "Q006": "Data Quality Issues Detection",
    }

    # Get all task IDs
    all_tasks = set()
    for agent_data in validation["agents"].values():
        all_tasks.update(agent_data["tasks"].keys())

    for task_id in sorted(all_tasks):
        report += f"\n### {task_id}: {task_names.get(task_id, task_id)}\n\n"
        report += "| Agent | Score | Pass | Details |\n"
        report += "|-------|-------|------|--------|\n"

        for agent_name, agent_data in validation["agents"].items():
            if task_id in agent_data["tasks"]:
                task = agent_data["tasks"][task_id]
                pass_icon = "✅" if task["pass"] else "❌"
                details = ""

                if task_id == "Q001":
                    matched = task["details"]["matched_systems"]
                    details = f"{matched}/6 systems"
                elif task_id == "Q002":
                    details = f"{task['details']['found_count']} patients"
                elif task_id == "Q003":
                    details = f"{task['details']['found_count']} patients"
                elif task_id == "Q004":
                    details = f"{task['details']['found_groups']} groups"
                elif task_id == "Q005":
                    total = task["details"]["total_patients"]
                    valid = task["details"]["valid_matches"]
                    details = f"{total} patients, {valid} valid"
                elif task_id == "Q006":
                    o = task["details"]["orphaned_results"]["found"]
                    a = task["details"]["abandoned_orders"]["found"]
                    details = f"orph={o}, aband={a}"

                report += f"| {agent_name} | {task['score']:.1%} | {pass_icon} | {details} |\n"

    report += f"\n## Execution Details\n\n"
    report += f"- Total execution time: {sum(a['summary']['total_time_seconds'] for a in validation['agents'].values()):.0f}s\n"
    report += f"- Total turns: {sum(a['summary']['total_turns'] for a in validation['agents'].values())}\n"

    report += "\n## Notes\n\n"
    report += "- Ground truth validation performed against master patient index\n"
    report += "- Scores reflect accuracy against expected results\n"
    report += "- Pass threshold varies by task complexity\n"

    return report


async def main():
    parser = argparse.ArgumentParser(description="Run validated HDH-Bench with full results archiving")
    parser.add_argument("--agents", "-a", default="claude,codex", help="Agents to test")
    parser.add_argument("--tasks", "-t", help="Specific task IDs (comma-separated)")
    parser.add_argument("--all-tasks", action="store_true", help="Run all tasks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Create run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(__file__).parent.parent / "results" / "benchmark_runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"HDH-BENCH VALIDATED RUN")
    print(f"{'='*70}")
    print(f"Run ID: {timestamp}")
    print(f"Output: {run_dir}")
    print(f"{'='*70}\n")

    # Parse agents and tasks
    agent_names = [a.strip() for a in args.agents.split(",")]
    task_ids = [] if args.all_tasks else ([t.strip() for t in args.tasks.split(",")] if args.tasks else ["Q001", "Q002", "Q005"])

    # Run benchmark
    print("Running benchmark...")
    results = await run_benchmark(agent_names, task_ids, args.verbose)

    # Save raw results
    raw_file = run_dir / "raw_results.json"
    with open(raw_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✓ Raw results: {raw_file.name}")

    # Load ground truth
    benchmark_dir = Path(__file__).parent.parent / "data" / "benchmark"
    mpi_path = benchmark_dir / "ground_truth" / "master_patient_index.json"

    with open(mpi_path) as f:
        mpi = json.load(f)

    # Validate
    print("Validating against ground truth...")
    validation = validate_against_ground_truth(results, mpi)

    # Save validation
    validation_file = run_dir / "validation.json"
    with open(validation_file, "w") as f:
        json.dump(validation, f, indent=2)
    print(f"✓ Validation: {validation_file.name}")

    # Generate report
    print("Generating summary report...")
    report = generate_summary_report(validation, results)

    report_file = run_dir / "REPORT.md"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"✓ Report: {report_file.name}")

    # Save metadata
    metadata = {
        "run_id": timestamp,
        "timestamp": datetime.now().isoformat(),
        "agents": agent_names,
        "tasks": task_ids or "all",
        "files": {
            "raw_results": str(raw_file),
            "validation": str(validation_file),
            "report": str(report_file),
        }
    }

    metadata_file = run_dir / "metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata: {metadata_file.name}")

    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for agent_name, agent_data in validation["agents"].items():
        summary = agent_data["summary"]
        print(f"{agent_name:30} {summary['average_score']:6.1%}  ({summary['tasks_completed']} tasks, {summary['total_time_seconds']:.0f}s)")

    print(f"\n{'='*70}")
    print(f"Results saved to: {run_dir}")
    print(f"View report: cat {report_file}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
