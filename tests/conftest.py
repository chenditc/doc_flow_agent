"""
Pytest configuration file for doc_flow_agent tests
"""
import os
import shutil
import sys
import pytest
from pathlib import Path

# Add project root to Python path for all tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True, scope="function")
def cleanup_test_data():
    """Automatically clean up test data before and after each test function.
    
    This fixture runs automatically for every test function, ensuring
    that tests don't interfere with each other by leaving behind test data.
    """
    def _cleanup():
        """Remove test session directories to ensure clean test runs"""
        test_sessions_dir = project_root / "user_comm" / "sessions"
        if test_sessions_dir.exists():
            # Only remove test session directories (those starting with test patterns)
            test_patterns = ['api_test_', 'status_test_', 'test_', 'llm_test', 'existing_test']
            for session_dir in test_sessions_dir.iterdir():
                if session_dir.is_dir() and any(session_dir.name.startswith(pattern) for pattern in test_patterns):
                    shutil.rmtree(session_dir, ignore_errors=True)
    
    # Clean up before test
    _cleanup()
    
    # Run the test
    yield
    
    # Clean up after test
    _cleanup()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment once per test session"""
    # Ensure user_comm directories exist
    user_comm_dir = project_root / "user_comm" / "sessions"
    user_comm_dir.mkdir(parents=True, exist_ok=True)

    # Use the real embedding model + on-disk cache.
    # The cache directory is intended to be committed so tests stay fast/offline
    # as long as SOP docs (and common queries) do not change.
    cache_dir = (project_root / ".cache" / "embeddings").resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("EMBEDDING_CACHE_DIR", str(cache_dir))
    os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-ada-002")
    # Keep tests offline/deterministic: rewrite would trigger additional LLM calls in mocks.
    # Unit tests that validate rewrite behavior explicitly override this env var.
    os.environ["SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE"] = "off"
    
    yield
    
    # Final cleanup after all tests
    if user_comm_dir.exists():
        test_patterns = ['api_test_', 'status_test_', 'test_', 'llm_test', 'existing_test']
        for session_dir in user_comm_dir.iterdir():
            if session_dir.is_dir() and any(session_dir.name.startswith(pattern) for pattern in test_patterns):
                shutil.rmtree(session_dir, ignore_errors=True)
