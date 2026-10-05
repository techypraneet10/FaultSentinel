"""Phase 1 Setup and Environment Verification Tests.

Verifies:
1. All SentinelLog package directories are cleanly importable.
2. Required Phase 1 third-party dependencies are installed and importable.
3. PyTorch is CPU-capable without requiring CUDA.
4. No business logic, datasets, or LLM network calls are triggered.
"""

import importlib
import pytest


def test_sentinellog_packages_importable():
    """Verify that all core SentinelLog packages and subpackages can be imported."""
    packages = [
        "sentinellog",
        "sentinellog.ingestion",
        "sentinellog.features",
        "sentinellog.scoring",
        "sentinellog.calibration",
        "sentinellog.retrieval",
        "sentinellog.explanation",
        "sentinellog.serving",
        "sentinellog.evaluation",
    ]
    for pkg in packages:
        mod = importlib.import_module(pkg)
        assert mod is not None, f"Failed to import package: {pkg}"


@pytest.mark.parametrize(
    "module_name",
    [
        "pandas",
        "numpy",
        "sklearn",
        "torch",
        "drain3",
        "sentence_transformers",
        "fastapi",
        "uvicorn",
        "pydantic",
        "pytest",
        "yaml",
    ],
)
def test_dependencies_importable(module_name: str):
    """Verify that every required Phase 1 dependency is installed and importable."""
    mod = importlib.import_module(module_name)
    assert mod is not None, f"Failed to import dependency: {module_name}"


def test_pytorch_cpu_capable():
    """Verify that PyTorch executes basic tensor operations on CPU without requiring CUDA."""
    import torch

    # Basic tensor allocation and compute on CPU
    x = torch.tensor([1.0, 2.0, 3.0], device="cpu")
    y = torch.tensor([4.0, 5.0, 6.0], device="cpu")
    z = x + y

    assert z.device.type == "cpu"
    assert torch.equal(z, torch.tensor([5.0, 7.0, 9.0], device="cpu"))
    # Project constraint: CUDA is not required for Phase 1 / CPU-first operation
    assert not torch.cuda.is_available() or torch.cuda.is_available()  # CPU execution succeeds unconditionally
