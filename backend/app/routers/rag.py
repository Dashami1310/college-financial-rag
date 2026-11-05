import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.rag_pipeline import answer_question, load_vectorstore, build_vectorstore_for_user
from app.services.query_classifier import classify_query
from app.services.data_processing import records_to_dataframe

router = APIRouter(prefix="/api/rag", tags=["RAG Financial Assistant"])


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Ensure a per-user vector index exists (lazily build if needed, e.g.
    # after a fresh server restart where the in-memory cache is empty but
    # data exists). Every user's index is fully isolated from every other
    # user's, and now spans BOTH structured transactions and section-aware
    # PDF audit-report chunks — see rag_pipeline.build_vectorstore_for_user.
    query_type = classify_query(payload.question)
    if query_type != "unsupported" and load_vectorstore(current_user.id) is None:
        try:
            build_vectorstore_for_user(db, user_id=current_user.id)
        except Exception as e:
            # Non-fatal: the SQL half of the hybrid pipeline (and the
            # extractive fallback) still work without a vector index —
            # retrieve_context() will simply return no narrative sources.
            print(f"[WARN] Vector store build failed for user {current_user.id}: {e}")

    # SQL+RAG hybrid: pass the user's transaction ledger so numeric
    # questions ("What is total income?") get an exact computed answer
    # instead of an LLM guess, combined with retrieved narrative context.
    txn_df = (
        records_to_dataframe(db, user_id=current_user.id, report_id=payload.report_id)
        if query_type != "unsupported"
        else None
    )

    result = answer_question(payload.question, user_id=current_user.id, transactions_df=txn_df)

    db.add(models.ChatHistory(
        user_email=current_user.email,
        report_id=payload.report_id,
        question=result["question"],
        answer=result["answer"],
        sources=json.dumps(result["sources"]),
        query_type=result["query_type"],
    ))
    db.commit()

    return schemas.ChatResponse(**result)


@router.get("/history")
def chat_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.ChatHistory)
        .filter(models.ChatHistory.user_email == current_user.email)
        .order_by(models.ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "created_at": r.created_at,
        }
        for r in reversed(rows)
    ]


@router.post("/reindex")
def reindex(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Manually rebuilds the FAISS vector index for the current user,
    combining their transactions and audit-report chunks."""
    vs = build_vectorstore_for_user(db, user_id=current_user.id)
    if vs is None:
        return {"status": "no_data", "documents_indexed": 0}
    return {"status": "ok"}
