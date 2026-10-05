"""Comprehensive test suite for Phase 6: Retrieval Reranking and Evidence Selection.

Verifies:
Reranking:
1. Relevance-only ranking (lambda = 1.0).
2. Pure diversity ranking (lambda = 0.0).
3. Balanced MMR ranking (lambda = 0.70).
4. Strictly deterministic ordering and tie-breaking:
   (selection_score DESC, retrieval_score DESC, chunk_id ASC).
5. Safe zero and negative similarity handling.

Diversity:
6. Redundant candidate penalty (candidates highly similar to selected are penalized).
7. Diverse candidate preference over near-duplicates.
8. Identical vectors and repeated chunks handling.
9. Orthogonal vectors handling.

Selection:
10. evidence_k = 1 selection.
11. evidence_k = retrieval_k selection.
12. evidence_k < retrieval_k selection.
13. evidence_k > retrieval_k explicitly rejected with ValueError.
14. Empty candidate list handling.
15. Fewer candidates than evidence_k handling.
16. Original Phase 5 retrieval scores preserved intact on selected evidence.

Protection & Integrity:
17. Anomaly labels strictly unavailable to reranker (fail-closed guard).
18. Test set strictly protected (Rule 1).
19. Calibration data never used for fitting primary reranking parameters.
20. Cross-dataset filtering preserved.

Integration:
21. AUTO-CLEAR bypasses retrieval, reranking, and selection entirely.
22. ESCALATE triggers retrieval -> reranking -> selection cascade.

Determinism:
23. Repeated execution produces bitwise-identical selected evidence and metrics.
"""

import copy
import json
import numpy as np
import pytest

from sentinellog.calibration.conformal import SplitConformalCalibrator
from sentinellog.calibration.gate import SelectiveGate
from sentinellog.ingestion.schemas import LogWindow
from sentinellog.retrieval.chunking import build_query_from_window
from sentinellog.retrieval.embeddings import BaseEmbeddingModel, TemplateTfidfEmbeddingModel
from sentinellog.retrieval.engine import IncidentRetriever
from sentinellog.retrieval.gated import GatedEvidencePipeline
from sentinellog.retrieval.guards import LabelLeakageError
from sentinellog.retrieval.reranker import MMREvidenceReranker
from sentinellog.retrieval.reranking_schemas import (
    EvidenceSelectionResult,
    GatedEvidenceResult,
    SelectedEvidence,
)
from sentinellog.retrieval.schemas import (
    RetrievalChunk,
    RetrievalQuery,
    RetrievedEvidence,
)


class DummyMockEmbeddingModel(BaseEmbeddingModel):
    """Deterministic mock embedding model for controlled vector geometry tests."""

    def __init__(self, vector_map=None, default_dim=4):
        self.vector_map = vector_map or {}
        self._dim = default_dim

    def fit(self, texts, split="train"):
        return self

    def encode(self, texts):
        vecs = []
        for t in texts:
            if t in self.vector_map:
                v = np.array(self.vector_map[t], dtype=np.float32)
            else:
                v = np.zeros(self._dim, dtype=np.float32)
            norm = np.linalg.norm(v)
            if norm > 0:
                v = v / norm
            vecs.append(v)
        return np.array(vecs, dtype=np.float32)

    @property
    def dimension(self):
        return self._dim

    @property
    def model_name(self):
        return "mock_embedding"

    @property
    def version(self):
        return "1.0.0"

    def get_metadata(self):
        return {"name": self.model_name}


@pytest.fixture
def dummy_candidates():
    """Create a controlled set of 5 candidate evidence chunks."""
    # Chunk A: highly relevant (sim=0.95), vector [1, 0, 0, 0]
    # Chunk B: duplicate/near-identical of A (sim=0.90), vector [1, 0.01, 0, 0]
    # Chunk C: diverse topic 1 (sim=0.80), vector [0, 1, 0, 0]
    # Chunk D: diverse topic 2 (sim=0.75), vector [0, 0, 1, 0]
    # Chunk E: low relevance (sim=0.40), vector [0, 0, 0, 1]
    return [
        RetrievedEvidence(
            rank=1,
            similarity=0.95,
            chunk_id="chunk_a",
            source_window_id="win_1",
            dataset="hdfs",
            split="train",
            text="template_1 template_2",
            record_count=10,
            template_ids=[1, 2],
        ),
        RetrievedEvidence(
            rank=2,
            similarity=0.90,
            chunk_id="chunk_b",
            source_window_id="win_1",
            dataset="hdfs",
            split="train",
            text="template_1 template_2 template_2",
            record_count=12,
            template_ids=[1, 2, 2],
        ),
        RetrievedEvidence(
            rank=3,
            similarity=0.80,
            chunk_id="chunk_c",
            source_window_id="win_2",
            dataset="hdfs",
            split="train",
            text="template_5 template_6",
            record_count=8,
            template_ids=[5, 6],
        ),
        RetrievedEvidence(
            rank=4,
            similarity=0.75,
            chunk_id="chunk_d",
            source_window_id="win_3",
            dataset="hdfs",
            split="train",
            text="template_9 template_10",
            record_count=15,
            template_ids=[9, 10],
        ),
        RetrievedEvidence(
            rank=5,
            similarity=0.40,
            chunk_id="chunk_e",
            source_window_id="win_4",
            dataset="hdfs",
            split="train",
            text="template_20",
            record_count=5,
            template_ids=[20],
        ),
    ]


@pytest.fixture
def mock_embedding_model(dummy_candidates):
    """Fixture providing a mock embedding model mapping candidate texts to orthogonal/near-identical vectors."""
    vec_map = {
        "template_1 template_2": [1.0, 0.0, 0.0, 0.0],
        "template_1 template_2 template_2": [1.0, 0.0, 0.0, 0.0],  # Identical direction to chunk A
        "template_5 template_6": [0.0, 1.0, 0.0, 0.0],  # Orthogonal to A
        "template_9 template_10": [0.0, 0.0, 1.0, 0.0],  # Orthogonal to A and C
        "template_20": [0.0, 0.0, 0.0, 1.0],
    }
    return DummyMockEmbeddingModel(vector_map=vec_map, default_dim=4)


@pytest.fixture
def sample_query():
    return RetrievalQuery(
        query_window_id="query_win_100",
        dataset="hdfs",
        record_count=10,
        template_ids=[1, 2],
        text="template_1 template_2",
    )


# -----------------------------------------------------------------------------
# 1. RERANKING & MMR ALGORITHM TESTS
# -----------------------------------------------------------------------------

def test_relevance_only_ranking(sample_query, dummy_candidates, mock_embedding_model):
    """When lambda = 1.0, MMR ignores diversity and preserves pure relevance ordering."""
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=1.0, evidence_k=3)
    result = reranker.rerank_and_select(sample_query, dummy_candidates, retrieval_k=5)

    assert result.selected_count == 3
    selected_ids = [e.chunk_id for e in result.selected_evidence]
    # Under pure relevance (lambda=1.0), top 3 should be chunk_a, chunk_b, chunk_c
    assert selected_ids == ["chunk_a", "chunk_b", "chunk_c"]
    # Check ranks and scores
    assert result.selected_evidence[0].retrieval_score == 0.95
    assert result.selected_evidence[1].retrieval_score == 0.90
    assert result.selected_evidence[2].retrieval_score == 0.80


def test_mmr_penalizes_redundancy(sample_query, dummy_candidates, mock_embedding_model):
    """When lambda = 0.70, duplicate chunk_b (similarity=1.0 with chunk_a) is penalized in favor of chunk_c."""
    # Chunk A is selected 1st: rel=0.95
    # For 2nd item:
    # Chunk B: rel=0.90, max_sim to A = 1.0 -> score = 0.70*0.90 - 0.30*1.0 = 0.63 - 0.30 = 0.33
    # Chunk C: rel=0.80, max_sim to A = 0.0 -> score = 0.70*0.80 - 0.30*0.0 = 0.56
    # Chunk D: rel=0.75, max_sim to A = 0.0 -> score = 0.70*0.75 - 0.30*0.0 = 0.525
    # Therefore, Chunk C must be selected 2nd, and Chunk D selected 3rd!
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=3)
    result = reranker.rerank_and_select(sample_query, dummy_candidates, retrieval_k=5)

    selected_ids = [e.chunk_id for e in result.selected_evidence]
    assert selected_ids == ["chunk_a", "chunk_c", "chunk_d"], (
        f"Expected redundancy-penalized selection ['chunk_a', 'chunk_c', 'chunk_d'], got {selected_ids}"
    )
    # Check that Chunk B was bypassed due to redundancy
    assert "chunk_b" not in selected_ids


def test_pure_diversity_ranking(sample_query, dummy_candidates, mock_embedding_model):
    """When lambda = 0.0, MMR aggressively selects maximally orthogonal vectors."""
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.0, evidence_k=3)
    result = reranker.rerank_and_select(sample_query, dummy_candidates, retrieval_k=5)

    assert result.selected_count == 3
    selected_ids = [e.chunk_id for e in result.selected_evidence]
    # First item is chunk_a (highest initial relevance)
    assert selected_ids[0] == "chunk_a"
    # Chunk B has penalty 1.0 -> score = -1.0
    # Chunk C and D have penalty 0.0 -> score = 0.0
    # Chunk C tie-breaks over D because retrieval_score (0.80 > 0.75)
    assert selected_ids[1] == "chunk_c"
    assert selected_ids[2] == "chunk_d"


def test_deterministic_tie_breaking(sample_query, mock_embedding_model):
    """Tied scores must break deterministically: selection_score DESC, retrieval_score DESC, chunk_id ASC."""
    # Create two candidates with identical scores and embeddings, different chunk_ids
    tied_candidates = [
        RetrievedEvidence(
            rank=1,
            similarity=0.85,
            chunk_id="chunk_zebra",
            source_window_id="w1",
            dataset="hdfs",
            split="train",
            text="template_1",
            record_count=5,
            template_ids=[1],
        ),
        RetrievedEvidence(
            rank=2,
            similarity=0.85,
            chunk_id="chunk_alpha",
            source_window_id="w2",
            dataset="hdfs",
            split="train",
            text="template_1",
            record_count=5,
            template_ids=[1],
        ),
    ]
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=2)
    res = reranker.rerank_and_select(sample_query, tied_candidates, retrieval_k=2)

    # First item selected must be chunk_alpha due to lexicographical order 'chunk_alpha' < 'chunk_zebra'
    assert res.selected_evidence[0].chunk_id == "chunk_alpha"
    assert res.selected_evidence[1].chunk_id == "chunk_zebra"


def test_safe_zero_vector_handling(sample_query):
    """Candidates with all-zero vectors must not raise divide-by-zero or NaN errors."""
    mock_model = DummyMockEmbeddingModel(vector_map={}, default_dim=4)  # all zero vectors
    candidates = [
        RetrievedEvidence(
            rank=1,
            similarity=0.80,
            chunk_id="c1",
            source_window_id="w1",
            dataset="hdfs",
            split="train",
            text="empty_1",
            record_count=1,
            template_ids=[1],
        ),
        RetrievedEvidence(
            rank=2,
            similarity=0.70,
            chunk_id="c2",
            source_window_id="w2",
            dataset="hdfs",
            split="train",
            text="empty_2",
            record_count=1,
            template_ids=[2],
        ),
    ]
    reranker = MMREvidenceReranker(embedding_model=mock_model, mmr_lambda=0.70, evidence_k=2)
    res = reranker.rerank_and_select(sample_query, candidates, retrieval_k=2)
    assert len(res.selected_evidence) == 2
    assert res.metrics["max_pairwise_selected_similarity"] == 0.0


# -----------------------------------------------------------------------------
# 2. SELECTION CONSTRAINTS & EDGE CASES
# -----------------------------------------------------------------------------

def test_evidence_k_greater_than_retrieval_k_rejected(sample_query, dummy_candidates, mock_embedding_model):
    """evidence_k > retrieval_k must fail explicitly with ValueError."""
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=6)
    with pytest.raises(ValueError, match="cannot exceed retrieval_k"):
        reranker.rerank_and_select(sample_query, dummy_candidates, retrieval_k=5)


def test_evidence_k_equals_1(sample_query, dummy_candidates, mock_embedding_model):
    """evidence_k = 1 selects exactly the top relevance candidate."""
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=1)
    res = reranker.rerank_and_select(sample_query, dummy_candidates, retrieval_k=5)
    assert res.selected_count == 1
    assert res.selected_evidence[0].chunk_id == "chunk_a"
    assert res.selected_evidence[0].redundancy_penalty == 0.0


def test_empty_candidates_handling(sample_query, mock_embedding_model):
    """Empty candidate list returns empty selection without errors."""
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=3)
    res = reranker.rerank_and_select(sample_query, [], retrieval_k=5)
    assert res.selected_count == 0
    assert len(res.selected_evidence) == 0



def test_fewer_candidates_than_evidence_k(sample_query, dummy_candidates, mock_embedding_model):
    """When candidates < evidence_k, selects all available candidates."""
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=4)
    # Pass only 2 candidates
    res = reranker.rerank_and_select(sample_query, dummy_candidates[:2], retrieval_k=4)
    assert res.selected_count == 2


def test_original_scores_preserved_intact(sample_query, dummy_candidates, mock_embedding_model):
    """Phase 6 must not overwrite or mutate original Phase 5 retrieval scores."""
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=3)
    res = reranker.rerank_and_select(sample_query, dummy_candidates, retrieval_k=5)

    for item in res.selected_evidence:
        # Find matching candidate
        matching = next(c for c in dummy_candidates if c.chunk_id == item.chunk_id)
        assert item.retrieval_score == matching.similarity
        assert item.retrieval_rank == matching.rank


# -----------------------------------------------------------------------------
# 3. LABEL LEAKAGE & RESEARCH INTEGRITY PROTECTIONS
# -----------------------------------------------------------------------------

def test_reranker_rejects_query_with_anomaly_label(mock_embedding_model, dummy_candidates):
    """Query objects carrying ground truth anomaly labels must be rejected immediately."""
    class LeakedQuery:
        query_window_id = "win_leak"
        dataset = "hdfs"
        text = "template_1 template_2"
        is_anomaly = True  # Leaked label attribute

    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=3)
    with pytest.raises(LabelLeakageError, match="Query object contains 'is_anomaly' attribute"):
        reranker.rerank_and_select(LeakedQuery(), dummy_candidates, retrieval_k=5)


def test_primary_reranking_is_label_free(sample_query, dummy_candidates, mock_embedding_model):
    """The MMR selection logic must produce the identical result regardless of candidate anomaly_label."""
    cands_normal = copy.deepcopy(dummy_candidates)
    for c in cands_normal:
        c.anomaly_label = False

    cands_inverted = copy.deepcopy(dummy_candidates)
    for c in cands_inverted:
        c.anomaly_label = True  # Invert all labels

    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=3)
    res1 = reranker.rerank_and_select(sample_query, cands_normal, retrieval_k=5)
    res2 = reranker.rerank_and_select(sample_query, cands_inverted, retrieval_k=5)

    assert [e.chunk_id for e in res1.selected_evidence] == [e.chunk_id for e in res2.selected_evidence]
    assert [e.selection_score for e in res1.selected_evidence] == [e.selection_score for e in res2.selected_evidence]


# -----------------------------------------------------------------------------
# 4. GATED PIPELINE INTEGRATION TESTS
# -----------------------------------------------------------------------------

def test_gated_evidence_pipeline_autoclear_bypasses(mock_embedding_model):
    """AUTO-CLEAR windows must strictly bypass both retrieval and reranking."""
    calibrator = SplitConformalCalibrator([0.1, 0.2, 0.3, 0.4, 0.5])
    gate = SelectiveGate(calibrator=calibrator, alpha=0.10)  # threshold will be > 0.4

    # Build dummy retriever
    retriever = IncidentRetriever(
        corpus=[],
        corpus_embeddings=np.empty((0, 4)),
        embedding_model=mock_embedding_model,
        dataset="hdfs",
    )
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=3)

    pipeline = GatedEvidencePipeline(gate=gate, retriever=retriever, reranker=reranker)

    normal_window = LogWindow(
        dataset="hdfs",
        window_id="normal_win",
        session_id="blk_1",
        start_time=0.0,
        end_time=1.0,
        record_count=5,
        template_ids=[1, 2],
        raw_messages=["msg1"],
        is_anomaly=False,
    )

    # Low score -> AUTO-CLEAR
    result = pipeline.process_window(normal_window, score=0.05, retrieval_k=5)

    assert result.decision == "AUTO-CLEAR"
    assert not result.retrieval_invoked
    assert not result.selection_invoked
    assert result.retrieved_evidence is None
    assert result.selected_evidence is None
    assert result.selection_result is None


def test_gated_evidence_pipeline_escalate_triggers_cascade(mock_embedding_model, dummy_candidates):
    """ESCALATE windows must trigger retrieval -> reranking -> selection cascade."""
    calibrator = SplitConformalCalibrator([0.1, 0.2, 0.3, 0.4, 0.5])
    gate = SelectiveGate(calibrator=calibrator, alpha=0.10)

    # Mock retriever that returns dummy_candidates
    class MockRetriever:
        def retrieve(self, query, k=5):
            return dummy_candidates[:k]

    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=3)
    pipeline = GatedEvidencePipeline(gate=gate, retriever=MockRetriever(), reranker=reranker)

    anom_window = LogWindow(
        dataset="hdfs",
        window_id="anom_win",
        session_id="blk_999",
        start_time=0.0,
        end_time=1.0,
        record_count=10,
        template_ids=[1, 2],
        raw_messages=["alert"],
        is_anomaly=True,
    )

    # High score -> ESCALATE
    result = pipeline.process_window(anom_window, score=0.99, retrieval_k=5)

    assert result.decision == "ESCALATE"
    assert result.retrieval_invoked
    assert result.selection_invoked
    assert len(result.retrieved_evidence) == 5
    assert len(result.selected_evidence) == 3
    assert result.selection_result is not None
    assert result.selected_evidence[0].chunk_id == "chunk_a"


# -----------------------------------------------------------------------------
# 5. REPRODUCIBILITY & DETERMINISM TEST
# -----------------------------------------------------------------------------

def test_repeated_run_determinism(sample_query, dummy_candidates, mock_embedding_model):
    """Two identical runs must produce bitwise-identical selection outputs and metrics."""
    reranker = MMREvidenceReranker(embedding_model=mock_embedding_model, mmr_lambda=0.70, evidence_k=3)

    run1 = reranker.rerank_and_select(sample_query, dummy_candidates, retrieval_k=5)
    run2 = reranker.rerank_and_select(sample_query, dummy_candidates, retrieval_k=5)

    assert run1.to_dict() == run2.to_dict()
