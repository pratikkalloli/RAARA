from __future__ import annotations

from io import BytesIO
import re

import pymupdf as fitz

from app.services.chunker import TokenChunker
from app.services.document_processor import extract_pdf_pages
from app.services.document_summarizer import DocumentSummarizer
from app.services.generator import AnswerStatus, CitationValidationSummary, EvidenceItem, SourceItem, StructuredAnswer
from app.services.retriever import RetrievalResult


class MemoryDocumentStore:
    def __init__(self, records):
        self.records = records
    def get_document_chunks(self, document_id):
        return [record for record in self.records if record["metadata"]["document_id"] == str(document_id)]


class DeterministicGenerator:
    """Mock model output; every test passage is clearly synthetic test content."""
    def __init__(self):
        self.calls = []
    def generate(self, retrieval: RetrievalResult, *, prompt_type="C"):
        self.calls.append(retrieval)
        section_pass = "Summarize this section" in retrieval.question
        if section_pass:
            answer_text = "1. Synthetic section observation A.\n2. Synthetic section observation B."
        elif len(retrieval.passages) == 1:
            answer_text = "1. The fictional material describes one synthetic topic.\n2. It records one distinct simulated condition."
        elif "exactly 10" in retrieval.question:
            answer_text = "\n".join(f"{i}. Distinct synthetic fact {i} from the fictional test document." for i in range(1, 11))
        else:
            answer_text = "\n".join(f"{i}. Distinct synthetic summary fact {i}." for i in range(1, 4))
        evidence = [_evidence(passage) for passage in retrieval.passages]
        sources = _sources(retrieval.passages)
        return StructuredAnswer(
            answer=answer_text,
            evidence=evidence,
            sources=sources,
            status=AnswerStatus.SUPPORTED,
            validation=CitationValidationSummary(citation_status="VERIFIED"),
        )


def _evidence(passage):
    metadata = passage.metadata
    return EvidenceItem(
        text=passage.text, document=metadata["document_name"], page=metadata["page_number"],
        section=metadata["section"], passage_id=passage.id, document_id=metadata["document_id"],
        version=metadata["version"], effective_date=metadata["effective_date"],
        academic_year=metadata["academic_year"], verification_status=metadata["verification_status"],
    )


def _sources(passages):
    if not passages:
        return []
    metadata = passages[0].metadata
    return [SourceItem(
        document=metadata["document_name"], document_id=metadata["document_id"],
        document_type=metadata["document_type"], pages=list(dict.fromkeys(p.metadata["page_number"] for p in passages)),
        sections=list(dict.fromkeys(p.metadata["section"] for p in passages if p.metadata["section"])),
        academic_year=metadata["academic_year"], version=metadata["version"], effective_date=metadata["effective_date"],
        source_type=metadata["source_type"], verification_status=metadata["verification_status"],
    )]


def _synthetic_pdf(page_count=10, *, limited=False):
    pdf = fitz.open()
    for number in range(1, page_count + 1):
        page = pdf.new_page()
        page.insert_text((48, 50), "SYNTHETIC TEST NOTES — NOT OFFICIAL UNIVERSITY POLICY", fontsize=14, fontname="hebo")
        page.insert_text((48, 85), f"Fictional Science Section {number}", fontsize=12, fontname="hebo")
        text = (
            "A fictional research note describes a distinct simulated observation about the invented Atlas instrument. "
            "This example exists only for summarization tests and does not describe a university regulation. "
            if not limited else "This synthetic page has only one distinct fictional observation."
        )
        page.insert_textbox(fitz.Rect(48, 112, 545, 740), (text + " ") * (3 if limited else 9), fontsize=10)
    output = BytesIO()
    pdf.save(output)
    pdf.close()
    return output.getvalue()


def _index_pdf(pdf_bytes, document_id="81"):
    pages = extract_pdf_pages(pdf_bytes)
    metadata = {
        "document_id": str(document_id), "document_name": f"Synthetic Research Test {document_id}.pdf",
        "document_type": "synthetic_test", "academic_year": "", "version": "1",
        "effective_date": "", "source_type": "synthetic_test", "verification_status": "unverified",
        "uploaded_by_user_id": "12",
    }
    chunks = TokenChunker(chunk_size=700, overlap=100).chunk_pages(pages, metadata)
    records = [{"id": f"doc-{document_id}-chunk-{chunk.chunk_index}", "text": chunk.text, "metadata": chunk.metadata} for chunk in chunks]
    return pages, records


def test_ten_point_summary_uses_complete_synthetic_pdf_and_page_citations():
    pages, records = _index_pdf(_synthetic_pdf(10), document_id="81")
    generator = DeterministicGenerator()
    service = DocumentSummarizer(MemoryDocumentStore(records), generator)

    answer = service.summarize(81, "Summarize this PDF in 10 bullet points", requested_points=10)

    assert len(pages) == 10
    assert len(generator.calls) == 1
    assert len(generator.calls[0].passages) == len(records)
    assert len(re.findall(r"(?m)^\d+\. ", answer.answer)) == 10
    assert answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "unverified" in answer.answer.casefold()
    assert answer.validation.citation_status == "VERIFIED"
    assert {item.page for item in answer.evidence} == set(range(1, 11))
    assert all(item.document == f"Synthetic Research Test 81.pdf" for item in answer.evidence)


def test_multi_page_summary_keeps_exact_source_pages():
    pages, records = _index_pdf(_synthetic_pdf(2), document_id="82")
    answer = DocumentSummarizer(MemoryDocumentStore(records), DeterministicGenerator()).summarize(
        82, "Summarize this PDF in 3 points", requested_points=3
    )
    assert [page.page_number for page in pages] == [1, 2]
    assert {item.page for item in answer.evidence} == {1, 2}
    assert answer.validation.citation_status == "VERIFIED"


def test_one_page_limited_document_does_not_repeat_points_to_reach_ten():
    _, records = _index_pdf(_synthetic_pdf(1, limited=True), document_id="83")
    answer = DocumentSummarizer(MemoryDocumentStore(records), DeterministicGenerator()).summarize(
        83, "Summarize this PDF in 10 points", requested_points=10
    )
    assert len(re.findall(r"(?m)^\d+\. ", answer.answer)) == 2
    assert answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "fewer than the 10 requested" in answer.coverage


def test_exact_duplicate_chunks_are_suppressed_before_summarization():
    _, records = _index_pdf(_synthetic_pdf(1, limited=True), document_id="84")
    records = [records[0], {**records[0], "id": "doc-84-chunk-999"}]
    generator = DeterministicGenerator()
    DocumentSummarizer(MemoryDocumentStore(records), generator).summarize(84, "Summarize this PDF in 2 points", requested_points=2)
    assert len(generator.calls[0].passages) == 1


def test_empty_index_reports_retrieval_gap_without_invoking_generator():
    generator = DeterministicGenerator()
    answer = DocumentSummarizer(MemoryDocumentStore([]), generator).summarize(
        99, "Summarize this PDF in 10 points", requested_points=10
    )
    assert answer.status == AnswerStatus.NOT_FOUND
    assert "indexing or retrieval gap" in answer.coverage
    assert answer.evidence == []
    assert generator.calls == []


def test_large_document_uses_hierarchical_batches_and_discloses_sampling_limit():
    _, records = _index_pdf(_synthetic_pdf(10), document_id="85")
    # Duplicate each page chunk with unique source identity and text to model a large indexed PDF.
    expanded = []
    for index in range(18):
        source = records[index % len(records)]
        metadata = {**source["metadata"], "page_number": index + 1, "section": f"Fictional Section {index + 1}"}
        expanded.append({"id": f"doc-85-chunk-{index}", "text": f"{source['text']} Unique simulated note {index}.", "metadata": metadata})
    generator = DeterministicGenerator()
    answer = DocumentSummarizer(
        MemoryDocumentStore(expanded), generator, batch_size=4, direct_chunk_limit=4, max_chunks=13
    ).summarize(85, "Summarize this PDF in 10 points", requested_points=10)

    assert len(generator.calls) > 2
    assert len(generator.calls[0].passages) == 4
    assert "18 indexed chunks" in answer.coverage
    assert "spread sample of 13" in answer.coverage
    assert answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert all(evidence.passage_id in {record["id"] for record in expanded} for evidence in answer.evidence)


def test_hierarchical_summary_retries_once_to_recover_requested_distinct_points():
    _, records = _index_pdf(_synthetic_pdf(10), document_id="86")
    expanded = []
    for index in range(18):
        source = records[index % len(records)]
        metadata = {**source["metadata"], "page_number": index + 1, "section": f"Synthetic Section {index + 1}"}
        expanded.append({"id": f"doc-86-chunk-{index}", "text": f"{source['text']} Unique synthetic fact {index}.", "metadata": metadata})

    class UnderproducingThenCompleteGenerator(DeterministicGenerator):
        def generate(self, retrieval, *, prompt_type="C"):
            self.calls.append(retrieval)
            if "Summarize this section" in retrieval.question:
                text = "1. Intermediate synthetic fact A.\n2. Intermediate synthetic fact B."
            elif "Completeness review" in retrieval.question:
                text = "\n".join(
                    f"{i}. Distinct supported synthetic summary point {i}, retaining the exception and {i * 7} marks."
                    for i in range(1, 6)
                )
            else:
                text = "1. One overly compressed synthetic point."
            evidence = [_evidence(passage) for passage in retrieval.passages]
            return StructuredAnswer(
                answer=text, evidence=evidence, sources=_sources(retrieval.passages),
                status=AnswerStatus.SUPPORTED,
                validation=CitationValidationSummary(citation_status="VERIFIED"),
            )

    generator = UnderproducingThenCompleteGenerator()
    answer = DocumentSummarizer(
        MemoryDocumentStore(expanded), generator, batch_size=4, direct_chunk_limit=4, max_chunks=30
    ).summarize(86, "Summarize this synthetic PDF in 5 points", requested_points=5)

    assert "Completeness review" in generator.calls[-1].question
    assert len(re.findall(r"(?m)^\d+\. ", answer.answer)) == 5
    assert "fewer than the 5 requested" not in (answer.coverage or "")
    assert {evidence.passage_id for evidence in answer.evidence}.issubset({record["id"] for record in expanded})
    assert "exception" in answer.answer.casefold()
    assert "marks" in answer.answer.casefold()


def test_failed_intermediate_batch_is_disclosed_and_successful_batches_keep_page_citations():
    _, records = _index_pdf(_synthetic_pdf(10), document_id="87")
    expanded = []
    for index in range(14):
        source = records[index % len(records)]
        metadata = {**source["metadata"], "page_number": index + 1, "section": f"Synthetic Section {index + 1}"}
        expanded.append({
            "id": f"doc-87-chunk-{index}",
            "text": f"{source['text']} Unique synthetic statement {index}.",
            "metadata": metadata,
        })

    class OneBatchFailsGenerator(DeterministicGenerator):
        def generate(self, retrieval, *, prompt_type="C"):
            if "Summarize this section" in retrieval.question and retrieval.passages[0].metadata["page_number"] == 5:
                self.calls.append(retrieval)
                return StructuredAnswer(
                    answer="No reliable intermediate summary was produced.", evidence=[], sources=[],
                    status=AnswerStatus.NOT_FOUND,
                    validation=CitationValidationSummary(citation_status="NOT_APPLICABLE"),
                )
            return super().generate(retrieval, prompt_type=prompt_type)

    generator = OneBatchFailsGenerator()
    answer = DocumentSummarizer(
        MemoryDocumentStore(expanded), generator, batch_size=4, direct_chunk_limit=4, max_chunks=30,
    ).summarize(87, "Summarize the whole synthetic document in 3 points", requested_points=3)

    assert answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "4 of 14 indexed chunks" in answer.coverage
    assert "full-document coverage was not established" in answer.coverage
    assert answer.evidence
    assert set(item.page for item in answer.evidence).isdisjoint({5, 6, 7, 8})
    assert all(item.passage_id in {record["id"] for record in expanded} for item in answer.evidence)


def test_all_unverifiable_intermediate_batches_return_specific_abstention():
    _, records = _index_pdf(_synthetic_pdf(10), document_id="88")
    expanded = []
    for index in range(14):
        source = records[index % len(records)]
        metadata = {**source["metadata"], "page_number": index + 1}
        expanded.append({
            "id": f"doc-88-chunk-{index}", "text": f"{source['text']} unique note {index}", "metadata": metadata,
        })

    class FabricatedCitationGenerator(DeterministicGenerator):
        def generate(self, retrieval, *, prompt_type="C"):
            self.calls.append(retrieval)
            fabricated = _evidence(retrieval.passages[0]).model_copy(
                update={"passage_id": "fabricated-intermediate-passage-id"}
            )
            return StructuredAnswer(
                answer="1. Unsupported intermediate statement.", evidence=[fabricated],
                sources=_sources(retrieval.passages), status=AnswerStatus.SUPPORTED,
                validation=CitationValidationSummary(citation_status="VERIFIED"),
            )

    generator = FabricatedCitationGenerator()
    answer = DocumentSummarizer(
        MemoryDocumentStore(expanded), generator, batch_size=4, direct_chunk_limit=4, max_chunks=30,
    ).summarize(88, "Summarize the whole synthetic document", requested_points=3)

    assert answer.status == AnswerStatus.NOT_FOUND
    assert "reliable whole-document summary" in answer.answer
    assert "14 of 14 indexed chunks" in answer.coverage
    assert "No full-document summary was produced" in answer.coverage
    # A failed intermediate phase must not be followed by a fabricated final summary call.
    assert len(generator.calls) == 4


def test_final_summary_discloses_when_valid_citations_cover_only_a_subset_of_processed_chunks():
    _, records = _index_pdf(_synthetic_pdf(10), document_id="89")
    expanded = []
    for index in range(14):
        source = records[index % len(records)]
        metadata = {**source["metadata"], "page_number": index + 1}
        expanded.append({
            "id": f"doc-89-chunk-{index}", "text": f"{source['text']} distinct summary test detail {index}",
            "metadata": metadata,
        })

    class NarrowFinalCitationGenerator(DeterministicGenerator):
        def generate(self, retrieval, *, prompt_type="C"):
            if "Summarize this section" in retrieval.question:
                return super().generate(retrieval, prompt_type=prompt_type)
            self.calls.append(retrieval)
            passage = retrieval.passages[0]
            return StructuredAnswer(
                answer="1. One synthetic summary statement.", evidence=[_evidence(passage)],
                sources=_sources([passage]), status=AnswerStatus.SUPPORTED,
                validation=CitationValidationSummary(citation_status="VERIFIED"),
            )

    answer = DocumentSummarizer(
        MemoryDocumentStore(expanded), NarrowFinalCitationGenerator(), batch_size=4,
        direct_chunk_limit=4, max_chunks=30,
    ).summarize(89, "Summarize the whole synthetic document in 3 points", requested_points=3)

    assert answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert {item.page for item in answer.evidence} == {1, 2, 3, 4}
    assert "Validated citations represent 4 of 14 processed source chunks" in answer.coverage
    assert "not cited in the final answer" in answer.coverage


def test_mixed_intermediate_summary_is_marked_unverified_and_never_reported_fully_supported():
    _, records = _index_pdf(_synthetic_pdf(10), document_id="90")
    expanded = []
    for index in range(14):
        source = records[index % len(records)]
        metadata = {**source["metadata"], "page_number": index + 1, "section": f"Synthetic Section {index + 1}"}
        expanded.append({
            "id": f"doc-90-chunk-{index}",
            "text": f"{source['text']} supported source fact {index}.",
            "metadata": metadata,
        })

    class MixedIntermediateGenerator(DeterministicGenerator):
        def generate(self, retrieval, *, prompt_type="C"):
            self.calls.append(retrieval)
            if "Summarize this section" in retrieval.question:
                # Citation identity is valid for every passage, but it cannot
                # establish that the second sentence is supported.
                answer_text = (
                    "1. The source records a supported synthetic observation.\n"
                    "2. The source also requires exactly 99 exams per term."
                )
            else:
                answer_text = (
                    "1. The source records a supported synthetic observation.\n"
                    "2. The source also requires exactly 99 exams per term."
                )
            return StructuredAnswer(
                answer=answer_text,
                evidence=[_evidence(passage) for passage in retrieval.passages],
                sources=_sources(retrieval.passages),
                status=AnswerStatus.SUPPORTED,
                validation=CitationValidationSummary(citation_status="VERIFIED"),
            )

    answer = DocumentSummarizer(
        MemoryDocumentStore(expanded), MixedIntermediateGenerator(), batch_size=4,
        direct_chunk_limit=4, max_chunks=30,
    ).summarize(90, "Summarize the whole synthetic document", requested_points=2)

    assert answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert answer.validation.semantic_faithfulness == "NOT_VERIFIED"
    assert "semantic faithfulness" in answer.answer.casefold()
    assert "not independently verified" in (answer.coverage or "").casefold()
    assert all(item.passage_id in {record["id"] for record in expanded} for item in answer.evidence)
