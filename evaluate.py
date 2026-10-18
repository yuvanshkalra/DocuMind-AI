import asyncio
import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from ragas import SingleTurnSample
from ragas.metrics import Faithfulness, ContextPrecision

load_dotenv()

# ---------------------------------------------------------------------------
# Mock test case
# ---------------------------------------------------------------------------

sample = SingleTurnSample(
    user_input="What are the main benefits of retrieval-augmented generation?",
    response=(
        "Retrieval-augmented generation (RAG) improves LLM accuracy by grounding "
        "responses in external documents [Page 1]. It reduces hallucinations because "
        "the model is constrained to verified source material [Page 2]. It also allows "
        "knowledge to be updated without retraining the model [Page 3]."
    ),
    retrieved_contexts=[
        # Page 1
        "Retrieval-augmented generation (RAG) is a technique that enhances large "
        "language models by retrieving relevant documents from an external knowledge "
        "base before generating a response. This grounding in real source material "
        "significantly improves factual accuracy.",
        # Page 2
        "One of the primary advantages of RAG systems is the reduction of "
        "hallucinations. Because the model generates answers based on retrieved "
        "context rather than relying solely on parametric memory, fabricated or "
        "incorrect facts are less likely to appear in the output.",
        # Page 3
        "Unlike fine-tuning, RAG does not require the underlying language model to "
        "be retrained when new information becomes available. The knowledge base can "
        "be updated independently, making RAG a cost-effective solution for "
        "keeping AI systems current.",
    ],
)

# ---------------------------------------------------------------------------
# Judge model
# ---------------------------------------------------------------------------

judge_llm = ChatOllama(
    model="llama3.2",
    temperature=0,
)

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

faithfulness = Faithfulness(llm=judge_llm)       # hallucination check
context_precision = ContextPrecision(llm=judge_llm)  # retrieval accuracy


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

async def evaluate() -> None:
    faith_score = await faithfulness.single_turn_ascore(sample)
    precision_score = await context_precision.single_turn_ascore(sample)

    print("=" * 45)
    print("        DocuMind AI — Ragas Evaluation")
    print("=" * 45)
    print(f"  Faithfulness      (0–1, higher = less hallucination): {faith_score:.4f}")
    print(f"  Context Precision (0–1, higher = better retrieval)  : {precision_score:.4f}")
    print("=" * 45)


if __name__ == "__main__":
    asyncio.run(evaluate())
