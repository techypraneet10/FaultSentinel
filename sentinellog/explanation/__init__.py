"""SentinelLog Phase 9: LLM Explanation & Orchestration Package.

Provides:
- ExplanationOrchestrator: primary entry point for grounded explanation synthesis.
- BaseLLMProvider & MockLLMProvider: extensible, deterministic LLM abstractions.
- ExplanationValidator: multi-stage verification enforcing decision immutability.
- FaithfulnessChecker: programmatic grounding verification.
- CitationValidator & ClaimExtractor: citation and claim integrity checkers.
- FallbackHandler: deterministic abstention handler.
"""

from sentinellog.explanation.citations import CitationValidator
from sentinellog.explanation.claims import ClaimExtractor
from sentinellog.explanation.client import SafeLLMClient
from sentinellog.explanation.context import ExplanationContextBuilder
from sentinellog.explanation.exceptions import (
    CitationValidationError,
    ClaimValidationError,
    ConfigurationError,
    DecisionImmutabilityError,
    ExplanationError,
    ExplanationValidationError,
    FaithfulnessCheckError,
    InvalidSplitError,
    LabelLeakageError,
    MalformedOutputError,
    ProviderError,
    ProviderTimeoutError,
    SeverityImmutabilityError,
)
from sentinellog.explanation.fallback import FallbackHandler
from sentinellog.explanation.faithfulness import FaithfulnessChecker
from sentinellog.explanation.orchestrator import (
    ExplanationOrchestrator,
    compute_configuration_hash,
)
from sentinellog.explanation.prompts import (
    SENTINELLOG_SYSTEM_PROMPT_V1,
    build_explanation_prompt,
)
from sentinellog.explanation.provider import (
    BaseLLMProvider,
    MockLLMProvider,
    OpenAILLMProvider,
    get_provider,
)
from sentinellog.explanation.schemas import (
    CitationValidationStatus,
    ClaimType,
    ExplanationCitation,
    ExplanationClaim,
    ExplanationResult,
    ExplanationStatus,
    FaithfulnessResult,
    FaithfulnessStatus,
    LLMUsageMetadata,
    ValidationResult,
)
from sentinellog.explanation.validator import ExplanationValidator
from sentinellog.explanation.version import EXPLANATION_ENGINE_VERSION, PROMPT_VERSION

__all__ = [
    "EXPLANATION_ENGINE_VERSION",
    "PROMPT_VERSION",
    "ExplanationOrchestrator",
    "compute_configuration_hash",
    "BaseLLMProvider",
    "MockLLMProvider",
    "OpenAILLMProvider",
    "get_provider",
    "SafeLLMClient",
    "ExplanationValidator",
    "FaithfulnessChecker",
    "CitationValidator",
    "ClaimExtractor",
    "FallbackHandler",
    "ExplanationContextBuilder",
    "build_explanation_prompt",
    "SENTINELLOG_SYSTEM_PROMPT_V1",
    "ExplanationResult",
    "ExplanationClaim",
    "ExplanationCitation",
    "FaithfulnessResult",
    "ValidationResult",
    "LLMUsageMetadata",
    "ClaimType",
    "FaithfulnessStatus",
    "ExplanationStatus",
    "CitationValidationStatus",
    "ExplanationError",
    "ExplanationValidationError",
    "DecisionImmutabilityError",
    "SeverityImmutabilityError",
    "CitationValidationError",
    "ClaimValidationError",
    "FaithfulnessCheckError",
    "ProviderError",
    "ProviderTimeoutError",
    "LabelLeakageError",
    "MalformedOutputError",
    "InvalidSplitError",
    "ConfigurationError",
]
