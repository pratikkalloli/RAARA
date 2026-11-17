from __future__ import annotations
import re, unicodedata
from dataclasses import dataclass
from app.services.chunker import TextChunk
from evaluation.schemas.dataset import EvaluationQuestion

class GroundTruthMappingError(ValueError): pass

@dataclass(frozen=True)
class QuestionGroundTruth:
    question_id: str
    relevant_passage_ids: frozenset[str]
    relevant_document_ids: frozenset[str]
    relevant_pages: frozenset[tuple[str, int]]
    evidence_to_passage_ids: dict[str, tuple[str, ...]]
    answerable: bool

def normalize_evidence(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().casefold()

def evaluation_passage_id(document_id: str, chunk_index: int) -> str:
    return f"doc-{document_id}-chunk-{chunk_index}"

def build_ground_truth(questions: list[EvaluationQuestion], chunks_by_document: dict[str, list[TextChunk]]) -> dict[str, QuestionGroundTruth]:
    results = {}
    for question in questions:
        mapping, passages = {}, set()
        for evidence in question.relevant_evidence:
            target = normalize_evidence(evidence.text)
            matched = tuple(evaluation_passage_id(evidence.document_id, chunk.chunk_index)
                for chunk in chunks_by_document.get(evidence.document_id, [])
                if chunk.page_number == evidence.page_number and chunk.section == evidence.section
                and target in normalize_evidence(chunk.text))
            if not matched:
                raise GroundTruthMappingError(f"{question.question_id}/{evidence.evidence_id}: exact evidence span not found in matching document/page/section chunk")
            mapping[evidence.evidence_id] = matched
            passages.update(matched)
        if question.expected_status == "NOT_FOUND" and passages:
            raise GroundTruthMappingError(f"{question.question_id}: NOT_FOUND question maps to evidence")
        results[question.question_id] = QuestionGroundTruth(
            question.question_id, frozenset(passages), frozenset(question.relevant_document_ids),
            frozenset((p.document_id, p.page_number) for p in question.relevant_pages), mapping,
            question.expected_status != "NOT_FOUND")
    return results
