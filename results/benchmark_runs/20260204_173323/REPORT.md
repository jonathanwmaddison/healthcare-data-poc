# HDH-Bench Results
**Generated**: 2026-02-04 17:38:26
**Benchmark Version**: 1.0.0

## Agents Tested
Claude-Direct

## Overall Scores

| Agent | Avg Score | Tasks | Time | Turns |
|-------|-----------|-------|------|-------|
| Claude-Direct | 47.5% | 6 | 302s | 68 |

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
| Claude-Direct | 40.8% | ❌ | 29 patients |

### Q004: Duplicate Patient Detection

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 0.0% | ❌ | 8 groups |

### Q005: Cross-System Cohort with Validation

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 0.0% | ❌ | 0 patients, 0 valid |

### Q006: Data Quality Issues Detection

| Agent | Score | Pass | Details |
|-------|-------|------|--------|
| Claude-Direct | 44.1% | ❌ | orph=104, aband=40 |

## Execution Details

- Total execution time: 302s
- Total turns: 68

## Notes

- Ground truth validation performed against master patient index
- Scores reflect accuracy against expected results
- Pass threshold varies by task complexity
