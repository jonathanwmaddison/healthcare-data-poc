#!/bin/bash
# Run the Healthcare Data Harmony Benchmark
#
# Usage:
#   ./scripts/run_benchmark.sh                    # Interactive mode
#   ./scripts/run_benchmark.sh --output results/  # Save results to directory
#   ./scripts/run_benchmark.sh --agent-url http://localhost:8080/v1/chat
#
# Environment variables:
#   AGENT_API_URL  - Agent API endpoint
#   AGENT_API_KEY  - Agent API key (optional)
#   AGENT_MODEL    - Model name (optional)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
OUTPUT_DIR=""
INTERACTIVE=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --agent-url)
            AGENT_API_URL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Healthcare Data Harmony Benchmark Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --output, -o DIR    Save results to directory"
            echo "  --agent-url URL     Agent API endpoint"
            echo "  --help, -h          Show this help"
            echo ""
            echo "Environment variables:"
            echo "  AGENT_API_URL       Agent API endpoint"
            echo "  AGENT_API_KEY       Agent API key"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "============================================================"
echo "    HEALTHCARE DATA HARMONY BENCHMARK"
echo "============================================================"
echo ""

# Step 1: Validate environment
echo -e "${YELLOW}Step 1: Validating benchmark environment...${NC}"
if ! "$SCRIPT_DIR/validate_benchmark.sh" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Benchmark environment validation failed.${NC}"
    echo "Run: docker-compose up -d"
    exit 1
fi
echo -e "${GREEN}Environment validated.${NC}"
echo ""

# Step 2: Generate agent prompt
echo -e "${YELLOW}Step 2: Generating agent prompt...${NC}"
PROMPT_FILE=$(mktemp)
"$SCRIPT_DIR/generate_agent_prompt.sh" > "$PROMPT_FILE"
echo -e "${GREEN}Prompt generated: $PROMPT_FILE${NC}"
echo ""

# Step 3: Check if automated or interactive
if [ -n "$AGENT_API_URL" ]; then
    echo -e "${YELLOW}Step 3: Running automated benchmark against $AGENT_API_URL${NC}"
    echo ""
    echo -e "${RED}NOTE: Automated agent integration not yet implemented.${NC}"
    echo "Please use interactive mode or implement your own agent caller."
    echo ""
    echo "The agent prompt has been saved to: $PROMPT_FILE"
    echo ""
    INTERACTIVE=true
fi

if [ "$INTERACTIVE" = true ]; then
    echo "============================================================"
    echo "    INTERACTIVE MODE"
    echo "============================================================"
    echo ""
    echo "The benchmark prompt has been generated. To complete the benchmark:"
    echo ""
    echo "1. Copy the prompt to your agent:"
    echo "   cat $PROMPT_FILE"
    echo ""
    echo "   Or copy to clipboard (macOS):"
    echo "   cat $PROMPT_FILE | pbcopy"
    echo ""
    echo "2. Run your agent and collect the JSON responses"
    echo ""
    echo "3. Save responses to a file (e.g., responses.json)"
    echo ""
    echo "4. Score the results:"
    echo "   python3 $SCRIPT_DIR/score_results.py responses.json"
    echo ""
    echo "============================================================"
    echo ""

    if [ -n "$OUTPUT_DIR" ]; then
        mkdir -p "$OUTPUT_DIR"
        cp "$PROMPT_FILE" "$OUTPUT_DIR/agent_prompt.txt"
        echo "Prompt saved to: $OUTPUT_DIR/agent_prompt.txt"
        echo ""
        echo "After getting agent responses, save them to:"
        echo "  $OUTPUT_DIR/agent_responses.json"
        echo ""
        echo "Then score with:"
        echo "  python3 $SCRIPT_DIR/score_results.py $OUTPUT_DIR/agent_responses.json -o $OUTPUT_DIR/scores.json"
    fi
fi

# Cleanup
if [ -z "$OUTPUT_DIR" ]; then
    echo "Temporary prompt file: $PROMPT_FILE"
    echo "(Will be deleted when terminal closes)"
fi
