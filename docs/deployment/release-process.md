# SentinelLog Release Process & Versioning (Phase 15)

## 1. Versioning Specification (Rule 28)

SentinelLog strictly adheres to Semantic Versioning (`vMAJOR.MINOR.PATCH`):
- Format: `v0.15.0`
- Current Phase Release: `v0.15.0`
- Git Tag: `v0.15.0`

## 2. Immutable Image Identifiers (Rule 13, Rule 81)

The tag `:latest` is **strictly prohibited** as a release identifier in production environments. Every release must be referenced by an immutable combination:
1. Pinned Semantic Version tag: `v0.15.0`
2. Pinned Git Commit SHA: `git-e8dfa6f`
3. Immutable Cryptographic Digest: `sha256:7f9b8c1a...`

## 3. Release Manifest Structure

Every release produces an immutable manifest stored in `results/phase15/release_manifest.json`:
```json
{
  "release_version": "0.15.0",
  "git_commit": "e8dfa6f",
  "image_tag": "v0.15.0",
  "image_digest": "sha256:7f9b8c1a2e3d4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
  "terraform_version": ">= 1.5.0",
  "build_timestamp": "2026-10-07T07:35:00Z",
  "frozen_benchmark_hash": "d3fdf5e83bbb24040416f11637ace5f181bb3db028b2aa61fe0e343ac20eaca3"
}
```

## 4. Release Promotion Workflow

```
[ Git Release Tag (e.g. v0.15.0) ]
               │
               ▼
   [ Build & Scan Immutable ECR Image ]
               │
               ▼
   [ Deploy to Staging ECS Fargate ]
               │
               ▼
   [ Execute Automated Staging Smoke Tests ]
               │
     ┌─────────┴─────────┐
  [ PASS ]            [ FAIL ]
     │                   │
     ▼                   ▼
[ Release Gate Approval ] [ Abort & Alert ]
     │
     ▼
[ Production Rolling Update (Min 100%, Max 200%) ]
     │
     ▼
[ Production Smoke & Health Verification ]
```
