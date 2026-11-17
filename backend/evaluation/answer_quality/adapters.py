from __future__ import annotations
import re
from typing import Any
from app.prompting.system_prompt import PromptType
from app.services.generator import AnswerStatus, EvidenceItem, GenerationRecord, SourceItem, StructuredAnswer
from app.services.retriever import RetrievalResult, RetrievedPassage

class DeterministicMockGenerator:
    """Offline extractive adapter for framework validation; it is not an LLM."""
    model = "deterministic-extractive-mock-v1"
    def generate_with_usage(self, retrieval: RetrievalResult, *, prompt_type: PromptType|str=PromptType.C) -> GenerationRecord:
        if not retrieval.passages:
            answer=StructuredAnswer(answer="I couldn't find relevant evidence for this question in the available documents.",evidence=[],sources=[],status=AnswerStatus.NOT_FOUND)
            return GenerationRecord(answer,self.model,PromptType.C)
        stop={"the","is","in","what","does","do","how","many","according","to","and","or","a","an","of","for","version","states","state","synthetic"}
        terms=set(re.findall(r"[a-z0-9]+",retrieval.question.casefold()))-stop
        candidates=[]
        for passage in retrieval.passages:
            sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+",passage.text) if s.strip()]
            if not sentences: sentences=[passage.text]
            sentence=max(sentences,key=lambda s:len(terms & set(re.findall(r"[a-z0-9]+",s.casefold()))))
            score=len(terms & set(re.findall(r"[a-z0-9]+",sentence.casefold())))
            if score: candidates.append((score,passage,sentence))
        candidates.sort(key=lambda row:(-row[0],row[1].id))
        chosen=candidates[:max(1,min(3,len(candidates)))]
        if not chosen:
            answer=StructuredAnswer(answer="I couldn't find relevant evidence for this question in the available documents.",evidence=[],sources=[],status=AnswerStatus.NOT_FOUND)
            return GenerationRecord(answer,self.model,PromptType.C)
        statements=[]; evidence=[]; sources={}
        for _,passage,sentence in chosen:
            meta=passage.metadata; version=str(meta.get("version", ""))
            statements.append((f"Version {version}: " if version else "")+sentence)
            evidence.append(EvidenceItem(text=passage.text,document=str(meta["document_name"]),page=int(meta["page_number"]),section=str(meta.get("section", "")),passage_id=passage.id,document_id=str(meta["document_id"]),version=version,effective_date=str(meta.get("effective_date", "")),academic_year=str(meta.get("academic_year", "")),verification_status=str(meta.get("verification_status", "unverified"))))
            key=(str(meta["document_id"]),str(meta["document_name"]),version)
            source=sources.setdefault(key,{"document":key[1],"document_id":key[0],"document_type":str(meta.get("document_type","")),"pages":[],"sections":[],"academic_year":str(meta.get("academic_year","")),"version":version,"effective_date":str(meta.get("effective_date","")),"source_type":str(meta.get("source_type","")),"verification_status":str(meta.get("verification_status","unverified"))})
            if int(meta["page_number"]) not in source["pages"]: source["pages"].append(int(meta["page_number"]))
            if meta.get("section") and meta["section"] not in source["sections"]: source["sections"].append(str(meta["section"]))
        status=AnswerStatus.SUPPORTED
        numbers=set(re.findall(r"\d+(?:\.\d+)?", " ".join(x[2] for x in chosen)))
        if "agree" in retrieval.question.casefold() and len(numbers)>1 and len({x[1].metadata.get("document_id") for x in chosen})>1:
            status=AnswerStatus.CONFLICTING_SOURCES
        answer=StructuredAnswer(answer=" ".join(statements),evidence=evidence,sources=[SourceItem(**v) for v in sources.values()],status=status)
        return GenerationRecord(answer,self.model,PromptType.C)

