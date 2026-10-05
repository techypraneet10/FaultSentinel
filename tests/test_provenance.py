"""Comprehensive test suite for Phase 7: Citation and Provenance Engine.

Verifies:
1. Provenance data model validation and serialization.
2. Exact source location resolution for HDFS and BGL.
3. Deterministic citation ID derivation.
4. Deterministic canonical human-readable citation formatting.
5. Deterministic citation bundle ID derivation.
6. Content fingerprint computation and round-trip verification.
7. Modified source detection (integrity failure).
8. Missing or invalid source handling (unresolved).
9. Label leakage protection: anomaly labels do not affect citation ID, text, or content hash.
10. Test set protection: test partition lookups are rejected.
11. Train-only partition invariant: non-train splits are rejected.
12. Gated selective triage integration: AUTO-CLEAR bypasses provenance, ESCALATE produces verified bundle.
13. Repeated-run bitwise determinism across bundles and citations.
"""

import copy
import hashlib
import json
import os
import pytest

from sentinellog.calibration.conformal import SplitConformalCalibrator
from sentinellog.calibration.gate import SelectiveGate
from sentinellog.ingestion.schemas import LogWindow
from sentinellog.provenance.engine import ProvenanceEngine
from sentinellog.provenance.gated import GatedCitationPipeline
from sentinellog.provenance.hashing import (
    compute_bundle_id,
    compute_canonical_source_text,
    compute_citation_id,
    compute_content_hash,
    compute_source_content_hash,
    compute_template_content_hash,
    format_citation_text,
)
from sentinellog.provenance.resolver import ProvenanceResolutionError, SourceResolver
from sentinellog.provenance.schemas import (
    Citation,
    CitationBundle,
    EvidenceProvenance,
    SourceArtifact,
    SourceLocation,
    VerificationResult,
)
from sentinellog.provenance.verifier import ProvenanceVerifier
from sentinellog.retrieval.guards import InvalidSplitError
from sentinellog.retrieval.reranker import MMREvidenceReranker
from sentinellog.retrieval.reranking_schemas import SelectedEvidence
from sentinellog.scoring.artifacts import TestAccessViolationError


@pytest.fixture
def sample_location():
    return SourceLocation(
        source_file="data/processed/hdfs/train.jsonl",
        line_start=100,
        line_end=150,
        record_count=15,
        session_id="blk_12345",
        timestamp_start=1226243118.0,
        timestamp_end=1226243186.0,
    )


@pytest.fixture
def sample_artifact():
    return SourceArtifact(
        dataset="hdfs",
        split="train",
        artifact_path="data/processed/hdfs/train.jsonl",
        artifact_sha256="27ba33bacaf1d09591ffbdc0784a68350f693503aeda6006a2d5440502b8506e",
        pipeline_version="0.2.1-phase2-freeze",
        raw_sha256="0783096174d7832c618337f9609e06e04abd86ddd7089b3c12b407e63bfebc52",
    )


@pytest.fixture
def sample_selected_evidence():
    # Uses actual window from HDFS train.jsonl
    return SelectedEvidence(
        chunk_id="cc3d148de670cd88da6b9662ca6ba3f58fe651d82541214e117e41acf4603279",
        source_window_id="hdfs_session_blk_-1608999687919862906",
        dataset="hdfs",
        split="train",
        text="template_1 template_2",
        record_count=249,
        template_ids=[1, 2],
        retrieval_rank=1,
        retrieval_score=0.95,
        selected_rank=1,
        selection_score=0.95,
        redundancy_penalty=0.0,
        timestamp_start=1226243118.0,
        timestamp_end=1226243186.0,
        anomaly_label=False,
        provenance={"source_window_id": "hdfs_session_blk_-1608999687919862906"},
    )


# -----------------------------------------------------------------------------
# 1. DATA MODEL & SERIALIZATION
# -----------------------------------------------------------------------------

def test_source_location_dataclass(sample_location):
    d = sample_location.to_dict()
    reconstructed = SourceLocation.from_dict(d)
    assert reconstructed == sample_location
    assert reconstructed.line_start == 100
    assert reconstructed.line_end == 150
    assert reconstructed.session_id == "blk_12345"


def test_source_artifact_dataclass(sample_artifact):
    d = sample_artifact.to_dict()
    reconstructed = SourceArtifact.from_dict(d)
    assert reconstructed == sample_artifact
    assert reconstructed.dataset == "hdfs"
    assert reconstructed.split == "train"


def test_citation_bundle_dataclass(sample_artifact, sample_location):
    prov = EvidenceProvenance(
        citation_id="cit_123",
        chunk_id="chunk_abc",
        dataset="hdfs",
        split="train",
        source_window_id="win_1",
        source_artifact=sample_artifact,
        source_location=sample_location,
        source_content_hash="src_hash_123",
        template_content_hash="tmpl_hash_456",
        content_hash="src_hash_123",
    )
    citation = Citation(
        citation_id="cit_123",
        citation_text="[HDFS | train | window=win_1]",
        chunk_id="chunk_abc",
        source_window_id="win_1",
        dataset="hdfs",
        split="train",
        selected_rank=1,
        retrieval_score=0.9,
        selection_score=0.9,
        source_content_hash="src_hash_123",
        template_content_hash="tmpl_hash_456",
        content_hash="src_hash_123",
        provenance=prov,
    )
    bundle = CitationBundle(
        bundle_id="bundle_xyz",
        query_id="q_1",
        dataset="hdfs",
        split="train",
        evidence_count=1,
        citations=[citation],
        all_verified=True,
    )

    d = bundle.to_dict()
    reconstructed = CitationBundle.from_dict(d)
    assert reconstructed.bundle_id == "bundle_xyz"
    assert reconstructed.evidence_count == 1
    assert reconstructed.citations[0].citation_id == "cit_123"
    assert reconstructed.citations[0].source_content_hash == "src_hash_123"
    assert reconstructed.citations[0].template_content_hash == "tmpl_hash_456"
    assert reconstructed.all_verified is True



# -----------------------------------------------------------------------------
# 2. DETERMINISTIC DERIVATION & FORMATTING
# -----------------------------------------------------------------------------

def test_deterministic_citation_id():
    cid1 = compute_citation_id("hdfs", "train", "chk1", "win1", 10, 50)
    cid2 = compute_citation_id("hdfs", "train", "chk1", "win1", 10, 50)
    cid_diff = compute_citation_id("hdfs", "train", "chk1", "win1", 11, 50)

    assert cid1 == cid2
    assert cid1 != cid_diff
    assert len(cid1) == 64  # SHA-256 hex


def test_deterministic_bundle_id():
    b1 = compute_bundle_id(["c1", "c2", "c3"], "hdfs", "1.0")
    b2 = compute_bundle_id(["c1", "c2", "c3"], "hdfs", "1.0")
    b3 = compute_bundle_id(["c2", "c1", "c3"], "hdfs", "1.0")  # Different order

    assert b1 == b2
    assert b1 != b3  # Order matters


def test_format_citation_text(sample_location):
    txt = format_citation_text("hdfs", "train", "win_blk_1", sample_location)
    assert txt == "[HDFS | train | window=win_blk_1 | lines=100-150 | records=15]"


def test_content_hash_deterministic():
    h1 = compute_content_hash("template_1 template_2")
    h2 = compute_content_hash("template_1 template_2")
    h3 = compute_content_hash("template_1 template_3")

    assert h1 == h2
    assert h1 != h3


# -----------------------------------------------------------------------------
# 3. SOURCE RESOLUTION & VERIFICATION
# -----------------------------------------------------------------------------

def test_source_resolution_hdfs(sample_selected_evidence):
    resolver = SourceResolver()
    artifact, location, canon_text, src_hash, tmpl_hash = resolver.resolve_source(
        dataset="hdfs",
        split="train",
        source_window_id=sample_selected_evidence.source_window_id,
    )

    assert artifact.dataset == "hdfs"
    assert artifact.split == "train"
    assert location.record_count == 249
    assert location.line_start == 1
    assert location.line_end == 5339
    assert location.session_id == "blk_-1608999687919862906"
    assert len(src_hash) == 64
    assert len(tmpl_hash) == 64
    assert src_hash != tmpl_hash


def test_source_resolution_bgl():
    resolver = SourceResolver()
    artifact, location, canon_text, src_hash, tmpl_hash = resolver.resolve_source(
        dataset="bgl",
        split="train",
        source_window_id="bgl_window_0000000",
    )

    assert artifact.dataset == "bgl"
    assert artifact.split == "train"
    assert location.record_count == 100
    assert location.line_start == 1
    assert location.line_end == 100
    assert location.session_id is None
    assert len(src_hash) == 64
    assert len(tmpl_hash) == 64
    assert src_hash != tmpl_hash


def test_source_resolution_missing_window_fails_closed():
    resolver = SourceResolver()
    with pytest.raises(ProvenanceResolutionError, match="not found in artifact"):
        resolver.resolve_source(
            dataset="hdfs",
            split="train",
            source_window_id="nonexistent_window_99999",
        )


def test_provenance_verifier_round_trip(sample_selected_evidence):
    engine = ProvenanceEngine()
    citation = engine.create_citation(sample_selected_evidence)

    verifier = ProvenanceVerifier()
    res = verifier.verify_citation(citation)

    assert res.status == "VALID"
    assert res.content_hash_match is True
    assert res.source_content_hash_match is True
    assert res.template_content_hash_match is True
    assert res.stored_source_hash == res.recomputed_source_hash
    assert res.stored_template_hash == res.recomputed_template_hash


def test_provenance_verifier_detects_corrupted_content_hash(sample_selected_evidence):
    engine = ProvenanceEngine()
    citation = engine.create_citation(sample_selected_evidence)

    # Tamper with source_content_hash
    tampered_citation = Citation(
        citation_id=citation.citation_id,
        citation_text=citation.citation_text,
        chunk_id=citation.chunk_id,
        source_window_id=citation.source_window_id,
        dataset=citation.dataset,
        split=citation.split,
        selected_rank=citation.selected_rank,
        retrieval_score=citation.retrieval_score,
        selection_score=citation.selection_score,
        source_content_hash="0000000000000000000000000000000000000000000000000000000000000000",  # Corrupted!
        template_content_hash=citation.template_content_hash,
        content_hash="0000000000000000000000000000000000000000000000000000000000000000",
        provenance=citation.provenance,
    )

    verifier = ProvenanceVerifier()
    res = verifier.verify_citation(tampered_citation)

    assert res.status == "INVALID"
    assert res.content_hash_match is False
    assert res.source_content_hash_match is False
    assert res.template_content_hash_match is True
    assert "source_content_hash" in res.message


def test_raw_source_mutation_regression(sample_selected_evidence):
    """Regression check: modifying raw source records while keeping Drain3 template tokens unchanged

    must cause:
    - template_content_hash to remain unchanged (match == True)
    - source_content_hash to change (match == False)
    - provenance verification status to become INVALID
    """
    resolver = SourceResolver()
    engine = ProvenanceEngine(resolver=resolver)
    verifier = ProvenanceVerifier(resolver=resolver)

    citation = engine.create_citation(sample_selected_evidence)
    res_orig = verifier.verify_citation(citation)
    assert res_orig.status == "VALID"
    assert res_orig.source_content_hash_match is True
    assert res_orig.template_content_hash_match is True

    # Mutate raw source records in resolver's window cache while keeping template_ids untouched
    wid = sample_selected_evidence.source_window_id
    win_data = resolver._window_cache["hdfs"][wid]
    orig_raw = list(win_data["raw_messages"])
    orig_tmpl = list(win_data["template_ids"])

    try:
        # Mutate raw message content
        win_data["raw_messages"] = [orig_raw[0] + " [MUTATED_SOURCE_RECORD]"] + orig_raw[1:]
        # template_ids remain strictly identical
        win_data["template_ids"] = orig_tmpl

        res_mutated = verifier.verify_citation(citation)

        assert res_mutated.status == "INVALID"
        assert res_mutated.template_content_hash_match is True  # Template unchanged!
        assert res_mutated.source_content_hash_match is False  # Source changed!
        assert res_mutated.content_hash_match is False
        assert "source_content_hash" in res_mutated.message
    finally:
        # Restore original window data
        win_data["raw_messages"] = orig_raw
        win_data["template_ids"] = orig_tmpl


def test_template_mutation_regression(sample_selected_evidence):
    """Confirm that modifying Drain3 templates while raw source records remain unchanged

    causes:
    - source_content_hash to remain unchanged (match == True)
    - template_content_hash to change (match == False)
    - provenance verification status to become INVALID
    """
    resolver = SourceResolver()
    engine = ProvenanceEngine(resolver=resolver)
    verifier = ProvenanceVerifier(resolver=resolver)

    citation = engine.create_citation(sample_selected_evidence)

    wid = sample_selected_evidence.source_window_id
    win_data = resolver._window_cache["hdfs"][wid]
    orig_raw = list(win_data["raw_messages"])
    orig_tmpl = list(win_data["template_ids"])

    try:
        win_data["template_ids"] = [99999] + orig_tmpl[1:]
        win_data["raw_messages"] = orig_raw

        res_mutated = verifier.verify_citation(citation)

        assert res_mutated.status == "INVALID"
        assert res_mutated.source_content_hash_match is True  # Source unchanged!
        assert res_mutated.template_content_hash_match is False  # Template changed!
        assert res_mutated.content_hash_match is False
        assert "template_content_hash" in res_mutated.message
    finally:
        win_data["raw_messages"] = orig_raw
        win_data["template_ids"] = orig_tmpl


def test_separate_hashes_distinct_and_documented(sample_selected_evidence):
    """Confirm that source_content_hash and template_content_hash are distinct and non-empty."""
    engine = ProvenanceEngine()
    citation = engine.create_citation(sample_selected_evidence)

    assert citation.source_content_hash is not None
    assert citation.template_content_hash is not None
    assert len(citation.source_content_hash) == 64
    assert len(citation.template_content_hash) == 64
    assert citation.source_content_hash != citation.template_content_hash
    assert citation.provenance.source_content_hash == citation.source_content_hash
    assert citation.provenance.template_content_hash == citation.template_content_hash



# -----------------------------------------------------------------------------
# 4. LABEL LEAKAGE & PARTITION GUARDS
# -----------------------------------------------------------------------------

def test_anomaly_labels_do_not_affect_citation_identity(sample_selected_evidence):
    engine = ProvenanceEngine()

    ev_normal = copy.deepcopy(sample_selected_evidence)
    ev_normal.anomaly_label = False

    ev_anom = copy.deepcopy(sample_selected_evidence)
    ev_anom.anomaly_label = True

    cit1 = engine.create_citation(ev_normal)
    cit2 = engine.create_citation(ev_anom)

    assert cit1.citation_id == cit2.citation_id
    assert cit1.citation_text == cit2.citation_text
    assert cit1.content_hash == cit2.content_hash
    assert "anomaly" not in cit1.citation_text.lower()


def test_test_partition_lookup_strictly_rejected():
    resolver = SourceResolver()
    with pytest.raises(TestAccessViolationError):
        resolver.resolve_source("hdfs", "test", "any_id")


def test_non_train_partition_strictly_rejected():
    resolver = SourceResolver()
    with pytest.raises(InvalidSplitError):
        resolver.resolve_source("hdfs", "calibration", "any_id")


# -----------------------------------------------------------------------------
# 5. GATED PIPELINE INTEGRATION
# -----------------------------------------------------------------------------

def test_gated_citation_pipeline_autoclear():
    calibrator = SplitConformalCalibrator([0.1, 0.2, 0.3, 0.4, 0.5])
    gate = SelectiveGate(calibrator=calibrator, alpha=0.10)

    class DummyRetriever:
        pass

    class DummyReranker:
        pass

    engine = ProvenanceEngine()
    pipeline = GatedCitationPipeline(
        gate=gate,
        retriever=DummyRetriever(),
        reranker=DummyReranker(),
        provenance_engine=engine,
    )

    normal_window = LogWindow(
        dataset="hdfs",
        window_id="norm_win",
        session_id="blk_1",
        start_time=0.0,
        end_time=1.0,
        record_count=1,
        template_ids=[1],
        raw_messages=["msg"],
        is_anomaly=False,
    )

    res = pipeline.process_window(normal_window, score=0.01)
    assert res.decision == "AUTO-CLEAR"
    assert not res.retrieval_invoked
    assert not res.selection_invoked
    assert not res.provenance_invoked
    assert res.citation_bundle is None


def test_gated_citation_pipeline_escalate(sample_selected_evidence):
    calibrator = SplitConformalCalibrator([0.1, 0.2, 0.3, 0.4, 0.5])
    gate = SelectiveGate(calibrator=calibrator, alpha=0.10)

    class DummyRetriever:
        def retrieve(self, query, k=5):
            return []

    class DummyReranker:
        def rerank_and_select(self, query, candidates, retrieval_k=5):
            from sentinellog.retrieval.reranking_schemas import EvidenceSelectionResult
            return EvidenceSelectionResult(
                query_id=query.query_window_id,
                dataset=query.dataset,
                candidate_count=1,
                selected_count=1,
                retrieval_k=5,
                evidence_k=3,
                mmr_lambda=0.7,
                diversity_mode="mmr",
                selected_evidence=[sample_selected_evidence],
            )

    engine = ProvenanceEngine()
    pipeline = GatedCitationPipeline(
        gate=gate,
        retriever=DummyRetriever(),
        reranker=DummyReranker(),
        provenance_engine=engine,
    )

    anom_window = LogWindow(
        dataset="hdfs",
        window_id="anom_win",
        session_id="blk_999",
        start_time=0.0,
        end_time=1.0,
        record_count=1,
        template_ids=[1],
        raw_messages=["alert"],
        is_anomaly=True,
    )

    res = pipeline.process_window(anom_window, score=0.99)
    assert res.decision == "ESCALATE"
    assert res.retrieval_invoked
    assert res.selection_invoked
    assert res.provenance_invoked
    assert res.citation_bundle is not None
    assert res.citation_bundle.evidence_count == 1
    assert res.citation_bundle.all_verified is True


# -----------------------------------------------------------------------------
# 6. DETERMINISM & IMMUTABILITY
# -----------------------------------------------------------------------------

def test_repeated_run_determinism(sample_selected_evidence):
    engine = ProvenanceEngine()

    bundle1 = engine.create_bundle("q1", "hdfs", [sample_selected_evidence])
    bundle2 = engine.create_bundle("q1", "hdfs", [sample_selected_evidence])

    assert bundle1.to_dict() == bundle2.to_dict()
    assert bundle1.bundle_id == bundle2.bundle_id
    assert bundle1.citations[0].citation_id == bundle2.citations[0].citation_id
