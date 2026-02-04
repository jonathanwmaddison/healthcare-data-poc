# Oncology Biomarker Tasks

Tasks requiring understanding of oncology pathology, biomarker testing, and molecular diagnostics to identify treatment-eligible patients

---

## HDH-ONC-001: Find HER2-Positive Breast Cancer Patients

**Difficulty**: medium

**Systems Required**: ehr, lis

**Max Turns**: 20

### Description

Identify all patients with breast cancer (ICD-10 C50.x) who have HER2-positive biomarker results. HER2 status is determined by IHC (LOINC 18474-7) with result 3+ or FISH (LOINC 32996-3) with result 'positive'. These patients may be eligible for targeted therapy.

### Expected Response Format

```json
{
  "breast_cancer_patients": "integer",
  "patients_with_her2_testing": "integer",
  "her2_positive_patients": [
    {
      "ehr_id": "string",
      "lis_id": "string",
      "diagnosis_code": "string",
      "her2_result": "string (3+, positive, amplified)",
      "test_date": "string",
      "test_type": "IHC|FISH"
    }
  ],
  "her2_positive_count": "integer",
  "positivity_rate": "float"
}
```

---

## HDH-ONC-002: EGFR Mutation Lung Cancer Cohort

**Difficulty**: hard

**Systems Required**: ehr, lis

**Max Turns**: 25

### Description

Build a cohort of non-small cell lung cancer (NSCLC) patients with EGFR mutations. NSCLC is coded as ICD-10 C34.x. EGFR mutations are detected via molecular testing (LOINC 21659-7). Look for specific mutations like exon 19 deletion or L858R in the test comments/notes.

### Expected Response Format

```json
{
  "nsclc_patients": "integer",
  "patients_with_egfr_testing": "integer",
  "egfr_mutation_positive": [
    {
      "ehr_id": "string",
      "lis_id": "string",
      "mutation_type": "string (exon 19 del, L858R, T790M, etc.)",
      "test_date": "string",
      "report_text": "string (relevant excerpt)"
    }
  ],
  "mutation_distribution": {
    "exon_19_deletion": "integer",
    "L858R": "integer",
    "T790M": "integer",
    "other": "integer"
  }
}
```

---

## HDH-ONC-003: PD-L1 Expression for Immunotherapy

**Difficulty**: hard

**Systems Required**: ehr, lis

**Max Turns**: 25

### Description

Find cancer patients who may be eligible for immunotherapy based on PD-L1 expression. PD-L1 is tested via IHC (LOINC 85147-9). Eligibility varies by cancer type: >=50% TPS for first-line NSCLC, >=1% for second-line. Extract TPS percentage from test results.

### Expected Response Format

```json
{
  "cancer_patients_tested": "integer",
  "pdl1_results": [
    {
      "patient_ehr_id": "string",
      "cancer_type": "string",
      "tps_percentage": "integer",
      "first_line_eligible": "boolean",
      "second_line_eligible": "boolean"
    }
  ],
  "first_line_eligible_count": "integer",
  "second_line_only_eligible_count": "integer"
}
```

---

## HDH-ONC-004: Comprehensive Biomarker Panel Review

**Difficulty**: expert

**Systems Required**: ehr, lis

**Max Turns**: 35

### Description

For all lung cancer patients, compile a comprehensive biomarker summary including EGFR, ALK, ROS1, BRAF, PD-L1, and KRAS status. Data may be spread across multiple tests and time points. Create a unified view showing all tested biomarkers and their results.

### Expected Response Format

```json
{
  "lung_cancer_patients": "integer",
  "biomarker_summary": [
    {
      "patient_ehr_id": "string",
      "patient_lis_id": "string",
      "diagnosis": "string",
      "biomarkers": {
        "EGFR": {
          "status": "positive|negative|not_tested",
          "mutation": "string or null"
        },
        "ALK": {
          "status": "positive|negative|not_tested"
        },
        "ROS1": {
          "status": "positive|negative|not_tested"
        },
        "BRAF": {
          "status": "positive|negative|not_tested",
          "mutation": "string or null"
        },
        "PD_L1": {
          "status": "tested|not_tested",
          "tps": "integer or null"
        },
        "KRAS": {
          "status": "positive|negative|not_tested",
          "mutation": "string or null"
        }
      },
      "recommended_therapy": "string based on biomarkers"
    }
  ],
  "testing_gaps": {
    "no_biomarker_testing": "integer",
    "incomplete_panel": "integer"
  }
}
```

---

## HDH-ONC-005: Pathology Report Data Extraction

**Difficulty**: expert

**Systems Required**: ehr, lis

**Max Turns**: 30

### Description

Pathology reports contain critical structured and unstructured data. Extract tumor characteristics from pathology DocumentReferences: tumor grade (well/moderate/poorly differentiated), tumor size, lymph node involvement, margin status, and any molecular findings mentioned in the narrative.

### Expected Response Format

```json
{
  "pathology_reports_analyzed": "integer",
  "extracted_data": [
    {
      "report_id": "string",
      "patient_id": "string",
      "cancer_type": "string",
      "tumor_grade": "well|moderate|poorly differentiated",
      "tumor_size_cm": "number or null",
      "lymph_nodes_positive": "integer or null",
      "lymph_nodes_examined": "integer or null",
      "margin_status": "positive|negative|close",
      "molecular_findings": [
        "list of biomarkers/mutations mentioned"
      ],
      "stage": "string or null"
    }
  ]
}
```

---

