#!/usr/bin/env python3
"""
Generate All Agent Documentation for HDH-Bench

This script generates all documentation files that agents need to run the benchmark:
1. api_catalog.json - Full API documentation (full_catalog mode)
2. base_urls.json - Minimal URLs only (minimal mode)
3. fhir_cheatsheet.md - FHIR quick reference
4. agent_prompt.md - Main agent instructions
5. task_prompts/ - Individual task prompts for each category

Usage:
    python scripts/generate_agent_docs.py
    python scripts/generate_agent_docs.py --output data/benchmark
    python scripts/generate_agent_docs.py --mode full_catalog
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


# System configuration - single source of truth
SYSTEMS = {
    "ehr": {
        "name": "Electronic Health Record",
        "description": "Core clinical records including patient demographics, diagnoses, and problem lists",
        "base_url": "http://localhost:8001",
        "fhir_path": "/fhir/r4",
        "port": 8001,
        "patient_id_prefix": "MRN-",
        "patient_id_offset": 100000,
        "resources": {
            "Patient": {
                "description": "Patient demographics and identifiers",
                "search_params": ["_id", "name", "birthdate", "gender", "identifier"],
                "example_query": "GET /fhir/r4/Patient?name=Smith"
            },
            "Condition": {
                "description": "Diagnoses and problem list (ICD-10-CM coded)",
                "search_params": ["subject", "code", "clinical-status", "onset-date"],
                "example_query": "GET /fhir/r4/Condition?code=E11"
            }
        }
    },
    "lis": {
        "name": "Laboratory Information System",
        "description": "Laboratory orders and results including panels, individual tests, and biomarkers",
        "base_url": "http://localhost:8002",
        "fhir_path": "/fhir/r4",
        "port": 8002,
        "patient_id_prefix": "LAB-",
        "patient_id_offset": 200000,
        "resources": {
            "Patient": {
                "description": "Lab system patient registry",
                "search_params": ["_id", "name", "birthdate", "identifier"],
                "example_query": "GET /fhir/r4/Patient/LAB-200001"
            },
            "ServiceRequest": {
                "description": "Lab orders (LOINC coded)",
                "search_params": ["subject", "code", "status", "authored"],
                "example_query": "GET /fhir/r4/ServiceRequest?subject=Patient/LAB-200001"
            },
            "Observation": {
                "description": "Lab results with values and interpretations (LOINC coded)",
                "search_params": ["subject", "code", "status", "date", "based-on"],
                "example_query": "GET /fhir/r4/Observation?code=2345-7"
            }
        }
    },
    "ris": {
        "name": "Radiology Information System",
        "description": "Imaging orders and study metadata",
        "base_url": "http://localhost:8003",
        "fhir_path": "/fhir/r4",
        "port": 8003,
        "patient_id_prefix": "RAD-",
        "patient_id_offset": 300000,
        "resources": {
            "Patient": {
                "description": "Radiology patient registry",
                "search_params": ["_id", "name", "birthdate"],
                "example_query": "GET /fhir/r4/Patient/RAD-300001"
            },
            "ServiceRequest": {
                "description": "Imaging orders",
                "search_params": ["subject", "code", "status"],
                "example_query": "GET /fhir/r4/ServiceRequest?subject=Patient/RAD-300001"
            },
            "ImagingStudy": {
                "description": "Imaging study metadata",
                "search_params": ["subject", "status", "started"],
                "example_query": "GET /fhir/r4/ImagingStudy?subject=Patient/RAD-300001"
            }
        }
    },
    "pharmacy": {
        "name": "Pharmacy System",
        "description": "Medication orders and prescriptions",
        "base_url": "http://localhost:8005",
        "fhir_path": "/fhir/r4",
        "port": 8005,
        "patient_id_prefix": "RX-",
        "patient_id_offset": 400000,
        "resources": {
            "Patient": {
                "description": "Pharmacy patient registry",
                "search_params": ["_id", "name", "birthdate"],
                "example_query": "GET /fhir/r4/Patient/RX-400001"
            },
            "MedicationRequest": {
                "description": "Prescriptions and medication orders (RxNorm coded)",
                "search_params": ["subject", "code", "status", "authoredon"],
                "example_query": "GET /fhir/r4/MedicationRequest?subject=Patient/RX-400001"
            }
        }
    },
    "pas": {
        "name": "Patient Administration System",
        "description": "Patient visits, admissions, and encounters",
        "base_url": "http://localhost:8006",
        "fhir_path": "/fhir/r4",
        "port": 8006,
        "patient_id_prefix": "ADT-",
        "patient_id_offset": 500000,
        "resources": {
            "Patient": {
                "description": "ADT patient registry",
                "search_params": ["_id", "name", "birthdate"],
                "example_query": "GET /fhir/r4/Patient/ADT-500001"
            },
            "Encounter": {
                "description": "Patient visits and admissions",
                "search_params": ["subject", "class", "status", "date"],
                "example_query": "GET /fhir/r4/Encounter?subject=Patient/ADT-500001"
            }
        }
    },
    "billing": {
        "name": "Billing System",
        "description": "Insurance claims and coverage information",
        "base_url": "http://localhost:8007",
        "fhir_path": "/fhir/r4",
        "port": 8007,
        "patient_id_prefix": "ACCT-",
        "patient_id_offset": 600000,
        "resources": {
            "Patient": {
                "description": "Billing patient registry",
                "search_params": ["_id", "name", "birthdate"],
                "example_query": "GET /fhir/r4/Patient/ACCT-600001"
            },
            "Claim": {
                "description": "Insurance claims",
                "search_params": ["patient", "status", "created"],
                "example_query": "GET /fhir/r4/Claim?patient=Patient/ACCT-600001"
            },
            "Coverage": {
                "description": "Insurance coverage",
                "search_params": ["beneficiary", "status"],
                "example_query": "GET /fhir/r4/Coverage?beneficiary=Patient/ACCT-600001"
            }
        }
    }
}

# Common clinical codes for reference
CLINICAL_CODES = {
    "conditions": {
        "system": "http://hl7.org/fhir/sid/icd-10-cm",
        "examples": [
            {"code": "E11.9", "display": "Type 2 diabetes mellitus without complications"},
            {"code": "I10", "display": "Essential (primary) hypertension"},
            {"code": "E78.5", "display": "Hyperlipidemia, unspecified"},
            {"code": "J44.9", "display": "COPD, unspecified"},
            {"code": "F32.9", "display": "Major depressive disorder"},
        ]
    },
    "labs": {
        "system": "http://loinc.org",
        "examples": [
            {"code": "2345-7", "display": "Glucose [Mass/volume] in Serum or Plasma"},
            {"code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"},
            {"code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma"},
            {"code": "718-7", "display": "Hemoglobin [Mass/volume] in Blood"},
            {"code": "2093-3", "display": "Cholesterol [Mass/volume] in Serum or Plasma"},
        ]
    },
    "medications": {
        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
        "examples": [
            {"code": "860975", "display": "Metformin 500 MG Oral Tablet"},
            {"code": "314076", "display": "Lisinopril 10 MG Oral Tablet"},
            {"code": "617311", "display": "Atorvastatin 20 MG Oral Tablet"},
            {"code": "197361", "display": "Amlodipine 5 MG Oral Tablet"},
            {"code": "198048", "display": "Omeprazole 20 MG Capsule"},
        ]
    }
}


def generate_api_catalog() -> Dict:
    """Generate full API catalog (full_catalog mode)"""
    catalog = {
        "benchmark": "HDH-Bench",
        "version": "1.0.0",
        "description": "Healthcare Data Harmonization Benchmark - API Catalog",
        "generated_at": datetime.now().isoformat(),
        "note": "Each system has its own patient ID scheme. The same physical patient will have different IDs in each system. There is NO shared patient identifier.",
        "systems": {},
        "clinical_codes": CLINICAL_CODES,
        "common_search_patterns": {
            "by_patient": "GET /fhir/r4/{Resource}?subject=Patient/{id}",
            "by_code": "GET /fhir/r4/{Resource}?code={code}",
            "by_status": "GET /fhir/r4/{Resource}?status={status}",
            "pagination": "GET /fhir/r4/{Resource}?_count={n}&_offset={m}",
            "capability_statement": "GET /fhir/r4/metadata"
        }
    }

    for system_id, system in SYSTEMS.items():
        catalog["systems"][system_id] = {
            "name": system["name"],
            "description": system["description"],
            "base_url": system["base_url"],
            "fhir_base": f"{system['base_url']}{system['fhir_path']}",
            "patient_id_prefix": system["patient_id_prefix"],
            "patient_id_example": f"{system['patient_id_prefix']}{system['patient_id_offset'] + 1}",
            "resources": system["resources"]
        }

    return catalog


def generate_base_urls() -> Dict:
    """Generate minimal base URLs only (minimal mode)"""
    return {
        "benchmark": "HDH-Bench",
        "version": "1.0.0",
        "description": "Base URLs for healthcare systems - agent must discover capabilities",
        "generated_at": datetime.now().isoformat(),
        "note": "Use /fhir/r4/metadata endpoint to discover supported resources",
        "systems": {
            system_id: {
                "base_url": f"{system['base_url']}{system['fhir_path']}"
            }
            for system_id, system in SYSTEMS.items()
        }
    }


def generate_fhir_cheatsheet() -> str:
    """Generate FHIR quick reference markdown"""
    cheatsheet = """# FHIR R4 Quick Reference for HDH-Bench

## Base Pattern

All systems expose standard FHIR R4 REST APIs:

```
GET /fhir/r4/{ResourceType}              # List/search resources
GET /fhir/r4/{ResourceType}/{id}         # Get by ID
GET /fhir/r4/{ResourceType}?param=value  # Search with parameters
GET /fhir/r4/metadata                    # Capability statement
```

## Systems Overview

| System | Port | Patient ID Format | Key Resources |
|--------|------|-------------------|---------------|
| EHR | 8001 | MRN-XXXXXX | Patient, Condition |
| LIS | 8002 | LAB-XXXXXX | Patient, ServiceRequest, Observation |
| RIS | 8003 | RAD-XXXXXX | Patient, ServiceRequest, ImagingStudy |
| Pharmacy | 8005 | RX-XXXXXX | Patient, MedicationRequest |
| PAS | 8006 | ADT-XXXXXX | Patient, Encounter |
| Billing | 8007 | ACCT-XXXXXX | Patient, Claim, Coverage |

## Common Search Parameters

### Patient Searches
```bash
# Search by name
curl "http://localhost:8001/fhir/r4/Patient?name=Smith"

# Search by birth date
curl "http://localhost:8001/fhir/r4/Patient?birthdate=1980-03-15"

# Get specific patient
curl "http://localhost:8001/fhir/r4/Patient/MRN-100001"
```

### Clinical Data Searches
```bash
# Get conditions for a patient
curl "http://localhost:8001/fhir/r4/Condition?subject=Patient/MRN-100001"

# Search conditions by ICD-10 code
curl "http://localhost:8001/fhir/r4/Condition?code=E11"

# Get lab results for a patient
curl "http://localhost:8002/fhir/r4/Observation?subject=Patient/LAB-200001"

# Search labs by LOINC code
curl "http://localhost:8002/fhir/r4/Observation?code=2345-7"

# Get medications for a patient
curl "http://localhost:8005/fhir/r4/MedicationRequest?subject=Patient/RX-400001"
```

### Pagination
```bash
# Get first 50 records
curl "http://localhost:8001/fhir/r4/Patient?_count=50"

# Get next page
curl "http://localhost:8001/fhir/r4/Patient?_count=50&_offset=50"
```

## Code Systems

### Diagnoses (ICD-10-CM)
System URI: `http://hl7.org/fhir/sid/icd-10-cm`

| Code | Description |
|------|-------------|
| E11.9 | Type 2 diabetes mellitus |
| I10 | Essential hypertension |
| E78.5 | Hyperlipidemia |
| J44.9 | COPD |
| F32.9 | Major depressive disorder |

### Lab Tests (LOINC)
System URI: `http://loinc.org`

| Code | Description |
|------|-------------|
| 2345-7 | Glucose |
| 4548-4 | Hemoglobin A1c (HbA1c) |
| 2160-0 | Creatinine |
| 718-7 | Hemoglobin |
| 2093-3 | Cholesterol |

### Medications (RxNorm)
System URI: `http://www.nlm.nih.gov/research/umls/rxnorm`

| Code | Description |
|------|-------------|
| 860975 | Metformin 500 MG |
| 314076 | Lisinopril 10 MG |
| 617311 | Atorvastatin 20 MG |
| 197361 | Amlodipine 5 MG |

## Response Format

FHIR Bundle response structure:

```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 100,
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "MRN-100001",
        "name": [{"family": "Smith", "given": ["John"]}],
        "birthDate": "1980-03-15",
        "gender": "male"
      }
    }
  ]
}
```

## Key FHIR Concepts

### Patient References
Clinical resources reference patients like this:
```json
"subject": {"reference": "Patient/MRN-100001"}
```

### Code/Coding Structure
```json
"code": {
  "coding": [
    {
      "system": "http://loinc.org",
      "code": "2345-7",
      "display": "Glucose"
    }
  ]
}
```

### Interpretation (Lab Results)
```json
"interpretation": [
  {"coding": [{"code": "H"}]}  // H=High, L=Low, N=Normal
]
```

## Critical: Patient ID Fragmentation

**The same patient has DIFFERENT IDs in each system!**

Example mapping (hidden from agents):
- EHR: MRN-100042
- LIS: LAB-200042
- RIS: RAD-300042
- Pharmacy: RX-400042
- PAS: ADT-500042
- Billing: ACCT-600042

To find the same patient across systems, you must **match on demographics** (name, DOB, etc.).
"""
    return cheatsheet


def generate_agent_prompt(tasks_dir: Path) -> str:
    """Generate main agent prompt markdown"""

    # Load task summaries
    task_categories = []
    total_tasks = 0

    if tasks_dir.exists():
        for task_file in sorted(tasks_dir.glob("*.json")):
            try:
                with open(task_file) as f:
                    data = json.load(f)
                    category = data.get("category", task_file.stem)
                    tasks = data.get("tasks", [])
                    total_tasks += len(tasks)

                    difficulties = {}
                    for task in tasks:
                        d = task.get("difficulty", "unknown")
                        difficulties[d] = difficulties.get(d, 0) + 1

                    task_categories.append({
                        "category": category,
                        "count": len(tasks),
                        "difficulties": difficulties,
                        "description": data.get("description", "")
                    })
            except Exception as e:
                print(f"Warning: Could not load {task_file}: {e}")

    # Build task summary table
    task_table = "| Category | Tasks | Easy | Medium | Hard | Expert |\n"
    task_table += "|----------|-------|------|--------|------|--------|\n"
    for cat in task_categories:
        d = cat["difficulties"]
        task_table += f"| {cat['category']} | {cat['count']} | {d.get('easy', 0)} | {d.get('medium', 0)} | {d.get('hard', 0)} | {d.get('expert', 0)} |\n"

    prompt = f"""# Healthcare Data Integration Agent Instructions

You are an AI agent tasked with querying and integrating data from a hospital's healthcare information systems.

## Environment Overview

You have access to **6 independent healthcare systems**, each exposing FHIR R4 REST APIs. Each system maintains its own patient registry with its own ID scheme.

**CRITICAL: There is NO shared patient identifier across systems.** The same physical patient has different IDs in each system. To find a patient across systems, you must match on demographics (name, date of birth, etc.).

## Available Systems

| System | Base URL | Patient ID | Description |
|--------|----------|------------|-------------|
| EHR | http://localhost:8001/fhir/r4 | MRN-XXXXXX | Demographics, diagnoses |
| LIS | http://localhost:8002/fhir/r4 | LAB-XXXXXX | Lab orders and results |
| RIS | http://localhost:8003/fhir/r4 | RAD-XXXXXX | Imaging orders |
| Pharmacy | http://localhost:8005/fhir/r4 | RX-XXXXXX | Prescriptions |
| PAS | http://localhost:8006/fhir/r4 | ADT-XXXXXX | Encounters |
| Billing | http://localhost:8007/fhir/r4 | ACCT-XXXXXX | Claims, coverage |

## API Reference

### Standard FHIR Endpoints
```
GET /fhir/r4/{{ResourceType}}              # List/search resources
GET /fhir/r4/{{ResourceType}}/{{id}}       # Get by ID
GET /fhir/r4/{{ResourceType}}?param=value  # Search
GET /fhir/r4/metadata                      # Capability statement
```

### Common Search Parameters
- `subject=Patient/{{id}}` - Filter by patient
- `code={{code}}` - Filter by clinical code
- `status={{status}}` - Filter by status
- `_count={{n}}` - Limit results
- `_offset={{n}}` - Pagination

### Resources by System

**EHR (localhost:8001)**: Patient, Condition

**LIS (localhost:8002)**: Patient, ServiceRequest, Observation

**RIS (localhost:8003)**: Patient, ServiceRequest, ImagingStudy

**Pharmacy (localhost:8005)**: Patient, MedicationRequest

**PAS (localhost:8006)**: Patient, Encounter

**Billing (localhost:8007)**: Patient, Claim, Coverage

## Clinical Code Systems

| Type | System URI | Example |
|------|------------|---------|
| Diagnoses | http://hl7.org/fhir/sid/icd-10-cm | E11.9 (Diabetes) |
| Lab Tests | http://loinc.org | 2345-7 (Glucose) |
| Medications | http://www.nlm.nih.gov/research/umls/rxnorm | 860975 (Metformin) |

## Example Queries

```bash
# List patients in EHR
curl http://localhost:8001/fhir/r4/Patient

# Get specific patient
curl http://localhost:8001/fhir/r4/Patient/MRN-100001

# Find diabetic patients (ICD-10 E11.x)
curl "http://localhost:8001/fhir/r4/Condition?code=E11"

# Get conditions for a patient
curl "http://localhost:8001/fhir/r4/Condition?subject=Patient/MRN-100001"

# Search lab results by LOINC code
curl "http://localhost:8002/fhir/r4/Observation?code=2345-7"

# Get medications for a patient
curl "http://localhost:8005/fhir/r4/MedicationRequest?subject=Patient/RX-400001"
```

## Benchmark Task Categories

{task_table}

**Total: {total_tasks} tasks**

## Response Format

For each task, return your results as JSON with the structure specified in the task definition.

## Important Notes

1. **Patient Matching is Hard**: Names may have variations (Mike vs Michael), dates may be formatted differently, some fields may be missing.

2. **Data Quality Issues Exist**: You may encounter orphaned records, abandoned orders, legacy codes, and inconsistencies.

3. **Code Systems Vary**: Some legacy records use ICD-9 instead of ICD-10. Be prepared to handle both.

4. **No Ground Truth Access**: You do not have access to the master patient index. You must discover relationships through data exploration.

---

*This prompt is provided by HDH-Bench. Do not request additional hints or ground truth data.*
"""
    return prompt


def generate_task_prompts(tasks_dir: Path, output_dir: Path):
    """Generate individual task prompt files"""
    task_prompts_dir = output_dir / "task_prompts"
    task_prompts_dir.mkdir(parents=True, exist_ok=True)

    if not tasks_dir.exists():
        print(f"Warning: Tasks directory {tasks_dir} does not exist")
        return

    for task_file in tasks_dir.glob("*.json"):
        try:
            with open(task_file) as f:
                data = json.load(f)

            category = data.get("category", task_file.stem)
            tasks = data.get("tasks", [])

            # Generate markdown for each category
            md_content = f"# {category.replace('_', ' ').title()} Tasks\n\n"
            md_content += f"{data.get('description', '')}\n\n"
            md_content += "---\n\n"

            for task in tasks:
                md_content += f"## {task['task_id']}: {task['title']}\n\n"
                md_content += f"**Difficulty**: {task.get('difficulty', 'unknown')}\n\n"
                md_content += f"**Systems Required**: {', '.join(task.get('systems_required', []))}\n\n"
                md_content += f"**Max Turns**: {task.get('max_turns', 'unlimited')}\n\n"
                md_content += f"### Description\n\n{task['description']}\n\n"

                if "expected_response" in task:
                    md_content += "### Expected Response Format\n\n```json\n"
                    md_content += json.dumps(task["expected_response"], indent=2)
                    md_content += "\n```\n\n"

                if "hints" in task:
                    md_content += "### Hints (if enabled)\n\n"
                    for level, hint in task["hints"].items():
                        md_content += f"- **{level}**: {hint}\n"
                    md_content += "\n"

                md_content += "---\n\n"

            # Write category task file
            output_file = task_prompts_dir / f"{category}_tasks.md"
            with open(output_file, "w") as f:
                f.write(md_content)
            print(f"  Generated {output_file}")

            # Also write JSON version for programmatic access
            json_output = task_prompts_dir / f"{category}_tasks.json"
            with open(json_output, "w") as f:
                # Strip ground truth from tasks before writing
                clean_tasks = []
                for task in tasks:
                    clean_task = {k: v for k, v in task.items() if k != "ground_truth"}
                    clean_tasks.append(clean_task)

                json.dump({
                    "category": category,
                    "description": data.get("description", ""),
                    "tasks": clean_tasks
                }, f, indent=2)
            print(f"  Generated {json_output}")

        except Exception as e:
            print(f"Warning: Could not process {task_file}: {e}")


def generate_combined_task_list(tasks_dir: Path) -> Dict:
    """Generate a combined list of all tasks for the benchmark runner"""
    all_tasks = {
        "benchmark": "HDH-Bench",
        "version": "1.0.0",
        "generated_at": datetime.now().isoformat(),
        "categories": {},
        "task_index": {}
    }

    if not tasks_dir.exists():
        return all_tasks

    for task_file in sorted(tasks_dir.glob("*.json")):
        try:
            with open(task_file) as f:
                data = json.load(f)

            category = data.get("category", task_file.stem)
            tasks = data.get("tasks", [])

            # Add to categories
            all_tasks["categories"][category] = {
                "description": data.get("description", ""),
                "task_count": len(tasks),
                "task_ids": [t["task_id"] for t in tasks]
            }

            # Add to task index (without ground truth)
            for task in tasks:
                task_id = task["task_id"]
                all_tasks["task_index"][task_id] = {
                    "category": category,
                    "title": task.get("title", ""),
                    "difficulty": task.get("difficulty", "unknown"),
                    "systems_required": task.get("systems_required", []),
                    "max_turns": task.get("max_turns", 20)
                }

        except Exception as e:
            print(f"Warning: Could not process {task_file}: {e}")

    return all_tasks


def main():
    parser = argparse.ArgumentParser(description="Generate agent documentation for HDH-Bench")
    parser.add_argument("--output", "-o", default="data/benchmark",
                        help="Output directory for generated docs")
    parser.add_argument("--tasks-dir", "-t", default="benchmark/tasks",
                        help="Directory containing task definition JSON files")
    parser.add_argument("--mode", choices=["all", "full_catalog", "minimal", "prompts"],
                        default="all", help="Which docs to generate")
    args = parser.parse_args()

    # Resolve paths relative to script location
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / args.output
    tasks_dir = script_dir / args.tasks_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating agent documentation...")
    print(f"  Output directory: {output_dir}")
    print(f"  Tasks directory: {tasks_dir}")
    print()

    if args.mode in ["all", "full_catalog"]:
        # Generate full API catalog
        api_catalog = generate_api_catalog()
        catalog_path = output_dir / "api_catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(api_catalog, f, indent=2)
        print(f"Generated: {catalog_path}")

        # Generate FHIR cheatsheet
        cheatsheet = generate_fhir_cheatsheet()
        cheatsheet_path = output_dir / "fhir_cheatsheet.md"
        with open(cheatsheet_path, "w") as f:
            f.write(cheatsheet)
        print(f"Generated: {cheatsheet_path}")

    if args.mode in ["all", "minimal"]:
        # Generate minimal base URLs
        base_urls = generate_base_urls()
        urls_path = output_dir / "base_urls.json"
        with open(urls_path, "w") as f:
            json.dump(base_urls, f, indent=2)
        print(f"Generated: {urls_path}")

    if args.mode in ["all", "prompts"]:
        # Generate main agent prompt
        agent_prompt = generate_agent_prompt(tasks_dir)
        prompt_path = output_dir / "agent_prompt.md"
        with open(prompt_path, "w") as f:
            f.write(agent_prompt)
        print(f"Generated: {prompt_path}")

        # Generate task-specific prompts
        print("\nGenerating task prompts:")
        generate_task_prompts(tasks_dir, output_dir)

        # Generate combined task list
        task_list = generate_combined_task_list(tasks_dir)
        task_list_path = output_dir / "task_list.json"
        with open(task_list_path, "w") as f:
            json.dump(task_list, f, indent=2)
        print(f"\nGenerated: {task_list_path}")

    print("\n" + "=" * 60)
    print("AGENT DOCUMENTATION GENERATED")
    print("=" * 60)
    print(f"""
Files generated in {output_dir}:

FOR AGENTS (provide these):
  - api_catalog.json     Full API documentation (full_catalog mode)
  - base_urls.json       Minimal URLs only (minimal mode)
  - fhir_cheatsheet.md   FHIR quick reference
  - agent_prompt.md      Main agent instructions
  - task_prompts/        Individual task prompts by category
  - task_list.json       Combined task index

DO NOT PROVIDE TO AGENTS:
  - ground_truth/        Contains answer keys for scoring

Usage modes (per evaluation_config.json):
  - full_catalog: Give agents api_catalog.json + fhir_cheatsheet.md
  - minimal: Give agents base_urls.json only
  - discovery: Give agents nothing (they must discover APIs)
""")


if __name__ == "__main__":
    main()
