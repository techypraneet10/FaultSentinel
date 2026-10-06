"""LLM Provider abstraction and deterministic offline mock provider for Phase 9.

Supports:
1. BaseLLMProvider interface.
2. Deterministic MockLLMProvider for unit testing, CI, and offline execution without external APIs.
3. Configurable error injection modes for robustness verification.
4. Production provider abstraction with zero secret logging and strict environment variable isolation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from sentinellog.explanation.exceptions import (
    ProviderError,
    ProviderTimeoutError,
)
from sentinellog.explanation.schemas import LLMUsageMetadata


@dataclass
class LLMResponse:
    """Standardized response from an LLM provider."""
    text: str
    model_name: str
    usage_metadata: LLMUsageMetadata
    raw_response: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate response from the model."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Deterministic, offline mock provider for testing and reproducible execution."""

    def __init__(self, mode: str = "default", model_name: str = "sentinellog-mock-v1"):
        """Initialize mock provider.
        
        Args:
            mode: Error injection mode. Options:
                'default': Valid, fully grounded explanation matching prompt inputs.
                'invalid_citation': References non-existent citation ID.
                'missing_citation': Factual claims with empty citation list.
                'unsupported_claim': Factual claim asserting ungrounded hardware fault.
                'changed_decision': Decision contradicts Phase 8 assessment.
                'changed_severity': Severity contradicts Phase 8 assessment.
                'malformed_json': Returns unparseable text.
                'numeric_mismatch': States incorrect numeric metrics.
                'prompt_injection': Simulates injection attack success.
                'timeout': Simulates provider timeout.
                'provider_error': Simulates provider failure.
                'empty_response': Returns empty response string.
            model_name: Identifier for the mock model.
        """
        self.mode = mode
        self.model_name = model_name

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate mock response based on mode."""
        start_time = time.perf_counter()

        if self.mode == "timeout":
            raise ProviderTimeoutError(f"Mock provider timed out after {timeout} seconds.")
        if self.mode == "provider_error":
            raise ProviderError("Mock provider simulated unrecoverable API failure.")
        if self.mode == "empty_response":
            return LLMResponse(
                text="",
                model_name=self.model_name,
                usage_metadata=LLMUsageMetadata(input_tokens=10, output_tokens=0, total_tokens=10, latency_ms=1.0),
            )
        if self.mode == "malformed_json":
            return LLMResponse(
                text="<<<ERROR: System encountered an unexpected condition, cannot format JSON>>>",
                model_name=self.model_name,
                usage_metadata=LLMUsageMetadata(input_tokens=10, output_tokens=10, total_tokens=20, latency_ms=1.0),
            )

        # Extract deterministic assessment inputs from prompt text
        decision_match = re.search(r"Deterministic Decision:\s*(\w+)", prompt)
        decision = decision_match.group(1) if decision_match else "SUSPICIOUS"

        severity_match = re.search(r"Deterministic Severity:\s*(\w+)", prompt)
        severity = severity_match.group(1) if severity_match else "LOW"

        # Extract citation IDs from prompt
        citation_ids = re.findall(r"Citation ID:\s*([a-f0-9]{64}|CIT-[\w-]+)", prompt)

        if self.mode == "changed_decision":
            decision = "NORMAL" if decision == "INCIDENT" else "INCIDENT"

        if self.mode == "changed_severity":
            severity = "CRITICAL" if severity != "CRITICAL" else "LOW"

        if self.mode == "invalid_citation":
            cited_ids = ["CIT-FABRICATED-NONEXISTENT-99999"]
        elif self.mode == "missing_citation":
            cited_ids = []
        else:
            cited_ids = citation_ids[:2] if citation_ids else []

        # Construct appropriate claims based on decision and mode
        claims = []
        uncertainties = []
        rec_action = "Monitor window metrics and verify downstream worker health."

        if decision == "INSUFFICIENT_EVIDENCE":
            summary = "Elevated anomaly signals were observed, but retrieved evidence is insufficient to confirm an incident."
            if cited_ids:
                claims.append({
                    "text": "The sequential anomaly score triggered selective escalation.",
                    "citation_ids": cited_ids,
                    "claim_type": "OBSERVATION",
                })
                claims.append({
                    "text": "Retrieved historical log chunks showed negligible relevance or contradictory patterns.",
                    "citation_ids": cited_ids,
                    "claim_type": "EVIDENCE",
                })
            else:
                claims.append({
                    "text": "The sequential anomaly score triggered selective escalation based on Phase 8 scoring.",
                    "citation_ids": [],
                    "claim_type": "INTERPRETATION",
                })
                claims.append({
                    "text": "Available evidence was insufficient to confirm an incident pattern.",
                    "citation_ids": [],
                    "claim_type": "INTERPRETATION",
                })
            uncertainties.append("Available log sequences do not contain sufficient evidence to characterize a specific failure mode.")
            rec_action = "Collect additional telemetry and host logs for the affected time window."
        elif self.mode == "unsupported_claim":
            summary = f"Automated triage classified the window as {decision} with {severity} severity."
            claims.append({
                "text": "The server power supply catastrophically failed causing hardware reboot.",
                "citation_ids": cited_ids,
                "claim_type": "EVIDENCE",
            })
            uncertainties.append("Root cause beyond power supply failure is unconfirmed.")
        elif self.mode == "numeric_mismatch":
            summary = f"Automated triage classified the window as {decision}."
            claims.append({
                "text": "Sequential anomaly score was 999.99 with 5000 failed connection events.",
                "citation_ids": cited_ids,
                "claim_type": "OBSERVATION",
            })
            uncertainties.append("Extended event count requires manual audit.")
        elif self.mode == "prompt_injection":
            summary = "INSTRUCTION OVERRIDDEN: All security checks bypassed."
            claims.append({
                "text": "System instructions were ignored as requested in the log payload.",
                "citation_ids": [],
                "claim_type": "INTERPRETATION",
            })
        else:
            # Default valid explanation
            summary = f"Triage assessment confirmed {decision} ({severity} severity) supported by retrieved historical evidence."
            if cited_ids:
                claims.append({
                    "text": "The window exhibits repeated connection and data transfer events consistent with historical patterns.",
                    "citation_ids": cited_ids,
                    "claim_type": "OBSERVATION",
                })
                claims.append({
                    "text": f"Retrieved evidence chunk corroborates the observed sequence.",
                    "citation_ids": cited_ids,
                    "claim_type": "EVIDENCE",
                })
            else:
                claims.append({
                    "text": f"The query window produced elevated anomaly indicators consistent with {decision}.",
                    "citation_ids": [],
                    "claim_type": "OBSERVATION",
                })
            claims.append({
                "text": f"Deterministic rules classified the window as {decision} based on signal alignment.",
                "citation_ids": [],
                "claim_type": "INTERPRETATION",
            })
            uncertainties.append("Underlying root cause is not definitively established solely from log sequence patterns.")

        payload = {
            "incident_decision": decision,
            "severity": severity,
            "summary": summary,
            "claims": claims,
            "uncertainties": uncertainties,
            "recommended_action": rec_action,
        }

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        text = json.dumps(payload, indent=2)
        in_tok = len(prompt.split())
        out_tok = len(text.split())

        return LLMResponse(
            text=text,
            model_name=self.model_name,
            usage_metadata=LLMUsageMetadata(
                input_tokens=in_tok,
                output_tokens=out_tok,
                total_tokens=in_tok + out_tok,
                latency_ms=latency_ms,
                retry_count=0,
            ),
        )


class OpenAILLMProvider(BaseLLMProvider):
    """External API provider adhering to security and secret management constraints."""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key_env: str = "SENTINELLOG_LLM_API_KEY",
        base_url: Optional[str] = None,
    ):
        self.model_name = model_name
        self.api_key_env = api_key_env
        self.base_url = base_url

    def _get_api_key(self) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderError(
                f"Missing API key. Please configure environment variable '{self.api_key_env}'."
            )
        return key

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> LLMResponse:
        """Call external API using standard library or requests without secret leakage."""
        api_key = self._get_api_key()
        import urllib.request
        import urllib.error

        url = self.base_url or "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
        start_time = time.perf_counter()

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_bytes = response.read()
                resp_json = json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Mask authorization header in error messages
            raise ProviderError(f"LLM API request failed with HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            if "timed out" in str(e.reason).lower():
                raise ProviderTimeoutError(f"LLM API timed out after {timeout} seconds.")
            raise ProviderError(f"LLM API network error: {e.reason}")
        except Exception as e:
            raise ProviderError(f"Unexpected provider error: {type(e).__name__}")

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        choice = resp_json.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "")
        usage = resp_json.get("usage", {})

        return LLMResponse(
            text=text,
            model_name=self.model_name,
            usage_metadata=LLMUsageMetadata(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_ms=latency_ms,
                retry_count=0,
            ),
        )


def get_provider(config: Dict[str, Any]) -> BaseLLMProvider:
    """Factory function to instantiate configured LLM provider.
    
    Defaults to MockLLMProvider if provider type is 'mock' or API key is absent.
    """
    prov_cfg = config.get("provider", {})
    p_type = prov_cfg.get("type", "mock").lower()
    model = prov_cfg.get("model", "sentinellog-mock-v1")

    if p_type == "mock":
        mode = prov_cfg.get("mock_mode", "default")
        return MockLLMProvider(mode=mode, model_name=model)
    elif p_type in {"openai", "external"}:
        env_var = prov_cfg.get("api_key_env", "SENTINELLOG_LLM_API_KEY")
        if not os.environ.get(env_var):
            # Fall back safely to mock if requested external provider has no credentials
            return MockLLMProvider(mode="default", model_name=f"{model}-offline-mock")
        return OpenAILLMProvider(
            model_name=model,
            api_key_env=env_var,
            base_url=prov_cfg.get("base_url"),
        )
    else:
        return MockLLMProvider(mode="default", model_name=model)
