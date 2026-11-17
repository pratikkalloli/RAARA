from __future__ import annotations
import argparse, tempfile
from pathlib import Path
from app.config import settings
from evaluation.retrieval.runner import run_benchmark

def main() -> int:
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description="Run isolated offline RAARA retrieval benchmark.")
    parser.add_argument("--dataset",type=Path,default=root/"evaluation/datasets/development/raara_synthetic_starter_v0.1.0.jsonl")
    parser.add_argument("--manifest",type=Path,default=root/"evaluation/datasets/development/manifest.json")
    parser.add_argument("--output-json",type=Path,default=root/"evaluation/results/retrieval_benchmark.json")
    parser.add_argument("--output-markdown",type=Path,default=root/"evaluation/results/retrieval_benchmark.md")
    parser.add_argument("--repetitions",type=int,default=3)
    args=parser.parse_args()
    # Always use a unique temporary Chroma directory; never touch configured production Chroma.
    with tempfile.TemporaryDirectory(prefix="raara-phase7b-") as temp:
        original=settings.chroma_persist_dir
        settings.chroma_persist_dir=temp
        try: report=run_benchmark(args.dataset,args.manifest,args.output_json,args.output_markdown,repetitions=args.repetitions,collection_name="phase7b_retrieval")
        finally: settings.chroma_persist_dir=original
    print(f"Questions: {report['question_count']}; chunks: {report['index']['chunk_count']}; outputs: {args.output_json}, {args.output_markdown}")
    return 0
if __name__=="__main__": raise SystemExit(main())
