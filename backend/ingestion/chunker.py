from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

_embeddings: HuggingFaceEmbeddings | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
    return _embeddings


def chunk_document(text: str) -> list[str]:
    splitter = SemanticChunker(
        _get_embeddings(),
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=95,
    )
    docs = splitter.create_documents([text])
    return [doc.page_content for doc in docs if doc.page_content.strip()]
