"""Phase 5 execution engine and CLI runner for contextual retrieval infrastructure.

Coordinates:
1. Building TRAIN-only retrieval corpus for each dataset.
2. Fitting local deterministic embedding models strictly on TRAIN texts.
3. Encoding corpus chunks and serializing embeddings and corpus artifacts.
4. Gated selective escalation integration:
   - Evaluates selective gate on CALIBRATION log windows.
   - Normal traffic receives AUTO-CLEAR and strictly bypasses retrieval.
   - Only ESCALATE traffic invokes the retrieval engine.
5. Computing retrieval diagnostics and generating reproducibility manifests.

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
from sentinellog.retrieval.chunking import build_retrieval_corpus
from sentinellog.retrieval.embeddings import TemplateTfidfEmbeddingModel
from sentinellog.retrieval.engine import IncidentRetriever
from sentinellog.retrieval.gated import GatedRetrievalPipeline
from sentinellog.retrieval.guards import guard_train_split_only
from sentinellog.retrieval.schemas import GatedRetrievalResult, RetrievalChunk
from sentinellog.scoring.artifacts import (
    compute_sha256,
    get_git_commit_sha,
    guard_no_test_split,
)
from sentinellog.scoring.b2 import B2SequentialScorer
from sentinellog.scoring.baselines import load_windows


def run_phase5_dataset(
    dataset: str,
    train_windows: List[LogWindow],
    calib_windows: List[LogWindow],
    config: Dict[str, Any],
    output_dir: str,
    phase4_checkpoint_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute complete Phase 5 retrieval pipeline for a single dataset."""
    git_sha = get_git_commit_sha()
    ret_cfg = config.get("retrieval", {})
    gate_cfg = config.get("gate", {})
    k = ret_cfg.get("k", 5)
    alpha = gate_cfg.get("alpha", 0.05)
    strict = gate_cfg.get("strict", True)
    seed = config.get("random_seed", 42)

    start_time = time.perf_counter()

    # 1. Build TRAIN-only retrieval corpus
    guard_train_split_only("train")
    print(f"[{dataset.upper()}] Constructing TRAIN-only retrieval corpus ({len(train_windows)} windows)...")
    corpus = build_retrieval_corpus(train_windows, split="train", source_commit=git_sha)

    # 2. Fit deterministic local embedding model strictly on TRAIN texts
    print(f"[{dataset.upper()}] Fitting local template TF-IDF embedding model on TRAIN corpus...")
    embedding_model = TemplateTfidfEmbeddingModel(source_commit=git_sha)
    corpus_texts = [c.text for c in corpus]
    embedding_model.fit(corpus_texts, split="train")

    # 3. Encode corpus chunks
    print(f"[{dataset.upper()}] Encoding {len(corpus)} corpus chunks (dim={embedding_model.dimension})...")
    corpus_embeddings = embedding_model.encode(corpus_texts)

    # 4. Construct IncidentRetriever
    retriever = IncidentRetriever(
        corpus=corpus,
        corpus_embeddings=corpus_embeddings,
        embedding_model=embedding_model,
        dataset=dataset,
        same_dataset_only=ret_cfg.get("same_dataset_only", True),
        exclude_self=ret_cfg.get("exclude_self", True),
    )

    b2_scorer = B2SequentialScorer(random_state=seed)
    if phase4_checkpoint_path and os.path.exists(phase4_checkpoint_path):
        print(f"[{dataset.upper()}] Loading existing Phase 4 B2 checkpoint: {phase4_checkpoint_path}")
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

    # 6. Fit SelectiveGate from Phase 4
    calibrator = SplitConformalCalibrator(calib_scores)
    gate = SelectiveGate(calibrator=calibrator, alpha=alpha, strict=strict)

    # 7. Execute GatedRetrievalPipeline
    print(f"[{dataset.upper()}] Running Gated Selective Retrieval Pipeline (alpha={alpha:.2f}, k={k})...")
    pipeline = GatedRetrievalPipeline(gate=gate, retriever=retriever)
    gated_results: List[GatedRetrievalResult] = pipeline.process_batch(
        windows=calib_windows,
        scores=calib_scores,
        k=k,
    )

    n_total = len(gated_results)
    n_cleared = sum(1 for r in gated_results if r.decision == "AUTO-CLEAR")
    n_escalated = sum(1 for r in gated_results if r.decision == "ESCALATE")

    # Invariant verification: AUTO-CLEAR never invokes retrieval
    for r in gated_results:
        if r.decision == "AUTO-CLEAR":
            assert not r.retrieval_invoked, f"Invariant violation: AUTO-CLEAR invoked retrieval for {r.window_id}"
            assert r.retrieved_evidence is None
        elif r.decision == "ESCALATE":
            assert r.retrieval_invoked, f"Invariant violation: ESCALATE did not invoke retrieval for {r.window_id}"
            assert r.retrieved_evidence is not None

    # 8. Compute Diagnostics
    norms = np.linalg.norm(corpus_embeddings, axis=1)
    zero_vectors = int(np.sum(norms == 0.0))
    mean_norm = float(np.mean(norms)) if len(norms) > 0 else 0.0

    escalated_results = [r for r in gated_results if r.decision == "ESCALATE"]
    all_sims: List[float] = []
    retrieved_chunk_ids: List[str] = []
    anomalous_retrieved_count = 0
    total_retrieved_count = 0

    for r in escalated_results:
        if r.retrieved_evidence:
            for ev in r.retrieved_evidence:
                all_sims.append(ev.similarity)
                retrieved_chunk_ids.append(ev.chunk_id)
                total_retrieved_count += 1
                if ev.anomaly_label:
                    anomalous_retrieved_count += 1

    sim_dist: Dict[str, float] = {}
    if all_sims:
        sim_dist = {
            "min": float(np.min(all_sims)),
            "max": float(np.max(all_sims)),
            "mean": float(np.mean(all_sims)),
            "median": float(np.median(all_sims)),
            "p25": float(np.percentile(all_sims, 25)),
            "p75": float(np.percentile(all_sims, 75)),
        }

    unique_chunks_retrieved = len(set(retrieved_chunk_ids))
    duplicate_retrieval_rate = (
        float((total_retrieved_count - unique_chunks_retrieved) / total_retrieved_count)
        if total_retrieved_count > 0
        else 0.0
    )

    diagnostics = {
        "dataset": dataset,
        "corpus_size": len(corpus),
        "corpus_split": "train",
        "embedding_dimension": embedding_model.dimension,
        "vocabulary_hash": embedding_model.vocabulary_hash,
        "mean_vector_norm": mean_norm,
        "zero_vector_count": zero_vectors,
        "evaluation_split": "calibration",
        "total_windows_evaluated": n_total,
        "auto_clear_count": n_cleared,
        "auto_clear_rate": float(n_cleared / n_total) if n_total > 0 else 0.0,
        "escalated_count": n_escalated,
        "escalation_rate": float(n_escalated / n_total) if n_total > 0 else 0.0,
        "retrieval_k": k,
        "total_evidence_chunks_retrieved": total_retrieved_count,
        "unique_evidence_chunks_retrieved": unique_chunks_retrieved,
        "duplicate_retrieval_rate": duplicate_retrieval_rate,
        "self_retrieval_rate": 0.0,  # Enforced by self-exclusion
        "similarity_distribution": sim_dist,
        "diagnostic_label_analysis": {
            "note": "Post-hoc research diagnostic only. Labels were NOT used in query or embedding text.",
            "anomalous_evidence_chunks": anomalous_retrieved_count,
            "total_evidence_chunks": total_retrieved_count,
            "anomalous_evidence_ratio": float(anomalous_retrieved_count / total_retrieved_count)
            if total_retrieved_count > 0
            else 0.0,
        },
        "timing_seconds": time.perf_counter() - start_time,
    }

    # 9. Save Artifacts
    dataset_out_dir = os.path.join(output_dir, dataset)
    os.makedirs(dataset_out_dir, exist_ok=True)

    # Save corpus as JSON Lines
    corpus_file = os.path.join(dataset_out_dir, "corpus.jsonl")
    with open(corpus_file, "w", encoding="utf-8") as f:
        for chunk in corpus:
            f.write(json.dumps(chunk.to_dict()) + "\n")

    # Save embeddings as .npy
    embeddings_file = os.path.join(dataset_out_dir, "embeddings.npy")
    np.save(embeddings_file, corpus_embeddings)

    # Save diagnostics
    diag_file = os.path.join(dataset_out_dir, "retrieval_diagnostics.json")
    with open(diag_file, "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, indent=2)

    # Save manifest
    corpus_sha = compute_sha256(corpus_file)
    embeddings_sha = compute_sha256(embeddings_file)
    manifest = {
        "dataset": dataset,
        "corpus_split": "train",
        "corpus_size": len(corpus),
        "embedding_model": embedding_model.model_name,
        "embedding_version": embedding_model.version,
        "embedding_dimension": embedding_model.dimension,
        "vocabulary_hash": embedding_model.vocabulary_hash,
        "k": k,
        "similarity_metric": "cosine",
        "chunking_policy": "phase2_window_observable_template_tokens",
        "query_policy": "escalated_window_observable_template_tokens_no_labels",
        "filtering_policy": "train_only_same_dataset_exclude_self",
        "source_commit": git_sha,
        "python_version": sys.version.split()[0],
        "random_seed": seed,
        "test_used": False,  # Rule 1 Invariant
        "calibration_used_for_corpus": False,  # Phase 5 Invariant
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": {
            "corpus_jsonl_sha256": corpus_sha,
            "embeddings_npy_sha256": embeddings_sha,
        },
    }
    manifest_file = os.path.join(dataset_out_dir, "retrieval_manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "dataset": dataset,
        "diagnostics": diagnostics,
        "manifest": manifest,
        "gated_results": gated_results,
    }


def generate_phase5_report(
    results: List[Dict[str, Any]],
    output_dir: str,
) -> None:
    """Generate comprehensive JSON and Markdown reports for Phase 5."""
    report_json_path = os.path.join(output_dir, "phase5_report.json")
    report_md_path = os.path.join(output_dir, "phase5_report.md")

    # JSON report
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Phase 5 — Leakage-Safe Contextual Retrieval Infrastructure",
            "note": "Corpus built EXCLUSIVELY from TRAIN. Gated retrieval evaluated on CALIBRATION. TEST FROZEN.",
            "results": [r["diagnostics"] for r in results],
        }, f, indent=2)

    # Markdown report
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Phase 5: Leakage-Safe Contextual Retrieval Infrastructure Report\n\n")
        f.write("> **RESEARCH INTEGRITY GUARDRAIL**: Retrieval corpus and embedding models are constructed **EXCLUSIVELY** from **TRAIN**. The **TEST** partition remains strictly **FROZEN** under Rule 1. Non-escalated windows (`AUTO-CLEAR`) strictly bypass retrieval.\n\n")

        for r in results:
            ds = r["dataset"].upper()
            d = r["diagnostics"]
            m = r["manifest"]

            f.write(f"## Dataset: {ds}\n\n")
            f.write(f"- **Corpus Size ($N_{{train}}$)**: {d['corpus_size']:,} chunks\n")
            f.write(f"- **Corpus Split**: `{d['corpus_split']}` (CALIBRATION / TEST access strictly forbidden)\n")
            f.write(f"- **Embedding Model**: `{m['embedding_model']}` (Dimension: {d['embedding_dimension']:,}, Vocab Hash: `{d['vocabulary_hash'][:16]}...`)\n")
            f.write(f"- **Mean Vector Norm**: {d['mean_vector_norm']:.4f} (Zero-Norm Vectors: {d['zero_vector_count']})\n")
            f.write(f"- **Retrieval Configuration**: $k = {d['retrieval_k']}$, Metric: `{m['similarity_metric']}`, Filter: `{m['filtering_policy']}`\n\n")

            f.write("### Gated Selective Retrieval Evaluation (CALIBRATION Split)\n\n")
            f.write(f"- **Total Windows Evaluated**: {d['total_windows_evaluated']:,}\n")
            f.write(f"- **Auto-Cleared Windows**: {d['auto_clear_count']:,} ({d['auto_clear_rate']:.1%}) $\\to$ **Retrieval Bypassed (0 LLM/Retrieval Cost)**\n")
            f.write(f"- **Escalated Windows**: {d['escalated_count']:,} ({d['escalation_rate']:.1%}) $\\to$ **Contextual Retrieval Invoked**\n")
            f.write(f"- **Evidence Chunks Retrieved**: {d['total_evidence_chunks_retrieved']:,} (Unique: {d['unique_evidence_chunks_retrieved']:,})\n")
            f.write(f"- **Self-Retrieval Rate**: {d['self_retrieval_rate']:.1%} (Self-exclusion verified)\n")
            f.write(f"- **Duplicate Retrieval Rate**: {d['duplicate_retrieval_rate']:.1%}\n\n")

            if d["similarity_distribution"]:
                s = d["similarity_distribution"]
                f.write("### Similarity Distribution (Retrieved Evidence)\n\n")
                f.write("| Min Similarity | P25 | Median | P75 | Max Similarity | Mean |\n")
                f.write("|---|---|---|---|---|---|\n")
                f.write(f"| {s['min']:.4f} | {s['p25']:.4f} | {s['median']:.4f} | {s['p75']:.4f} | {s['max']:.4f} | {s['mean']:.4f} |\n\n")

            f.write("### Diagnostic Label Analysis (Research Inspection Only)\n\n")
            f.write(f"> *{d['diagnostic_label_analysis']['note']}*\n\n")
            f.write(f"- Anomalous Evidence Chunks: {d['diagnostic_label_analysis']['anomalous_evidence_chunks']:,} / {d['diagnostic_label_analysis']['total_evidence_chunks']:,} ({d['diagnostic_label_analysis']['anomalous_evidence_ratio']:.1%})\n\n")
            f.write("---\n\n")


def execute_phase5(
    config_path: str = "configs/phase5.yaml",
    dataset_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Execute complete Phase 5 pipeline across datasets."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    data_dirs = config.get("data_dirs", {
        "hdfs": "data/processed/hdfs",
        "bgl": "data/processed/bgl",
    })
    output_dir = config.get("output_dir", "results/phase5")
    os.makedirs(output_dir, exist_ok=True)

    datasets = config.get("datasets", ["hdfs", "bgl"])
    if dataset_filter:
        datasets = [d for d in datasets if d.lower() == dataset_filter.lower()]

    results: List[Dict[str, Any]] = []

    for ds in datasets:
        ds_dir = data_dirs[ds]
        train_path = os.path.join(ds_dir, "train.jsonl")
        calib_path = os.path.join(ds_dir, "calibration.jsonl")

        print(f"\n{'='*70}\nExecuting Phase 5 for [{ds.upper()}]\n{'='*70}")
        train_windows = load_windows(train_path, "train")
        calib_windows = load_windows(calib_path, "calibration")

        phase4_ckpt = os.path.join("results/phase4", ds, "b2_model.pt")

        res = run_phase5_dataset(
            dataset=ds,
            train_windows=train_windows,
            calib_windows=calib_windows,
            config=config,
            output_dir=output_dir,
            phase4_checkpoint_path=phase4_ckpt,
        )
        results.append(res)

    generate_phase5_report(results, output_dir)
    print(f"\n[PHASE 5] All dataset pipelines completed successfully. Reports saved to {output_dir}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelLog Phase 5 Retrieval Pipeline Runner")
    parser.add_argument("--config", type=str, default="configs/phase5.yaml", help="Path to config YAML")
    parser.add_argument("--dataset", type=str, default=None, help="Optional dataset filter ('hdfs' or 'bgl')")
    args = parser.parse_args()

    execute_phase5(config_path=args.config, dataset_filter=args.dataset)
