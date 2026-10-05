"""Phase 5 contextual retrieval package for incident triage evidence.

Provides leakage-safe historical log retrieval infrastructure strictly over the TRAIN partition,
integrated with the Phase 4 split-conformal selective gate.
"""

from sentinellog.retrieval.chunking import (
    build_query_from_window,
    build_retrieval_chunk,
    build_retrieval_corpus,
    compute_chunk_id,
    format_template_tokens,
)
from sentinellog.retrieval.embeddings import (
    BaseEmbeddingModel,
    TemplateTfidfEmbeddingModel,
)
from sentinellog.retrieval.engine import (
    IncidentRetriever,
    batch_cosine_similarities,
    cosine_similarity,
)
from sentinellog.retrieval.gated import GatedRetrievalPipeline
from sentinellog.retrieval.guards import (
    InvalidSplitError,
    LabelLeakageError,
    guard_no_label_in_text,
    guard_query_does_not_contain_labels,
    guard_train_split_only,
)
from sentinellog.retrieval.schemas import (
    GatedRetrievalResult,
    RetrievalChunk,
    RetrievalQuery,
    RetrievedEvidence,
)

__all__ = [
    "InvalidSplitError",
    "LabelLeakageError",
    "guard_train_split_only",
    "guard_no_label_in_text",
    "guard_query_does_not_contain_labels",
    "RetrievalChunk",
    "RetrievalQuery",
    "RetrievedEvidence",
    "GatedRetrievalResult",
    "format_template_tokens",
    "compute_chunk_id",
    "build_retrieval_chunk",
    "build_retrieval_corpus",
    "build_query_from_window",
    "BaseEmbeddingModel",
    "TemplateTfidfEmbeddingModel",
    "cosine_similarity",
    "batch_cosine_similarities",
    "IncidentRetriever",
    "GatedRetrievalPipeline",
]
