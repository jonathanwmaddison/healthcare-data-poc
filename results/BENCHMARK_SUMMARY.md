# HDH-Bench Agent Comparison Results

## Executive Summary

This repository contains validated benchmark results comparing AI agent performance on healthcare data integration tasks.

**Latest Results** (2026-02-04):
- **Claude Sonnet 4.5**: 47.5% overall (best run)
- **GPT-5.2 (Agents SDK)**: 21.3% overall  
- **GPT-4o (Direct API)**: 8.2% overall

## Key Findings

### Claude Sonnet 4.5 Strengths
- ✅ **Perfect patient matching** across 6 healthcare systems (100%)
- ✅ **Perfect cohort building** - found exact diabetic patient count (100%)
- Uses 2-3x more turns (68 avg) for thorough exploration
- Most consistent across multiple runs

### GPT-5.2 Strengths
- ✅ Best at cross-system cohort matching (71% - only agent with valid matches)
- Faster execution but less consistent

### Common Challenges (All Agents)
- ❌ Duplicate patient detection (0% across all agents)
- ❌ Cross-system cohort with validation
- ❌ Data quality issue detection

## Validated Runs

All runs stored in `results/benchmark_runs/` with:
- Raw agent responses
- Ground truth validation
- Detailed scoring breakdown
- Human-readable reports

See [benchmark_runs/README.md](benchmark_runs/README.md) for details.

## Benchmark Tasks

| ID | Task | Difficulty | Best Agent | Best Score |
|----|------|------------|------------|------------|
| Q001 | Patient 360 View | Hard | Claude | 100% |
| Q002 | Diabetic Cohort | Easy | Claude | 100% |
| Q003 | Abnormal Glucose | Medium | Claude | 55% |
| Q004 | Duplicate Detection | Hard | All | 0% |
| Q005 | Cross-System Cohort | Expert | GPT-5.2 | 71% |
| Q006 | Data Quality | Medium | Claude | 44% |

## Running Your Own Tests

```bash
# Quick test
python scripts/run_validated_benchmark.py --agents claude --tasks Q001,Q002

# Full benchmark
python scripts/run_validated_benchmark.py --agents claude --all-tasks

# Compare multiple agents
python scripts/run_validated_benchmark.py --agents claude,codex --all-tasks
```

Results automatically saved to `results/benchmark_runs/TIMESTAMP/` with full validation.
