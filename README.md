# Healthcare Data Harmony Benchmark

A benchmark for evaluating AI agents and data pipelines on realistic healthcare data integration challenges.

## The Challenge

Healthcare data is fragmented across multiple systems, each with different patient IDs, data formats, and quality issues. This benchmark tests how well AI agents can:

1. **Discover** APIs across multiple healthcare systems
2. **Match** patient identities without shared identifiers
3. **Query** and aggregate clinical data from disparate sources
4. **Handle** real-world data quality problems

## Quick Start

```bash
# Clone the repo
git clone https://github.com/your-org/healthcare-data-benchmark.git
cd healthcare-data-benchmark

# Start the benchmark environment
docker-compose up -d

# Validate setup
./scripts/validate_benchmark.sh

# Run the benchmark harness
./scripts/run_benchmark.sh
```

## How It Works

### Data Fragmentation

The benchmark simulates 6 healthcare systems, each with **its own patient ID scheme**:

```
Same patient "Margaret Martin" appears as:

  EHR:      MRN-100042    "M. Martin"        DOB: 1950-12-14
  LIS:      LAB-200042    "Margaret Martin"  DOB: null
  Pharmacy: RX-400042     "Margaret Maroin"  DOB: 1950-12-14  (typo!)
  Billing:  ACCT-600042   "M. Martin"        DOB: null
```

### Benchmark Tasks

| Task | Difficulty | Description |
|------|------------|-------------|
| Q001 | Medium | Aggregate all data for one patient across systems |
| Q002 | Easy | Find all diabetic patients (single-system query) |
| Q003 | Medium | Find patients with abnormal lab results |
| Q004 | Hard | Identify duplicate patient records |
| Q005 | Hard | Cross-system cohort: diabetics on metformin with recent HbA1c |
| Q006 | Medium | Detect data quality issues (orphaned records) |

### What the Agent Receives

The benchmark harness provides agents with **only**:

1. **System prompt** with FHIR basics
2. **API catalog** listing available endpoints
3. **Benchmark queries** (tasks to complete)

Agents do **not** receive:
- Ground truth patient mappings
- Expected answers
- Hints about data quality issues

## Running the Benchmark

### Option 1: Interactive Mode

```bash
# Generate the agent prompt
./scripts/generate_agent_prompt.sh > agent_prompt.txt

# Give this to your agent and collect responses
# Then score the results
./scripts/score_results.sh agent_responses.json
```

### Option 2: Automated Harness

```bash
# Configure your agent endpoint
export AGENT_API_URL="http://localhost:8080/v1/chat"
export AGENT_API_KEY="your-key"

# Run full benchmark
./scripts/run_benchmark.sh --output results/

# View scores
cat results/scores.json
```

## Scoring

### Patient Matching (Q001, Q004, Q005)
```
Precision = Correct matches / Total claimed matches
Recall = Correct matches / Total true matches
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

### Cohort Queries (Q002, Q003, Q006)
```
Accuracy = Correct patients / Expected patients
```

### Aggregate Score
```
Total = Σ (query_score × query_weight)
```

## Repository Structure

```
healthcare-data-benchmark/
├── README.md                    # This file
├── BENCHMARK.md                 # Detailed benchmark documentation
├── docker-compose.yml           # Container orchestration
├── data/
│   ├── seed/                    # System seed data (loaded into DBs)
│   └── benchmark/
│       ├── agent_prompt.md      # What agents receive
│       ├── api_catalog.json     # API discovery info (for agents)
│       ├── benchmark_queries.json  # Tasks (for agents)
│       └── ground_truth/        # Scoring data (NOT for agents)
│           ├── master_patient_index.json
│           └── expected_results.json
├── scripts/
│   ├── validate_benchmark.sh    # Environment validation
│   ├── generate_agent_prompt.sh # Generate agent input
│   ├── run_benchmark.sh         # Automated benchmark runner
│   └── score_results.py         # Scoring script
└── services/                    # Healthcare system implementations
```

## Adding Your Own Queries

1. Add query to `data/benchmark/benchmark_queries.json`
2. Add expected results to `data/benchmark/ground_truth/expected_results.json`
3. Update scoring weights in `scripts/score_results.py`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE)

## Citation

If you use this benchmark in your research, please cite:

```bibtex
@software{healthcare_data_benchmark,
  title = {Healthcare Data Harmony Benchmark},
  year = {2024},
  url = {https://github.com/your-org/healthcare-data-benchmark}
}
```
