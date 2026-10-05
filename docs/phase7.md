# SentinelLog Phase 7: Citation & Provenance Engine

## 1. Overview & Research Objective

Phase 7 introduces the **Citation and Provenance Engine** for SentinelLog. Following Phase 5 (TRAIN-only contextual candidate retrieval) and Phase 6 (MMR diversity-aware evidence selection), Phase 7 establishes end-to-end auditability and source addressability for all retrieved evidence.

```
RAW LOG WINDOW
      ↓
Phase 4 Selective Gate
      ↓
┌───────────────────────┬────────────────────────────────────────┐
│ AUTO-CLEAR (95-98%)   │ ESCALATE (2-5%)                        │
│ Bypasses Retrieval,   │ 1. Phase 5 Candidate Retrieval (k=5)   │
│ Reranking & Provenance│ 2. Phase 6 MMR Selection (k=3)         │
│ (Zero LLM/Audit Cost) │ 3. Phase 7 Citation & Provenance       │
│                       │ 4. Auditable Citation Bundle           │
│                       │ 5. STOP (No LLM generation in Phase 7) │
└───────────────────────┴────────────────────────────────────────┘
```

**Central Research Principle**:
> *A citation is NOT merely an opaque chunk ID. A valid provenance record must allow any independent reviewer or automated auditor to resolve: exactly where did this evidence originate, in what dataset partition, at what physical coordinates, and has its underlying content remained untampered?*

**Absolute Scope Boundary**:
Phase 7 is strictly concerned with **evidence provenance, source-location resolution, deterministic citation formatting, and content-hash integrity verification**.
**NO LLM generation, OpenAI/Anthropic APIs, RAG answer generation, prompt engineering, explanation synthesis, faithfulness checking, hallucination detection, FastAPI serving, or Docker containerization are implemented in Phase 7.**

---

## 2. Provenance Chain & Data Model

Every evidence unit is traceable through a rigid cryptographic chain:

$$\text{citation\_id} \longrightarrow \text{chunk\_id} \longrightarrow \text{source\_window\_id} \longrightarrow \text{source\_artifact} \longrightarrow \text{source\_location} \longrightarrow \text{content\_hash}$$

### 2.1 Core Dataclasses

1. [`SourceArtifact`](file:///d:/FaultSentinel/sentinellog/provenance/schemas.py#L31-L47):
   - `dataset`: Target dataset (`'hdfs'` or `'bgl'`).
   - `split`: Partition name (`'train'`, strictly TRAIN-only).
   - `artifact_path`: Physical file path (e.g., `data/processed/hdfs/train.jsonl`).
   - `artifact_sha256`: SHA-256 fingerprint of the physical processed data file.
   - `pipeline_version`: Version string from Phase 2 manifest.
   - `raw_sha256`: SHA-256 of the original raw log file acquired from Zenodo.
2. [`SourceLocation`](file:///d:/FaultSentinel/sentinellog/provenance/schemas.py#L12-L28):
   - `source_file`: File path containing the window record.
   - `line_start`: 1-indexed raw log line start.
   - `line_end`: 1-indexed raw log line end.
   - `record_count`: Number of raw log events in the window.
   - `session_id`: HDFS block ID (e.g., `blk_-1608999687919862906`) or `None` for BGL.
   - `timestamp_start` / `timestamp_end`: Epoch time boundaries.
3. [`EvidenceProvenance`](file:///d:/FaultSentinel/sentinellog/provenance/schemas.py#L50-L94):
   - Ties `citation_id`, `chunk_id`, `source_artifact`, `source_location`, and `content_hash` into an immutable verifiable record.
4. [`Citation`](file:///d:/FaultSentinel/sentinellog/provenance/schemas.py#L97-L140):
   - Holds human-readable `citation_text`, retrieval score, selection score, rank, and complete provenance.
5. [`CitationBundle`](file:///d:/FaultSentinel/sentinellog/provenance/schemas.py#L143-L186):
   - Holds the ordered citations for an escalated window with a deterministic `bundle_id`.

---

## 3. Cryptographic Derivations & Algorithms

### 3.1 Content Fingerprint (`content_hash`)
Computed deterministically via SHA-256 over the canonical observable template token text:
$$\text{content\_hash} = \text{SHA256}(\text{canonical\_text})$$
where `canonical_text` is the space-separated observable template token string (e.g., `"template_1 template_2"`).

### 3.2 Deterministic Citation Identifier (`citation_id`)
Derived via canonical serialization of the spatial and identity coordinates:
$$\text{citation\_id} = \text{SHA256}(\text{dataset} : \text{split} : \text{chunk\_id} : \text{source\_window\_id} : \text{line\_start} : \text{line\_end})$$

### 3.3 Deterministic Citation Bundle Identifier (`bundle_id`)
Derived via canonical concatenation of the ordered citation identifiers:
$$\text{bundle\_id} = \text{SHA256}(\text{dataset} : \text{provenance\_version} : \text{citation\_id}_1, \dots, \text{citation\_id}_k)$$
This guarantees that changing any evidence item or evidence order alters the `bundle_id`.

### 3.4 Canonical Citation Text
Format:
- **HDFS**: `[HDFS | train | window=hdfs_session_blk_-7598755695670995274 | lines=2322-37840 | records=14]`
- **BGL**: `[BGL | train | window=bgl_window_0000147 | lines=14701-14800 | records=100]`

---

## 4. Source Resolution & Round-Trip Verification

### 4.1 Resolution Engine ([`SourceResolver`](file:///d:/FaultSentinel/sentinellog/provenance/resolver.py#L27-L125))
- Resolves any cited evidence back to its exact line coordinates in `data/processed/<dataset>/train.jsonl`.
- Fails closed with [`ProvenanceResolutionError`](file:///d:/FaultSentinel/sentinellog/provenance/resolver.py#L21-L24) if the source window cannot be found.
- Forbids access to test data via [`guard_no_test_split`](file:///d:/FaultSentinel/sentinellog/scoring/artifacts.py#L21-L46) and rejects non-train partitions via [`guard_train_split_only`](file:///d:/FaultSentinel/sentinellog/retrieval/guards.py#L26-L59).

### 4.2 Round-Trip Integrity Verification ([`ProvenanceVerifier`](file:///d:/FaultSentinel/sentinellog/provenance/verifier.py#L28-L170))
For every citation:
1. Recomputes `expected_citation_id` and verifies identity match.
2. Resolves physical source window from disk.
3. Recomputes `content_hash` over observable template tokens.
4. Compares stored `content_hash` against recomputed hash.
5. Verifies physical source artifact SHA-256 against known dataset baseline.
6. Returns `VALID`, `INVALID` (if corrupted), or `UNRESOLVED` (if missing).

---

## 5. Experimental Results & Verification

Phase 7 was executed over the Phase 6 evidence selections for both HDFS and BGL.

### 5.1 Summary Statistics

| Metric | HDFS | BGL |
|---|---|---|
| Escalated Query Windows | 39 | 2 |
| Total Citation Bundles | 39 | 2 |
| Total Citations Generated | 117 | 6 |
| Unique Citation IDs | 9 | 3 |
| Unique Chunks Cited | 9 | 3 |
| Unique Source Windows Cited | 9 | 3 |
| Source Resolution Success Rate | **100.00%** (117/117) | **100.00%** (6/6) |
| Integrity Verification Success Rate | **100.00%** (117/117) | **100.00%** (6/6) |
| Invalid Citations Count | **0** | **0** |
| Unresolved Citations Count | **0** | **0** |
| All Bundles Fully Verified | **True** | **True** |

### 5.2 Deterministic Artifact Hashes
- HDFS `citations.jsonl`: `cead5f2369368f21329087ae5e6ca4e181f7277403883aff552c0744e3e776d4`
- BGL `citations.jsonl`: `a104ea06f438f77a13d5e8ecf5cf248a4181f69ddf656972104cf9d15d8666b3`

---

## 6. Concrete Citation Examples

### 6.1 HDFS Example
- **Query Window**: `hdfs_session_blk_-7628164677193243450`
- **Bundle ID**: `a195417910fe02c806a400ded675735ec900a952c4704f2b9eb11debde8f8183`
- **Citation 1**:
  - `citation_id`: `305cfaab8b3fccba7eb477a3d9059f3e48816828277ee7f8a7e0c7e2c90c74fb`
  - `citation_text`: `[HDFS | train | window=hdfs_session_blk_-7598755695670995274 | lines=2322-37840 | records=14]`
  - `content_hash`: `47baebcb4c457813a0784260ef9a3df7a7605d336829e79fa7b864a78c1228fe`
  - `source_file`: `data/processed/hdfs/train.jsonl`
  - `source_artifact_hash`: `27ba33bacaf1d09591ffbdc0784a68350f693503aeda6006a2d5440502b8506e`

### 6.2 BGL Example
- **Query Window**: `bgl_window_0000349`
- **Bundle ID**: `883108ba686b517c23137e3b700e27957d21d1a95347763f14fed1bfa5910224`
- **Citation 1**:
  - `citation_id`: `6677bfa3da93a7e3a936a287fa4757cff545b7367c30d9779df50c5ce68b449b`
  - `citation_text`: `[BGL | train | window=bgl_window_0000147 | lines=14701-14800 | records=100]`
  - `content_hash`: `05e5d32658b1fbfe3299778216ef32ca30b95eb7c0a969f64bf1d0c4104d49a4`
  - `source_file`: `data/processed/bgl/train.jsonl`
  - `source_artifact_hash`: `d21c41ca02daa15416c88ee22e54c5a1b793710064c381e3bf60d62dfc008d94`

---

## 7. Research Limitations

1. **Syntactic vs Semantic Verification**: Provenance proves that an exact evidence log chunk originated at a specific source file location and has not been altered; it does not guarantee that the evidence is causally related to the query incident.
2. **No Hallucination Prevention**: Having verifiable citations does not guarantee that a downstream LLM will faithfully cite or interpret them without hallucinating. Downstream explanation and faithfulness layers must independently evaluate citation alignment.
3. **Repeated Log Workflows**: Because system logs have structural template repetition, multiple distinct source windows can share identical template sequences, resulting in distinct citation IDs pointing to different physical line ranges with identical content hashes.
4. **Offline Local Filesystem Scope**: Source resolution operates over local filesystem artifacts; distributed log stores (e.g., remote Elasticsearch/S3) would require corresponding distributed storage adapters.
