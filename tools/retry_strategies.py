#!/usr/bin/env python3
"""Retry strategy implementations for LLMTool

Defines pluggable strategies applied sequentially. Each strategy controls a
block of attempts (1 + max_retries) before the next strategy is tried.

A strategy may adjust prompt, model, temperature, etc., by returning a full
parameter dict for each attempt. It must not mutate the base_parameters dict
passed to build_attempt_parameters.
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List
import copy


class RetryStrategy:
    """Base retry strategy interface.

    Lifecycle per strategy:
      1. start(base_parameters) called once before attempts for this strategy.
      2. For each attempt (1..N): build_attempt_parameters invoked.

    build_attempt_parameters must return a FULL parameter dict (copy of
    base parameters plus modifications). It must include 'prompt'.
    It MUST NOT include retry control keys (max_retries, retry_strategies, validators, retry_llm_tool).
    """

    def name(self) -> str:  # pragma: no cover - trivial
        return self.__class__.__name__

    def start(self, base_parameters: Dict[str, Any]) -> None:  # pragma: no cover - default no-op
        pass

    async def build_attempt_parameters(
        self,
        *,
        base_parameters: Dict[str, Any],
        attempt_index: int,
        last_response: Optional[Dict[str, Any]],
        last_error: Optional[Exception],
    ) -> Dict[str, Any]:  # pragma: no cover - abstract
        raise NotImplementedError


class SimpleRetryStrategy(RetryStrategy):
    """Simple strategy: reuse base parameters unchanged every attempt."""

    async def build_attempt_parameters(
        self,
        *,
        base_parameters: Dict[str, Any],
        attempt_index: int,
        last_response: Optional[Dict[str, Any]],
        last_error: Optional[Exception],
    ) -> Dict[str, Any]:
        return copy.deepcopy(base_parameters)


class AppendValidationHintStrategy(RetryStrategy):
    """Strategy that appends validation/error hints to the prompt after failures.

    On first attempt returns original prompt. After each failed attempt, it
    records a hint block referencing last response & error, included in
    subsequent attempt prompts.
    """

    def __init__(self):
        self._hints: List[str] = []
        self._base_prompt: Optional[str] = None

    def start(self, base_parameters: Dict[str, Any]) -> None:
        # Capture original prompt so we can append hints cumulatively
        self._base_prompt = base_parameters.get("prompt", "")
        self._hints.clear()

    async def build_attempt_parameters(
        self,
        *,
        base_parameters: Dict[str, Any],
        attempt_index: int,
        last_response: Optional[Dict[str, Any]],
        last_error: Optional[Exception],
    ) -> Dict[str, Any]:
        params = copy.deepcopy(base_parameters)
        # attempt_index 1: original prompt (no hints yet)
        if attempt_index > 1 and last_response is not None and last_error is not None:
            # Build new hint block from *previous* attempt's response
            content = last_response.get("content", "")
            tool_call = last_response.get("tool_calls", [])
            block = (
                f"\n<Previous Invalid Response>\n{content}\ntool_calls: {tool_call}\n</Previous Invalid Response>"
                f"\n<Validation Error>\n{last_error}\n</Validation Error>"  # validation error
                f"\n<Instruction>\nRegenerate a corrected response following the original instructions. Avoid the validation error you encountered previously.\n</Instruction>\n"
            )
            if block not in self._hints:
                self._hints.append(block)
        # Compose prompt
        composed_prompt = self._base_prompt or base_parameters.get("prompt", "")
        if self._hints:
            composed_prompt += "".join(self._hints)
        params["prompt"] = composed_prompt
        return params
