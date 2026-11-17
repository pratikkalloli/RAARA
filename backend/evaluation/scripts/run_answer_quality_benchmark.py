from __future__ import annotations
import argparse
from pathlib import Path
from evaluation.answer_quality.runner import run_answer_quality

def main() -> int:
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description="Run offline RAARA Phase 7C answer/citation evaluation.")
    parser.add_argument("--dataset",type=Path,default=root/"evaluation/datasets/development/raara_synthetic_starter_v0.1.0.jsonl")
    parser.add_argument("--manifest",type=Path,default=root/"evaluation/datasets/development/manifest.json")
    parser.add_argument("--output-json",type=Path,default=root/"evaluation/results/answer_quality_benchmark.json")
    parser.add_argument("--output-markdown",type=Path,default=root/"evaluation/results/answer_quality_benchmark.md")
    args=parser.parse_args()
    report=run_answer_quality(args.dataset,args.manifest,args.output_json,args.output_markdown)
    print(f"Dataset {report['dataset_version']}: {report['question_count']} questions; wrote {args.output_json} and {args.output_markdown}")
    return 0

if __name__=="__main__": raise SystemExit(main())
