"""Safe LLM client wrapper with bounded retries and runtime telemetry.

Enforces:
1. Strict retry limits (no infinite loops).
2. Latency and token tracking across attempts.
3. Clean error translation without secret exposure.
"""

import time
from typing import Any, Dict, Optional

from sentinellog.explanation.exceptions import ProviderError, ProviderTimeoutError
from sentinellog.explanation.provider import BaseLLMProvider, LLMResponse
from sentinellog.explanation.schemas import LLMUsageMetadata


class SafeLLMClient:
    """Robust client wrapper around BaseLLMProvider."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        max_retries: int = 2,
        timeout: float = 30.0,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ):
        self.provider = provider
        self.max_retries = max(0, max_retries)
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    def execute(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute generation with bounded retries and token aggregation.
        
        Args:
            prompt: User prompt text.
            system_prompt: System prompt text.
            
        Returns:
            LLMResponse with aggregated usage metadata.
            
        Raises:
            ProviderError or ProviderTimeoutError after max_retries exhausted.
        """
        attempts = 0
        total_latency = 0.0
        last_error: Optional[Exception] = None

        while attempts <= self.max_retries:
            t0 = time.perf_counter()
            try:
                resp = self.provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                    **kwargs,
                )
                dur_ms = (time.perf_counter() - t0) * 1000.0
                total_latency += dur_ms

                # Record final retry count and accumulated latency
                combined_usage = LLMUsageMetadata(
                    input_tokens=resp.usage_metadata.input_tokens,
                    output_tokens=resp.usage_metadata.output_tokens,
                    total_tokens=resp.usage_metadata.total_tokens,
                    latency_ms=round(total_latency, 2),
                    retry_count=attempts,
                )
                return LLMResponse(
                    text=resp.text,
                    model_name=resp.model_name,
                    usage_metadata=combined_usage,
                    raw_response=resp.raw_response,
                )

            except (ProviderError, ProviderTimeoutError) as e:
                dur_ms = (time.perf_counter() - t0) * 1000.0
                total_latency += dur_ms
                last_error = e
                attempts += 1
                if attempts <= self.max_retries:
                    time.sleep(0.1 * attempts)  # Short deterministic backoff
            except Exception as e:
                dur_ms = (time.perf_counter() - t0) * 1000.0
                total_latency += dur_ms
                last_error = ProviderError(f"Unexpected provider error: {type(e).__name__}")
                attempts += 1
                if attempts <= self.max_retries:
                    time.sleep(0.1 * attempts)

        if isinstance(last_error, ProviderTimeoutError):
            raise ProviderTimeoutError(
                f"Generation timed out after {attempts} attempts ({total_latency:.1f}ms total latency)."
            )
        raise ProviderError(
            f"Generation failed after {attempts} attempts: {last_error}"
        )
