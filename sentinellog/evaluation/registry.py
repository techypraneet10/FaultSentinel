"""Structured experiment registry for Phase 12 evaluation experiments."""

import json
import os
from pathlib import Path
from typing import Any, Dict


class ExperimentRegistry:
    """Manages persistent experiment records in results/phase12/experiments/."""

    def __init__(self, root_dir: str = "results/phase12/experiments"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def register_experiment(
        self,
        experiment_id: str,
        config: Dict[str, Any],
        manifest: Dict[str, Any],
        metrics: Dict[str, Any],
        confusion_matrix: Dict[str, int],
        provenance_metadata: Dict[str, Any],
    ) -> Path:
        """Register a completed evaluation experiment in its own directory."""
        exp_dir = self.root_dir / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        with open(exp_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, sort_keys=True)

        with open(exp_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)

        with open(exp_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, sort_keys=True)

        with open(exp_dir / "confusion_matrix.json", "w", encoding="utf-8") as f:
            json.dump(confusion_matrix, f, indent=2, sort_keys=True)

        with open(exp_dir / "provenance_metadata.json", "w", encoding="utf-8") as f:
            json.dump(provenance_metadata, f, indent=2, sort_keys=True)

        return exp_dir
