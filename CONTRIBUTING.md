# Contributing to Healthcare Data Harmony Benchmark

Thank you for your interest in contributing! This document provides guidelines for contributing to the benchmark.

## Ways to Contribute

### 1. Adding New Benchmark Queries

To add a new query:

1. Add the query definition to `data/benchmark/benchmark_queries.json`:
   ```json
   {
     "id": "Q007",
     "title": "Your Query Title",
     "description": "What the agent needs to do...",
     "difficulty": "easy|medium|hard",
     "response_format": { ... }
   }
   ```

2. Add expected results to `data/benchmark/ground_truth/expected_results.json`

3. Add scoring logic to `scripts/score_results.py`

4. Update documentation in `BENCHMARK.md`

### 2. Improving Data Realism

The seed data generator is in `scripts/generate_benchmark_data.py`. You can:

- Add more realistic data quality issues
- Increase data volume
- Add new clinical scenarios
- Improve demographic variations

After changes, regenerate data:
```bash
python scripts/generate_benchmark_data.py
docker-compose build --no-cache
docker-compose down -v && docker-compose up -d
```

### 3. Adding New Healthcare Systems

To add a new system (e.g., a scheduling system):

1. Create service directory: `services/scheduling/`
2. Add Dockerfile and `app/main.py`
3. Add to `docker-compose.yml`
4. Update seed data generator
5. Update API catalog and documentation

### 4. Improving Scoring

The scoring algorithm in `scripts/score_results.py` can be improved:

- More nuanced patient matching scoring
- Partial credit for near-matches
- Better handling of edge cases

## Development Setup

```bash
# Clone the repo
git clone https://github.com/your-org/healthcare-data-benchmark.git
cd healthcare-data-benchmark

# Start services
docker-compose up -d

# Run validation
./scripts/validate_benchmark.sh

# Test scoring with sample response
python scripts/score_results.py data/benchmark/sample_response.json
```

## Code Style

- Python: Follow PEP 8
- Shell scripts: Use shellcheck
- JSON: 2-space indentation

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run validation: `./scripts/validate_benchmark.sh`
5. Test scoring: `python scripts/score_results.py data/benchmark/sample_response.json`
6. Submit a pull request

## Reporting Issues

When reporting issues, please include:

- Docker and Docker Compose versions
- Output of `./scripts/validate_benchmark.sh`
- Steps to reproduce
- Expected vs actual behavior

## Questions?

Open an issue with the "question" label.
