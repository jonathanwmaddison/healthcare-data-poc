# HDH-Bench: Healthcare Data Harmonization Benchmark

A benchmark for evaluating AI agents on healthcare data integration tasks across fragmented systems.

## Overview

HDH-Bench tests an agent's ability to navigate real-world healthcare data challenges:

- **Patient Identity Fragmentation**: Same patient has different IDs in each system (EHR, LIS, Pharmacy, etc.)
- **Terminology Variations**: ICD-10, ICD-9, LOINC, RxNorm across systems
- **Data Quality Issues**: Orphaned records, abandoned orders, legacy codes
- **Cross-System Integration**: Coordinating data from multiple sources to answer clinical questions

## What Makes This Benchmark Unique

Unlike single-EHR benchmarks (MedAgentBench) or FHIR query generation (FHIR-AgentBench), HDH-Bench evaluates:

1. **Multi-System Navigation**: 6 independent FHIR R4 APIs with fragmented patient identities
2. **Real-World Data Variations**: FEBRL-style name typos, abbreviations, case changes
3. **Ground Truth MPI**: Hidden master patient index for scoring without data leakage
4. **Clinical Integration Tasks**: Medication monitoring, care gap analysis, billing reconciliation

## Systems Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (:8000)                       │
└───────┬─────────┬─────────┬─────────┬─────────┬─────────────┘
        │         │         │         │         │
   ┌────▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼────┐ ┌──▼──┐ ┌───────┐
   │  EHR   │ │  LIS  │ │  RIS  │ │Pharmacy│ │ PAS │ │Billing│
   │ :8001  │ │ :8002 │ │ :8003 │ │ :8005  │ │:8006│ │ :8007 │
   │MRN-*   │ │LAB-*  │ │RAD-*  │ │RX-*    │ │ADT-*│ │ACCT-* │
   └────────┘ └───────┘ └───────┘ └────────┘ └─────┘ └───────┘
```

## Task Categories

| Category | Tasks | Description |
|----------|-------|-------------|
| `patient_matching` | 5 | Match patients across systems without MPI access |
| `cross_system_integration` | 5 | Clinical questions requiring multi-system data |
| `cohort_building` | 5 | Build patient cohorts from clinical criteria |
| `data_quality` | 6 | Find data issues (orphans, duplicates, anomalies) |
| `data_provenance` | 5 | Trace data lineage, resolve conflicts |
| `terminology` | 5 | Navigate ICD-10, ICD-9, LOINC, RxNorm codes |

**Total: 31 tasks** across easy, medium, hard, and expert difficulty levels.

## Quick Start

### 1. Start the Environment

```bash
# Generate benchmark data (1000 patients, 6 systems)
python scripts/generate_hdh_benchmark_data.py --patients 1000

# Start all services
docker-compose up -d

# Verify services are running
curl http://localhost:8001/health  # EHR
curl http://localhost:8002/health  # LIS
```

### 2. Run Your Agent

Provide your agent with:
- `data/benchmark/agent_prompt.md` - System descriptions and API reference
- Base URLs: `http://localhost:8001-8007/fhir/r4/`

**Do NOT provide**:
- Ground truth files in `data/benchmark/ground_truth/`
- Task answer keys or expected results

### 3. Score Results

```bash
python benchmark/evaluation/scorer.py \
  --responses your_agent_responses.json \
  --output results.json \
  --verbose
```

## Response Format

Agent responses should be JSON with this structure:

```json
{
  "task_id": "HDH-MPI-001",
  "response": {
    // Task-specific response fields
  },
  "turns_used": 4,
  "time_seconds": 12.5
}
```

See `benchmark/examples/sample_responses.json` for examples.

## Metrics

| Metric | Description |
|--------|-------------|
| **Success Rate** | Tasks fully completed correctly |
| **Progress Rate** | Percentage of sub-goals achieved |
| **F1 Score** | Precision/recall for matching tasks |
| **Efficiency** | Turns and time per task |

## Evaluation Dimensions

HDH-Bench supports multiple evaluation configurations:

- **Information Mode**: Full API docs vs discovery mode
- **Interaction Mode**: Single-turn vs multi-turn
- **Hint Level**: None, minimal, moderate, full

## File Structure

```
benchmark/
├── tasks/                    # Task definitions (31 tasks)
│   ├── patient_matching.json
│   ├── cross_system_integration.json
│   ├── cohort_building.json
│   ├── data_quality.json
│   ├── data_provenance.json
│   └── terminology.json
├── config/
│   └── evaluation_config.json
├── evaluation/
│   └── scorer.py            # Scoring implementation
├── examples/
│   └── sample_responses.json
└── schema/
    └── task_schema.json

data/
├── benchmark/
│   ├── agent_prompt.md      # Give this to agents
│   └── ground_truth/        # DO NOT give to agents
│       ├── master_patient_index.json
│       └── expected_results.json
└── seed/                    # System seed data
```

## Research Use

If you use HDH-Bench in your research, please cite:

```bibtex
@misc{hdh-bench-2026,
  title={HDH-Bench: Healthcare Data Harmonization Benchmark},
  year={2026},
  url={https://github.com/your-repo/hdh-bench}
}
```

## License

MIT License - See LICENSE file for details.
