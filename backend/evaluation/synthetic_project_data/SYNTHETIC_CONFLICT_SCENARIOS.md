# Controlled Synthetic Conflict and Scope Scenarios

All sources and resolutions below are project-authored fixtures, not PES University rules. The two old documents live only in `conflicts/`; the primary current-policy corpus and its Chroma collection exclude them. Current policy fixtures are version 1.0 effective 2026-09-01; old versions are 0.9 effective 2025-09-01.

## P9A-C01 — Attendance version change

- **Older source:** `SYNTH-P9A-ATTENDANCE-OLD-C01`, v0.9, effective 2025-09-01, synthetic 70% per subject.
- **Current source:** `SYNTH-P9A-ATTENDANCE-05`, v1.0, effective 2026-09-01, 75% per subject.
- **Applicability:** Project-model B.Tech students across the two model campuses.
- **Expected resolution:** Apply current v1.0's 75% threshold; do not combine it with the explicitly superseded 70% threshold.
- **Ground-truth evidence:** The exact historical threshold and supersession text plus the current attendance threshold are recorded under question `P9A-CONF-001` in `conflicts/synthetic_conflict_scenarios.json`.

## P9A-C02 — Assessment weight version change

- **Older source:** `SYNTH-P9A-ASSESSMENT-OLD-C02`, v0.9, effective 2025-09-01, 15/15/60/10.
- **Current source:** `SYNTH-P9A-ASSESSMENT-06`, v1.0, effective 2026-09-01, 20/20/50/10.
- **Applicability:** Project-model B.Tech assessment scheme.
- **Expected resolution:** Use current v1.0's 20/20/50/10 weights; the older weighting is explicitly superseded.
- **Ground-truth evidence:** Both versions' exact weight and supersession passages plus current component passages are recorded under `P9A-CONF-002`.

## P9A-C03 — Entry-category progression scope

- **Regular-entry source:** `SYNTH-P9A-PROGRESSION-REG-03`, v1.0, effective 2026-09-01, threshold 72 cumulative credits after Semester 4.
- **Lateral-entry source:** `SYNTH-P9A-PROGRESSION-LAT-04`, v1.0, effective 2026-09-01, threshold 24 credits from Semesters 3 and 4.
- **Applicability:** The 72-credit rule applies to regular entry; the 24-credit rule applies to diploma lateral entry.
- **Expected resolution:** This is a student-category scope distinction, not an unresolved temporal contradiction. Do not apply 72 credits to lateral-entry students.
- **Ground-truth evidence:** Both category-specific threshold passages and the explicit non-transfer statement are recorded under `P9A-CONF-003`.

The machine-readable scenarios include exact source IDs, versions, effective dates, ground-truth spans and expected resolution. No scenario fabricates unresolved current-policy contradictions.
