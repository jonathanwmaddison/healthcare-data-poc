# HDH-Bench: Healthcare Data Harmony Benchmark

A benchmark for evaluating AI agents on realistic healthcare data integration tasks across 6 fragmented FHIR R4 systems with no shared patient identifiers.

HDH-Bench tests whether AI agents can match patient identities, build clinical cohorts, perform cross-system joins, and detect data quality issues — the same challenges faced by real-world health data engineers.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      AI Agent                           │
│            (Claude, GPT-4o, Gemini, ...)                │
└──────────────────────┬──────────────────────────────────┘
                       │ FHIR R4 REST (tool use)
        ┌──────────────┼──────────────────────┐
        ▼              ▼                      ▼
   ┌─────────┐   ┌──────────┐          ┌──────────┐
   │   EHR   │   │   LIS    │   ...    │ Billing  │
   │ :8001   │   │ :8002    │          │ :8007    │
   │ Patient │   │ Patient  │          │ Patient  │
   │ Cond.   │   │ Order    │          │ Claim    │
   │         │   │ Obs.     │          │ Coverage │
   └─────────┘   └──────────┘          └──────────┘
   MRN-XXXXXX    LAB-XXXXXX            ACCT-XXXXXX

   No shared patient ID — agents must match by demographics
```

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- An API key for your agent (Anthropic, OpenAI, etc.)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate seed data and ground truth
python3 scripts/generate.py

# 3. Verify ground truth against seed data
python3 scripts/verify.py

# 4. Start the 6 FHIR services
docker-compose up -d

# 5. Run the benchmark
export ANTHROPIC_API_KEY=sk-...
python3 scripts/run.py --agent anthropic --all-tasks
```

Or use the Makefile:

```bash
make generate
make verify
make services
make run
```

## Tasks

HDH-Bench includes 12 tasks across 4 categories:

| ID | Category | Title | Difficulty | Systems |
|----|----------|-------|-----------|---------|
| T01 | Patient Matching | Single-system patient lookup | Easy | EHR |
| T02 | Patient Matching | Cross-system match (EHR + Pharmacy) | Medium | EHR, Pharmacy |
| T03 | Patient Matching | Full 360 match (all 6 systems) | Hard | All 6 |
| T04 | Cohort Building | Diabetic patients (ICD-10 E11.9) | Easy | EHR |
| T05 | Cohort Building | HbA1c lab results (LOINC 4548-4) | Easy | LIS |
| T06 | Cohort Building | Active metformin (RxNorm 860975) | Easy | Pharmacy |
| T07 | Cross-System | Diabetics on metformin | Hard | EHR + Pharmacy |
| T08 | Cross-System | Diabetics + metformin + HbA1c | Hard | EHR + Pharmacy + LIS |
| T09 | Cross-System | Complete record for one patient | Medium | All 6 |
| T10 | Data Quality | Orphaned lab results (no `basedOn`) | Medium | LIS |
| T11 | Data Quality | Abandoned orders (stale active) | Medium | LIS |
| T12 | Terminology | Legacy ICD-9 conditions | Easy | EHR |

Task definitions: [`benchmark/tasks.json`](benchmark/tasks.json)

## Scoring

| Metric | Description |
|--------|-------------|
| **F1 score** | Used for ID-set tasks (T04-T06, T10-T12) and cross-system pair/triple tasks (T07, T08) |
| **Field-level average** | Used for exact-record tasks (T01-T03, T09) — average of per-field scores |
| **Pass threshold** | 0.7 for all tasks |
| **Overall score** | Simple average of 12 task scores (0.0 – 1.0) |

No difficulty multipliers or category weights. A perfect score is 1.0 (12/12 tasks at F1 = 1.0).

## Leaderboard

| Agent | Overall | Passed | T01 | T02 | T03 | T04 | T05 | T06 | T07 | T08 | T09 | T10 | T11 | T12 | Date |
|-------|---------|--------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|------|
| *Submit a PR to add your results* | | | | | | | | | | | | | | | |

## Results Format

Each benchmark run produces a directory under `results/benchmark_runs/<run_id>/` containing:

| File | Description |
|------|-------------|
| `metadata.json` | Run ID, agent name, timestamp, overall score |
| `raw_results.json` | Per-task agent responses, turn counts, timing |
| `scored_results.json` | Per-task scores, pass/fail, scoring details |
| `REPORT.md` | Human-readable summary |

## Adding a New Agent

1. Implement an async runner function in `scripts/run.py`:

```python
async def run_my_agent(task_prompt: str, context: str, max_turns: int = 20) -> Dict:
    # Send context + task_prompt to your agent
    # The agent calls fhir_request(url) as a tool to query FHIR services
    # Return: {"response": {...}, "turns": N, "time_seconds": T, "tokens": N}
```

2. Register it in `AGENT_RUNNERS`:

```python
AGENT_RUNNERS = {
    "anthropic": run_anthropic,
    "openai": run_openai,
    "my_agent": run_my_agent,
}
```

3. Run:

```bash
python3 scripts/run.py --agent my_agent --all-tasks
```

The agent receives the system prompt from [`data/benchmark/agent_prompt.md`](data/benchmark/agent_prompt.md) and uses the `fhir_request` tool to query the 6 FHIR services.

## Repository Structure

```
healthcare-data-poc/
├── benchmark/
│   ├── __init__.py
│   ├── tasks.json              # 12 task definitions
│   └── scorer.py               # Scoring logic (F1, field-level)
├── data/
│   ├── seed/                   # FHIR bundles loaded by services
│   └── benchmark/
│       ├── agent_prompt.md     # System prompt for agents
│       └── ground_truth/
│           ├── ground_truth.json
│           └── master_patient_index.json
├── scripts/
│   ├── generate.py             # Data + ground truth generator
│   ├── verify.py               # GT verification against seed data
│   └── run.py                  # Benchmark runner
├── services/                   # 6 FHIR R4 microservices (Docker)
├── results/                    # Benchmark run outputs
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── README.md
```

## Citation

```bibtex
@misc{hdh-bench-2025,
  title={HDH-Bench: Healthcare Data Harmony Benchmark},
  author={HDH-Bench Contributors},
  year={2025},
  url={https://github.com/your-org/healthcare-data-poc}
}
```

## License

MIT License — see [LICENSE](LICENSE).
