#!/usr/bin/env python3
"""
Test cases for BaseTool abstract base class
"""

import unittest
import sys
import os
from typing import Dict, Any

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.base_tool import BaseTool


class ConcreteTool(BaseTool):
    """Concrete implementation of BaseTool for testing"""
    
    def __init__(self, tool_id: str = "test_tool"):
        super().__init__(tool_id)
        self.execute_called = False
        self.execute_params = None
        self.execute_return_value = "test_result"
    
    async def execute(self, parameters: Dict[str, Any]) -> str:
        """Test implementation of execute method"""
        self.execute_called = True
        self.execute_params = parameters
        return self.execute_return_value


class TestBaseTool(unittest.TestCase):
    """Test cases for BaseTool class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tool = ConcreteTool("test_tool")
    
    def test_init(self):
        """Test BaseTool initialization"""
        self.assertEqual(self.tool.tool_id, "test_tool")
    
    def test_init_custom_id(self):
        """Test BaseTool initialization with custom ID"""
        custom_tool = ConcreteTool("custom_id")
        self.assertEqual(custom_tool.tool_id, "custom_id")
    
    def test_validate_parameters_success(self):
        """Test successful parameter validation"""
        parameters = {"param1": "value1", "param2": "value2"}
        required_params = ["param1", "param2"]
        
        # Should not raise any exception
        self.tool.validate_parameters(parameters, required_params)
    
    def test_validate_parameters_missing_single(self):
        """Test parameter validation with single missing parameter"""
        parameters = {"param1": "value1"}
        required_params = ["param1", "param2"]
        
        with self.assertRaises(ValueError) as context:
            self.tool.validate_parameters(parameters, required_params)
        
        self.assertIn("test_tool tool requires parameters: param2", str(context.exception))
    
    def test_validate_parameters_missing_multiple(self):
        """Test parameter validation with multiple missing parameters"""
        parameters = {"param1": "value1"}
        required_params = ["param1", "param2", "param3"]
        
        with self.assertRaises(ValueError) as context:
            self.tool.validate_parameters(parameters, required_params)
        
        error_msg = str(context.exception)
        self.assertIn("test_tool tool requires parameters:", error_msg)
        self.assertIn("param2", error_msg)
        self.assertIn("param3", error_msg)
    
    def test_validate_parameters_empty_required(self):
        """Test parameter validation with no required parameters"""
        parameters = {"param1": "value1"}
        required_params = []
        
        # Should not raise any exception
        self.tool.validate_parameters(parameters, required_params)
    
    def test_validate_parameters_empty_parameters(self):
        """Test parameter validation with empty parameters dict"""
        parameters = {}
        required_params = ["param1"]
        
        with self.assertRaises(ValueError) as context:
            self.tool.validate_parameters(parameters, required_params)
        
        self.assertIn("test_tool tool requires parameters: param1", str(context.exception))
    
    def test_validate_parameters_none_values(self):
        """Test parameter validation with None values (should be considered present)"""
        parameters = {"param1": None, "param2": "value2"}
        required_params = ["param1", "param2"]
        
        # Should not raise any exception - None is a valid value
        self.tool.validate_parameters(parameters, required_params)
    
    def test_str_representation(self):
        """Test string representation of tool"""
        expected = "ConcreteTool(tool_id=test_tool)"
        self.assertEqual(str(self.tool), expected)
    
    def test_repr_representation(self):
        """Test repr representation of tool"""
        expected = "ConcreteTool(tool_id=test_tool)"
        self.assertEqual(repr(self.tool), expected)
    
    def test_str_repr_consistency(self):
        """Test that __str__ and __repr__ return the same value"""
        self.assertEqual(str(self.tool), repr(self.tool))
    
    def test_abstract_method_implementation(self):
        """Test that abstract execute method is properly implemented"""
        # This test verifies that ConcreteTool can be instantiated
        # and that the execute method is implemented
        self.assertIsInstance(self.tool, BaseTool)
        self.assertTrue(hasattr(self.tool, 'execute'))
        self.assertTrue(callable(self.tool.execute))
    
    def test_cannot_instantiate_base_tool_directly(self):
        """Test that BaseTool cannot be instantiated directly"""
        with self.assertRaises(TypeError):
            BaseTool("test")


if __name__ == '__main__':
    unittest.main()
