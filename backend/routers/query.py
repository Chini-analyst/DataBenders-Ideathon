import time

from fastapi import APIRouter

from models.query import QueryRequest, QueryResponse
from services.llm import generate_answer
from services.retrieval import retrieve

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query_knowledge_base(request: QueryRequest):
    total_start = time.perf_counter()

    # Retrieve relevant sources
    sources, retrieval_ms = retrieve(
        query=request.question,
        mode=request.mode,
        top_k=request.top_k,
        doc_filter=request.doc_filter,
    )

    # Generate answer
    answer, generation_ms = generate_answer(request.question, sources)

    total_ms = (time.perf_counter() - total_start) * 1000

    return QueryResponse(
        question=request.question,
        answer=answer,
        sources=sources,
        mode=request.mode,
        retrieval_time_ms=round(retrieval_ms, 1),
        generation_time_ms=round(generation_ms, 1),
        total_time_ms=round(total_ms, 1),
    )
