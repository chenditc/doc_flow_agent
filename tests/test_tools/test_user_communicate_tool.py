#!/usr/bin/env python3
"""
Test cases for UserCommunicateTool
"""

import unittest
import sys
import os
import json
import asyncio
from unittest.mock import patch, MagicMock
from io import StringIO

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.user_communicate_tool import UserCommunicateTool


class TestUserCommunicateTool(unittest.TestCase):
    """Test cases for UserCommunicateTool class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tool = UserCommunicateTool()
    
    def test_init(self):
        """Test UserCommunicateTool initialization"""
        self.assertEqual(self.tool.tool_id, "USER_COMMUNICATE")
    
    def test_validate_parameters_success(self):
        """Test successful parameter validation"""
        parameters = {"message": "Hello user"}
        
        # Should not raise any exception
        self.tool.validate_parameters(parameters, ['message'])
    
    def test_validate_parameters_missing_message(self):
        """Test parameter validation with missing message"""
        parameters = {}
        
        with self.assertRaises(ValueError) as context:
            self.tool.validate_parameters(parameters, ['message'])
        
        self.assertIn("USER_COMMUNICATE tool requires parameters: message", str(context.exception))
    
    @patch('builtins.input', side_effect=['User response', 'Second line', '###END###'])
    @patch('builtins.print')
    def test_get_multiline_input_with_end_marker(self, mock_print, mock_input):
        """Test multiline input with end marker"""
        result = self.tool._get_multiline_input()
        
        expected = "User response\nSecond line"
        self.assertEqual(result, expected)
        
        # Verify print was called with instructions
        mock_print.assert_any_call("Please enter your reply (press Ctrl+D on Unix/Ctrl+Z on Windows when finished, or type '###END###' on a new line):")
    
    @patch('builtins.input', side_effect=EOFError())
    @patch('builtins.print')
    def test_get_multiline_input_with_eof(self, mock_print, mock_input):
        """Test multiline input with EOF (Ctrl+D/Ctrl+Z)"""
        result = self.tool._get_multiline_input()
        
        self.assertEqual(result, "")  # No input before EOF
    
    @patch('builtins.input', side_effect=['Line 1', 'Line 2', EOFError()])
    @patch('builtins.print')
    def test_get_multiline_input_with_content_then_eof(self, mock_print, mock_input):
        """Test multiline input with content followed by EOF"""
        result = self.tool._get_multiline_input()
        
        expected = "Line 1\nLine 2"
        self.assertEqual(result, expected)
    
    @patch('builtins.input', side_effect=KeyboardInterrupt())
    @patch('builtins.print')
    def test_get_multiline_input_with_keyboard_interrupt(self, mock_print, mock_input):
        """Test multiline input with keyboard interrupt (Ctrl+C)"""
        result = self.tool._get_multiline_input()
        
        self.assertEqual(result, "")
        # Should print cancellation message
        mock_print.assert_any_call("\nUser communication cancelled.")
    
    @patch('builtins.input', side_effect=['', '   ', '###END###'])
    @patch('builtins.print')
    def test_get_multiline_input_empty_lines(self, mock_print, mock_input):
        """Test multiline input with only empty/whitespace lines"""
        result = self.tool._get_multiline_input()
        
        # Should be empty after stripping
        self.assertEqual(result, "")
        # Should print no input message
        mock_print.assert_any_call("No input received from user.")
    
    @patch('builtins.input', side_effect=['Valid input', '###END###'])
    @patch('builtins.print')
    def test_get_multiline_input_with_character_count_message(self, mock_print, mock_input):
        """Test that character count is logged"""
        result = self.tool._get_multiline_input()
        
        self.assertEqual(result, "Valid input")
        # Should print character count
        expected_call = f"\n[USER_COMMUNICATE] Received reply ({len('Valid input')} characters)"
        mock_print.assert_any_call(expected_call)
    
    @patch.object(UserCommunicateTool, '_get_multiline_input', return_value="User's response")
    @patch('builtins.print')
    def test_execute_success(self, mock_print, mock_get_input):
        """Test successful execution"""
        async def run_test():
            parameters = {"message": "Please provide your input"}
            result = await self.tool.execute(parameters)
            return result
        
        result = asyncio.run(run_test())
        
        # Verify the result
        # Updated: execute now returns both question and user_reply
        expected = {"question": "Please provide your input", "user_reply": "User's response"}
        self.assertEqual(result, expected)
        
        # Verify message was printed
        mock_print.assert_any_call("[USER_COMMUNICATE] Sending message to user:")
        mock_print.assert_any_call("Please provide your input")
        mock_print.assert_any_call("\n" + "="*50)
    
    @patch.object(UserCommunicateTool, '_get_multiline_input', return_value="")
    @patch('builtins.print')
    def test_execute_empty_response(self, mock_print, mock_get_input):
        """Test execution with empty user response"""
        async def run_test():
            parameters = {"message": "Please respond"}
            result = await self.tool.execute(parameters)
            return result
        
        result = asyncio.run(run_test())
        
        # Should still return structure with empty reply
        expected = {"question": "Please respond", "user_reply": ""}
        self.assertEqual(result, expected)
    
    def test_execute_missing_message_parameter(self):
        """Test execute with missing message parameter"""
        async def run_test():
            parameters = {}
            with self.assertRaises(ValueError) as context:
                await self.tool.execute(parameters)
            return str(context.exception)
        
        error_message = asyncio.run(run_test())
        self.assertIn("USER_COMMUNICATE tool requires parameters: message", error_message)
    
    @patch.object(UserCommunicateTool, '_get_multiline_input', return_value="Detailed\nmultiline\nresponse")
    @patch('builtins.print')
    def test_execute_multiline_response(self, mock_print, mock_get_input):
        """Test execution with multiline user response"""
        async def run_test():
            parameters = {"message": "Explain in detail"}
            result = await self.tool.execute(parameters)
            return result
        
        result = asyncio.run(run_test())
        expected = {"user_reply": "Detailed\nmultiline\nresponse"}
        self.assertEqual(result, {"question": "Explain in detail", **expected})
    
    @patch.object(UserCommunicateTool, '_get_multiline_input', return_value="Response with special chars: !@#$%^&*()")
    @patch('builtins.print')
    def test_execute_special_characters(self, mock_print, mock_get_input):
        """Test execution with special characters in response"""
        async def run_test():
            parameters = {"message": "Enter special text"}
            result = await self.tool.execute(parameters)
            return result
        
        result = asyncio.run(run_test())
        expected = {"question": "Enter special text", "user_reply": "Response with special chars: !@#$%^&*()"}
        self.assertEqual(result, expected)
    
    @patch.object(UserCommunicateTool, '_get_multiline_input', return_value="Unicode test: 你好 🌟")
    @patch('builtins.print')
    def test_execute_unicode_response(self, mock_print, mock_get_input):
        """Test execution with Unicode characters in response"""
        async def run_test():
            parameters = {"message": "Enter Unicode text"}
            result = await self.tool.execute(parameters)
            return result
        
        result = asyncio.run(run_test())
        expected = {"question": "Enter Unicode text", "user_reply": "Unicode test: 你好 🌟"}
        self.assertEqual(result, expected)
    
    @patch('builtins.input', side_effect=['  Leading and trailing spaces  ', '###END###'])
    @patch('builtins.print')
    def test_get_multiline_input_whitespace_handling(self, mock_print, mock_input):
        """Test that whitespace is properly handled in multiline input"""
        result = self.tool._get_multiline_input()
        
        # Should preserve internal whitespace but strip leading/trailing
        self.assertEqual(result, "Leading and trailing spaces")
    
    @patch.object(UserCommunicateTool, '_get_multiline_input', return_value="Test response")
    @patch('builtins.print')
    def test_execute_parameter_extraction(self, mock_print, mock_get_input):
        """Test that message parameter is correctly extracted"""
        async def run_test():
            parameters = {
                "message": "Test message", 
                "extra_param": "should be ignored",
                "another_param": 123
            }
            result = await self.tool.execute(parameters)
            return result
        result = asyncio.run(run_test())
        # Should use the message parameter
        mock_print.assert_any_call("Test message")
        # Result should contain user reply
        expected = {"question": "Test message", "user_reply": "Test response"}
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
