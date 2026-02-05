# HDH-Bench Results
**Generated**: 2026-02-04 18:45:13
**Benchmark Version**: 1.0.0

## Agents Tested
Claude-Direct

## Overall Scores

| Agent | Avg Score | Tasks | Time | Turns |
|-------|-----------|-------|------|-------|
| Claude-Direct | 47.1% | 6 | 329s | 75 |

## Task-by-Task Results


### Q001: Patient 360 View (Cross-System Matching)

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 83.3% | ✅ | 5/6 systems |

### Q002: Diabetic Cohort Building

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 100.0% | ✅ | 134 patients |

### Q003: Abnormal Glucose Detection

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 56.3% | ❌ | 40 patients |

### Q004: Duplicate Patient Detection

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 0.0% | ❌ | 7 groups |

### Q005: Cross-System Cohort with Validation

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 0.0% | ❌ | 0 patients, 0 valid |

### Q006: Data Quality Issues Detection

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 42.8% | ❌ | orph=101, aband=40 |

## Execution Details

- Total execution time: 329s
- Total turns: 75

## Notes

- Ground truth validation performed against master patient index
- Scores reflect accuracy against expected results
- Pass threshold varies by task complexity
