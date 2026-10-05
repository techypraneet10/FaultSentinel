"""Phase 6 execution engine and CLI runner for evidence reranking and selection.

Coordinates:
1. Loading Phase 5 corpus, embeddings, and fitted embedding model for HDFS and BGL.
2. Generating Phase 5 candidates for ESCALATE windows on CALIBRATION split.
3. Executing Phase 6 MMR evidence reranking and selection (evidence_k=3, lambda=0.70).
4. Running controlled ablations:
   - Ablation A: Phase 5 top-k retrieval vs Phase 5 + MMR evidence selection.
   - Ablation B: Lambda sensitivity (1.0, 0.85, 0.70, 0.50, 0.0).
   - Ablation C: Evidence budget compression (k=1, k=3, k=5).
5. Computing diversity, redundancy, and compression diagnostics before/after reranking.
6. Generating reproducibility manifests with SHA-256 artifact hashes.

Rule 1 (Test Set Protection) is strictly enforced: TEST is never loaded or accessed.
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
import torch
import yaml

from sentinellog.calibration.conformal import SplitConformalCalibrator
from sentinellog.calibration.gate import SelectiveGate
from sentinellog.ingestion.schemas import LogWindow
from sentinellog.retrieval.chunking import build_query_from_window
from sentinellog.retrieval.embeddings import TemplateTfidfEmbeddingModel
from sentinellog.retrieval.engine import IncidentRetriever
from sentinellog.retrieval.gated import GatedEvidencePipeline
from sentinellog.retrieval.guards import guard_train_split_only
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
from sentinellog.scoring.artifacts import (
    compute_sha256,
    get_git_commit_sha,
    guard_no_test_split,
)
from sentinellog.scoring.b2 import B2SequentialScorer
from sentinellog.scoring.baselines import load_windows


def run_phase6_dataset(
    dataset: str,
    train_windows: List[LogWindow],
    calib_windows: List[LogWindow],
    config: Dict[str, Any],
    output_dir: str,
    phase5_dir: str = "results/phase5",
    phase4_checkpoint_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute complete Phase 6 evidence reranking and selection pipeline for a single dataset."""
    git_sha = get_git_commit_sha()
    ret_cfg = config.get("retrieval", {})
    rerank_cfg = config.get("reranking", {})
    gate_cfg = config.get("gate", {})
    ablations_cfg = config.get("ablations", {})

    retrieval_k = ret_cfg.get("k", 5)
    evidence_k = rerank_cfg.get("evidence_k", 3)
    mmr_lambda = rerank_cfg.get("mmr_lambda", 0.70)
    diversity_mode = rerank_cfg.get("diversity_mode", "mmr")
    alpha = gate_cfg.get("alpha", 0.05)
    strict = gate_cfg.get("strict", True)
    seed = config.get("random_seed", 42)

    start_time = time.perf_counter()

    # Rule 1 & Split Protection Checks
    guard_no_test_split("calibration")
    guard_train_split_only("train")

    print(f"[{dataset.upper()}] Loading Phase 5 artifacts from {phase5_dir}/{dataset}...")
    corpus_file = os.path.join(phase5_dir, dataset, "corpus.jsonl")
    embeddings_file = os.path.join(phase5_dir, dataset, "embeddings.npy")
    p5_manifest_file = os.path.join(phase5_dir, dataset, "retrieval_manifest.json")

    with open(p5_manifest_file, "r", encoding="utf-8") as f:
        p5_manifest = json.load(f)
    phase5_commit = p5_manifest.get("source_commit", "523a32d")

    # Load corpus
    corpus: List[RetrievalChunk] = []
    with open(corpus_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                corpus.append(RetrievalChunk.from_dict(json.loads(line)))

    # Load embeddings
    corpus_embeddings = np.load(embeddings_file)

    # Initialize and fit deterministic embedding model on TRAIN corpus texts
    corpus_texts = [c.text for c in corpus]
    embedding_model = TemplateTfidfEmbeddingModel(source_commit=git_sha)
    embedding_model.fit(corpus_texts, split="train")

    # Construct IncidentRetriever
    retriever = IncidentRetriever(
        corpus=corpus,
        corpus_embeddings=corpus_embeddings,
        embedding_model=embedding_model,
        dataset=dataset,
        same_dataset_only=ret_cfg.get("same_dataset_only", True),
        exclude_self=ret_cfg.get("exclude_self", True),
    )

    # Construct MMREvidenceReranker
    reranker = MMREvidenceReranker(
        embedding_model=embedding_model,
        mmr_lambda=mmr_lambda,
        evidence_k=evidence_k,
        diversity_mode=diversity_mode,
    )

    # Setup B2 Scorer and Gate from Phase 4
    b2_scorer = B2SequentialScorer(random_state=seed)
    if phase4_checkpoint_path and os.path.exists(phase4_checkpoint_path):
        print(f"[{dataset.upper()}] Loading Phase 4 B2 checkpoint: {phase4_checkpoint_path}")
        ckpt = torch.load(phase4_checkpoint_path, weights_only=False)
        from sentinellog.scoring.b2_model import SequentialGRU
        b2_scorer.tokenizer.fit(train_windows)
        m_meta = ckpt.get("model_metadata", {})
        emb_dim = m_meta.get("embedding_dim", b2_scorer.embedding_dim)
        hid_dim = m_meta.get("hidden_dim", b2_scorer.hidden_dim)
        n_lay = m_meta.get("num_layers", b2_scorer.num_layers)
        b2_scorer.model = SequentialGRU(
            vocab_size=b2_scorer.tokenizer.vocab_size,
            embedding_dim=emb_dim,
            hidden_dim=hid_dim,
            num_layers=n_lay,
            dropout=0.0,
        )
        b2_scorer.model.load_state_dict(ckpt["model_state_dict"])
        b2_scorer.model.eval()
        b2_scorer.is_fitted = True
    else:
        print(f"[{dataset.upper()}] Fitting B2 Sequential Scorer on TRAIN...")
        b2_scorer.fit(train_windows)

    # Score CALIBRATION windows
    print(f"[{dataset.upper()}] Scoring CALIBRATION windows ({len(calib_windows)} windows)...")
    calib_scores = b2_scorer.score(calib_windows)

    # Selective Gate from Phase 4
    calibrator = SplitConformalCalibrator(calib_scores)
    gate = SelectiveGate(calibrator=calibrator, alpha=alpha, strict=strict)

    # Execute GatedEvidencePipeline
    print(f"[{dataset.upper()}] Running Gated Evidence Pipeline (alpha={alpha:.2f}, ret_k={retrieval_k}, ev_k={evidence_k}, lambda={mmr_lambda})...")
    pipeline = GatedEvidencePipeline(gate=gate, retriever=retriever, reranker=reranker)
    gated_results: List[GatedEvidenceResult] = pipeline.process_batch(
        windows=calib_windows,
        scores=calib_scores,
        retrieval_k=retrieval_k,
    )

    n_total = len(gated_results)
    n_cleared = sum(1 for r in gated_results if r.decision == "AUTO-CLEAR")
    n_escalated = sum(1 for r in gated_results if r.decision == "ESCALATE")

    # Invariant verification: AUTO-CLEAR never invokes retrieval or reranking
    for r in gated_results:
        if r.decision == "AUTO-CLEAR":
            assert not r.retrieval_invoked, f"Invariant violation: AUTO-CLEAR invoked retrieval for {r.window_id}"
            assert not r.selection_invoked, f"Invariant violation: AUTO-CLEAR invoked selection for {r.window_id}"
            assert r.retrieved_evidence is None
            assert r.selected_evidence is None
        elif r.decision == "ESCALATE":
            assert r.retrieval_invoked, f"Invariant violation: ESCALATE did not invoke retrieval for {r.window_id}"
            assert r.selection_invoked, f"Invariant violation: ESCALATE did not invoke selection for {r.window_id}"
            assert r.retrieved_evidence is not None
            assert r.selected_evidence is not None
            assert len(r.selected_evidence) <= evidence_k
            # Verify Phase 5 retrieval scores preserved intact
            for sel_ev in r.selected_evidence:
                assert sel_ev.retrieval_score is not None
                assert sel_ev.retrieval_rank >= 1

    escalated_results = [r for r in gated_results if r.decision == "ESCALATE"]

    # Compute Before/After Aggregate Diagnostics
    cand_sims: List[float] = []
    sel_sims: List[float] = []
    cand_pairwise_sims: List[float] = []
    sel_pairwise_sims: List[float] = []
    cand_chunk_ids: List[str] = []
    sel_chunk_ids: List[str] = []
    cand_windows: List[str] = []
    sel_windows: List[str] = []

    for r in escalated_results:
        if r.retrieved_evidence and r.selected_evidence and r.selection_result:
            for c in r.retrieved_evidence:
                cand_sims.append(c.similarity)
                cand_chunk_ids.append(c.chunk_id)
                cand_windows.append(c.source_window_id)
            for s in r.selected_evidence:
                sel_sims.append(s.retrieval_score)
                sel_chunk_ids.append(s.chunk_id)
                sel_windows.append(s.source_window_id)

            cand_pairwise_sims.append(r.selection_result.metrics.get("mean_pairwise_candidate_similarity", 0.0))
            sel_pairwise_sims.append(r.selection_result.metrics.get("mean_pairwise_selected_similarity", 0.0))

    mean_cand_sim = float(np.mean(cand_sims)) if cand_sims else 0.0
    mean_sel_sim = float(np.mean(sel_sims)) if sel_sims else 0.0
    mean_cand_pairwise = float(np.mean(cand_pairwise_sims)) if cand_pairwise_sims else 0.0
    mean_sel_pairwise = float(np.mean(sel_pairwise_sims)) if sel_pairwise_sims else 0.0

    cand_unique_chunks = len(set(cand_chunk_ids))
    sel_unique_chunks = len(set(sel_chunk_ids))
    cand_dup_rate = float((len(cand_chunk_ids) - cand_unique_chunks) / len(cand_chunk_ids)) if cand_chunk_ids else 0.0
    sel_dup_rate = float((len(sel_chunk_ids) - sel_unique_chunks) / len(sel_chunk_ids)) if sel_chunk_ids else 0.0

    cand_unique_windows = len(set(cand_windows))
    sel_unique_windows = len(set(sel_windows))

    primary_diagnostics = {
        "dataset": dataset,
        "total_windows_evaluated": n_total,
        "auto_clear_count": n_cleared,
        "auto_clear_rate": float(n_cleared / n_total) if n_total > 0 else 0.0,
        "escalated_count": n_escalated,
        "escalation_rate": float(n_escalated / n_total) if n_total > 0 else 0.0,
        "retrieval_k": retrieval_k,
        "evidence_k": evidence_k,
        "mmr_lambda": mmr_lambda,
        "diversity_mode": diversity_mode,
        "evidence_compression_ratio": float(len(sel_chunk_ids) / len(cand_chunk_ids)) if cand_chunk_ids else 0.0,
        "mean_candidate_similarity": round(mean_cand_sim, 4),
        "mean_selected_similarity": round(mean_sel_sim, 4),
        "relevance_delta": round(mean_sel_sim - mean_cand_sim, 4),
        "mean_candidate_pairwise_similarity": round(mean_cand_pairwise, 4),
        "mean_selected_pairwise_similarity": round(mean_sel_pairwise, 4),
        "pairwise_similarity_reduction": round(mean_cand_pairwise - mean_sel_pairwise, 4),
        "candidate_total_chunks": len(cand_chunk_ids),
        "candidate_unique_chunks": cand_unique_chunks,
        "candidate_duplicate_rate": round(cand_dup_rate, 4),
        "candidate_unique_source_windows": cand_unique_windows,
        "selected_total_chunks": len(sel_chunk_ids),
        "selected_unique_chunks": sel_unique_chunks,
        "selected_duplicate_rate": round(sel_dup_rate, 4),
        "selected_unique_source_windows": sel_unique_windows,
    }

    # Execute Controlled Ablations over the escalated queries
    print(f"[{dataset.upper()}] Running controlled research ablations...")
    ablation_results = run_ablations(
        escalated_results=escalated_results,
        embedding_model=embedding_model,
        retrieval_k=retrieval_k,
        ablations_cfg=ablations_cfg,
    )

    primary_diagnostics["ablations"] = ablation_results
    primary_diagnostics["timing_seconds"] = time.perf_counter() - start_time

    # Save Phase 6 Artifacts
    dataset_out_dir = os.path.join(output_dir, dataset)
    os.makedirs(dataset_out_dir, exist_ok=True)

    # 1. Save evidence_selection.jsonl (one line per escalated window)
    sel_file = os.path.join(dataset_out_dir, "evidence_selection.jsonl")
    with open(sel_file, "w", encoding="utf-8") as f:
        for r in escalated_results:
            if r.selection_result:
                f.write(json.dumps(r.selection_result.to_dict()) + "\n")

    # 2. Save reranking_diagnostics.json
    diag_file = os.path.join(dataset_out_dir, "reranking_diagnostics.json")
    with open(diag_file, "w", encoding="utf-8") as f:
        json.dump(primary_diagnostics, f, indent=2)

    # 3. Save reranking_manifest.json
    sel_sha = compute_sha256(sel_file)
    diag_sha = compute_sha256(diag_file)

    manifest = {
        "dataset": dataset,
        "corpus_split": "train",
        "retrieval_k": retrieval_k,
        "evidence_k": evidence_k,
        "mmr_lambda": mmr_lambda,
        "diversity_mode": diversity_mode,
        "similarity_metric": "cosine",
        "source_commit": git_sha,
        "source_phase5_commit": phase5_commit,
        "python_version": sys.version.split()[0],
        "random_seed": seed,
        "test_used": False,  # Rule 1 Invariant
        "calibration_used_for_fitting": False,  # Calib used solely for evaluation
        "artifact_hashes": {
            "evidence_selection.jsonl": sel_sha,
            "reranking_diagnostics.json": diag_sha,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    manifest_file = os.path.join(dataset_out_dir, "reranking_manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return primary_diagnostics


def run_ablations(
    escalated_results: List[GatedEvidenceResult],
    embedding_model: TemplateTfidfEmbeddingModel,
    retrieval_k: int,
    ablations_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute Ablation A, B, and C over escalated evaluation queries."""
    # Pre-extract queries and candidate sets
    queries_and_candidates = []
    for r in escalated_results:
        if r.retrieved_evidence:
            first_ev = r.retrieved_evidence[0]
            # Construct label-free query from first evidence chunk's dataset & text
            q_obj = RetrievalQuery(
                query_window_id=r.window_id,
                dataset=first_ev.dataset,
                record_count=first_ev.record_count,
                template_ids=list(first_ev.template_ids),
                text=first_ev.text,
            )
            queries_and_candidates.append((q_obj, r.retrieved_evidence))


    # Ablation A: Phase 5 top-k retrieval (k=3) vs Phase 5 + MMR evidence selection (5 -> 3, lambda=0.70)
    top3_retrieval_sims = []
    top3_pairwise_sims = []
    mmr3_sims = []
    mmr3_pairwise_sims = []

    reranker_mmr = MMREvidenceReranker(embedding_model=embedding_model, mmr_lambda=0.70, evidence_k=3)

    for q, cands in queries_and_candidates:
        # Phase 5 top 3 candidates directly
        top3_cands = cands[:3]
        top3_sims = [c.similarity for c in top3_cands]
        top3_retrieval_sims.extend(top3_sims)
        if len(top3_cands) > 1:
            t_vecs = embedding_model.encode([c.text for c in top3_cands])
            t_norms = np.linalg.norm(t_vecs, axis=1, keepdims=True)
            safe_n = np.where(t_norms == 0.0, 1.0, t_norms)
            normed = np.where(t_norms == 0.0, 0.0, t_vecs / safe_n)
            pw = np.dot(normed, normed.T)
            top3_pairwise_sims.append(float(np.mean(pw[np.triu_indices(len(top3_cands), k=1)])))

        # MMR selection (5 -> 3)
        res = reranker_mmr.rerank_and_select(query=q, candidates=cands, retrieval_k=retrieval_k)
        for s in res.selected_evidence:
            mmr3_sims.append(s.retrieval_score)
        mmr3_pairwise_sims.append(res.metrics.get("mean_pairwise_selected_similarity", 0.0))

    ablation_a = {
        "name": "Ablation A: Phase 5 Top-3 Retrieval vs Phase 5 + MMR Evidence Selection (5 -> 3)",
        "phase5_top3_mean_relevance": round(float(np.mean(top3_retrieval_sims)), 4) if top3_retrieval_sims else 0.0,
        "phase5_top3_mean_pairwise_similarity": round(float(np.mean(top3_pairwise_sims)), 4) if top3_pairwise_sims else 0.0,
        "mmr_top3_mean_relevance": round(float(np.mean(mmr3_sims)), 4) if mmr3_sims else 0.0,
        "mmr_top3_mean_pairwise_similarity": round(float(np.mean(mmr3_pairwise_sims)), 4) if mmr3_pairwise_sims else 0.0,
        "pairwise_similarity_reduction": round(
            float(np.mean(top3_pairwise_sims) - np.mean(mmr3_pairwise_sims)), 4
        ) if top3_pairwise_sims and mmr3_pairwise_sims else 0.0,
    }

    # Ablation B: Lambda Sensitivity
    lambdas = ablations_cfg.get("lambdas", [1.0, 0.85, 0.70, 0.50, 0.0])
    ablation_b = {}
    for lam in lambdas:
        r_lam = MMREvidenceReranker(embedding_model=embedding_model, mmr_lambda=lam, evidence_k=3)
        l_sims = []
        l_pws = []
        for q, cands in queries_and_candidates:
            res = r_lam.rerank_and_select(query=q, candidates=cands, retrieval_k=retrieval_k)
            for s in res.selected_evidence:
                l_sims.append(s.retrieval_score)
            l_pws.append(res.metrics.get("mean_pairwise_selected_similarity", 0.0))

        ablation_b[f"lambda_{lam}"] = {
            "lambda": lam,
            "mean_relevance": round(float(np.mean(l_sims)), 4) if l_sims else 0.0,
            "mean_pairwise_similarity": round(float(np.mean(l_pws)), 4) if l_pws else 0.0,
        }

    # Ablation C: Evidence Budget Compression
    evidence_ks = ablations_cfg.get("evidence_ks", [1, 3, 5])
    ablation_c = {}
    for k_val in evidence_ks:
        r_k = MMREvidenceReranker(embedding_model=embedding_model, mmr_lambda=0.70, evidence_k=k_val)
        k_sims = []
        k_pws = []
        for q, cands in queries_and_candidates:
            res = r_k.rerank_and_select(query=q, candidates=cands, retrieval_k=retrieval_k)
            for s in res.selected_evidence:
                k_sims.append(s.retrieval_score)
            k_pws.append(res.metrics.get("mean_pairwise_selected_similarity", 0.0))

        ablation_c[f"k_{k_val}"] = {
            "evidence_k": k_val,
            "mean_relevance": round(float(np.mean(k_sims)), 4) if k_sims else 0.0,
            "mean_pairwise_similarity": round(float(np.mean(k_pws)), 4) if k_pws else 0.0,
            "compression_ratio": round(float(k_val / retrieval_k), 4),
        }

    return {
        "ablation_a": ablation_a,
        "ablation_b": ablation_b,
        "ablation_c": ablation_c,
    }


def main() -> None:
    """CLI entrypoint for Phase 6 execution."""
    parser = argparse.ArgumentParser(description="SentinelLog Phase 6: Retrieval Reranking & Evidence Selection")
    parser.add_argument("--config", type=str, default="configs/phase6.yaml", help="Path to Phase 6 config")
    parser.add_argument("--datasets", nargs="+", default=["hdfs", "bgl"], help="Datasets to evaluate")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    data_dirs = config.get("data_dirs", {})
    output_dir = config.get("output_dir", "results/phase6")
    phase5_dir = config.get("phase5_dir", "results/phase5")
    os.makedirs(output_dir, exist_ok=True)

    summary_report: Dict[str, Any] = {
        "phase": 6,
        "title": "SentinelLog Phase 6: Retrieval Reranking and Evidence Selection",
        "datasets": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_commit": get_git_commit_sha(),
        "test_used": False,
    }

    for dataset in args.datasets:
        ds_dir = data_dirs.get(dataset)
        if not ds_dir or not os.path.exists(ds_dir):
            print(f"Skipping {dataset}: data directory {ds_dir} not found.")
            continue

        train_path = os.path.join(ds_dir, "train.jsonl")
        calib_path = os.path.join(ds_dir, "calibration.jsonl")
        train_windows = load_windows(train_path, "train")
        calib_windows = load_windows(calib_path, "calibration")

        phase4_ckpt = f"results/phase4/{dataset}/b2_model.pt"

        diag = run_phase6_dataset(
            dataset=dataset,
            train_windows=train_windows,
            calib_windows=calib_windows,
            config=config,
            output_dir=output_dir,
            phase5_dir=phase5_dir,
            phase4_checkpoint_path=phase4_ckpt if os.path.exists(phase4_ckpt) else None,
        )
        summary_report["datasets"][dataset] = diag

    # Write summary report JSON
    report_json_path = os.path.join(output_dir, "phase6_report.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    # Write summary report Markdown
    report_md_path = os.path.join(output_dir, "phase6_report.md")
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Phase 6 Summary Report: Retrieval Reranking & Evidence Selection\n\n")
        f.write(f"- **Execution Timestamp**: {summary_report['timestamp']}\n")
        f.write(f"- **Git Commit**: `{summary_report['source_commit']}`\n")
        f.write(f"- **Rule 1 Enforced (Test Used)**: `{summary_report['test_used']}`\n\n")

        for ds_name, ds_diag in summary_report["datasets"].items():
            f.write(f"## Dataset: {ds_name.upper()}\n\n")
            f.write(f"- **Total Evaluated Windows**: {ds_diag['total_windows_evaluated']}\n")
            f.write(f"- **AUTO-CLEAR Windows**: {ds_diag['auto_clear_count']} ({ds_diag['auto_clear_rate'] * 100:.2f}%)\n")
            f.write(f"- **ESCALATE Windows**: {ds_diag['escalated_count']} ({ds_diag['escalation_rate'] * 100:.2f}%)\n")
            f.write(f"- **Retrieval Candidates (k)**: {ds_diag['retrieval_k']}\n")
            f.write(f"- **Selected Evidence Budget (k)**: {ds_diag['evidence_k']}\n")
            f.write(f"- **MMR Lambda**: {ds_diag['mmr_lambda']}\n")
            f.write(f"- **Compression Ratio**: {ds_diag['evidence_compression_ratio'] * 100:.1f}%\n")
            f.write(f"- **Mean Relevance**: Candidates = {ds_diag['mean_candidate_similarity']}, Selected = {ds_diag['mean_selected_similarity']} (Delta: {ds_diag['relevance_delta']})\n")
            f.write(f"- **Mean Pairwise Similarity**: Candidates = {ds_diag['mean_candidate_pairwise_similarity']}, Selected = {ds_diag['mean_selected_pairwise_similarity']} (Reduction: {ds_diag['pairwise_similarity_reduction']})\n")
            f.write(f"- **Duplicate Selection Rate**: Candidates = {ds_diag['candidate_duplicate_rate'] * 100:.2f}%, Selected = {ds_diag['selected_duplicate_rate'] * 100:.2f}%\n\n")

            abls = ds_diag.get("ablations", {})
            f.write("### Controlled Research Ablations\n\n")
            f.write("#### Ablation A: Top-3 Retrieval vs MMR Selection (5 -> 3)\n")
            ab_a = abls.get("ablation_a", {})
            f.write(f"- Phase 5 Top-3 Relevance: {ab_a.get('phase5_top3_mean_relevance')}, Pairwise Sim: {ab_a.get('phase5_top3_mean_pairwise_similarity')}\n")
            f.write(f"- MMR (5 -> 3) Relevance: {ab_a.get('mmr_top3_mean_relevance')}, Pairwise Sim: {ab_a.get('mmr_top3_mean_pairwise_similarity')}\n")
            f.write(f"- Pairwise Redundancy Reduction: {ab_a.get('pairwise_similarity_reduction')}\n\n")

            f.write("#### Ablation B: Lambda Sensitivity\n")
            f.write("| Lambda | Relevance | Pairwise Sim |\n")
            f.write("|---|---|---|\n")
            for l_key, l_data in abls.get("ablation_b", {}).items():
                f.write(f"| {l_data['lambda']} | {l_data['mean_relevance']} | {l_data['mean_pairwise_similarity']} |\n")
            f.write("\n")

            f.write("#### Ablation C: Evidence Budget Compression\n")
            f.write("| Evidence Budget (k) | Compression | Relevance | Pairwise Sim |\n")
            f.write("|---|---|---|---|\n")
            for k_key, k_data in abls.get("ablation_c", {}).items():
                f.write(f"| {k_data['evidence_k']} | {k_data['compression_ratio'] * 100:.1f}% | {k_data['mean_relevance']} | {k_data['mean_pairwise_similarity']} |\n")
            f.write("\n---\n\n")

    print(f"Phase 6 execution complete. Artifacts written to {output_dir}")


if __name__ == "__main__":
    main()
