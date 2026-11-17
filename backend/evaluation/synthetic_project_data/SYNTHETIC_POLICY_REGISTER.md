# Synthetic Policy Register

Every listed item is **project-authored synthetic content, not an official PES University regulation**. Dataset classification: `SYNTHETIC_PROJECT_DATA`; `is_official_university_policy: false`; `source_type: PROJECT_AUTHORED`; dataset version `9A.1.0`. The primary manifest contains only the ten current-model policies. Superseded items are isolated in the conflict directory.

| Synthetic document ID | Document | Version / effective date | Coverage |
|---|---|---|---|
| `SYNTH-P9A-STRUCTURE-01` | Academic Structure and Programme Regulations | 1.0 / 2026-09-01 | 8 semesters; 24 credits per semester; regular-entry standard total 192; campuses share model rules |
| `SYNTH-P9A-LATERAL-02` | Lateral Entry and Mathematics Bridge Policy | 1.0 / 2026-09-01 | Semester 3 entry; no Semester 1–2 credit requirement; mandatory additional Math bridge classes |
| `SYNTH-P9A-PROGRESSION-REG-03` | Regular-Entry Progression and Year-Back | 1.0 / 2026-09-01 | At least 72 cumulative credits after Semester 4; below threshold restarts Semester 3 |
| `SYNTH-P9A-PROGRESSION-LAT-04` | Lateral-Entry Progression and Year-Back | 1.0 / 2026-09-01 | At least 24 credits from Semesters 3–4; separate lateral year-back rule |
| `SYNTH-P9A-ATTENDANCE-05` | Attendance and ESA Eligibility | 1.0 / 2026-09-01 | 75% per subject; medical exception conditions and Chairperson review; no automatic eligibility |
| `SYNTH-P9A-ASSESSMENT-06` | ISA, ESA and Laboratory Assessment | 1.0 / 2026-09-01 | 20/20/50/10 weighting, normalization, formula and worked example |
| `SYNTH-P9A-GRADING-07` | Grading and Grade Point | 1.0 / 2026-09-01 | S–F project-default grade boundaries, 35% pass, CGPA illustration |
| `SYNTH-P9A-SGPA-08` | SGPA and CGPA Calculation | 1.0 / 2026-09-01 | Credit-weighted formula and numerical examples |
| `SYNTH-P9A-BACKLOG-09` | Backlog and Supplementary Examination | 1.0 / 2026-09-01 | Supplementary cap A, replacement grade, record retention, no fixed backlog cap |
| `SYNTH-P9A-REVALUATION-10` | Revaluation, Answer-Script Inspection and Examination Procedures | 1.0 / 2026-09-01 | User-provided revaluation rules; deadline, INR fee and processing-time synthetic defaults; injection test fixtures |

## Separate historical conflict fixtures

These are not current policies and are excluded from `synthetic_dataset_manifest.json` and the primary current-policy collection:

| ID | Version / effective date | Scenario |
|---|---|---|
| `SYNTH-P9A-ATTENDANCE-OLD-C01` | 0.9 / 2025-09-01 | Historical 70% attendance, explicitly superseded by current v1.0 at 75% effective 2026-09-01. |
| `SYNTH-P9A-ASSESSMENT-OLD-C02` | 0.9 / 2025-09-01 | Historical 15/15/60/10 weighting, explicitly superseded by current v1.0 at 20/20/50/10 effective 2026-09-01. |

