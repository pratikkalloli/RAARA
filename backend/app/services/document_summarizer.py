"""Full-document hierarchical summaries backed by the existing Chroma index."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
import logging
from typing import Any, Callable

from app.prompting.system_prompt import PromptType
from app.services.citation_verifier import CitationVerifier
from app.services.factual_verifier import FactualConsistencyVerifier
from app.services.generator import AnswerStatus, CitationValidationSummary, EvidenceItem, SourceItem, StructuredAnswer
from app.services.retriever import RetrievalResult, RetrievedPassage
from app.services.vector_store import ChromaVectorStore, VectorStoreError

DocumentStateLookup = Callable[[list[str]], dict[str, tuple[str, str]]]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Node:
    passage: RetrievedPassage
    originals: tuple[str, ...]


@dataclass(frozen=True)
class _ReductionResult:
    nodes: tuple[_Node, ...]
    unrepresented_original_ids: tuple[str, ...]
    failed_batches: tuple[int, ...]


class DocumentSummarizer:
    """Summarize all indexed chunks, reducing large documents hierarchically."""

    def __init__(
        self,
        vector_store: Any | None,
        generator: Any,
        *,
        verifier: CitationVerifier | None = None,
        factual_verifier: FactualConsistencyVerifier | None = None,
        document_state_lookup: DocumentStateLookup | None = None,
        batch_size: int = 6,
        direct_chunk_limit: int = 12,
        max_chunks: int = 120,
    ) -> None:
        if batch_size < 2 or direct_chunk_limit < 1 or max_chunks < max(2, direct_chunk_limit):
            raise ValueError("Invalid document summary size limits.")
        self.vector_store = vector_store or ChromaVectorStore()
        self.generator = generator
        self.verifier = verifier or CitationVerifier()
        self.factual_verifier = factual_verifier
        self.document_state_lookup = document_state_lookup
        self.batch_size = batch_size
        self.direct_chunk_limit = direct_chunk_limit
        self.max_chunks = max_chunks

    def summarize(
        self,
        document_id: int | str,
        question: str,
        *,
        requested_points: int | None = None,
        prompt_type: PromptType | str = PromptType.C,
    ) -> StructuredAnswer:
        requested = max(1, min(int(requested_points or 8), 20))
        try:
            records = self.vector_store.get_document_chunks(document_id)
        except VectorStoreError:
            raise
        if not records:
            return _not_found("No chunks are available in this document's vector index.",
                              "This is an indexing or retrieval gap, not confirmation that content is absent from the PDF.")

        state = None
        if self.document_state_lookup:
            state = self.document_state_lookup([str(document_id)]).get(str(document_id))
            if state is None or state[1] != "synced" or state[0] == "rejected":
                return _not_found("The database and vector index do not confirm this document as available for analysis.",
                                  "Document synchronization or review state prevented reliable analysis.")
        passages = _dedupe(_passages(records, str(document_id), state))
        if not passages:
            return _not_found("No readable page-addressable text was available in the index.",
                              "This indicates an extraction or indexing limitation, not that requested information is absent from the PDF.")

        total = len(passages)
        hierarchical_reduction = len(passages) > self.direct_chunk_limit
        all_passage_ids = {passage.id for passage in passages}
        limited = total > self.max_chunks
        if limited:
            passages = _spread_sample(passages, self.max_chunks)
        selected_passage_ids = {passage.id for passage in passages}
        sampling_omitted_ids = all_passage_ids - selected_passage_ids
        unrepresented_original_ids: set[str] = set()
        document_name = str(passages[0].metadata["document_name"])

        if len(passages) <= self.direct_chunk_limit:
            final_question = _summary_question(question, requested, document_name, total, len(passages), limited)
            retrieval = _retrieval(final_question, passages)
            generated = self._generate_final(retrieval, requested, len(passages), prompt_type)
            answer = self.verifier.verify(generated, retrieval).answer
        else:
            original_by_id = {passage.id: passage for passage in passages}
            nodes = [_Node(passage, (passage.id,)) for passage in passages]
            level = 1
            failed_batch_count = 0
            while len(nodes) > self.batch_size:
                reduction = self._reduce(nodes, level, document_name, question, requested, prompt_type)
                nodes = list(reduction.nodes)
                unrepresented_original_ids.update(reduction.unrepresented_original_ids)
                failed_batch_count += len(reduction.failed_batches)
                if not nodes:
                    failure = (
                        f"Intermediate summarization did not produce verifiable summaries for "
                        f"{len(unrepresented_original_ids | sampling_omitted_ids)} of {total} indexed chunks across "
                        f"{failed_batch_count} batch(es). No full-document summary was produced."
                    )
                    return _not_found(
                        "I couldn't produce a reliable whole-document summary because the intermediate summaries "
                        "did not retain usable evidence citations.",
                        failure,
                    )
                level += 1
            final_question = _summary_question(
                question, requested, document_name, total, len(passages), limited,
                unrepresented_count=len(unrepresented_original_ids | sampling_omitted_ids),
            )
            final_retrieval = _retrieval(final_question, [node.passage for node in nodes])
            generated = self._generate_final(final_retrieval, requested, len(passages), prompt_type)
            # Validate the model's references against the actual intermediate
            # summary passages before translating them back to original pages.
            # Otherwise an invalid intermediate ID could disappear during the
            # remapping step and evade citation validation.
            generated = self.verifier.verify(generated, final_retrieval).answer
            source_ids = list(dict.fromkeys(
                original_id
                for citation in generated.evidence
                for node in nodes if node.passage.id == citation.passage_id
                for original_id in node.originals
            ))
            originals = [original_by_id[key] for key in source_ids if key in original_by_id]
            remapped = _remap(generated, originals)
            answer = self.verifier.verify(remapped, _retrieval(question, passages)).answer

        cited_source_ids = {
            evidence.passage_id for evidence in answer.evidence
            if evidence.passage_id in all_passage_ids
        }
        uncited_source_count = len(selected_passage_ids - cited_source_ids)

        if self.factual_verifier is not None:
            answer = self.factual_verifier.verify(question, answer, _retrieval(question, passages))

        if answer.status == AnswerStatus.NOT_FOUND:
            if unrepresented_original_ids:
                processing_note = (
                    f"{len(unrepresented_original_ids)} of {len(passages)} selected chunks were not represented in "
                    "reliable intermediate summaries; complete document coverage was not established."
                )
            elif sampling_omitted_ids:
                processing_note = (
                    f"A spread sample of {len(passages)} from {total} indexed chunks was processed, but no summary "
                    "passed evidence and citation checks."
                )
            else:
                processing_note = "The indexed document was processed, but no summary passed evidence and citation checks."
            coverage = " ".join(part for part in (answer.coverage, processing_note) if part)
            return answer.model_copy(update={
                "answer": "I couldn't produce a reliable summary from the indexed document because the generated "
                          "answer did not pass evidence validation.",
                "coverage": coverage,
            })
        safety_prefix, answer_body = _take_safety_prefix(answer.answer)
        bullets = _distinct_bullets(answer_body)
        enough = len(bullets) >= requested
        numbered = "\n".join(f"{i + 1}. {point}" for i, point in enumerate(bullets[:requested]))
        final_text = f"{safety_prefix}\n{numbered}" if bullets and safety_prefix else (numbered if bullets else answer.answer)
        notes = []
        if not enough:
            notes.append(f"The indexed content supports {len(bullets)} distinct summary points, fewer than the {requested} requested; facts were not repeated to fill the list.")
        if limited:
            notes.append(f"Coverage limitation: {total} indexed chunks were found; a spread sample of {len(passages)} chunks was summarized.")
        if unrepresented_original_ids:
            notes.append(
                f"Coverage limitation: {len(unrepresented_original_ids)} of {total} indexed chunks could not be "
                "represented by verifiable intermediate summaries; full-document coverage was not established."
            )
        if uncited_source_count:
            notes.append(
                f"Validated citations represent {len(cited_source_ids)} of {len(selected_passage_ids)} processed "
                "source chunks; other chunks may have been processed but are not cited in the final answer."
            )
        if hierarchical_reduction:
            notes.append(
                "Semantic faithfulness of generated intermediate summaries was not independently verified; "
                "citation identity checks do not establish that every summary sentence is entailed by its cited passages."
            )
        status = answer.status
        if notes and status == AnswerStatus.SUPPORTED:
            status = AnswerStatus.PARTIALLY_SUPPORTED
        if hierarchical_reduction:
            semantic_warning = "Semantic faithfulness of the hierarchical summary was not independently verified. "
            if semantic_warning.casefold() not in final_text.casefold():
                final_text = semantic_warning + final_text
        return answer.model_copy(update={"answer": final_text, "status": status, "coverage": " ".join(notes) or None})

    def _generate_final(self, retrieval, requested, source_count, prompt_type):
        generated = self.generator.generate(retrieval, prompt_type=prompt_type)
        initial_count = _summary_point_count(generated.answer)
        if generated.status == AnswerStatus.NOT_FOUND or initial_count >= requested or source_count < requested:
            return generated

        retry_prompt = (
            f"\n\nCompleteness review: the previous draft contained {initial_count} distinct point(s), while "
            f"the user requested {requested}. Re-examine all supplied document material and intermediate section "
            "summaries. Include the requested number only when each point is a distinct, directly supported fact. "
            "Do not collapse independent facts into one point, repeat a point, or infer missing facts. If fewer are "
            "supported, return fewer and explain the limitation. Keep numerical claims attached to their exact "
            "labels, units, conditions, and source evidence."
        )
        retry = self.generator.generate(
            _with_question(retrieval, retrieval.question + retry_prompt),
            prompt_type=prompt_type,
        )
        return retry if _summary_point_count(retry.answer) > initial_count else generated

    def _reduce(self, nodes, level, document_name, question, requested, prompt_type):
        node_map = {node.passage.id: node for node in nodes}
        output = []
        unrepresented = set()
        failed_batches = []
        for batch_no, start in enumerate(range(0, len(nodes), self.batch_size), start=1):
            batch = nodes[start : start + self.batch_size]
            prompt = (
                f"Summarize this section of {document_name!r} in up to 3 concise, distinct bullet points. Consider "
                "each supplied passage before compressing the section. Keep separately stated facts, different "
                "quantities, conditions, exceptions, dates, and numerical labels distinct; do not substitute one "
                "nearby value for another. Preserve source meaning and do not infer or repeat. The user's final task is: "
                f"{question}. "
                f"Final requested point count: {requested}."
            )
            batch_retrieval = _retrieval(prompt, [node.passage for node in batch])
            response = self.generator.generate(batch_retrieval, prompt_type=prompt_type)
            # Apply the same canonical citation validator at every reduction
            # level. Intermediate model output is not trusted merely because it
            # has a plausible status or text.
            checked = self.verifier.verify(response, batch_retrieval).answer
            child_ids = list(dict.fromkeys(
                item.passage_id for item in checked.evidence
                if item.passage_id in node_map
            ))
            cited_child_ids = set(child_ids)
            children = [node for node in batch if node.passage.id in cited_child_ids]
            if checked.status == AnswerStatus.NOT_FOUND or not children:
                unrepresented.update(original for node in batch for original in node.originals)
                failed_batches.append(batch_no)
                continue
            citation_integrity_issues = {
                "MISSING_PASSAGE_ID", "INVALID_PASSAGE_REFERENCE", "UNAVAILABLE_PASSAGE_REFERENCE",
                "DUPLICATE_PASSAGE_REFERENCE", "MISSING_EVIDENCE_REFERENCES", "MISSING_SOURCE_METADATA",
                "DOCUMENT_ID_MISMATCH", "DOCUMENT_NAME_MISMATCH", "PAGE_NUMBER_MISMATCH",
                "SECTION_MISMATCH", "EVIDENCE_TEXT_MISMATCH", "VERIFICATION_STATUS_MISMATCH",
                "VERSION_MISMATCH", "SOURCE_WITHOUT_VALID_EVIDENCE", "INVALID_SOURCE_SUMMARY",
            }
            if checked.validation and citation_integrity_issues.intersection(checked.validation.issues):
                # A partly valid citation list does not make a mixed answer safe
                # to compress. Discard the entire intermediate prose and report
                # its source chunks as unrepresented.
                unrepresented.update(original for node in batch for original in node.originals)
                failed_batches.append(batch_no)
                continue
            originals = tuple(dict.fromkeys(key for child in children for key in child.originals))
            unrepresented.update(
                original for node in batch if node.passage.id not in cited_child_ids
                for original in node.originals
            )
            metadata = dict(children[0].passage.metadata)
            metadata["semantic_faithfulness"] = "NOT_VERIFIED"
            identifier = f"summary-level-{level}-batch-{batch_no}"
            marked_unverified = (
                "[UNVERIFIED INTERMEDIATE SUMMARY: citations were checked for identity, but semantic support "
                "of every sentence was not established.]\n"
                + checked.answer
            )
            output.append(_Node(RetrievedPassage(identifier, marked_unverified, metadata, 1.0, 0.0), originals))
        if failed_batches:
            logger.warning(
                "Document summary reduction had batches without usable evidence citations "
                "(level=%s, failed_batches=%s, unrepresented_chunks=%s)",
                level, len(failed_batches), len(unrepresented),
            )
        return _ReductionResult(tuple(output), tuple(sorted(unrepresented)), tuple(failed_batches))


def _passages(records, document_id, state):
    passages = []
    for record in records:
        text, metadata = record.get("text"), record.get("metadata")
        if not isinstance(text, str) or not text.strip() or not isinstance(metadata, dict):
            continue
        if str(metadata.get("document_id", "")) != document_id or not metadata.get("document_name") or not metadata.get("verification_status"):
            continue
        try:
            page = int(metadata["page_number"])
        except (KeyError, TypeError, ValueError):
            continue
        if page < 1:
            continue
        clean = dict(metadata)
        clean["page_number"] = page
        if state:
            clean["verification_status"] = state[0]
        for field in ("section", "document_type", "academic_year", "version", "effective_date", "source_type"):
            clean.setdefault(field, "")
        identifier = str(record.get("id", ""))
        if not identifier:
            continue
        passages.append(RetrievedPassage(identifier, text.strip(), clean, 1.0, 0.0))
    passages.sort(key=lambda p: (int(p.metadata["page_number"]), _chunk_index(p.id), p.id))
    return passages


def _chunk_index(identifier):
    match = re.search(r"-chunk-(\d+)$", identifier)
    return int(match.group(1)) if match else 0


def _dedupe(passages):
    seen, result = set(), []
    for passage in passages:
        text = _normalize(passage.text)
        if text and text not in seen:
            seen.add(text)
            result.append(passage)
    return result


def _spread_sample(passages, limit):
    if limit <= 1:
        return [passages[len(passages) // 2]]
    indexes = {round(i * (len(passages) - 1) / (limit - 1)) for i in range(limit)}
    return [passage for i, passage in enumerate(passages) if i in indexes]


def _summary_question(question, requested, document_name, total, included, limited, *, unrepresented_count=0):
    if limited:
        scope = f"The PDF has {total} indexed chunks; a spread sample of {included} is supplied. State this coverage limitation."
    elif unrepresented_count:
        scope = (
            f"The PDF has {total} indexed chunks, but {unrepresented_count} chunks are not represented in the "
            "usable intermediate summaries. Do not claim complete document coverage; explicitly disclose this limitation."
        )
    else:
        scope = "The supplied passages cover the complete indexed document."
    return (
        f"Summarize the document {document_name!r} in exactly {requested} distinct numbered bullet points if supported. "
        "Preserve important facts, conditions, exceptions, dates, terminology, and numbers. Do not invent or repeat. "
        "Return fewer points if the document does not support the requested number, and cite only supplied evidence IDs. "
        f"{scope} Original user request: {question}"
    )


def _distinct_bullets(answer):
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    bullets = [re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", line).strip() for line in lines
               if re.match(r"^(?:[-*•]|\d+[.)])\s+", line)]
    if not bullets:
        bullets = [line.strip() for line in re.split(r"(?<=[.!?])\s+", answer) if line.strip()]
    seen, token_sets, result = set(), [], []
    for bullet in bullets:
        tokens = set(_normalize(bullet).split())
        normalized = " ".join(sorted(tokens))
        if not tokens or normalized in seen:
            continue
        if any(len(tokens & existing) / min(len(tokens), len(existing)) >= 0.95 for existing in token_sets):
            continue
        seen.add(normalized)
        token_sets.append(tokens)
        result.append(bullet)
    return result


def _summary_point_count(answer):
    _prefix, body = _take_safety_prefix(answer)
    return len(_distinct_bullets(body))


_SAFETY_PREFIXES = (
    "Semantic faithfulness of the hierarchical summary was not independently verified. ",
    "Some generated source references failed citation checks; only validated evidence is listed. Treat unsupported details as unconfirmed. ",
    "Evidence includes unverified documents and is not confirmed as official policy. ",
    "Administrator verification indicates internal review only; university issuance has not been independently established. ",
    "A newer retrieved version may supersede some cited material; no replacement source was assumed. ",
)


def _take_safety_prefix(answer):
    prefix = ""
    remainder = answer
    while True:
        match = next((candidate for candidate in _SAFETY_PREFIXES if remainder.startswith(candidate)), None)
        if match is None:
            break
        prefix += match
        remainder = remainder[len(match):]
    return prefix, remainder


def _normalize(value):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold()))


def _retrieval(question, passages):
    return RetrievalResult(question, tuple(passages), len(passages), 0.0)


def _with_question(retrieval, question):
    return RetrievalResult(
        question, retrieval.passages, retrieval.top_k, retrieval.relevance_threshold,
        retrieval_state=retrieval.retrieval_state,
    )


def _remap(answer, passages):
    evidence = [EvidenceItem(
        text=p.text, document=str(p.metadata["document_name"]), page=int(p.metadata["page_number"]),
        section=str(p.metadata.get("section") or ""), passage_id=p.id, document_id=str(p.metadata["document_id"]),
        version=str(p.metadata.get("version") or ""), effective_date=str(p.metadata.get("effective_date") or ""),
        academic_year=str(p.metadata.get("academic_year") or ""), verification_status=str(p.metadata["verification_status"]),
    ) for p in passages]
    grouped = {}
    for p in passages:
        m = p.metadata
        key = (str(m["document_id"]), str(m["document_name"]), str(m.get("version") or ""))
        source = grouped.setdefault(key, {
            "document": key[1], "document_id": key[0], "document_type": str(m.get("document_type") or ""),
            "pages": [], "sections": [], "academic_year": str(m.get("academic_year") or ""), "version": key[2],
            "effective_date": str(m.get("effective_date") or ""), "source_type": str(m.get("source_type") or ""),
            "verification_status": str(m["verification_status"]),
        })
        page, section = int(m["page_number"]), str(m.get("section") or "")
        if page not in source["pages"]: source["pages"].append(page)
        if section and section not in source["sections"]: source["sections"].append(section)
    return answer.model_copy(update={"evidence": evidence, "sources": [SourceItem(**value) for value in grouped.values()]})


def _not_found(answer, coverage):
    return StructuredAnswer(answer=answer, evidence=[], sources=[], status=AnswerStatus.NOT_FOUND,
                            validation=CitationValidationSummary(citation_status="NOT_APPLICABLE"), coverage=coverage)
