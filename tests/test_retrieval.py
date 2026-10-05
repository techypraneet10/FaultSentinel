"""Comprehensive test suite for Phase 5: Leakage-Safe Contextual Retrieval Infrastructure.

Verifies:
1. Corpus construction is strictly restricted to TRAIN split.
2. Calibration and test split access attempts are strictly rejected.
3. Deterministic chunk ID generation via SHA-256 (no random seeds, no Python hash).
4. Anomaly labels are strictly excluded from searchable text and query objects.
5. Local TF-IDF embedding model fits strictly on TRAIN and produces deterministic representations.
6. Vector representations are properly L2-normalized with safe zero-norm handling.
7. Cosine similarity correctness on identical, orthogonal, opposite, and zero vectors.
8. Incident retriever returns exact top-k matches with deterministic tie-breaking (similarity DESC, chunk_id ASC).
9. Self-retrieval exclusion strictly excludes the query's own window ID.
10. Same-dataset filtering prevents cross-dataset retrieval pollution (HDFS vs BGL).
11. Gated retrieval pipeline verifies that AUTO-CLEAR windows bypass retrieval and ESCALATE windows invoke retrieval.
12. Configurable k handling, including k > corpus size and empty corpus edge cases.
13. Repeated execution determinism of corpus, embeddings, and evidence rankings.
14. Generated Phase 5 artifacts exist and adhere to research integrity guardrails.
"""

import copy
import hashlib
import json
import os
import numpy as np
import pytest

from sentinellog.calibration.conformal import SplitConformalCalibrator
from sentinellog.calibration.gate import SelectiveGate
from sentinellog.ingestion.schemas import LogWindow
from sentinellog.retrieval.chunking import (
    build_query_from_window,
    build_retrieval_chunk,
    build_retrieval_corpus,
    compute_chunk_id,
    format_template_tokens,
)
from sentinellog.retrieval.embeddings import TemplateTfidfEmbeddingModel
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
from sentinellog.scoring.artifacts import TestAccessViolationError


@pytest.fixture
def synthetic_train_windows():
    """Create deterministic synthetic TRAIN windows."""
    windows = []
    # Pattern A: templates [1, 2, 3]
    for i in range(10):
        windows.append(
            LogWindow(
                dataset="synth",
                window_id=f"train_win_a_{i}",
                session_id=f"sess_a_{i}",
                start_time=float(100 + i * 10),
                end_time=float(105 + i * 10),
                record_count=3,
                template_ids=[1, 2, 3],
                raw_messages=["msg1", "msg2", "msg3"],
                is_anomaly=False,
            )
        )
    # Pattern B: templates [4, 5, 6] (some anomalous)
    for j in range(5):
        windows.append(
            LogWindow(
                dataset="synth",
                window_id=f"train_win_b_{j}",
                session_id=f"sess_b_{j}",
                start_time=float(300 + j * 10),
                end_time=float(305 + j * 10),
                record_count=3,
                template_ids=[4, 5, 6],
                raw_messages=["msg4", "msg5", "msg6"],
                is_anomaly=(j % 2 == 1),
            )
        )
    return windows


# ---------------------------------------------------------------------------
# 1. Corpus Construction & Split Protection Tests
# ---------------------------------------------------------------------------
def test_corpus_construction_train_only(synthetic_train_windows):
    """Verify that retrieval corpus is constructed strictly from TRAIN windows."""
    corpus = build_retrieval_corpus(synthetic_train_windows, split="train")
    assert len(corpus) == len(synthetic_train_windows)
    for chunk in corpus:
        assert chunk.split == "train"
        assert chunk.chunk_id is not None
        assert len(chunk.chunk_id) == 64  # SHA-256 hex string


def test_corpus_construction_rejects_non_train(synthetic_train_windows):
    """Verify that attempting to build corpus from calibration or test raises InvalidSplitError."""
    with pytest.raises(InvalidSplitError, match="only be constructed from the 'train' split"):
        build_retrieval_corpus(synthetic_train_windows, split="calibration")

    with pytest.raises(TestAccessViolationError, match="Rule 1 Violation"):
        build_retrieval_corpus(synthetic_train_windows, split="test")


def test_guard_train_split_only_file_paths():
    """Verify that guard_train_split_only rejects non-train file paths."""
    guard_train_split_only("train", "data/processed/hdfs/train.jsonl")  # Valid

    with pytest.raises(InvalidSplitError):
        guard_train_split_only("calibration", "data/processed/hdfs/calibration.jsonl")

    with pytest.raises(TestAccessViolationError):
        guard_train_split_only("test", "data/processed/hdfs/test.jsonl")


# ---------------------------------------------------------------------------
# 2. Deterministic Chunk ID & Content Stability
# ---------------------------------------------------------------------------
def test_chunk_id_determinism():
    """Verify that chunk ID calculation is 100% deterministic across calls."""
    id1 = compute_chunk_id("hdfs", "train", "win_01", "template_1 template_2")
    id2 = compute_chunk_id("hdfs", "train", "win_01", "template_1 template_2")
    assert id1 == id2
    assert id1 == hashlib.sha256("hdfs:train:win_01:template_1 template_2".encode("utf-8")).hexdigest()

    # Changing any component must alter the chunk_id
    id3 = compute_chunk_id("hdfs", "train", "win_02", "template_1 template_2")
    assert id1 != id3


def test_format_template_tokens():
    """Verify template token formatting handles positive IDs, unknown, and empty lists."""
    assert format_template_tokens([1, 2, -1, 4]) == "template_1 template_2 template_unknown template_4"
    assert format_template_tokens([]) == ""


# ---------------------------------------------------------------------------
# 3. Label Leakage Protection Tests
# ---------------------------------------------------------------------------
def test_label_exclusion_from_chunk_text(synthetic_train_windows):
    """Verify that ground-truth anomaly labels do NOT appear in chunk searchable text."""
    corpus = build_retrieval_corpus(synthetic_train_windows, split="train")
    for chunk in corpus:
        # Searchable text must only contain template tokens
        assert "is_anomaly" not in chunk.text
        assert "anomaly" not in chunk.text
        assert "true" not in chunk.text
        assert "false" not in chunk.text
        # But anomaly_label metadata field preserves evaluation ground truth
        assert isinstance(chunk.anomaly_label, bool)


def test_guard_no_label_in_text_raises():
    """Verify guard detects and rejects text containing label indicators."""
    with pytest.raises(LabelLeakageError, match="Label Leakage Detected"):
        guard_no_label_in_text("template_1 is_anomaly=True")

    with pytest.raises(LabelLeakageError, match="Label Leakage Detected"):
        guard_no_label_in_text("template_2 label: anomaly")


def test_guard_query_does_not_contain_labels():
    """Verify guard verifies query objects do not expose label attributes."""
    query = RetrievalQuery(
        query_window_id="q1",
        dataset="hdfs",
        record_count=2,
        template_ids=[1, 2],
        text="template_1 template_2",
    )
    guard_query_does_not_contain_labels(query)  # Safe

    class LeakyQuery:
        def __init__(self):
            self.query_window_id = "q1"
            self.is_anomaly = True
            self.text = "template_1"

    with pytest.raises(LabelLeakageError, match="Query object contains 'is_anomaly'"):
        guard_query_does_not_contain_labels(LeakyQuery())


# ---------------------------------------------------------------------------
# 4. Embedding Model Tests
# ---------------------------------------------------------------------------
def test_embedding_model_train_only_fit():
    """Verify that TemplateTfidfEmbeddingModel fits strictly on TRAIN."""
    model = TemplateTfidfEmbeddingModel()
    with pytest.raises(InvalidSplitError):
        model.fit(["template_1 template_2"], split="calibration")

    model.fit(["template_1 template_2", "template_2 template_3"], split="train")
    assert model.is_fitted
    assert model.dimension == 3
    assert len(model.vocabulary_hash) == 64


def test_embedding_model_encode_and_normalization():
    """Verify vector dimensions, L2 normalization, and absence of NaN/Inf."""
    model = TemplateTfidfEmbeddingModel()
    model.fit(["template_1 template_2", "template_2 template_3"], split="train")

    vecs = model.encode(["template_1 template_2", "template_unknown", ""])
    assert vecs.shape == (3, 3)
    assert not np.isnan(vecs).any()
    assert not np.isinf(vecs).any()

    # First row has non-zero tokens in vocab -> norm should be 1.0
    norm_0 = float(np.linalg.norm(vecs[0]))
    assert norm_0 == pytest.approx(1.0, rel=1e-5)

    # Empty text or out-of-vocab -> zero norm vector safely returned
    norm_2 = float(np.linalg.norm(vecs[2]))
    assert norm_2 == 0.0


# ---------------------------------------------------------------------------
# 5. Cosine Similarity Function Tests
# ---------------------------------------------------------------------------
def test_cosine_similarity_properties():
    """Verify cosine similarity mathematical properties."""
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v_orth = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    v_opp = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    v_zero = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    # Identical vectors -> 1.0
    assert cosine_similarity(v1, v2) == pytest.approx(1.0)
    # Orthogonal vectors -> 0.0
    assert cosine_similarity(v1, v_orth) == pytest.approx(0.0)
    # Opposite vectors -> -1.0
    assert cosine_similarity(v1, v_opp) == pytest.approx(-1.0)
    # Zero vector -> 0.0 (safe, no division by zero)
    assert cosine_similarity(v1, v_zero) == 0.0


def test_batch_cosine_similarities():
    """Verify batch cosine similarity matrix computation."""
    q = np.array([1.0, 0.0], dtype=np.float32)
    corpus = np.array([
        [1.0, 0.0],
        [0.0, 1.0],
        [0.0, 0.0],
    ], dtype=np.float32)

    sims = batch_cosine_similarities(q, corpus)
    assert len(sims) == 3
    assert sims[0] == pytest.approx(1.0)
    assert sims[1] == pytest.approx(0.0)
    assert sims[2] == 0.0


# ---------------------------------------------------------------------------
# 6. Incident Retriever Tests
# ---------------------------------------------------------------------------
def test_incident_retriever_top_k_and_self_exclusion(synthetic_train_windows):
    """Verify that IncidentRetriever returns top-k evidence and excludes the query window."""
    corpus = build_retrieval_corpus(synthetic_train_windows, split="train")
    texts = [c.text for c in corpus]

    model = TemplateTfidfEmbeddingModel().fit(texts, split="train")
    embeddings = model.encode(texts)

    retriever = IncidentRetriever(
        corpus=corpus,
        corpus_embeddings=embeddings,
        embedding_model=model,
        dataset="synth",
        same_dataset_only=True,
        exclude_self=True,
    )

    # Query with the first window (which is in TRAIN)
    q_win = synthetic_train_windows[0]
    evidence = retriever.retrieve(q_win, k=3)

    assert len(evidence) == 3
    # Self-exclusion check: first window must NOT be retrieved
    for ev in evidence:
        assert ev.source_window_id != q_win.window_id
        assert ev.similarity <= 1.0001
        assert ev.rank in [1, 2, 3]


def test_incident_retriever_deterministic_tie_breaking(synthetic_train_windows):
    """Verify deterministic tie-breaking: identical similarity sorted by chunk_id ASC."""
    corpus = build_retrieval_corpus(synthetic_train_windows, split="train")
    texts = [c.text for c in corpus]
    model = TemplateTfidfEmbeddingModel().fit(texts, split="train")
    embeddings = model.encode(texts)

    retriever = IncidentRetriever(
        corpus=corpus,
        corpus_embeddings=embeddings,
        embedding_model=model,
        dataset="synth",
        same_dataset_only=True,
        exclude_self=False,
    )

    # All pattern A windows have identical templates [1, 2, 3], so similarity to pattern A will be identical
    q_win = synthetic_train_windows[0]
    ev1 = retriever.retrieve(q_win, k=5)
    ev2 = retriever.retrieve(q_win, k=5)

    # Identical retrieval results across calls
    assert [e.chunk_id for e in ev1] == [e.chunk_id for e in ev2]

    # For tied similarities, chunk_id must be strictly ascending
    for i in range(len(ev1) - 1):
        if ev1[i].similarity == ev1[i + 1].similarity:
            assert ev1[i].chunk_id < ev1[i + 1].chunk_id


def test_same_dataset_filtering():
    """Verify that retrieval strictly isolates datasets (e.g. HDFS vs BGL)."""
    w_hdfs = LogWindow(
        dataset="hdfs",
        window_id="w_h",
        session_id=None,
        start_time=1.0,
        end_time=2.0,
        record_count=1,
        template_ids=[1],
        raw_messages=["m"],
        is_anomaly=False,
    )
    corpus = build_retrieval_corpus([w_hdfs], split="train")
    model = TemplateTfidfEmbeddingModel().fit([c.text for c in corpus], split="train")
    embeddings = model.encode([c.text for c in corpus])

    retriever = IncidentRetriever(
        corpus=corpus,
        corpus_embeddings=embeddings,
        embedding_model=model,
        dataset="hdfs",
        same_dataset_only=True,
    )

    # Query with a BGL window against HDFS retriever
    w_bgl = LogWindow(
        dataset="bgl",
        window_id="w_b",
        session_id=None,
        start_time=1.0,
        end_time=2.0,
        record_count=1,
        template_ids=[1],
        raw_messages=["m"],
        is_anomaly=False,
    )

    evidence = retriever.retrieve(w_bgl, k=5)
    assert len(evidence) == 0  # Filtered out by dataset mismatch


# ---------------------------------------------------------------------------
# 7. Gated Selective Retrieval Integration Tests
# ---------------------------------------------------------------------------
def test_gated_retrieval_pipeline_selective_cost(synthetic_train_windows):
    """Verify central research property: AUTO-CLEAR bypasses retrieval, ESCALATE invokes it."""
    corpus = build_retrieval_corpus(synthetic_train_windows, split="train")
    texts = [c.text for c in corpus]
    model = TemplateTfidfEmbeddingModel().fit(texts, split="train")
    embeddings = model.encode(texts)

    retriever = IncidentRetriever(
        corpus=corpus,
        corpus_embeddings=embeddings,
        embedding_model=model,
        dataset="synth",
    )

    # Mock calibration scores: 10 scores from 0.1 to 1.0
    calib_scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    calibrator = SplitConformalCalibrator(calib_scores)
    # Threshold for alpha=0.20 on n=10 is 0.9
    gate = SelectiveGate(calibrator=calibrator, alpha=0.20, strict=True)

    pipeline = GatedRetrievalPipeline(gate=gate, retriever=retriever)

    # Normal window with low anomaly score (0.3 <= 0.9) -> AUTO-CLEAR
    win_normal = synthetic_train_windows[0]
    res_normal = pipeline.process_window(win_normal, score=0.3, k=3)
    assert res_normal.decision == "AUTO-CLEAR"
    assert res_normal.retrieval_invoked is False
    assert res_normal.retrieved_evidence is None

    # Anomalous window with high anomaly score (0.95 > 0.9) -> ESCALATE
    win_anom = synthetic_train_windows[10]
    res_anom = pipeline.process_window(win_anom, score=0.95, k=3)
    assert res_anom.decision == "ESCALATE"
    assert res_anom.retrieval_invoked is True
    assert res_anom.retrieved_evidence is not None
    assert len(res_anom.retrieved_evidence) == 3


# ---------------------------------------------------------------------------
# 8. Edge Cases: Empty Corpus & k > Corpus Size
# ---------------------------------------------------------------------------
def test_retriever_empty_corpus_and_large_k(synthetic_train_windows):
    """Verify behavior when corpus is empty or k exceeds corpus size."""
    w = synthetic_train_windows[0]
    chunk = build_retrieval_chunk(w, split="train")
    model = TemplateTfidfEmbeddingModel().fit([chunk.text], split="train")

    # Empty corpus
    empty_retriever = IncidentRetriever(
        corpus=[],
        corpus_embeddings=np.empty((0, model.dimension), dtype=np.float32),
        embedding_model=model,
        dataset="synth",
    )
    assert empty_retriever.retrieve(w, k=5) == []

    # Corpus size 1, requested k = 10 (exclude_self=False)
    single_retriever = IncidentRetriever(
        corpus=[chunk],
        corpus_embeddings=model.encode([chunk.text]),
        embedding_model=model,
        dataset="synth",
        exclude_self=False,
    )
    ev = single_retriever.retrieve(w, k=10)
    assert len(ev) == 1  # Gracefully returns all available chunks without crashing


# ---------------------------------------------------------------------------
# 9. Phase 5 Experiment Artifacts Conformance
# ---------------------------------------------------------------------------
def test_phase5_actual_artifacts_exist_and_conform():
    """Verify that Phase 5 generated manifests and artifacts for HDFS and BGL exist and conform."""
    for ds in ["hdfs", "bgl"]:
        ds_dir = os.path.join("results/phase5", ds)
        assert os.path.exists(ds_dir), f"Directory {ds_dir} missing"

        manifest_path = os.path.join(ds_dir, "retrieval_manifest.json")
        diag_path = os.path.join(ds_dir, "retrieval_diagnostics.json")
        corpus_path = os.path.join(ds_dir, "corpus.jsonl")
        embeddings_path = os.path.join(ds_dir, "embeddings.npy")

        assert os.path.exists(manifest_path)
        assert os.path.exists(diag_path)
        assert os.path.exists(corpus_path)
        assert os.path.exists(embeddings_path)

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["dataset"] == ds
        assert manifest["corpus_split"] == "train"
        assert manifest["test_used"] is False  # Rule 1 verification
        assert manifest["calibration_used_for_corpus"] is False

        # Verify embeddings shape matches corpus size
        embeddings = np.load(embeddings_path)
        assert embeddings.shape[0] == manifest["corpus_size"]
        assert embeddings.shape[1] == manifest["embedding_dimension"]


def test_repeated_pipeline_determinism(synthetic_train_windows):
    """Verify that repeating the retrieval pipeline yields bit-for-bit identical outputs."""
    # Run 1
    c1 = build_retrieval_corpus(synthetic_train_windows, split="train")
    m1 = TemplateTfidfEmbeddingModel().fit([c.text for c in c1], split="train")
    e1 = m1.encode([c.text for c in c1])
    r1 = IncidentRetriever(corpus=c1, corpus_embeddings=e1, embedding_model=m1, dataset="synth")
    ev1 = r1.retrieve(synthetic_train_windows[0], k=4)

    # Run 2
    c2 = build_retrieval_corpus(synthetic_train_windows, split="train")
    m2 = TemplateTfidfEmbeddingModel().fit([c.text for c in c2], split="train")
    e2 = m2.encode([c.text for c in c2])
    r2 = IncidentRetriever(corpus=c2, corpus_embeddings=e2, embedding_model=m2, dataset="synth")
    ev2 = r2.retrieve(synthetic_train_windows[0], k=4)

    # Verifications
    assert [c.chunk_id for c in c1] == [c.chunk_id for c in c2]
    assert m1.vocabulary_hash == m2.vocabulary_hash
    np.testing.assert_array_equal(e1, e2)
    assert [e.chunk_id for e in ev1] == [e.chunk_id for e in ev2]
    assert [e.similarity for e in ev1] == [e.similarity for e in ev2]

