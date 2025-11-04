#!/usr/bin/env python3
"""Shared helpers for sandbox configuration.

Provides a single source of truth for how to resolve the sandbox base URL
so different modules (CLI tool, Python executor tool, etc.) behave consistently.
"""

import os


def get_sandbox_base_url() -> str:
    """Return sandbox base URL with precedence:
    WORKSPACE_SANDBOX_URL > DEFAULT_WORKSPACE_SANDBOX_URL > SANDBOX_BASE_URL > http://localhost:8080

    The final URL is normalized by stripping any trailing '/'.
    """
    base = (
        os.getenv("WORKSPACE_SANDBOX_URL")
        or os.getenv("DEFAULT_WORKSPACE_SANDBOX_URL")
        or ""
    )
    return base.rstrip("/")
