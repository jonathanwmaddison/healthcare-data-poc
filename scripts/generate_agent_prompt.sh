#!/bin/bash
# Generate the complete prompt to give to an agent for benchmarking
# Usage: ./scripts/generate_agent_prompt.sh > agent_input.txt

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "# Healthcare Data Harmony Benchmark"
echo ""
echo "## Instructions"
echo ""
echo "You are being evaluated on your ability to query and integrate healthcare data from multiple systems."
echo "Complete each query below and return your results in the specified JSON format."
echo ""
echo "You have access to HTTP APIs. Use curl or equivalent to make requests."
echo ""
echo "---"
echo ""

# Include the agent prompt (context about the systems)
cat "$ROOT_DIR/data/benchmark/agent_prompt.md"

echo ""
echo "---"
echo ""
echo "## Benchmark Queries"
echo ""
echo "Complete each of the following queries. Return results in valid JSON matching the response_format."
echo ""

# Include the queries (but not expected results)
cat "$ROOT_DIR/data/benchmark/benchmark_queries.json" | jq -r '
  .queries[] |
  "### \(.id): \(.title)\n\n**Difficulty:** \(.difficulty)\n\n**Task:** \(.description)\n\n**Response Format:**\n```json\n\(.response_format | tojson)\n```\n\n---\n"
'

echo ""
echo "## Response Instructions"
echo ""
echo "For each query, provide your response in the following format:"
echo ""
echo '```json'
echo '{'
echo '  "query_id": "Q001",'
echo '  "response": { ... your response matching the response_format ... },'
echo '  "api_calls_made": [ ... list of API calls you made ... ],'
echo '  "reasoning": "Brief explanation of your approach"'
echo '}'
echo '```'
echo ""
echo "Submit all responses as a JSON array."
