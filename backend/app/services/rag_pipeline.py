from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Any

import pandas as pd

from app.config import settings, VECTORSTORE_DIR

# NOTE: langchain / faiss / sentence-transformers are intentionally imported
# lazily (inside functions) rather than at module load time. This keeps the
# rest of the FastAPI app (auth, dashboard, analytics, anomaly, forecasting,
# reports) fully functional even in environments where the heavier RAG
# dependencies haven't been installed yet, and gives clearer error messages
# when a RAG endpoint is actually invoked without them.

_EMBEDDINGS = None
# Cache is keyed by user_id — every user gets their own FAISS index on disk
# and in memory, so one user's RAG assistant can never retrieve another
# user's financial data (report ownership is enforced all the way down to
# the vector store, not just at the API layer).
_VECTORSTORE_CACHE: Dict[int, Any] = {}


def _index_path_for_user(user_id: int) -> Path:
    path = VECTORSTORE_DIR / f"user_{user_id}" / "faiss_index"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_embeddings():
    """Lazily loads the Sentence-Transformers embedding model (all-MiniLM-L6-v2)."""
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        _EMBEDDINGS = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    return _EMBEDDINGS


# ---------------------------------------------------------------------------
# 1. Document construction — turns structured rows into retrievable text
# ---------------------------------------------------------------------------
def build_documents_from_transactions(df: pd.DataFrame) -> List:
    from langchain_core.documents import Document
    docs: List[Document] = []

    # Per-record narrative chunks
    for _, row in df.iterrows():
        text = (
            f"In financial year {row['financial_year']}, {row['quarter']}, the "
            f"{row['department']} department was allocated a budget of "
            f"₹{row['budget_allocated']:.0f} and spent ₹{row['actual_expenditure']:.0f} "
            f"({(row['actual_expenditure'] / row['budget_allocated'] * 100) if row['budget_allocated'] else 0:.1f}% utilization), "
            f"leaving a remaining budget of ₹{row['remaining_budget']:.0f}. "
            f"The major expense head was '{row.get('major_expense_head') or 'General'}' "
            f"handled through vendor '{row.get('vendor') or 'N/A'}' across "
            f"{row.get('number_of_transactions', 0)} transactions. "
            f"Approval status: {row.get('approval_status', 'Approved')}. "
            + ("This record was flagged as an anomaly." if row.get("anomalies_detected") else "")
        )
        docs.append(Document(
            page_content=text,
            metadata={
                "type": "record",
                "department": row["department"],
                "financial_year": row["financial_year"],
                "quarter": row["quarter"],
            },
        ))

    # Department-level aggregate summaries (helps with comparison questions)
    if not df.empty:
        dept_summary = df.groupby("department").agg(
            total_budget=("budget_allocated", "sum"),
            total_expenditure=("actual_expenditure", "sum"),
            avg_utilization=("actual_expenditure", "mean"),
        ).reset_index()
        for _, row in dept_summary.iterrows():
            text = (
                f"Overall summary for {row['department']} department across all uploaded records: "
                f"total budget allocated ₹{row['total_budget']:.0f}, total actual expenditure "
                f"₹{row['total_expenditure']:.0f}, average per-record expenditure ₹{row['avg_utilization']:.0f}."
            )
            docs.append(Document(
                page_content=text,
                metadata={"type": "department_summary", "department": row["department"]},
            ))

        # Quarter-level summaries (helps with "which quarter had max spending")
        q_summary = df.groupby(["financial_year", "quarter"]).agg(
            total_expenditure=("actual_expenditure", "sum"),
            total_budget=("budget_allocated", "sum"),
        ).reset_index()
        for _, row in q_summary.iterrows():
            text = (
                f"In {row['financial_year']} {row['quarter']}, the institution's total expenditure "
                f"across all departments was ₹{row['total_expenditure']:.0f} against a total budget of "
                f"₹{row['total_budget']:.0f}."
            )
            docs.append(Document(
                page_content=text,
                metadata={"type": "quarter_summary", "financial_year": row["financial_year"], "quarter": row["quarter"]},
            ))

    return docs


# Backward-compatible alias — earlier callers used the shorter name
build_documents = build_documents_from_transactions


def build_documents_from_audit_chunks(chunks: List) -> List:
    """
    Converts persisted `AuditChunk` rows (from the PDF section-aware
    chunking pipeline — see services/pdf_processing.py) into LangChain
    Documents for embedding. Each chunk already carries its section and
    year, which are preserved as retrieval metadata so the RAG assistant
    can cite "Balance Sheet, FY2025-2026" style sources.
    """
    from langchain_core.documents import Document
    docs: List[Document] = []
    for chunk in chunks:
        header = f"[{chunk.section or 'General'}"
        if chunk.year:
            header += f" — FY {chunk.year}"
        header += "]"
        text = f"{header}\n{chunk.chunk_text}"
        docs.append(Document(
            page_content=text,
            metadata={
                "type": "audit_chunk",
                "report_id": chunk.report_id,
                "section": chunk.section,
                "year": chunk.year,
                "chunk_index": chunk.chunk_index,
            },
        ))
    return docs


# ---------------------------------------------------------------------------
# 2. Chunking + Vector store build
# ---------------------------------------------------------------------------
def build_vectorstore_for_user(db, user_id: int):
    """
    Master rebuild entry point: assembles documents from BOTH of a user's
    data sources — structured CSV/Excel transactions AND section-aware
    chunks from uploaded PDF audit reports — into one combined FAISS index.
    This is what every upload/delete endpoint should call after Phase 2,
    so a single RAG chat can answer questions spanning a user's whole
    report history regardless of source format.
    """
    from app import models
    from app.services.data_processing import records_to_dataframe

    txn_df = records_to_dataframe(db, user_id=user_id)
    txn_docs = build_documents_from_transactions(txn_df)

    audit_chunks = (
        db.query(models.AuditChunk)
        .join(models.Report, models.AuditChunk.report_id == models.Report.id)
        .filter(models.Report.user_id == user_id)
        .all()
    )
    audit_docs = build_documents_from_audit_chunks(audit_chunks)

    return _build_vectorstore_from_documents(txn_docs + audit_docs, user_id)


def build_vectorstore(df: pd.DataFrame, user_id: int):
    """Legacy entry point: builds the index from a transactions DataFrame
    only (no audit chunks). Kept for callers that don't have a `db` session
    handy; prefer `build_vectorstore_for_user` where possible so PDF-derived
    content is included too."""
    documents = build_documents_from_transactions(df)
    return _build_vectorstore_from_documents(documents, user_id)


def _build_vectorstore_from_documents(documents: List, user_id: int):
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    index_path = _index_path_for_user(user_id)

    if not documents:
        # Nothing to index yet (e.g. user has no reports) — clear any cache
        # entry but don't error; retrieve_context will just return [].
        _VECTORSTORE_CACHE.pop(user_id, None)
        return None

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(documents)

    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(str(index_path))

    _VECTORSTORE_CACHE[user_id] = vectorstore
    return vectorstore


def load_vectorstore(user_id: int):
    if user_id in _VECTORSTORE_CACHE:
        return _VECTORSTORE_CACHE[user_id]
    index_path = _index_path_for_user(user_id)
    if (index_path / "index.faiss").exists():
        from langchain_community.vectorstores import FAISS
        embeddings = get_embeddings()
        vs = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
        _VECTORSTORE_CACHE[user_id] = vs
        return vs
    return None


# ---------------------------------------------------------------------------
# 3. Retrieval + Generation
# ---------------------------------------------------------------------------
def retrieve_context(query: str, user_id: int, k: int = None) -> List:
    vs = load_vectorstore(user_id)
    if vs is None:
        return []
    k = k or settings.TOP_K
    return vs.similarity_search(query, k=k)


AUDITOR_PROMPT_TEMPLATE = """You are an expert Financial Analytics Assistant.

Always answer using exact figures from the uploaded dataset.

If the user asks:
- highest expenditure
- lowest expenditure
- department comparison
- budget utilization
- anomalies
- forecasts

provide department names, amounts, percentages and rankings.

Never give generic answers.
Always cite numerical values from the retrieved data.

Answer strictly using the uploaded audit reports and the financial figures \
provided below. Do not hallucinate. Do not invent financial figures.

Structure your response with these exact five sections:

1. Direct Answer
2. Supporting Financial Figures
3. Financial Analysis
4. Risk Indicators
5. Conclusion

If a section has nothing relevant to report, state that plainly (e.g.
"No risk indicators identified in the available data") rather than
inventing content for it.

Computed Financial Figures (from the transaction ledger, if applicable):
{sql_figures}

Retrieved Audit Report / Transaction Context:
{context}

Question: {question}

Auditor's Response:"""

# Kept as an alias in case anything still references the pre-Phase-3 name
PROMPT_TEMPLATE = AUDITOR_PROMPT_TEMPLATE


def _generate_with_gemini(question: str, context: str, sql_figures: str = "None computed for this question.") -> str:
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,
    )
    prompt = AUDITOR_PROMPT_TEMPLATE.format(context=context, question=question, sql_figures=sql_figures)
    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


def _generate_fallback(question: str, context_docs: List, sql_figures: str = "") -> str:
    """
    Concise extractive fallback for deployments without a Gemini API key.
    """
    has_figures = bool(sql_figures and sql_figures != "None computed for this question.")
    has_context = bool(context_docs)

    if not has_figures and not has_context:
        return (
            "1. Direct Answer\n"
            "I couldn't find relevant financial data to answer that question.\n\n"
            "2. Supporting Financial Figures\nNone available.\n\n"
            "3. Financial Analysis\nNot applicable — no data retrieved.\n\n"
            "4. Risk Indicators\nNot applicable.\n\n"
            "5. Conclusion\nPlease upload a report first, or configure GOOGLE_API_KEY "
            "for full AI-generated analysis."
        )

    parts = []
    if has_figures:
        parts.append(sql_figures)
    if has_context:
        excerpts = "\n".join(f"- {doc.page_content}" for doc in context_docs[:3])
        parts.append(f"Relevant uploaded-report excerpts:\n{excerpts}")
    parts.append(
        "This is an extractive response. Configure GOOGLE_API_KEY for AI-generated explanations."
    )
    return "\n\n".join(parts)


def answer_question(question: str, user_id: int, transactions_df: Optional[pd.DataFrame] = None) -> Dict:
    """
    Phase 3 SQL + RAG hybrid entry point.

    1. Classifies the question (sql / rag / hybrid) via query_classifier.
    2. If numeric intent is present, computes exact figures from the
       transaction ledger via sql_query_engine (never left to the LLM to
       "guess" a number).
    3. Uses deterministic answers for financial calculations and summaries.
    4. Retrieves narrative context for qualitative questions and uses Gemini
       when configured, otherwise returning a concise extractive response.
    """
    from app.services.query_classifier import classify_query
    from app.services.sql_query_engine import answer_sql_question

    query_type = classify_query(question)
    if query_type == "unsupported":
        return {
            "answer": (
                "I can only answer questions about your uploaded college financial "
                "data and audit reports. Please ask a finance-related question."
            ),
            "sources": [],
            "question": question,
            "query_type": query_type,
            "generation_mode": "out_of_scope",
        }

    has_transactions = transactions_df is not None and not transactions_df.empty

    if query_type == "sql":
        if not has_transactions:
            answer = "There are no uploaded financial records available to answer this question."
        else:
            answer = answer_sql_question(question, transactions_df)["narrative"]
        return {
            "answer": answer,
            "sources": [],
            "question": question,
            "query_type": query_type,
            "generation_mode": "calculated",
        }

    if (
        has_transactions
        and re.search(r"\b(summarize|summarise|summary|overview)\b", question, re.IGNORECASE)
    ):
        summary = answer_sql_question(question, transactions_df)
        if summary["figures"]:
            return {
                "answer": summary["narrative"],
                "sources": [],
                "question": question,
                "query_type": query_type,
                "generation_mode": "calculated",
            }

    sql_narrative = "None computed for this question."
    if has_transactions:
        sql_result = answer_sql_question(question, transactions_df)
        if sql_result["figures"]:
            sql_narrative = sql_result["narrative"]

    context_docs = retrieve_context(question, user_id=user_id, k=10)
    context_text = "\n".join(d.page_content for d in context_docs) or "No matching audit report or transaction context retrieved."

    generation_mode = "extractive"
    if settings.GOOGLE_API_KEY:
        try:
            answer = _generate_with_gemini(question, context_text, sql_narrative)
            generation_mode = "gemini"
        except Exception as e:  # pragma: no cover - network/key issues
            print(f"[WARN] Gemini generation failed; using retrieved context: {e}")
            answer = _generate_fallback(question, context_docs, sql_narrative)
    else:
        answer = _generate_fallback(question, context_docs, sql_narrative)

    sources = [
        {"content": d.page_content, "metadata": d.metadata} for d in context_docs
    ]
    return {
        "answer": answer,
        "sources": sources,
        "question": question,
        "query_type": query_type,
        "generation_mode": generation_mode,
    }
