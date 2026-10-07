"""Deterministic secret scanning utility for repository files and text payloads."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# High-confidence credential and key patterns
SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("AWS_ACCESS_KEY", re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}")),
    ("GITHUB_TOKEN", re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,255}")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----")),
    ("GENERIC_BEARER_TOKEN", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{25,}")),
    ("HARDCODED_SECRET_ASSIGNMENT", re.compile(r"(?i)(?:api_key|secret_key|client_secret|auth_token)\s*=\s*['\"][A-Za-z0-9_\-\.]{16,}['\"]")),
]

# Patterns explicitly allowed or marked as placeholders / test values
FALSE_POSITIVE_ALLOWLIST = [
    re.compile(r"placeholder", re.IGNORECASE),
    re.compile(r"mock-", re.IGNORECASE),
    re.compile(r"dummy", re.IGNORECASE),
    re.compile(r"your-api-key-here", re.IGNORECASE),
    re.compile(r"REDACTED", re.IGNORECASE),
]


def scan_text(text: str, context_source: str = "text") -> List[Dict[str, Any]]:
    """Scan string content for exposed secrets.
    
    Returns list of findings: {"pattern_name": ..., "snippet": ..., "source": ...}
    """
    findings = []
    for name, pattern in SECRET_PATTERNS:
        matches = pattern.finditer(text)
        for m in matches:
            matched_str = m.group(0)
            # Check false positive allowlist
            if any(fp.search(matched_str) for fp in FALSE_POSITIVE_ALLOWLIST):
                continue
            findings.append({
                "pattern_name": name,
                "source": context_source,
                "snippet": matched_str[:8] + "..." + matched_str[-4:] if len(matched_str) > 12 else "[SECRET]",
                "start": m.start(),
                "end": m.end(),
            })
    return findings


def scan_repository(repo_root: str = ".") -> List[Dict[str, Any]]:
    """Scan all tracked non-binary files in the repository for high-confidence secrets."""
    findings = []
    root_path = Path(repo_root).resolve()

    # Skip virtual environments, git metadata, cache, node_modules, and test files with synthetic test cases
    skip_dirs = {".git", ".venv", "venv", "node_modules", ".pytest_cache", "__pycache__", "dist", "build", "tests"}
    skip_files = {".env.example", "package-lock.json"}

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for f in filenames:
            if f in skip_files:
                continue
            file_path = Path(dirpath) / f
            # Only scan text files
            if file_path.suffix.lower() in (".py", ".json", ".yaml", ".yml", ".md", ".ts", ".tsx", ".js", ".html"):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    rel_path = file_path.relative_to(root_path).as_posix()
                    file_findings = scan_text(content, context_source=rel_path)
                    # Exclude the scanner itself from self-matching pattern definitions
                    if "secret_scanner.py" in rel_path or "test_security.py" in rel_path:
                        continue
                    findings.extend(file_findings)
                except Exception:
                    continue

    return findings
