from app.services.citation_verifier import CitationVerifier
from app.services.generator import (
    AnswerStatus,
    CitationValidationSummary,
    EvidenceItem,
    SourceItem,
    StructuredAnswer,
)
from app.services.retriever import RetrievalResult, RetrievedPassage


def passage(
    identifier="chunk-1",
    *,
    doc_id="doc-1",
    document="Synthetic Test Handbook.pdf",
    page=1,
    section="Synthetic Test Section",
    status="verified",
    version="1",
    effective_date="2026-08-01",
    text="Synthetic test passage; not an official regulation.",
    document_type="test_fixture",
    academic_year="2026-2027",
):
    return RetrievedPassage(
        id=identifier,
        text=text,
        metadata={
            "document_id": doc_id,
            "document_name": document,
            "document_type": document_type,
            "page_number": page,
            "section": section,
            "academic_year": academic_year,
            "version": version,
            "effective_date": effective_date,
            "source_type": "synthetic_test",
            "verification_status": status,
        },
        cosine_distance=0.1,
        relevance_score=0.9,
    )


def retrieval(*passages):
    return RetrievalResult("Synthetic test question", tuple(passages), 5, 0.35)


def answer_for(passage, *, status=AnswerStatus.SUPPORTED, **citation_overrides):
    metadata = passage.metadata
    evidence_values = {
        "text": passage.text,
        "document": metadata.get("document_name", ""),
        "page": metadata.get("page_number", 0),
        "section": metadata.get("section", "") or "",
        "passage_id": passage.id,
        "document_id": metadata.get("document_id", "") or "",
        "version": metadata.get("version", "") or "",
        "effective_date": metadata.get("effective_date", "") or "",
        "academic_year": metadata.get("academic_year", "") or "",
        "verification_status": metadata.get("verification_status", "") or "",
    }
    evidence_values.update(citation_overrides)
    evidence = EvidenceItem(**evidence_values)
    source = SourceItem(
        document=str(metadata.get("document_name", "")),
        document_id=str(metadata.get("document_id", "")),
        document_type=str(metadata.get("document_type", "")),
        pages=[int(metadata.get("page_number", 1))],
        sections=[str(metadata.get("section", ""))] if metadata.get("section") else [],
        academic_year=str(metadata.get("academic_year", "")),
        version=str(metadata.get("version", "")),
        effective_date=str(metadata.get("effective_date", "")),
        source_type=str(metadata.get("source_type", "")),
        verification_status=str(metadata.get("verification_status", "")),
    )
    return StructuredAnswer(
        answer="The cited synthetic passage supports this test answer.",
        evidence=[evidence],
        sources=[source],
        status=status,
    )


def test_valid_citation_is_accepted_and_rebuilt_from_retrieved_metadata():
    source = passage()

    result = CitationVerifier().verify(answer_for(source), retrieval(source))

    assert result.answer.status == AnswerStatus.SUPPORTED
    assert result.answer.validation.citation_status == "VERIFIED"
    assert result.answer.validation.semantic_faithfulness == "NOT_VERIFIED"
    assert result.answer.evidence[0].passage_id == "chunk-1"
    assert result.answer.evidence[0].document == "Synthetic Test Handbook.pdf"
    assert result.answer.evidence[0].page == 1
    assert result.valid_passage_ids == ("chunk-1",)
    assert result.issues == ()


def test_fabricated_document_name_is_rejected_without_replacement():
    source = passage()
    answer = answer_for(source, document="Invented University Policy.pdf")

    result = CitationVerifier().verify(answer, retrieval(source))

    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert result.answer.evidence == []
    assert result.answer.sources == []
    assert "DOCUMENT_NAME_MISMATCH" in result.issues
    assert "Invented University Policy.pdf" not in str(result.answer.model_dump())


def test_fabricated_page_number_is_rejected_without_substitution():
    source = passage(page=1)
    answer = answer_for(source, page=99)

    result = CitationVerifier().verify(answer, retrieval(source))

    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert result.answer.evidence == []
    assert "PAGE_NUMBER_MISMATCH" in result.issues


def test_invalid_passage_id_is_rejected():
    source = passage()
    answer = answer_for(source, passage_id="not-retrieved")

    result = CitationVerifier().verify(answer, retrieval(source))

    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert result.answer.evidence == []
    assert "INVALID_PASSAGE_REFERENCE" in result.issues


def test_missing_source_metadata_causes_abstention():
    source = passage()
    source.metadata.pop("document_id")
    answer = answer_for(source)

    result = CitationVerifier().verify(answer, retrieval(source))

    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert result.answer.sources == []
    assert "MISSING_SOURCE_METADATA" in result.issues


def test_empty_knowledge_base_abstains_without_claiming_citation_verification():
    answer = StructuredAnswer(
        answer="The attendance requirement is 75%.",
        evidence=[],
        sources=[],
        status=AnswerStatus.SUPPORTED,
    )

    result = CitationVerifier().verify(answer, retrieval())

    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert result.answer.evidence == []
    assert result.answer.validation.citation_status == "NOT_APPLICABLE"
    assert result.answer.validation.semantic_faithfulness == "NOT_VERIFIED"
    assert "NO_RETRIEVED_EVIDENCE" in result.issues


def test_model_abstention_explanation_is_preserved_when_no_passages_exist():
    answer = StructuredAnswer(
        answer="No documents are available in this user's library, so there is no evidence to assess.",
        evidence=[], sources=[], status=AnswerStatus.NOT_FOUND,
        validation=CitationValidationSummary(
            citation_status="NOT_APPLICABLE", unsupported_claims_flagged=True,
            issues=["INSUFFICIENT_RETRIEVED_EVIDENCE"],
        ),
    )

    result = CitationVerifier().verify(answer, retrieval())

    assert result.answer.answer == answer.answer
    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert result.answer.validation.citation_status == "NOT_APPLICABLE"
    assert result.answer.validation.issues == ["INSUFFICIENT_RETRIEVED_EVIDENCE"]


def test_model_abstention_explanation_is_preserved_when_relevant_passages_exist():
    source = passage(status="unverified")
    answer = StructuredAnswer(
        answer="The only relevant passage is synthetic and unverified, so it cannot establish an official university requirement.",
        evidence=[], sources=[], status=AnswerStatus.NOT_FOUND,
        validation=CitationValidationSummary(
            citation_status="NOT_APPLICABLE", unsupported_claims_flagged=True,
            issues=["INSUFFICIENT_RETRIEVED_EVIDENCE"],
        ),
    )

    result = CitationVerifier().verify(answer, retrieval(source))

    assert result.answer.answer == answer.answer
    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert result.answer.evidence == [] and result.answer.sources == []
    assert result.answer.validation.citation_status == "NOT_APPLICABLE"
    assert result.answer.validation.issues == ["INSUFFICIENT_RETRIEVED_EVIDENCE"]


def test_below_threshold_retrieval_abstains():
    answer = StructuredAnswer(
        answer="This generated claim has no accepted retrieval evidence.",
        evidence=[],
        sources=[],
        status=AnswerStatus.SUPPORTED,
    )

    result = CitationVerifier().verify(answer, retrieval())

    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert "NO_RETRIEVED_EVIDENCE" in result.issues


def test_unsupported_answer_without_evidence_is_downgraded_and_flagged():
    source = passage()
    answer = StructuredAnswer(
        answer="The policy requires 100% attendance.",
        evidence=[],
        sources=[],
        status=AnswerStatus.SUPPORTED,
    )

    result = CitationVerifier().verify(answer, retrieval(source))

    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert result.answer.validation.unsupported_claims_flagged is True
    assert result.answer.evidence == []


def test_conflicting_sources_status_is_preserved_with_two_valid_sources():
    first = passage("chunk-1", doc_id="doc-1", document="Synthetic Rules v1.pdf", version="1", text="Test rule says 75%.")
    second = passage("chunk-2", doc_id="doc-2", document="Synthetic Rules v2.pdf", version="2", page=2, text="Test rule says 80%.")
    answer = StructuredAnswer(
        answer="The retrieved synthetic versions conflict.",
        evidence=[answer_for(first).evidence[0], answer_for(second).evidence[0]],
        sources=[*answer_for(first).sources, *answer_for(second).sources],
        status=AnswerStatus.CONFLICTING_SOURCES,
    )

    result = CitationVerifier().verify(answer, retrieval(first, second))

    assert result.answer.status == AnswerStatus.CONFLICTING_SOURCES
    assert len(result.answer.evidence) == 2
    assert len(result.answer.sources) == 2


def test_unverified_source_is_explicit_and_downgraded():
    source = passage(status="unverified")

    result = CitationVerifier().verify(answer_for(source), retrieval(source))

    assert result.answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert result.answer.evidence[0].verification_status == "unverified"
    assert result.answer.sources[0].verification_status == "unverified"
    assert "unverified" in result.answer.answer.casefold()


def test_older_cited_version_is_flagged_without_replacing_it():
    older = passage("chunk-old", doc_id="doc-old", version="1", effective_date="2025-08-01")
    newer = passage("chunk-new", doc_id="doc-new", version="2", effective_date="2026-08-01")

    result = CitationVerifier().verify(answer_for(older), retrieval(older, newer))

    assert result.answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert result.answer.evidence[0].passage_id == "chunk-old"
    assert result.answer.sources[0].version == "1"
    assert "POSSIBLY_SUPERSEDED_VERSION" in result.issues
    assert "no replacement source was assumed" in result.answer.answer


def test_wrong_section_and_text_are_rejected():
    source = passage()
    answer = answer_for(source, section="Fabricated section", text="Different invented evidence.")

    result = CitationVerifier().verify(answer, retrieval(source))

    assert result.answer.status == AnswerStatus.NOT_FOUND
    assert "SECTION_MISMATCH" in result.issues


def test_valid_citations_are_preserved_when_another_reference_is_invalid():
    actual = passage("chunk-actual", doc_id="doc-actual")
    invented = passage("chunk-invented", doc_id="doc-invented", document="Invented Source.pdf")
    valid_answer = answer_for(actual)
    invalid_answer = answer_for(invented)
    answer = StructuredAnswer(
        answer="Some details have support; other generated details may not.",
        evidence=[valid_answer.evidence[0], invalid_answer.evidence[0]],
        sources=[valid_answer.sources[0], invalid_answer.sources[0]],
        status=AnswerStatus.SUPPORTED,
    )

    result = CitationVerifier().verify(answer, retrieval(actual))

    assert result.answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert [item.passage_id for item in result.answer.evidence] == ["chunk-actual"]
    assert [item.document for item in result.answer.sources] == ["Synthetic Test Handbook.pdf"]
    assert "failed citation checks" in result.answer.answer
    assert "INVALID_PASSAGE_REFERENCE" in result.issues


def test_source_summary_with_fabricated_page_is_flagged_and_rebuilt_from_valid_evidence():
    source = passage()
    answer = answer_for(source)
    answer.sources[0].pages = [99]

    result = CitationVerifier().verify(answer, retrieval(source))

    assert result.answer.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "INVALID_SOURCE_SUMMARY" in result.issues
    assert result.answer.sources[0].pages == [1]
    assert "failed citation checks" in result.answer.answer
