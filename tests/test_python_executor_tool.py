import unittest
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.python_executor_tool import PythonExecutorTool
from tools.llm_tool import LLMTool
from integration_test_framework import (
    IntegrationTestBase,
    IntegrationTestMode,
    get_test_mode,
    print_test_mode_info,
)


class TestPythonExecutorTool(unittest.TestCase):
    """Integration tests for PythonExecutorTool that work with REAL and MOCK modes"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_mode = get_test_mode()
        print_test_mode_info(self.test_mode)
        
        # Use class and method name to create unique test names
        test_name = f"python_executor_tool_{self._testMethodName}"
        
        # Initialize integration test framework
        self.integration_test = IntegrationTestBase(
            test_name=test_name,
            mode=self.test_mode
        )
        
        # Create wrapped tools
        self.llm_tool = self.integration_test.wrap_tool(LLMTool())
        self.tool = PythonExecutorTool(llm_tool=self.llm_tool)

    def tearDown(self):
        """Persist recorded tool calls when running in REAL mode"""
        if self.test_mode == IntegrationTestMode.REAL or self.test_mode == IntegrationTestMode.MOCK_THEN_REAL:
            # Save all recorded calls for this test so MOCK runs can replay them
            self.integration_test.save_test_data()

    def test_simple_arithmetic(self):
        """Test simple arithmetic calculation"""
        async def run_test():
            params = {
                "task_description": "Calculate the sum of numbers a and b from context, and return the result as a dictionary with key 'sum'",
                "related_context_content": {"a": 15, "b": 25},
            }
            
            result = await self.tool.execute(params)

            # Verify result structure
            self.assertIn("python_code", result)
            self.assertIn("return_value", result)
            self.assertIn("stdout", result)
            self.assertIn("stderr", result)
            self.assertIn("exception", result)

            # Verify code was generated
            self.assertIn("def process_step", result["python_code"])

            # Print results for debugging
            print(f"\nGenerated code:\n{result['python_code']}")
            print(f"Return value: {result['return_value']}")
            print(f"Exception: {result['exception']}")
            
            # If successful execution, verify the result
            if result["exception"] is None:
                self.assertIsNotNone(result["return_value"])
                if isinstance(result["return_value"], dict) and "sum" in result["return_value"]:
                    self.assertEqual(result["return_value"]["sum"], 40)

        asyncio.run(run_test())

    def test_string_concatenation(self):
        """Test string concatenation task"""
        async def run_test():
            params = {
                "task_description": "Combine first_name and last_name from context with a space between them, return as dict with key 'full_name'",
                "related_context_content": {"first_name": "John", "last_name": "Doe"},
            }
            
            result = await self.tool.execute(params)

            # Verify result structure
            self.assertIn("python_code", result)
            self.assertIn("def process_step", result["python_code"])

            # Print results for debugging
            print(f"\nGenerated code:\n{result['python_code']}")
            print(f"Return value: {result['return_value']}")
            print(f"Exception: {result['exception']}")
            
            # If successful execution, verify the result
            if result["exception"] is None:
                self.assertIsNotNone(result["return_value"])
                if isinstance(result["return_value"], dict) and "full_name" in result["return_value"]:
                    self.assertEqual(result["return_value"]["full_name"], "John Doe")

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
