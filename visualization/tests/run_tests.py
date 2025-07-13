#!/usr/bin/env python3
"""
Test runner for visualization module
Runs backend tests, component integration tests, and optionally frontend tests
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def run_command(cmd, description, cwd=None):
    """Run a command and return success status"""
    print(f"\n🔧 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd or project_root,
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Success")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_server_running():
    """Check if visualization server is running"""
    try:
        import requests
        response = requests.get('http://localhost:8000/health', timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Run all visualization tests"""
    print("🧪 Doc Flow Visualization Test Suite")
    print("="*50)
    
    # Change to project root directory
    os.chdir(project_root)
    
    success_count = 0
    test_num = 0
    
    # 1. Backend API tests
    test_num += 1
    print(f"\n📋 Test {test_num}/3: Backend API Tests")
    if run_command([
        sys.executable, '-m', 'pytest', 
        'visualization/tests/test_viz_server.py', 
        '-v', '--tb=short'
    ], "Testing visualization server API"):
        success_count += 1
    
    # 2. Component integration tests  
    test_num += 1
    print(f"\n📋 Test {test_num}/3: Component Integration Tests")
    if run_command([
        sys.executable, '-m', 'pytest',
        'visualization/tests/test_components.py',
        '-v', '--tb=short'
    ], "Testing component data flow and integration"):
        success_count += 1
    
    # 3. Frontend tests (optional, requires Selenium)
    if os.environ.get('RUN_SELENIUM_TESTS'):
        total_tests += 1
        print(f"\n📋 Test 3/{total_tests}: Frontend Browser Tests")
        
        # Check if server is running
        if not check_server_running():
            print("⚠️  Visualization server not running on localhost:8000")
            print("   Start server with: python -m visualization.server.viz_server")
            print("   Skipping frontend tests...")
        else:
            if run_command([
                sys.executable, '-m', 'pytest',
                'tests/test_frontend.py',
                '-v', '--tb=short'
            ], "Testing frontend components with Selenium"):
                success_count += 1
    else:
        print(f"\n⏭️  Skipping frontend tests (set RUN_SELENIUM_TESTS=1 to enable)")
    
    # 3. Static file checks
    test_num += 1
    print(f"\n📋 Test {test_num}/3: Static File Validation")
    success = True
    
    # Check that all component files exist
    required_files = [
        'frontend/index.html',
        'frontend/assets/js/utils/api.js',
        'frontend/assets/js/utils/formatting.js',
        'frontend/assets/js/utils/dom.js',
        'frontend/assets/js/components/timeline.js',
        'frontend/assets/js/components/task-details.js',
        'frontend/assets/js/components/trace-selector.js',
        'frontend/assets/js/main.js'
    ]
    
    viz_dir = project_root / 'visualization'
    for file_path in required_files:
        full_path = viz_dir / file_path
        if not full_path.exists():
            print(f"❌ Missing required file: {file_path}")
            success = False
        else:
            print(f"✅ Found: {file_path}")
    
    if success:
        success_count += 1
        print("✅ All required files present")
    
    # Summary
    print("\n" + "="*50)
    print(f"📊 Test Results: {success_count}/3 passed")
    
    if success_count == 3:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {3 - success_count} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
