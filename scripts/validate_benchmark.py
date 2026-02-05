#!/usr/bin/env python3
"""
Validate benchmark environment is running correctly.
Run this before benchmarking to ensure all systems are healthy.
"""
import requests
import json
import sys

SYSTEMS = {
    "ehr": {"port": 8001, "resources": ["Patient", "Condition"]},
    "lis": {"port": 8002, "resources": ["Patient", "ServiceRequest", "Observation"]},
    "ris": {"port": 8003, "resources": ["Patient", "ServiceRequest"]},
    "pharmacy": {"port": 8005, "resources": ["Patient", "MedicationRequest"]},
    "pas": {"port": 8006, "resources": ["Patient", "Encounter"]},
    "billing": {"port": 8007, "resources": ["Patient", "Claim"]},
}

def check_health(name, port):
    """Check if service is healthy"""
    try:
        r = requests.get(f"http://localhost:{port}/health", timeout=5)
        if r.status_code == 200:
            return True, "healthy"
        return False, f"status {r.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "connection refused"
    except Exception as e:
        return False, str(e)

def check_data(name, port, resources):
    """Check if service has data loaded"""
    counts = {}
    for resource in resources:
        try:
            r = requests.get(f"http://localhost:{port}/fhir/r4/{resource}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                counts[resource] = data.get("total", 0)
            else:
                counts[resource] = f"error:{r.status_code}"
        except Exception as e:
            counts[resource] = f"error:{e}"
    return counts

def validate_patient_fragmentation():
    """Verify same patient has different IDs across systems"""
    print("\n=== Patient ID Fragmentation Check ===")

    # Check patient 42 across systems
    patient_ids = {
        "ehr": "MRN-100042",
        "lis": "LAB-200042",
        "ris": "RAD-300042",
        "pharmacy": "RX-400042",
        "pas": "ADT-500042",
        "billing": "ACCT-600042",
    }

    found = 0
    for system, patient_id in patient_ids.items():
        port = SYSTEMS[system]["port"]
        try:
            r = requests.get(f"http://localhost:{port}/fhir/r4/Patient/{patient_id}", timeout=5)
            if r.status_code == 200:
                data = r.json()
                name = data.get("name", [{}])[0]
                family = name.get("family", "?")
                given = name.get("given", ["?"])[0]
                print(f"  {system:10} {patient_id:15} -> {given} {family}")
                found += 1
            else:
                print(f"  {system:10} {patient_id:15} -> NOT FOUND")
        except Exception as e:
            print(f"  {system:10} {patient_id:15} -> ERROR: {e}")

    return found == len(patient_ids)

def validate_benchmark_files():
    """Check benchmark files exist and are valid"""
    print("\n=== Benchmark Files Check ===")

    files = [
        "data/benchmark/api_catalog.json",
        "data/benchmark/benchmark_queries.json",
        "data/benchmark/ground_truth/master_patient_index.json",
    ]

    all_valid = True
    for filepath in files:
        try:
            with open(filepath) as f:
                data = json.load(f)

            if "api_catalog" in filepath:
                count = len(data.get("systems", {}))
                print(f"  {filepath}: {count} systems defined")
            elif "benchmark_queries" in filepath:
                count = len(data.get("queries", []))
                print(f"  {filepath}: {count} queries defined")
            elif "master_patient_index" in filepath:
                count = data.get("total_patients", 0)
                print(f"  {filepath}: {count} patients in ground truth")
        except FileNotFoundError:
            print(f"  {filepath}: NOT FOUND")
            all_valid = False
        except json.JSONDecodeError:
            print(f"  {filepath}: INVALID JSON")
            all_valid = False

    return all_valid

def main():
    print("=" * 60)
    print("HEALTHCARE DATA BENCHMARK - ENVIRONMENT VALIDATION")
    print("=" * 60)

    # Check all services
    print("\n=== Service Health Check ===")
    all_healthy = True
    for name, config in SYSTEMS.items():
        healthy, msg = check_health(name, config["port"])
        status = "OK" if healthy else "FAIL"
        print(f"  {name:10} (:{config['port']}): {status} - {msg}")
        if not healthy:
            all_healthy = False

    if not all_healthy:
        print("\nERROR: Some services are not healthy. Run: docker-compose up -d")
        sys.exit(1)

    # Check data loaded
    print("\n=== Data Load Check ===")
    for name, config in SYSTEMS.items():
        counts = check_data(name, config["port"], config["resources"])
        counts_str = ", ".join(f"{k}={v}" for k, v in counts.items())
        print(f"  {name:10}: {counts_str}")

    # Check patient fragmentation
    fragmentation_ok = validate_patient_fragmentation()

    # Check benchmark files
    files_ok = validate_benchmark_files()

    # Summary
    print("\n" + "=" * 60)
    if all_healthy and fragmentation_ok and files_ok:
        print("VALIDATION PASSED - Benchmark environment is ready")
        print("=" * 60)
        print("""
Next steps:
1. Give your agent the API catalog:
   cat data/benchmark/api_catalog.json

2. Run benchmark queries:
   cat data/benchmark/benchmark_queries.json

3. Score against ground truth:
   cat data/benchmark/master_patient_index.json
""")
        sys.exit(0)
    else:
        print("VALIDATION FAILED - See errors above")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
