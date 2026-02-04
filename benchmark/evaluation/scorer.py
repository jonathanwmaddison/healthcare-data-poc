#!/usr/bin/env python3
"""
HDH-Bench Scorer - Standardized evaluation for Healthcare Data Harmonization Benchmark

Implements scoring aligned with AgentBench patterns:
- Success Rate (primary)
- Progress Rate (sub-goals)
- F1 Score (for matching tasks)
- Efficiency metrics

Usage:
    python scorer.py --responses responses.json --tasks-dir benchmark/tasks/
    python scorer.py --responses responses.json --output results.json --verbose
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import re


@dataclass
class TaskResult:
    """Result for a single task"""
    task_id: str
    success: bool
    progress: float  # 0-1, based on sub-goals
    score: float  # Weighted score
    sub_goals_completed: List[str]
    sub_goals_total: int
    turns_used: int
    time_seconds: float
    error: Optional[str] = None
    details: Optional[Dict] = None


@dataclass
class CategoryResult:
    """Aggregated results for a category"""
    category: str
    success_rate: float
    progress_rate: float
    avg_score: float
    task_count: int
    tasks_successful: int


@dataclass
class BenchmarkResult:
    """Complete benchmark results"""
    submission_id: str
    model: Dict[str, Any]
    timestamp: str
    overall: Dict[str, float]
    by_category: Dict[str, CategoryResult]
    by_difficulty: Dict[str, Dict[str, float]]
    efficiency: Dict[str, float]
    task_results: List[TaskResult]


class HDHScorer:
    """Scorer for HDH-Bench tasks"""

    def __init__(self, tasks_dir: Path, config_path: Optional[Path] = None):
        self.tasks_dir = tasks_dir
        self.tasks = self._load_tasks()
        self.config = self._load_config(config_path)

    def _load_tasks(self) -> Dict[str, Dict]:
        """Load all task definitions"""
        tasks = {}
        for task_file in self.tasks_dir.glob("*.json"):
            with open(task_file) as f:
                data = json.load(f)
                for task in data.get("tasks", []):
                    tasks[task["task_id"]] = task
        return tasks

    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """Load evaluation configuration"""
        default_config = {
            "category_weights": {
                "patient_matching": 0.30,
                "cohort_building": 0.25,
                "data_quality": 0.20,
                "data_provenance": 0.15,
                "terminology": 0.10
            },
            "difficulty_multipliers": {
                "easy": 1.0,
                "medium": 1.5,
                "hard": 2.0,
                "expert": 3.0
            }
        }

        if config_path and config_path.exists():
            with open(config_path) as f:
                loaded = json.load(f)
                # Merge with defaults, extracting from nested structure if needed
                if "scoring" in loaded:
                    default_config["category_weights"] = loaded["scoring"].get("category_weights", default_config["category_weights"])
                    default_config["difficulty_multipliers"] = loaded["scoring"].get("difficulty_multipliers", default_config["difficulty_multipliers"])

        return default_config

    def score_task(self, task_id: str, response: Dict, verbose: bool = False) -> TaskResult:
        """Score a single task response"""
        if task_id not in self.tasks:
            return TaskResult(
                task_id=task_id,
                success=False,
                progress=0.0,
                score=0.0,
                sub_goals_completed=[],
                sub_goals_total=0,
                turns_used=response.get("turns_used", 0),
                time_seconds=response.get("time_seconds", 0),
                error=f"Unknown task: {task_id}"
            )

        task = self.tasks[task_id]
        agent_response = response.get("response", {})
        ground_truth = task.get("ground_truth", {})
        success_criteria = task.get("success_criteria", {})

        # Evaluate based on success criteria type
        criteria_type = success_criteria.get("type", "exact_match")

        if criteria_type == "exact_match":
            success, score, details = self._evaluate_exact_match(
                agent_response, ground_truth, success_criteria
            )
        elif criteria_type == "set_match":
            success, score, details = self._evaluate_set_match(
                agent_response, ground_truth, success_criteria
            )
        elif criteria_type == "threshold":
            success, score, details = self._evaluate_threshold(
                agent_response, ground_truth, success_criteria
            )
        elif criteria_type == "f1_score":
            success, score, details = self._evaluate_f1(
                agent_response, ground_truth, success_criteria
            )
        else:
            success, score, details = False, 0.0, {"error": f"Unknown criteria type: {criteria_type}"}

        # Calculate progress based on sub-goals
        grading = task.get("grading", {})
        sub_goals = grading.get("sub_goals", [])
        sub_goals_completed = self._evaluate_sub_goals(agent_response, sub_goals, ground_truth)
        progress = len(sub_goals_completed) / len(sub_goals) if sub_goals else score

        # Apply difficulty multiplier
        difficulty = task.get("difficulty", "medium")
        multiplier = self.config["difficulty_multipliers"].get(difficulty, 1.0)
        weighted_score = score * multiplier

        return TaskResult(
            task_id=task_id,
            success=success,
            progress=progress,
            score=weighted_score,
            sub_goals_completed=sub_goals_completed,
            sub_goals_total=len(sub_goals),
            turns_used=response.get("turns_used", 0),
            time_seconds=response.get("time_seconds", 0),
            details=details if verbose else None
        )

    def _evaluate_exact_match(self, response: Dict, ground_truth: Dict, criteria: Dict) -> Tuple[bool, float, Dict]:
        """Evaluate exact match criteria"""
        target_field = criteria.get("target_field")

        if target_field:
            response_value = self._get_nested_value(response, target_field)
            expected_value = self._get_nested_value(ground_truth, target_field)
            match = response_value == expected_value
            return match, 1.0 if match else 0.0, {"matched": match, "expected": expected_value, "got": response_value}

        # Compare entire ground truth structure
        match = self._deep_compare(response, ground_truth)
        return match, 1.0 if match else 0.0, {"matched": match}

    def _evaluate_set_match(self, response: Dict, ground_truth: Dict, criteria: Dict) -> Tuple[bool, float, Dict]:
        """Evaluate set match criteria (order doesn't matter)"""
        target_field = criteria.get("target_field")
        partial_credit = criteria.get("partial_credit", True)

        response_set = set(self._flatten_to_set(self._get_nested_value(response, target_field)))
        expected_set = set(self._flatten_to_set(self._get_nested_value(ground_truth, target_field)))

        if not expected_set:
            return True, 1.0, {"note": "No expected values"}

        intersection = response_set & expected_set
        precision = len(intersection) / len(response_set) if response_set else 0
        recall = len(intersection) / len(expected_set)

        if partial_credit:
            score = recall  # Give credit for what was found
        else:
            score = 1.0 if response_set == expected_set else 0.0

        success = recall >= 0.9  # 90% recall for success
        return success, score, {
            "precision": precision,
            "recall": recall,
            "expected_count": len(expected_set),
            "response_count": len(response_set),
            "matched_count": len(intersection)
        }

    def _evaluate_threshold(self, response: Dict, ground_truth: Dict, criteria: Dict) -> Tuple[bool, float, Dict]:
        """Evaluate threshold-based criteria"""
        target_field = criteria.get("target_field")
        threshold = criteria.get("threshold", 0.8)

        # For count-based thresholds
        if "count_range" in ground_truth:
            response_count = self._get_nested_value(response, target_field.replace("_accuracy", "").replace("count", "") + "count") or \
                           self._get_nested_value(response, "total_count") or \
                           self._get_nested_value(response, target_field.split("_")[0] + "_count") or 0

            if isinstance(response_count, str):
                try:
                    response_count = int(response_count)
                except:
                    response_count = 0

            expected_range = ground_truth["count_range"]
            in_range = expected_range[0] <= response_count <= expected_range[1]

            if in_range:
                score = 1.0
            else:
                mid = (expected_range[0] + expected_range[1]) / 2
                deviation = abs(response_count - mid) / mid if mid > 0 else 1
                score = max(0, 1 - deviation)

            return score >= threshold, score, {
                "response_count": response_count,
                "expected_range": expected_range,
                "in_range": in_range
            }

        # Generic threshold check
        response_value = self._get_nested_value(response, target_field) or 0
        if isinstance(response_value, str):
            try:
                response_value = float(response_value)
            except:
                response_value = 0

        score = min(1.0, response_value)
        return score >= threshold, score, {"value": response_value, "threshold": threshold}

    def _evaluate_f1(self, response: Dict, ground_truth: Dict, criteria: Dict) -> Tuple[bool, float, Dict]:
        """Evaluate F1-score based criteria (for matching tasks)"""
        target_field = criteria.get("target_field")
        threshold = criteria.get("threshold", 0.5)

        # For patient matching tasks, evaluate the matches
        response_items = self._get_nested_value(response, target_field) or []
        if isinstance(response_items, dict):
            response_items = [response_items]

        # Simplified F1 calculation based on count ranges
        if "count_range" in ground_truth or "num_patients_with_duplicates_range" in ground_truth:
            expected_range = ground_truth.get("count_range") or ground_truth.get("num_patients_with_duplicates_range", [0, 100])
            response_count = len(response_items) if isinstance(response_items, list) else 0

            if expected_range[0] <= response_count <= expected_range[1]:
                score = 0.8  # Base score for being in range
            else:
                mid = (expected_range[0] + expected_range[1]) / 2
                deviation = abs(response_count - mid) / mid if mid > 0 else 1
                score = max(0, 0.8 - deviation * 0.5)

            return score >= threshold, score, {
                "response_count": response_count,
                "expected_range": expected_range
            }

        # Default: just check if something was returned
        has_response = len(response_items) > 0 if isinstance(response_items, list) else bool(response_items)
        score = 0.5 if has_response else 0.0
        return score >= threshold, score, {"has_response": has_response}

    def _evaluate_sub_goals(self, response: Dict, sub_goals: List[Dict], ground_truth: Dict) -> List[str]:
        """Evaluate which sub-goals were completed"""
        completed = []
        for goal in sub_goals:
            goal_id = goal.get("id", "")

            # Simple heuristics for common sub-goals
            if "fetch" in goal_id or "retrieved" in goal_id.lower() or "queried" in goal_id.lower():
                # Check if response has meaningful data
                if response and len(str(response)) > 50:
                    completed.append(goal_id)
            elif "found" in goal_id.lower() or "correct" in goal_id.lower():
                # Check if the relevant field exists and has data
                if response:
                    completed.append(goal_id)
            else:
                # Default: give credit if response exists
                if response:
                    completed.append(goal_id)

        return completed

    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get nested value from dict using dot notation"""
        if not path or not obj:
            return obj

        parts = path.split(".")
        current = obj
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _flatten_to_set(self, value: Any) -> List:
        """Flatten a value to a list for set comparison"""
        if value is None:
            return []
        if isinstance(value, dict):
            return list(value.values())
        if isinstance(value, list):
            return value
        return [value]

    def _deep_compare(self, a: Any, b: Any) -> bool:
        """Deep comparison of two values"""
        if type(a) != type(b):
            return False
        if isinstance(a, dict):
            if set(a.keys()) != set(b.keys()):
                return False
            return all(self._deep_compare(a[k], b[k]) for k in a.keys())
        if isinstance(a, list):
            if len(a) != len(b):
                return False
            return all(self._deep_compare(x, y) for x, y in zip(sorted(a, key=str), sorted(b, key=str)))
        return a == b

    def score_all(self, responses: List[Dict], model_info: Dict = None, verbose: bool = False) -> BenchmarkResult:
        """Score all task responses and compute aggregate metrics"""
        task_results = []
        response_map = {r.get("task_id") or r.get("query_id"): r for r in responses}

        # Score each task
        for task_id in self.tasks.keys():
            if task_id in response_map:
                result = self.score_task(task_id, response_map[task_id], verbose)
            else:
                # Task not attempted
                result = TaskResult(
                    task_id=task_id,
                    success=False,
                    progress=0.0,
                    score=0.0,
                    sub_goals_completed=[],
                    sub_goals_total=len(self.tasks[task_id].get("grading", {}).get("sub_goals", [])),
                    turns_used=0,
                    time_seconds=0,
                    error="Task not attempted"
                )
            task_results.append(result)

        # Aggregate by category
        categories = {}
        for result in task_results:
            task = self.tasks.get(result.task_id, {})
            category = task.get("category", "unknown")
            if category not in categories:
                categories[category] = []
            categories[category].append(result)

        by_category = {}
        for category, results in categories.items():
            successful = sum(1 for r in results if r.success)
            by_category[category] = CategoryResult(
                category=category,
                success_rate=successful / len(results) if results else 0,
                progress_rate=sum(r.progress for r in results) / len(results) if results else 0,
                avg_score=sum(r.score for r in results) / len(results) if results else 0,
                task_count=len(results),
                tasks_successful=successful
            )

        # Aggregate by difficulty
        difficulties = {}
        for result in task_results:
            task = self.tasks.get(result.task_id, {})
            difficulty = task.get("difficulty", "unknown")
            if difficulty not in difficulties:
                difficulties[difficulty] = []
            difficulties[difficulty].append(result)

        by_difficulty = {}
        for difficulty, results in difficulties.items():
            successful = sum(1 for r in results if r.success)
            by_difficulty[difficulty] = {
                "success_rate": successful / len(results) if results else 0,
                "task_count": len(results)
            }

        # Overall metrics
        total_tasks = len(task_results)
        successful_tasks = sum(1 for r in task_results if r.success)
        overall = {
            "success_rate": successful_tasks / total_tasks if total_tasks else 0,
            "progress_rate": sum(r.progress for r in task_results) / total_tasks if total_tasks else 0,
            "weighted_score": sum(r.score for r in task_results) / total_tasks if total_tasks else 0
        }

        # Calculate F1 for patient matching tasks
        pm_results = [r for r in task_results if self.tasks.get(r.task_id, {}).get("category") == "patient_matching"]
        if pm_results:
            overall["f1_patient_matching"] = sum(r.score for r in pm_results) / len(pm_results)

        # Efficiency metrics
        efficiency = {
            "total_turns": sum(r.turns_used for r in task_results),
            "avg_turns_per_task": sum(r.turns_used for r in task_results) / total_tasks if total_tasks else 0,
            "total_time_seconds": sum(r.time_seconds for r in task_results),
            "avg_time_per_task": sum(r.time_seconds for r in task_results) / total_tasks if total_tasks else 0
        }

        return BenchmarkResult(
            submission_id=f"hdh-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            model=model_info or {"name": "unknown"},
            timestamp=datetime.now().isoformat(),
            overall=overall,
            by_category={k: asdict(v) for k, v in by_category.items()},
            by_difficulty=by_difficulty,
            efficiency=efficiency,
            task_results=[asdict(r) for r in task_results]
        )


def main():
    parser = argparse.ArgumentParser(description="HDH-Bench Scorer")
    parser.add_argument("--responses", "-r", required=True, help="Path to responses JSON file")
    parser.add_argument("--tasks-dir", "-t", default="benchmark/tasks", help="Path to tasks directory")
    parser.add_argument("--config", "-c", help="Path to evaluation config")
    parser.add_argument("--output", "-o", help="Output file for results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Include detailed scoring info")
    parser.add_argument("--model-name", help="Model name for leaderboard")
    args = parser.parse_args()

    # Find paths relative to script or absolute
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent.parent

    tasks_dir = Path(args.tasks_dir)
    if not tasks_dir.is_absolute():
        tasks_dir = root_dir / args.tasks_dir

    config_path = Path(args.config) if args.config else root_dir / "benchmark/config/evaluation_config.json"

    # Load responses
    with open(args.responses) as f:
        responses = json.load(f)

    if isinstance(responses, dict):
        responses = [responses]

    # Create scorer and run
    scorer = HDHScorer(tasks_dir, config_path if config_path.exists() else None)

    model_info = {"name": args.model_name} if args.model_name else None
    result = scorer.score_all(responses, model_info, args.verbose)

    # Output
    output_dict = asdict(result)
    output_json = json.dumps(output_dict, indent=2, default=str)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Results written to {args.output}")
    else:
        print(output_json)

    # Summary to stderr
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"HDH-BENCH RESULTS", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"Success Rate: {result.overall['success_rate']*100:.1f}%", file=sys.stderr)
    print(f"Progress Rate: {result.overall['progress_rate']*100:.1f}%", file=sys.stderr)
    print(f"Tasks: {sum(1 for r in result.task_results if r['success'])}/{len(result.task_results)} successful", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)


if __name__ == "__main__":
    main()
