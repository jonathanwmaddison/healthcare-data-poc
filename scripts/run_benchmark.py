#!/usr/bin/env python3
"""
HDH-Bench CLI Runner

Usage:
    # Run full benchmark
    python scripts/run_benchmark.py --agent-script your_agent.py --output results.json

    # Run specific tasks
    python scripts/run_benchmark.py --tasks HDH-MPI-001,HDH-COH-001 --output results.json

    # Score existing responses
    python scripts/run_benchmark.py --score responses.json --output results.json
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.evaluation.scorer import HDHScorer


def check_services() -> bool:
    """Check if all healthcare services are running"""
    import urllib.request
    import urllib.error

    services = {
        "EHR": "http://localhost:8001/health",
        "LIS": "http://localhost:8002/health",
        "RIS": "http://localhost:8003/health",
        "Pharmacy": "http://localhost:8005/health",
        "PAS": "http://localhost:8006/health",
        "Billing": "http://localhost:8007/health",
    }

    all_running = True
    for name, url in services.items():
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    print(f"  [OK] {name}")
                else:
                    print(f"  [FAIL] {name}: HTTP {response.status}")
                    all_running = False
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            all_running = False

    return all_running


def start_services() -> bool:
    """Start the Docker services"""
    print("Starting services...")
    result = subprocess.run(
        ["docker-compose", "up", "-d"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Failed to start services: {result.stderr}")
        return False

    # Wait for services to be ready
    print("Waiting for services to be ready...")
    for _ in range(30):  # Wait up to 30 seconds
        time.sleep(1)
        if check_services():
            return True

    print("Services failed to start in time")
    return False


def load_tasks(tasks_dir: Path, task_ids: Optional[List[str]] = None) -> List[Dict]:
    """Load task definitions"""
    tasks = []
    for task_file in tasks_dir.glob("*.json"):
        with open(task_file) as f:
            data = json.load(f)
            for task in data.get("tasks", []):
                if task_ids is None or task["task_id"] in task_ids:
                    tasks.append(task)
    return tasks


def get_agent_prompt() -> str:
    """Get the agent prompt content"""
    prompt_path = Path(__file__).parent.parent / "data" / "benchmark" / "agent_prompt.md"
    with open(prompt_path) as f:
        return f.read()


def run_agent(agent_script: str, task: Dict, prompt: str) -> Dict:
    """Run an agent script for a single task"""
    # This is a placeholder - actual implementation depends on agent interface
    # For now, return a mock response
    start_time = time.time()

    # Create task prompt
    task_prompt = f"""
{prompt}

## Current Task

**Task ID**: {task['task_id']}
**Title**: {task['title']}
**Description**: {task['description']}
**Systems Required**: {', '.join(task.get('systems_required', []))}
**Max Turns**: {task.get('max_turns', 20)}

Please complete this task and return your response in JSON format.
"""

    # Run the agent (this would call the actual agent)
    # For now, we just return a placeholder
    result = subprocess.run(
        [sys.executable, agent_script, "--task", json.dumps(task), "--prompt", task_prompt],
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )

    elapsed = time.time() - start_time

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        response = {"error": result.stderr or "Failed to parse agent response"}

    return {
        "task_id": task["task_id"],
        "response": response,
        "turns_used": response.get("turns_used", 0),
        "time_seconds": elapsed
    }


def score_responses(responses_file: Path, output_file: Path, verbose: bool = False):
    """Score a file of responses"""
    benchmark_dir = Path(__file__).parent.parent / "benchmark"

    scorer = HDHScorer(
        tasks_dir=benchmark_dir / "tasks",
        config_path=benchmark_dir / "config" / "evaluation_config.json"
    )

    with open(responses_file) as f:
        responses = json.load(f)

    results = scorer.score_all(responses, verbose=verbose)

    # Convert to dict for JSON serialization
    output = {
        "submission_id": results.submission_id,
        "timestamp": results.timestamp,
        "overall": results.overall,
        "by_category": results.by_category,
        "by_difficulty": results.by_difficulty,
        "efficiency": results.efficiency,
        "task_results": results.task_results
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print("\n" + "="*60)
    print("HDH-BENCH RESULTS")
    print("="*60)
    print(f"\nSuccess Rate: {results.overall['success_rate']:.1%}")
    print(f"Progress Rate: {results.overall['progress_rate']:.1%}")
    print(f"Weighted Score: {results.overall['weighted_score']:.1%}")
    print(f"\nResults saved to: {output_file}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="HDH-Bench: Healthcare Data Harmonization Benchmark Runner"
    )
    parser.add_argument(
        "--agent-script",
        help="Path to agent script to run"
    )
    parser.add_argument(
        "--tasks",
        help="Comma-separated list of task IDs to run (default: all)"
    )
    parser.add_argument(
        "--score",
        help="Score an existing responses file instead of running agent"
    )
    parser.add_argument(
        "--output",
        default="benchmark_results.json",
        help="Output file for results (default: benchmark_results.json)"
    )
    parser.add_argument(
        "--check-services",
        action="store_true",
        help="Just check if services are running"
    )
    parser.add_argument(
        "--start-services",
        action="store_true",
        help="Start the services before running"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Just check services
    if args.check_services:
        print("Checking services...")
        if check_services():
            print("\nAll services are running!")
            sys.exit(0)
        else:
            print("\nSome services are not running.")
            sys.exit(1)

    # Start services if requested
    if args.start_services:
        if not start_services():
            sys.exit(1)

    # Score existing responses
    if args.score:
        score_responses(
            Path(args.score),
            Path(args.output),
            verbose=args.verbose
        )
        sys.exit(0)

    # Need agent script to run benchmark
    if not args.agent_script:
        parser.print_help()
        print("\nError: --agent-script or --score required")
        sys.exit(1)

    # Check services are running
    print("Checking services...")
    if not check_services():
        print("\nServices not running. Use --start-services to start them.")
        sys.exit(1)

    # Load tasks
    benchmark_dir = Path(__file__).parent.parent / "benchmark"
    task_ids = args.tasks.split(",") if args.tasks else None
    tasks = load_tasks(benchmark_dir / "tasks", task_ids)

    print(f"\nRunning {len(tasks)} tasks...")

    # Get agent prompt
    prompt = get_agent_prompt()

    # Run agent for each task
    responses = []
    for task in tasks:
        print(f"\nTask: {task['task_id']} - {task['title']}")
        try:
            response = run_agent(args.agent_script, task, prompt)
            responses.append(response)
            print(f"  Completed in {response['time_seconds']:.1f}s")
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT")
            responses.append({
                "task_id": task["task_id"],
                "response": {"error": "timeout"},
                "turns_used": 0,
                "time_seconds": 300
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            responses.append({
                "task_id": task["task_id"],
                "response": {"error": str(e)},
                "turns_used": 0,
                "time_seconds": 0
            })

    # Save responses
    responses_file = Path("agent_responses.json")
    with open(responses_file, "w") as f:
        json.dump(responses, f, indent=2)

    # Score
    score_responses(responses_file, Path(args.output), verbose=args.verbose)


if __name__ == "__main__":
    main()
