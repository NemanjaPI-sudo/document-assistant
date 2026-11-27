
import json
import sys
import time
from pathlib import Path

# Allow imports from the backend directory.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from database import get_documents
from llm import generate_answer
from rag import SYSTEM_INSTRUCTIONS, build_prompt, prepare_sources, validate_answer
from retrieval import retrieve_chunks

EVALUATION_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = EVALUATION_DIR / "questions.json"
RESULTS_PATH = EVALUATION_DIR / "results.json"


def load_questions() -> list[dict]:
    """Load questions from the evaluation dataset."""

    return json.loads(
        QUESTIONS_PATH.read_text(encoding="utf-8")
    )


def get_document_ids(
    filenames: list[str],
    documents: list[dict]
) -> list[str]:
    """Resolve document filenames to database identifiers."""

    document_ids = []

    for filename in filenames:
        matches = [
            document for document in documents
            if document["filename"] == filename
            and document["status"] == "ready"
        ]

        if not matches:
            raise ValueError(
                f"Ready document not found: {filename}"
            )

        if len(matches) > 1:
            raise ValueError(
                f"Multiple documents found: {filename}"
            )

        document_ids.append(matches[0]["id"])

    return document_ids


def get_source_keys(sources: list[dict]) -> set:
    """Convert source metadata into comparable filename-page pairs."""

    return {
        (source["filename"], source["page_number"])
        for source in sources
    }


def calculate_recall(
    expected_sources: list[dict],
    retrieved_chunks: list[dict]
) -> float | None:
    """Calculate the fraction of expected pages that were retrieved."""

    expected = get_source_keys(expected_sources)
    retrieved = get_source_keys(retrieved_chunks)

    if not expected:
        return None

    return len(expected & retrieved) / len(expected)


def extract_citations(answer: dict) -> list[dict]:
    """Collect citations from all validated claims."""

    citations = []

    for claim in answer.get("claims", []):
        citations.extend(claim.get("citations", []))

    return citations


def check_citations(
    citations: list[dict],
    chunks: list[dict]
) -> bool | None:
    """Check citations against the original retrieved chunks."""

    if not citations:
        return None

    chunks_by_id = {
        chunk["chunk_id"]: chunk
        for chunk in chunks
    }

    for citation in citations:
        chunk = chunks_by_id.get(citation["chunk_id"])

        if chunk is None:
            return False

        if not citation["quote"].strip():
            return False

        if citation["quote"] not in chunk["content"]:
            return False

        if citation["document_id"] != chunk["document_id"]:
            return False

        if citation["filename"] != chunk["filename"]:
            return False

        if citation["page_number"] != chunk["page_number"]:
            return False

    return True


def evaluate_question(
    item: dict,
    documents: list[dict]
) -> dict:
    """Evaluate retrieval, generation and citation validation."""

    question = item["question"]

    document_ids = get_document_ids(
        item["documents"],
        documents
    )

    start_time = time.perf_counter()

    # Measure semantic retrieval.
    retrieval_start = time.perf_counter()

    chunks = retrieve_chunks(
        question,
        document_ids=document_ids
    )

    retrieval_time = time.perf_counter() - retrieval_start

    raw_answer = {
        "status": "insufficient_information",
        "claims": []
    }

    generation_time = 0.0

    # Generate an answer only when sources are available.
    if chunks:
        sources = prepare_sources(chunks)
        prompt = build_prompt(question, sources)

        generation_start = time.perf_counter()

        raw_answer = generate_answer(
            SYSTEM_INSTRUCTIONS,
            prompt
        )

        generation_time = (
            time.perf_counter() - generation_start
        )

        answer = validate_answer(
            raw_answer,
            sources
        )
    else:
        answer = raw_answer

    total_time = time.perf_counter() - start_time

    citations = extract_citations(answer)

    # Compare retrieved pages with expected source pages.
    retrieval_recall = calculate_recall(
        item["expected_sources"],
        chunks
    )

    # Check whether expected pages were actually cited.
    expected_sources = get_source_keys(
        item["expected_sources"]
    )

    cited_sources = get_source_keys(citations)

    source_match = None

    if expected_sources:
        source_match = expected_sources.issubset(
            cited_sources
        )

    # Determine whether validation rejected a generated answer.
    validation_rejected = (
        raw_answer.get("status") == "answered"
        and answer["status"] != "answered"
    )

    return {
        "id": item["id"],
        "category": item["category"],
        "question": question,
        "documents": item["documents"],
        "expected_status": item["expected_status"],
        "actual_status": answer["status"],
        "raw_status": raw_answer.get("status"),
        "status_correct": (
            answer["status"] == item["expected_status"]
        ),
        "retrieval_recall": retrieval_recall,
        "expected_sources_cited": source_match,
        "citations_valid": check_citations(
            citations,
            chunks
        ),
        "validation_rejected": validation_rejected,
        "retrieved_chunks": len(chunks),
        "retrieval_time_seconds": round(
            retrieval_time, 3
        ),
        "generation_time_seconds": round(
            generation_time, 3
        ),
        "total_time_seconds": round(
            total_time, 3
        ),
        "expected_answer": item["expected_answer"],
        "actual_answer": answer,
        "raw_answer": raw_answer,
        "retrieved_sources": [
            {
                "filename": chunk["filename"],
                "page_number": chunk["page_number"],
                "similarity": chunk["similarity"]
            }
            for chunk in chunks
        ],
        "manual_answer_correctness": None
    }


def calculate_average(values: list) -> float | None:
    """Calculate an average while ignoring unavailable values."""

    valid_values = [
        value for value in values
        if value is not None
    ]

    if not valid_values:
        return None

    return round(
        sum(valid_values) / len(valid_values),
        4
    )


def build_summary(results: list[dict]) -> dict:
    """Calculate aggregate evaluation metrics."""

    completed = [
        result for result in results
        if "error" not in result
    ]

    return {
        "total_questions": len(results),
        "completed_questions": len(completed),
        "failed_executions": (
            len(results) - len(completed)
        ),
        "status_accuracy": calculate_average([
            result["status_correct"]
            for result in completed
        ]),
        "retrieval_recall_at_8": calculate_average([
            result["retrieval_recall"]
            for result in completed
        ]),
        "expected_source_accuracy": calculate_average([
            result["expected_sources_cited"]
            for result in completed
        ]),
        "citation_validity": calculate_average([
            result["citations_valid"]
            for result in completed
        ]),
        "validation_rejections": sum(
            result["validation_rejected"]
            for result in completed
        ),
        "average_response_time_seconds": calculate_average([
            result["total_time_seconds"]
            for result in completed
        ])
    }


def main():
    """Run the complete evaluation and save the report."""

    questions = load_questions()

    # Retrieve available documents directly from the database.
    documents = get_documents()

    results = []

    print("\nDocument Assistant Evaluation")
    print("=" * 50)

    for item in questions:
        print(
            f"\n[{item['id']}] {item['question']}"
        )

        try:
            result = evaluate_question(
                item,
                documents
            )

            results.append(result)

            status = (
                "PASS"
                if result["status_correct"]
                else "FAIL"
            )

            print(f"Status check: {status}")
            print(
                f"Expected: {result['expected_status']}"
            )
            print(
                f"Actual: {result['actual_status']}"
            )
            print(
                f"Raw status: {result['raw_status']}"
            )
            print(
                f"Recall: {result['retrieval_recall']}"
            )
            print(
                f"Citations valid: "
                f"{result['citations_valid']}"
            )
            print(
                f"Validation rejected: "
                f"{result['validation_rejected']}"
            )
            print(
                f"Response time: "
                f"{result['total_time_seconds']}s"
            )
# Continue evaluation if an individual question fails.
        except Exception as error:# noqa: BLE001
            results.append({
                "id": item["id"],
                "question": item["question"],
                "error": str(error)
            })

            print(f"ERROR: {error}")

    summary = build_summary(results)

    report = {
        "summary": summary,
        "results": results
    }

    RESULTS_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("\n" + "=" * 50)
    print("Evaluation summary")
    print("=" * 50)

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2
        )
    )

    print(f"\nResults saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
