#!/bin/bash
# Validate benchmark environment is running correctly

set -e

echo "============================================================"
echo "HEALTHCARE DATA BENCHMARK - ENVIRONMENT VALIDATION"
echo "============================================================"

echo ""
echo "=== Service Health Check ==="

SYSTEMS=("ehr:8001" "lis:8002" "ris:8003" "pharmacy:8005" "pas:8006" "billing:8007")
ALL_HEALTHY=true

for sys in "${SYSTEMS[@]}"; do
    name="${sys%%:*}"
    port="${sys##*:}"

    if curl -s "localhost:$port/health" > /dev/null 2>&1; then
        echo "  $name (port $port): OK"
    else
        echo "  $name (port $port): FAIL - not responding"
        ALL_HEALTHY=false
    fi
done

if [ "$ALL_HEALTHY" = false ]; then
    echo ""
    echo "ERROR: Some services are not healthy."
    echo "Run: docker-compose up -d"
    exit 1
fi

echo ""
echo "=== Data Load Check ==="

for sys in "${SYSTEMS[@]}"; do
    name="${sys%%:*}"
    port="${sys##*:}"

    count=$(curl -s "localhost:$port/fhir/r4/Patient" | jq '.total // 0' 2>/dev/null)
    echo "  $name: $count patients"
done

echo ""
echo "=== Patient ID Fragmentation Check ==="
echo "Same patient (patient-00042) across systems:"
echo ""

echo "  EHR (MRN-100042):"
curl -s localhost:8001/fhir/r4/Patient/MRN-100042 | jq -r '  "    Name: \(.name[0].given[0]) \(.name[0].family)"' 2>/dev/null || echo "    NOT FOUND"

echo "  LIS (LAB-200042):"
curl -s localhost:8002/fhir/r4/Patient/LAB-200042 | jq -r '"    Name: \(.name[0].given[0]) \(.name[0].family)"' 2>/dev/null || echo "    NOT FOUND"

echo "  Pharmacy (RX-400042):"
curl -s localhost:8005/fhir/r4/Patient/RX-400042 | jq -r '"    Name: \(.name[0].given[0]) \(.name[0].family)"' 2>/dev/null || echo "    NOT FOUND"

echo "  Billing (ACCT-600042):"
curl -s localhost:8007/fhir/r4/Patient/ACCT-600042 | jq -r '"    Name: \(.name[0].given[0]) \(.name[0].family)"' 2>/dev/null || echo "    NOT FOUND"

echo ""
echo "=== Benchmark Files Check ==="

if [ -f "data/benchmark/api_catalog.json" ]; then
    count=$(jq '.systems | length' data/benchmark/api_catalog.json)
    echo "  api_catalog.json: $count systems defined"
else
    echo "  api_catalog.json: NOT FOUND"
fi

if [ -f "data/benchmark/benchmark_queries.json" ]; then
    count=$(jq '.queries | length' data/benchmark/benchmark_queries.json)
    echo "  benchmark_queries.json: $count queries defined"
else
    echo "  benchmark_queries.json: NOT FOUND"
fi

if [ -f "data/benchmark/master_patient_index.json" ]; then
    count=$(jq '.total_patients' data/benchmark/master_patient_index.json)
    echo "  master_patient_index.json: $count patients in ground truth"
else
    echo "  master_patient_index.json: NOT FOUND"
fi

echo ""
echo "============================================================"
echo "VALIDATION COMPLETE - Benchmark environment is ready"
echo "============================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Give your agent the API catalog:"
echo "   cat data/benchmark/api_catalog.json"
echo ""
echo "2. Run benchmark queries (give these to your agent):"
echo "   cat data/benchmark/benchmark_queries.json"
echo ""
echo "3. Score results against ground truth (for evaluation only):"
echo "   cat data/benchmark/master_patient_index.json"
echo ""
