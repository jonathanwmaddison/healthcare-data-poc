# HDH-Bench Results
**Generated**: 2026-02-04 19:35:18
**Benchmark Version**: 1.0.0

## Agents Tested
Claude-Direct

## Overall Scores

| Agent | Avg Score | Tasks | Time | Turns |
|-------|-----------|-------|------|-------|
| Claude-Direct | 38.0% | 6 | 142s | 19 |

## Task-by-Task Results


### Q001: Patient 360 View (Cross-System Matching)

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 100.0% | ✅ | 6/6 systems |

### Q002: Diabetic Cohort Building

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 100.0% | ✅ | 134 patients |

### Q003: Abnormal Glucose Detection

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 28.2% | ❌ | 20 patients |

### Q004: Duplicate Patient Detection

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 0.0% | ❌ | 0 groups |

### Q005: Cross-System Cohort with Validation

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 0.0% | ❌ | 0 patients, 0 valid |

### Q006: Data Quality Issues Detection

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 0.0% | ❌ | orph=0, aband=0 |

## Execution Details

- Total execution time: 142s
- Total turns: 19

## Notes

- Ground truth validation performed against master patient index
- Scores reflect accuracy against expected results
- Pass threshold varies by task complexity
