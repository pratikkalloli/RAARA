from __future__ import annotations
import argparse
from pathlib import Path
from evaluation.prompt_experiments.runner import run_prompt_comparison

def main() -> int:
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description="Run simulated RAARA A/B/C prompt diagnostics without API calls.")
    parser.add_argument("--dataset",type=Path,default=root/"evaluation/datasets/development/raara_synthetic_starter_v0.1.0.jsonl")
    parser.add_argument("--manifest",type=Path,default=root/"evaluation/datasets/development/manifest.json")
    parser.add_argument("--output-json",type=Path,default=root/"evaluation/results/prompt_comparison.json")
    parser.add_argument("--output-markdown",type=Path,default=root/"evaluation/results/prompt_comparison.md")
    args=parser.parse_args()
    report=run_prompt_comparison(args.dataset,args.manifest,args.output_json,args.output_markdown)
    print(f"{report['simulation_label']}; {report['dataset_question_count']} questions; artifacts: {args.output_json}, {args.output_markdown}")
    return 0

if __name__=="__main__": raise SystemExit(main())
