"""
Pytest configuration file for doc_flow_agent tests
"""
import sys
from pathlib import Path

# Add project root to Python path for all tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
