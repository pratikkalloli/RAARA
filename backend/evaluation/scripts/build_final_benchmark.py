from __future__ import annotations

import html
import json
from pathlib import Path

from evaluation.final_benchmark import build_final_benchmark


def _svg(title: str, caption: str, labels: list[str], series: list[tuple[str, list[float]]], out: Path) -> None:
    w, h, left, top, pw, ph = 920, 500, 90, 70, 770, 330
    colors = ["#3568a8", "#d18a32", "#49876e", "#9367a8"]
    gw = pw / len(labels)
    bw = min(48, gw / (len(series) + 1))
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t d" viewBox="0 0 {w} {h}">',
         f'<title id="t">{html.escape(title)}</title><desc id="d">{html.escape(caption)}</desc>',
         '<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{w/2}" y="34" text-anchor="middle" font-family="Arial" font-size="21" font-weight="bold">{html.escape(title)}</text>']
    for tick in range(0, 11, 2):
        y = top + ph * (1 - tick / 10)
        s += [f'<line x1="{left}" y1="{y}" x2="{left+pw}" y2="{y}" stroke="#dce2e8"/>',
              f'<text x="{left-10}" y="{y+4}" text-anchor="end" font-family="Arial" font-size="12">{tick/10:.1f}</text>']
    for i, label in enumerate(labels):
        center = left + gw * (i + .5)
        x0 = center - len(series) * bw / 2
        for j, (name, values) in enumerate(series):
            value = max(0, min(1, values[i]))
            bar_h = ph * value
            x, y = x0 + j*bw, top + ph - bar_h
            s += [f'<rect x="{x}" y="{y}" width="{bw-4}" height="{bar_h}" fill="{colors[j%len(colors)]}" rx="2"><title>{html.escape(name)} {html.escape(label)}: {value:.3f}</title></rect>',
                  f'<text x="{x+(bw-4)/2}" y="{max(top+12,y-4)}" text-anchor="middle" font-family="Arial" font-size="10">{value:.2f}</text>']
        s.append(f'<text x="{center}" y="{top+ph+24}" text-anchor="middle" font-family="Arial" font-size="12">{html.escape(label)}</text>')
    for i, (name, _) in enumerate(series):
        x = left + i * pw / max(len(series), 1)
        y = h - 30
        s += [f'<rect x="{x}" y="{y-10}" width="12" height="12" fill="{colors[i%len(colors)]}"/>',
              f'<text x="{x+18}" y="{y}" font-family="Arial" font-size="11">{html.escape(name)}</text>']
    s.append('</svg>')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(s), encoding="utf-8")


def _fmt(m: dict) -> str:
    return "N/A" if m.get("value") is None or not m.get("count") else f"{m['value']:.3f} (n={m['count']})"


def render_markdown(d: dict) -> str:
    r, q, p = d["phase_7b"], d["phase_7c"], d["phase_7d"]
    out = ["# RAARA Final Benchmark Consolidation — Phase 7E", "",
           f"**Classification: {d['classification']}**", "",
           "This consolidates measured Phase 6E–7D outputs. It does not claim a held-out benchmark, live OpenAI result, semantic faithfulness validation, or statistically significant prompt winner.", "",
           "## Dataset and environment", "",
           "- Dataset: 12 question, version 0.1.0 synthetic development set; synthetic PDFs are not official regulations.",
           f"- Dataset SHA-256 `{d['dataset']['sha256']}`; manifest SHA-256 `{d['dataset']['manifest_sha256']}`.",
           "- Held-out dataset: NOT AVAILABLE (0 questions); final held-out benchmark: BLOCKED pending independent permitted data.",
           f"- Python {d['runtime']['python']}; {d['runtime']['platform']}; {d['runtime']['machine_architecture']}; {d['runtime']['logical_cpu_count']} logical CPUs.",
           f"- Project chat model configured: `{d['model_and_run_status']['production_chat_model_configured']}`; API key configured: `{str(d['model_and_run_status']['openai_api_key_configured_at_finalization']).lower()}`.",
           "- Live OpenAI calls in Phase 7E: 0. Live integration: NOT TESTED. Semantic faithfulness: NOT TESTED.",
           "- No production database, ChromaDB collection or application behavior was modified.", "",
           "## Phase 7B retrieval benchmark", "",
           "Offline isolated ChromaDB; `deterministic-tfidf-hash-v1`; cosine distance; threshold 0.35. The production retrieval configuration was unchanged.", "",
           "| K | Precision@K | Recall@K | MRR | Hit rate | Mean retrieval latency |", "|---:|---:|---:|---:|---:|---:|"]
    for k in ("1", "3", "5"):
        m, lat = r["retrieval_metrics"][k], r["latency_ms_by_k"][k]
        out.append(f"| {k} | {m['precision_at_k']['value']:.3f} (n=10) | {m['recall_at_k']['value']:.3f} (n=10) | {m['reciprocal_rank']['value']:.3f} (n=10) | {m['hit_rate']['value']:.3f} (n=10) | {lat['mean']:.3f} ms (36 samples) |")
    out += ["", "15 gold evidence spans mapped exactly once by exact document/page/section matching. Only 1 of 10 answerable questions retrieved relevant evidence. Small synthetic corpus and offline embeddings limit these results; production embedding performance is unverified.", "",
            "## Phase 7C answer and citation benchmark", "",
            "Deterministic extractive mock; lexical metrics do not prove semantic correctness or faithfulness. Answerable questions:", "",
            "| Metric | CONTROLLED_EVIDENCE | END_TO_END_RAG |", "|---|---:|---:|"]
    keys = ["normalized_exact_match", "key_fact_coverage", "claim_support_rate", "claim_contradiction_rate", "answer_relevance", "citation_precision", "citation_recall", "document_accuracy", "page_accuracy"]
    for key in keys:
        out.append(f"| {key} | {_fmt(q['CONTROLLED_EVIDENCE']['answerable'][key])} | {_fmt(q['END_TO_END_RAG']['answerable'][key])} |")
    out.append("")
    out.append("Unanswerable question metrics:")
    for key in ["correct_abstention_rate", "false_answer_rate", "fabricated_citation_rate"]:
        out.append(f"- {key}: controlled {_fmt(q['CONTROLLED_EVIDENCE']['unanswerable'][key])}; end-to-end {_fmt(q['END_TO_END_RAG']['unanswerable'][key])}.")
    out += ["", "CONTROLLED_EVIDENCE bypassed retrieval using gold evidence. END_TO_END_RAG retrieved once per question. These results do not measure OpenAI generation.", "",
            "## Phase 7D prompt diagnostics", "",
            "A/B/C tied because `deterministic-extractive-mock-v1` ignores prompt text. This does not measure prompt effects or show Prompt C improves grounding.", "",
            "| Experiment | Prompt | Key-fact coverage | Citation precision | Citation recall | Correct abstention | Mean local mock ms | Tokens / cost |", "|---|---|---:|---:|---:|---:|---:|---|"]
    for exp in ["CONTROLLED_EVIDENCE", "END_TO_END_RAG"]:
        for prompt_id in "ABC":
            item = p["experiments"][exp][prompt_id]
            metrics, usage = item["metrics"], item["usage"]
            out.append(f"| {exp} | {prompt_id} | {_fmt(metrics['key_fact_coverage'])} | {_fmt(metrics['citation_precision'])} | {_fmt(metrics['citation_recall'])} | {_fmt(metrics['correct_abstention_rate'])} | {usage['generation_latency_ms']['mean']:.3f} | null / null |")
    out += ["", "Input/output/total token counts and estimated API cost are null, not zero. Local mock latency is not model latency. No significance claim is made.", "",
            "### Existing prompt definition hashes", "", "| Prompt | Name | System SHA-256 |", "|---|---|---|"]
    for prompt_id in "ABC":
        prompt = p["prompt_definitions"][prompt_id]
        out.append(f"| {prompt_id} | {prompt['name']} | `{prompt['system_prompt_sha256']}` |")
    out += ["", f"Shared user-template hash: `{p['prompt_definitions']['A']['user_template_sha256']}`. Shared schema hash: `{p['prompt_definitions']['A']['output_schema_sha256']}`.", "",
            "## Visual summaries", "",
            "Static figures below use only metrics measured in preserved phase artifacts.", "",
            "![Phase 7B retrieval metrics](evaluation/results/figures/retrieval_metrics.svg)", "",
            "![Phase 7C answer and citation metrics](evaluation/results/figures/answer_quality_metrics.svg)", "",
            "![Phase 7D prompt mock diagnostics](evaluation/results/figures/prompt_diagnostics.svg)", "",
            "## Live OpenAI gate", "",
            "The live evaluation gate is fail-closed. At finalization, no API key was configured and the explicit opt-in/model/call/budget variables were not all configured. No client was created and no network request was made. Set `RAARA_ENABLE_LIVE_EVAL=true`, `RAARA_EVAL_MODEL`, `RAARA_EVAL_MAX_CALLS`, `RAARA_EVAL_MAX_BUDGET_USD`, and `OPENAI_API_KEY` only after explicit approval. Run `python -m evaluation.scripts.check_live_eval_readiness` to check readiness; it never calls OpenAI.", "",
            "Future checklist: authorize model and maximum budget; independently review permitted held-out sources and annotations; pin dataset and prompt hashes; record generation parameters/repetitions; use dated pricing for cost; enforce per-request spend/call ceilings; preserve source metadata; and obtain human semantic-faithfulness review.", "",
            "## Historical test outcomes", "",
            "| Phase | Test outcome |", "|---|---|",
            "| 6E backend regression | 105 passed, 0 failed |", "| 6E frontend tests/build | 7 passed; production build passed |", "| 6E isolated API acceptance | 48 checks passed |",
            "| 7A full backend | 129 passed, 0 failed |", "| 7B full backend | 135 passed, 0 failed |", "| 7C full backend | 148 passed, 0 failed |", "| 7D full backend | 152 passed, 0 failed |",
            "", "Phase 7E dataset validation passed (12 questions); evaluation tests: 52 passed, 0 failed; full backend suite: 157 passed, 0 failed (Python 3.11.9, isolated temporary SQLite/Chroma/upload paths). Browser acceptance, live OpenAI and semantic faithfulness remain NOT TESTED.", "",
            "## Held-out annotation workflow", "",
            "`evaluation/datasets/held_out/README.md` and `annotation_template.json` describe source review, annotation and split separation. The template is not a held-out sample. Do not move development questions into the held-out split.", "",
            "## Preserved source artifact hashes", ""]
    out.extend(f"- `{a['path']}` — SHA-256 `{a['sha256']}`" for a in d["source_artifacts"])
    return "\n".join(out) + "\n"


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    data = build_final_benchmark(root)
    target = root / "evaluation/results"
    target.mkdir(parents=True, exist_ok=True)
    (target / "final_benchmark.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "final_benchmark.md").write_text(render_markdown(data), encoding="utf-8")
    figures = target / "figures"
    ret = data["phase_7b"]["retrieval_metrics"]
    _svg("Phase 7B retrieval metrics", "Precision, recall, MRR and hit rate at K 1, 3, 5; synthetic corpus, offline embedding substitute.", ["K=1", "K=3", "K=5"], [(label, [ret[k][field]["value"] for k in ("1", "3", "5")]) for label, field in [("Precision@K", "precision_at_k"), ("Recall@K", "recall_at_k"), ("MRR", "reciprocal_rank"), ("Hit rate", "hit_rate")]], figures / "retrieval_metrics.svg")
    controlled = data["phase_7c"]["CONTROLLED_EVIDENCE"]["answerable"]
    e2e = data["phase_7c"]["END_TO_END_RAG"]["answerable"]
    keys = ["key_fact_coverage", "claim_support_rate", "answer_relevance", "citation_precision", "citation_recall"]
    _svg("Phase 7C answer and citation metrics", "Deterministic mock output; separate controlled and end-to-end experiments, answerable questions.", ["Key facts", "Claim support", "Relevance", "Citation P", "Citation R"], [("Controlled", [controlled[k]["value"] for k in keys]), ("End-to-end", [e2e[k]["value"] for k in keys])], figures / "answer_quality_metrics.svg")
    experiments = data["phase_7d"]["experiments"]
    _svg("Phase 7D prompt mock diagnostics", "The deterministic mock does not interpret prompts; tied bars are simulated diagnostics, not prompt performance evidence.", ["Controlled", "End-to-end"], [(pid, [experiments[condition][pid]["metrics"]["key_fact_coverage"]["value"] for condition in ("CONTROLLED_EVIDENCE", "END_TO_END_RAG")]) for pid in "ABC"], figures / "prompt_diagnostics.svg")
    print(f"Wrote final benchmark JSON/Markdown and 3 SVG figures to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
