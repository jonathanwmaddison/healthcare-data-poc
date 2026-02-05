# HDH-Bench Validated Runs

This directory contains timestamped benchmark runs with full validation against ground truth.

## Directory Structure

Each run is stored in a timestamped directory (YYYYMMDD_HHMMSS) containing:

```
20260204_172804/
├── metadata.json       # Run configuration and metadata
├── raw_results.json    # Complete agent responses and execution details
├── validation.json     # Ground truth validation with detailed scoring
└── REPORT.md          # Human-readable summary report
```

## Files Description

### metadata.json
- Run ID and timestamp
- Agents tested
- Tasks executed
- File references

### raw_results.json
- Complete agent responses for each task
- Execution metrics (time, turns, tokens)
- Raw output from agents

### validation.json
- Ground truth validation results
- Per-task scoring with details
- Pass/fail indicators
- System-level match validation
- Summary statistics

### REPORT.md
- Human-readable summary
- Task-by-task comparison table
- Overall scores and metrics
- Pass/fail indicators (✅/❌)

## Recent Runs

| Run ID | Agent | Overall | Q001 | Q002 | Q003 | Q004 | Q005 | Q006 |
|--------|-------|:-------:|:----:|:----:|:----:|:----:|:----:|:----:|
| 20260204_172804 | Claude Sonnet 4.5 | 38.3% | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 20260204_173323 | Claude Sonnet 4.5 | 47.5% | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |

## Task Key

- **Q001**: Patient 360 View (Cross-System Matching)
- **Q002**: Diabetic Cohort Building
- **Q003**: Abnormal Glucose Detection
- **Q004**: Duplicate Patient Detection
- **Q005**: Cross-System Cohort with Validation
- **Q006**: Data Quality Issues Detection

## Running New Benchmarks

```bash
# Run all tasks with Claude
python scripts/run_validated_benchmark.py --agents claude --all-tasks

# Run specific tasks
python scripts/run_validated_benchmark.py --agents claude --tasks Q001,Q002,Q005

# Compare multiple agents
python scripts/run_validated_benchmark.py --agents claude,codex --all-tasks

# Verbose output
python scripts/run_validated_benchmark.py --agents claude --all-tasks --verbose
```

## Validation Criteria

### Task Scoring

- **Q001 (Patient 360)**: Score = matched_systems / 6 (Pass ≥ 80%)
- **Q002 (Diabetic Cohort)**: In range [92-154] patients (Pass = in range)
- **Q003 (Abnormal Glucose)**: Deviation from ~71 patients (Pass ≥ 70%)
- **Q004 (Duplicates)**: In range [39-59] groups (Pass = in range)
- **Q005 (Cross-System)**: Valid cross-system matches (Pass ≥ 50%)
- **Q006 (Data Quality)**: Orphaned [113-123] + Abandoned [15-25] (Pass ≥ 70%)

### Overall Score

Overall score = average of all task scores, weighted equally.

## Notes

- All results validated against `data/benchmark/ground_truth/master_patient_index.json`
- Ground truth data is NOT provided to agents during execution
- Agents must discover patient relationships through API exploration
- Results are reproducible but may vary due to agent non-determinism
