"""
Frontend integration tests for the visualization components
Uses Selenium WebDriver for browser automation
"""

import pytest
import json
import time
import os
from pathlib import Path
from unittest.mock import patch
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# Test data
MOCK_TRACE_DATA = {
    "session_id": "test-session-frontend",
    "start_time": "2025-08-22T10:00:00Z",
    "end_time": "2025-08-22T10:05:00Z",
    "initial_task_description": "Frontend test task",
    "final_status": "completed",
    "task_executions": [
        {
            "task_execution_id": "test-task-frontend-1",
            "task_description": "Test task execution for frontend",
            "start_time": "2025-08-22T10:00:00Z",
            "end_time": "2025-08-22T10:02:00Z",
            "status": "completed",
            "error": None,
            "phases": {
                "sop_resolution": {
                    "start_time": "2025-08-22T10:00:00Z",
                    "end_time": "2025-08-22T10:01:00Z",
                    "status": "completed",
                    "test_data": "Phase test data"
                },
                "task_execution": {
                    "start_time": "2025-08-22T10:01:00Z", 
                    "end_time": "2025-08-22T10:02:00Z",
                    "status": "failed",
                    "error_message": "Test error"
                }
            },
            "engine_state_after": {
                "context": {
                    "last_task_output": "Test output from task execution"
                }
            }
        }
    ]
}

class TestFrontendComponents:
    """Test frontend components with browser automation"""

    @pytest.fixture(scope="class")
    def driver(self):
        """Set up Chrome WebDriver with headless options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)
            yield driver
        finally:
            if 'driver' in locals():
                driver.quit()

    @pytest.fixture
    def server_with_mock_data(self):
        """Start visualization server with mock data"""
        import tempfile
        import subprocess
        import threading
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock trace file
            trace_file = Path(temp_dir) / "session_frontend_test.json"
            with open(trace_file, 'w') as f:
                json.dump(MOCK_TRACE_DATA, f)
            
            # Start server in background
            with patch('visualization.server.viz_server.TRACES_DIR', temp_dir):
                from visualization.server.viz_server import app
                server_thread = threading.Thread(
                    target=lambda: app.run(host='127.0.0.1', port=8001, debug=False)
                )
                server_thread.daemon = True
                server_thread.start()
                
                # Give server time to start
                time.sleep(2)
                yield "http://127.0.0.1:8001"

    @pytest.mark.skipif(
        not os.environ.get('RUN_SELENIUM_TESTS'),
        reason="Selenium tests require RUN_SELENIUM_TESTS=1 and Chrome browser"
    )
    def test_page_loads(self, driver, server_with_mock_data):
        """Test that the main page loads correctly"""
        driver.get(server_with_mock_data)
        
        # Check title
        assert "Doc Flow Trace Viewer" in driver.title
        
        # Check main elements are present
        header = driver.find_element(By.TAG_NAME, "header")
        assert "Doc Flow Trace Viewer" in header.text
        
        # Check trace selector is present
        trace_select = driver.find_element(By.ID, "trace-select")
        assert trace_select.is_displayed()

    @pytest.mark.skipif(
        not os.environ.get('RUN_SELENIUM_TESTS'),
        reason="Selenium tests require RUN_SELENIUM_TESTS=1 and Chrome browser"
    )
    def test_trace_selection_and_timeline(self, driver, server_with_mock_data):
        """Test trace selection and timeline rendering"""
        driver.get(server_with_mock_data)
        
        # Wait for trace options to load
        wait = WebDriverWait(driver, 10)
        
        try:
            # Wait for traces to load (select should have options)
            wait.until(lambda d: len(Select(d.find_element(By.ID, "trace-select")).options) > 1)
            
            # Select the mock trace
            select = Select(driver.find_element(By.ID, "trace-select"))
            select.select_by_visible_text("frontend test")  # Based on mock trace naming pattern
            
            # Wait for timeline to render
            timeline = wait.until(EC.presence_of_element_located((By.ID, "timeline")))
            
            # Check that timeline items are rendered
            timeline_items = driver.find_elements(By.CLASS_NAME, "timeline-item")
            assert len(timeline_items) > 0
            
            # Check that task description is displayed
            task_descriptions = driver.find_elements(By.XPATH, "//h3[contains(@class, 'font-medium')]")
            assert any("Test task execution for frontend" in desc.text for desc in task_descriptions)
            
        except TimeoutException:
            pytest.fail("Failed to load traces or render timeline within timeout")

    @pytest.mark.skipif(
        not os.environ.get('RUN_SELENIUM_TESTS'),
        reason="Selenium tests require RUN_SELENIUM_TESTS=1 and Chrome browser"
    )
    def test_task_details_modal(self, driver, server_with_mock_data):
        """Test that clicking a task opens the details modal"""
        driver.get(server_with_mock_data)
        
        wait = WebDriverWait(driver, 10)
        
        try:
            # Load trace and wait for timeline
            wait.until(lambda d: len(Select(d.find_element(By.ID, "trace-select")).options) > 1)
            select = Select(driver.find_element(By.ID, "trace-select"))
            select.select_by_index(1)  # Select first real trace
            
            # Wait for and click timeline item
            timeline_item = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "timeline-item")))
            timeline_item.click()
            
            # Wait for modal to appear
            modal = wait.until(EC.visibility_of_element_located((By.ID, "task-details-modal")))
            assert modal.is_displayed()
            
            # Check modal content
            modal_title = driver.find_element(By.ID, "task-details-title")
            assert "Test task execution for frontend" in modal_title.text
            
            # Check that phases are displayed
            phases_container = driver.find_element(By.ID, "task-details-phases")
            phase_elements = phases_container.find_elements(By.XPATH, ".//div[contains(@class, 'font-medium')]")
            assert len(phase_elements) >= 2  # Should have at least our 2 test phases
            
            # Test close modal
            close_button = driver.find_element(By.ID, "task-details-close")
            close_button.click()
            
            # Wait for modal to disappear
            wait.until(EC.invisibility_of_element_located((By.ID, "task-details-modal")))
            
        except TimeoutException:
            pytest.fail("Failed to interact with task details modal within timeout")

    @pytest.mark.skipif(
        not os.environ.get('RUN_SELENIUM_TESTS'),
        reason="Selenium tests require RUN_SELENIUM_TESTS=1 and Chrome browser"
    )
    def test_phase_details_expansion(self, driver, server_with_mock_data):
        """Test expanding phase details in the modal"""
        driver.get(server_with_mock_data)
        
        wait = WebDriverWait(driver, 10)
        
        try:
            # Navigate to modal
            wait.until(lambda d: len(Select(d.find_element(By.ID, "trace-select")).options) > 1)
            select = Select(driver.find_element(By.ID, "trace-select"))
            select.select_by_index(1)
            
            timeline_item = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "timeline-item")))
            timeline_item.click()
            
            # Wait for modal and find expandable details
            wait.until(EC.visibility_of_element_located((By.ID, "task-details-modal")))
            
            # Find and click details toggle
            details_summary = driver.find_element(By.TAG_NAME, "summary")
            details_summary.click()
            
            # Check that JSON content is now visible
            json_content = driver.find_element(By.TAG_NAME, "pre")
            assert json_content.is_displayed()
            assert len(json_content.text) > 10  # Should have JSON content
            
        except TimeoutException:
            pytest.fail("Failed to expand phase details within timeout")

    @pytest.mark.skipif(
        not os.environ.get('RUN_SELENIUM_TESTS'),
        reason="Selenium tests require RUN_SELENIUM_TESTS=1 and Chrome browser"
    )
    def test_auto_select_latest_trace(self, driver, server_with_mock_data):
        """Test that the latest trace is automatically selected when page loads"""
        driver.get(server_with_mock_data)
        
        # Wait for trace options to load
        wait = WebDriverWait(driver, 10)
        
        try:
            # Wait for traces to load and auto-selection to occur
            # The trace select should have a selected value after auto-selection
            wait.until(lambda d: Select(d.find_element(By.ID, "trace-select")).first_selected_option.get_attribute("value") != "")
            
            # Verify that a trace was automatically selected
            select = Select(driver.find_element(By.ID, "trace-select"))
            selected_option = select.first_selected_option
            assert selected_option.get_attribute("value") != ""
            assert "frontend test" in selected_option.text
            
            # Verify that the timeline was automatically loaded
            timeline = wait.until(EC.presence_of_element_located((By.ID, "timeline")))
            timeline_items = driver.find_elements(By.CLASS_NAME, "timeline-item")
            assert len(timeline_items) > 0
            
            # Verify task content was loaded automatically
            task_descriptions = driver.find_elements(By.XPATH, "//h3[contains(@class, 'font-medium')]")
            assert any("Test task execution for frontend" in desc.text for desc in task_descriptions)
            
        except TimeoutException:
            pytest.fail("Auto-selection of latest trace failed or timed out")

class TestComponentsUnitTests:
    """Unit tests for individual component functions (JavaScript)"""

    def test_formatting_utils_exist(self):
        """Test that formatting utility functions are properly defined"""
        # This would require a JavaScript testing framework like Jest
        # For now, we'll add a placeholder that could be extended
        pass

    def test_dom_utils_exist(self):
        """Test that DOM utility functions are properly defined"""
        # This would require a JavaScript testing framework like Jest
        # For now, we'll add a placeholder that could be extended
        pass

# Helper function to run Selenium tests conditionally
def run_selenium_tests():
    """Helper to run Selenium tests with proper environment setup"""
    # Set environment variable to enable Selenium tests
    os.environ['RUN_SELENIUM_TESTS'] = '1'
    
    # Run pytest with Selenium tests
    import subprocess
    result = subprocess.run([
        'python', '-m', 'pytest', 
        'visualization/tests/test_frontend.py',
        '-v', '--tb=short'
    ], cwd=Path(__file__).parent.parent.parent)
    
    return result.returncode

if __name__ == "__main__":
    # Allow running Selenium tests directly
    print("Running frontend Selenium tests...")
    print("Note: This requires Chrome browser and chromedriver to be installed.")
    exit_code = run_selenium_tests()
    exit(exit_code)
