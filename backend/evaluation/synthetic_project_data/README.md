# SYNTHETIC_PROJECT_DATA

Everything in this directory is project-authored synthetic material for a college RAG demonstration. It is **not official PES University policy** and must not be applied as real advice. Every document and question is explicitly marked `dataset_type: SYNTHETIC_PROJECT_DATA`, `is_official_university_policy: false`, and `source_type: PROJECT_AUTHORED`.

- `corpus/` contains ten coherent current-model policies, their source Markdown and generated PDFs.
- `conflicts/` contains isolated, superseded project-model documents and controlled conflict ground truth. It is never mixed into the primary current-policy corpus.
- `datasets/` contains a 50-question master set and distinct development/held-out split files. Held-out items are not used for retrieval or prompt tuning.
- `results/` contains a reproducible, deterministic, offline validation report. No live OpenAI call is made.

The supplied user values are implemented only as the synthetic project model. Defaults for missing details are labeled synthetic. This model is not a representation of a verified university regulation.
