#!/usr/bin/env python3
"""
HDH-Bench Scorer

Three scoring modes:
  - id_set:        F1 score of returned IDs vs expected IDs (T04-T06, T10-T12)
  - id_pair_set:   F1 on (ehr_id, pharmacy_id) tuples (T07)
  - id_triple_set: F1 on (ehr_id, pharmacy_id, lis_id) tuples (T08)
  - exact_record:  Average of field-level scores (T01-T03, T09)

Rules:
  - All scores 0.0-1.0, never above
  - Pass threshold: 0.7 for all tasks
  - Overall score: simple average of 12 task scores
  - No difficulty multipliers, no category weights in scoring

Usage:
    from benchmark.scorer import score_task, score_all
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

PASS_THRESHOLD = 0.7


def f1(predicted: set, expected: set) -> float:
    if not expected and not predicted:
        return 1.0
    if not expected or not predicted:
        return 0.0
    tp = len(predicted & expected)
    precision = tp / len(predicted)
    recall = tp / len(expected)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def score_id_set(response: Dict, ground_truth: Dict) -> Tuple[float, Dict]:
    """Score id_set tasks (T04-T06, T10-T12).

    Accepts response IDs from any of these fields:
    patient_ids, observation_ids, service_request_ids, condition_ids
    """
    resp_ids = set()
    for key in ["patient_ids", "observation_ids", "service_request_ids", "condition_ids", "ids"]:
        if key in response:
            resp_ids = set(response[key])
            break

    # Ground truth stores IDs under system-specific keys (preferred) and canonical.
    # Prefer system-specific IDs since agents return those (MRN-X, LAB-X, RX-X).
    expected_ids = set()
    for key in ["expected_ehr_ids", "expected_lis_ids", "expected_pharmacy_ids", "expected_ids"]:
        if key in ground_truth and ground_truth[key]:
            expected_ids = set(ground_truth[key])
            break

    score = f1(resp_ids, expected_ids)
    return score, {
        "predicted_count": len(resp_ids),
        "expected_count": len(expected_ids),
        "true_positives": len(resp_ids & expected_ids),
        "f1": score,
    }


def _normalize_pair(pair: Dict) -> Tuple[str, str]:
    return (pair.get("ehr_id", ""), pair.get("pharmacy_id", ""))


def _normalize_triple(triple: Dict) -> Tuple[str, str, str]:
    return (triple.get("ehr_id", ""), triple.get("pharmacy_id", ""), triple.get("lis_id", ""))


def score_id_pair_set(response: Dict, ground_truth: Dict) -> Tuple[float, Dict]:
    """Score id_pair_set tasks (T07)."""
    resp_pairs = set()
    for p in response.get("patients", []):
        resp_pairs.add(_normalize_pair(p))

    expected_pairs = set()
    for p in ground_truth.get("expected_pairs", []):
        expected_pairs.add(_normalize_pair(p))

    score = f1(resp_pairs, expected_pairs)
    return score, {
        "predicted_count": len(resp_pairs),
        "expected_count": len(expected_pairs),
        "true_positives": len(resp_pairs & expected_pairs),
        "f1": score,
    }


def score_id_triple_set(response: Dict, ground_truth: Dict) -> Tuple[float, Dict]:
    """Score id_triple_set tasks (T08)."""
    resp_triples = set()
    for t in response.get("patients", []):
        resp_triples.add(_normalize_triple(t))

    expected_triples = set()
    for t in ground_truth.get("expected_triples", []):
        expected_triples.add(_normalize_triple(t))

    score = f1(resp_triples, expected_triples)
    return score, {
        "predicted_count": len(resp_triples),
        "expected_count": len(expected_triples),
        "true_positives": len(resp_triples & expected_triples),
        "f1": score,
    }


def _score_field(response_val: Any, expected_val: Any) -> float:
    """Score a single field. Exact match for strings, F1 for sets/lists."""
    if expected_val is None:
        return 1.0 if response_val is None else 0.0

    if isinstance(expected_val, list):
        return f1(set(response_val or []), set(expected_val))

    if isinstance(expected_val, dict):
        if not isinstance(response_val, dict):
            return 0.0
        if not expected_val:
            return 1.0
        scores = []
        for k, v in expected_val.items():
            scores.append(_score_field(response_val.get(k), v))
        return sum(scores) / len(scores) if scores else 0.0

    # Scalar: exact match (case-insensitive for strings)
    if isinstance(expected_val, str) and isinstance(response_val, str):
        return 1.0 if response_val.strip().lower() == expected_val.strip().lower() else 0.0

    return 1.0 if response_val == expected_val else 0.0


def score_exact_record(response: Dict, ground_truth: Dict) -> Tuple[float, Dict]:
    """Score exact_record tasks (T01-T03, T09).

    Average of field-level scores from the 'expected' dict.
    """
    expected = ground_truth.get("expected", {})
    if not expected:
        return 0.0, {"error": "no expected data in ground truth"}

    field_scores = {}
    for key, expected_val in expected.items():
        response_val = response.get(key)
        field_scores[key] = _score_field(response_val, expected_val)

    score = sum(field_scores.values()) / len(field_scores) if field_scores else 0.0
    return score, {"field_scores": field_scores, "overall": score}


def score_task(task_id: str, response: Dict, ground_truth: Dict) -> Dict:
    """Score a single task. Returns {score, passed, details}."""
    gt_type = ground_truth.get("type", "id_set")

    if gt_type == "id_set":
        score, details = score_id_set(response, ground_truth)
    elif gt_type == "id_pair_set":
        score, details = score_id_pair_set(response, ground_truth)
    elif gt_type == "id_triple_set":
        score, details = score_id_triple_set(response, ground_truth)
    elif gt_type == "exact_record":
        score, details = score_exact_record(response, ground_truth)
    else:
        score, details = 0.0, {"error": f"unknown GT type: {gt_type}"}

    score = max(0.0, min(1.0, score))
    return {
        "task_id": task_id,
        "score": score,
        "passed": score >= PASS_THRESHOLD,
        "type": gt_type,
        "details": details,
    }


def score_all(responses: Dict[str, Dict], ground_truth: Dict) -> Dict:
    """Score all tasks. Returns overall results."""
    tasks_gt = ground_truth.get("tasks", {})
    results = []

    for task_id in sorted(tasks_gt.keys()):
        resp = responses.get(task_id, {})
        gt = tasks_gt[task_id]
        results.append(score_task(task_id, resp, gt))

    scores = [r["score"] for r in results]
    passed = [r for r in results if r["passed"]]

    return {
        "overall_score": sum(scores) / len(scores) if scores else 0.0,
        "tasks_passed": len(passed),
        "tasks_total": len(results),
        "pass_rate": len(passed) / len(results) if results else 0.0,
        "task_results": results,
    }
