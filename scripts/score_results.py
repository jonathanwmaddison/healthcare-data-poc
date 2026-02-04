#!/usr/bin/env python3
"""
Score agent responses against ground truth.

Usage:
    python scripts/score_results.py agent_responses.json
    python scripts/score_results.py agent_responses.json --verbose
    python scripts/score_results.py agent_responses.json --output scores.json
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple


def load_ground_truth(root_dir: Path) -> Tuple[Dict, Dict]:
    """Load ground truth files."""
    mpi_path = root_dir / "data/benchmark/ground_truth/master_patient_index.json"
    expected_path = root_dir / "data/benchmark/ground_truth/expected_results.json"

    with open(mpi_path) as f:
        mpi = json.load(f)

    with open(expected_path) as f:
        expected = json.load(f)

    return mpi, expected


def score_q001(response: Dict, mpi: Dict, expected: Dict, verbose: bool) -> Dict:
    """Score Q001: Patient 360 View - patient matching across systems."""
    expected_ids = expected["queries"]["Q001"]["expected"]["patient_ids"]
    response_ids = response.get("response", {}).get("patient_ids", {})

    correct = 0
    total = len(expected_ids)
    details = []

    for system, expected_id in expected_ids.items():
        response_id = response_ids.get(system, "")
        if response_id == expected_id:
            correct += 1
            details.append(f"  {system}: CORRECT ({expected_id})")
        else:
            details.append(f"  {system}: WRONG (expected {expected_id}, got {response_id})")

    score = correct / total if total > 0 else 0

    result = {
        "query_id": "Q001",
        "score": round(score, 3),
        "correct_matches": correct,
        "total_systems": total,
        "max_score": 1.0
    }

    if verbose:
        result["details"] = details

    return result


def score_q002(response: Dict, mpi: Dict, expected: Dict, verbose: bool) -> Dict:
    """Score Q002: Diabetic Patient Cohort."""
    expected_range = expected["queries"]["Q002"]["expected"]["count_range"]
    response_count = response.get("response", {}).get("total_count", 0)
    response_ids = response.get("response", {}).get("patient_ids", [])

    # Check if count is in expected range
    in_range = expected_range[0] <= response_count <= expected_range[1]

    # Score based on how close to expected range
    if in_range:
        score = 1.0
    else:
        mid = (expected_range[0] + expected_range[1]) / 2
        deviation = abs(response_count - mid) / mid
        score = max(0, 1 - deviation)

    result = {
        "query_id": "Q002",
        "score": round(score, 3),
        "response_count": response_count,
        "expected_range": expected_range,
        "in_range": in_range,
        "max_score": 1.0
    }

    if verbose:
        result["response_patient_count"] = len(response_ids)

    return result


def score_q003(response: Dict, mpi: Dict, expected: Dict, verbose: bool) -> Dict:
    """Score Q003: Abnormal Glucose Results."""
    expected_range = expected["queries"]["Q003"]["expected"]["count_range"]
    response_count = response.get("response", {}).get("total_count", 0)

    in_range = expected_range[0] <= response_count <= expected_range[1]

    if in_range:
        score = 1.0
    else:
        mid = (expected_range[0] + expected_range[1]) / 2
        deviation = abs(response_count - mid) / mid
        score = max(0, 1 - deviation)

    result = {
        "query_id": "Q003",
        "score": round(score, 3),
        "response_count": response_count,
        "expected_range": expected_range,
        "in_range": in_range,
        "max_score": 1.0
    }

    return result


def score_q004(response: Dict, mpi: Dict, expected: Dict, verbose: bool) -> Dict:
    """Score Q004: Duplicate Patient Detection."""
    expected_range = expected["queries"]["Q004"]["expected"]["num_patients_with_duplicates_range"]

    duplicate_groups = response.get("response", {}).get("duplicate_groups", [])
    response_count = len(duplicate_groups)

    # Build set of actual duplicates from MPI
    actual_duplicates = set()
    for patient in mpi.get("patients", []):
        if "duplicate_ids" in patient:
            actual_duplicates.add(patient["canonical_id"])

    in_range = expected_range[0] <= response_count <= expected_range[1]

    if in_range:
        score = 0.8  # Base score for being in range
    else:
        mid = (expected_range[0] + expected_range[1]) / 2
        deviation = abs(response_count - mid) / mid
        score = max(0, 0.8 - deviation)

    # TODO: Could add precision/recall scoring by comparing detected duplicates
    # to actual duplicates in MPI

    result = {
        "query_id": "Q004",
        "score": round(score, 3),
        "response_duplicate_groups": response_count,
        "expected_range": expected_range,
        "actual_duplicates_in_ground_truth": len(actual_duplicates),
        "max_score": 1.0
    }

    return result


def score_q005(response: Dict, mpi: Dict, expected: Dict, verbose: bool) -> Dict:
    """Score Q005: Cross-System Cohort Query."""
    patients = response.get("response", {}).get("patients", [])
    response_count = response.get("response", {}).get("total_count", len(patients))

    # This is a hard query - we check if the agent:
    # 1. Made cross-system matches
    # 2. Has reasonable patient IDs

    valid_matches = 0
    for patient in patients:
        ehr_id = patient.get("ehr_id", "")
        pharmacy_id = patient.get("pharmacy_id", "")
        lis_id = patient.get("lis_id", "")

        # Check if IDs look valid (right prefix)
        if (ehr_id.startswith("MRN-") and
            pharmacy_id.startswith("RX-") and
            lis_id.startswith("LAB-")):

            # Check if they could be the same patient (same suffix number)
            try:
                ehr_num = int(ehr_id.replace("MRN-", "").replace("100", ""))
                pharm_num = int(pharmacy_id.replace("RX-", "").replace("400", ""))
                lis_num = int(lis_id.replace("LAB-", "").replace("200", ""))

                if ehr_num == pharm_num == lis_num:
                    valid_matches += 1
            except ValueError:
                pass

    # Score based on valid cross-system matches
    if len(patients) > 0:
        match_rate = valid_matches / len(patients)
    else:
        match_rate = 0

    # Also reward finding patients (even if matching isn't perfect)
    count_score = min(1.0, response_count / 50) if response_count > 0 else 0

    score = (match_rate * 0.7) + (count_score * 0.3)

    result = {
        "query_id": "Q005",
        "score": round(score, 3),
        "response_count": response_count,
        "valid_cross_system_matches": valid_matches,
        "match_rate": round(match_rate, 3),
        "max_score": 1.0
    }

    return result


def score_q006(response: Dict, mpi: Dict, expected: Dict, verbose: bool) -> Dict:
    """Score Q006: Data Quality Issues."""
    orphaned = response.get("response", {}).get("orphaned_results", {})
    abandoned = response.get("response", {}).get("abandoned_orders", {})

    orphaned_count = orphaned.get("count", 0)
    abandoned_count = abandoned.get("count", 0)

    expected_orphaned = expected["queries"]["Q006"]["expected"]["orphaned_results"]["count_range"]
    expected_abandoned = expected["queries"]["Q006"]["expected"]["abandoned_orders"]["count_range"]

    # Score orphaned results
    if expected_orphaned[0] <= orphaned_count <= expected_orphaned[1]:
        orphaned_score = 1.0
    else:
        mid = (expected_orphaned[0] + expected_orphaned[1]) / 2
        deviation = abs(orphaned_count - mid) / mid if mid > 0 else 1
        orphaned_score = max(0, 1 - deviation)

    # Score abandoned orders
    if expected_abandoned[0] <= abandoned_count <= expected_abandoned[1]:
        abandoned_score = 1.0
    else:
        mid = (expected_abandoned[0] + expected_abandoned[1]) / 2
        deviation = abs(abandoned_count - mid) / mid if mid > 0 else 1
        abandoned_score = max(0, 1 - deviation)

    score = (orphaned_score + abandoned_score) / 2

    result = {
        "query_id": "Q006",
        "score": round(score, 3),
        "orphaned_results": {
            "response": orphaned_count,
            "expected_range": expected_orphaned,
            "score": round(orphaned_score, 3)
        },
        "abandoned_orders": {
            "response": abandoned_count,
            "expected_range": expected_abandoned,
            "score": round(abandoned_score, 3)
        },
        "max_score": 1.0
    }

    return result


def score_all(responses: List[Dict], mpi: Dict, expected: Dict, verbose: bool) -> Dict:
    """Score all query responses."""
    scorers = {
        "Q001": score_q001,
        "Q002": score_q002,
        "Q003": score_q003,
        "Q004": score_q004,
        "Q005": score_q005,
        "Q006": score_q006,
    }

    # Query weights (sum to 1.0)
    weights = {
        "Q001": 0.20,  # Patient matching
        "Q002": 0.10,  # Simple cohort
        "Q003": 0.15,  # Lab query
        "Q004": 0.25,  # Duplicate detection (hard)
        "Q005": 0.20,  # Cross-system cohort (hard)
        "Q006": 0.10,  # Data quality
    }

    results = []
    response_map = {r.get("query_id"): r for r in responses}

    total_weighted_score = 0

    for query_id, scorer in scorers.items():
        response = response_map.get(query_id, {"query_id": query_id, "response": {}})
        result = scorer(response, mpi, expected, verbose)
        result["weight"] = weights[query_id]
        result["weighted_score"] = round(result["score"] * weights[query_id], 4)
        results.append(result)
        total_weighted_score += result["weighted_score"]

    return {
        "total_score": round(total_weighted_score, 3),
        "max_possible": 1.0,
        "percentage": round(total_weighted_score * 100, 1),
        "query_results": results
    }


def main():
    parser = argparse.ArgumentParser(description="Score benchmark responses")
    parser.add_argument("responses_file", help="JSON file with agent responses")
    parser.add_argument("--verbose", "-v", action="store_true", help="Include detailed scoring info")
    parser.add_argument("--output", "-o", help="Output file for scores (default: stdout)")
    args = parser.parse_args()

    # Find root directory
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    # Load ground truth
    try:
        mpi, expected = load_ground_truth(root_dir)
    except FileNotFoundError as e:
        print(f"Error: Could not load ground truth files: {e}", file=sys.stderr)
        sys.exit(1)

    # Load agent responses
    try:
        with open(args.responses_file) as f:
            responses = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find responses file: {args.responses_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in responses file: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle both array and single response formats
    if isinstance(responses, dict):
        responses = [responses]

    # Score responses
    scores = score_all(responses, mpi, expected, args.verbose)

    # Output
    output = json.dumps(scores, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Scores written to {args.output}")
    else:
        print(output)

    # Print summary
    print(f"\n{'='*50}", file=sys.stderr)
    print(f"BENCHMARK SCORE: {scores['percentage']}%", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)


if __name__ == "__main__":
    main()
