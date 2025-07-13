#!/usr/bin/env python3
"""
Test cases for CLITool
"""

import unittest
import sys
import os
import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.cli_tool import CLITool


class TestCLITool(unittest.TestCase):
    """Test cases for CLITool class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cli_tool = CLITool()
    
    def test_init(self):
        """Test CLITool initialization"""
        self.assertEqual(self.cli_tool.tool_id, "CLI")
    
    def test_validate_parameters_success(self):
        """Test successful parameter validation"""
        parameters = {"command": "echo hello"}
        
        # Should not raise any exception
        self.cli_tool.validate_parameters(parameters, ['command'])
    
    def test_validate_parameters_missing_command(self):
        """Test parameter validation with missing command"""
        parameters = {}
        
        with self.assertRaises(ValueError) as context:
            self.cli_tool.validate_parameters(parameters, ['command'])
        
        self.assertIn("CLI tool requires parameters: command", str(context.exception))
    
    @patch('asyncio.create_subprocess_shell')
    @patch('builtins.print')
    def test_execute_success(self, mock_print, mock_subprocess):
        """Test successful command execution"""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'Hello World\n', b'')
        mock_subprocess.return_value = mock_process
        
        async def run_test():
            parameters = {"command": "echo 'Hello World'"}
            result = await self.cli_tool.execute(parameters)
            return result
        
        result_dict = asyncio.run(run_test())
        
        # Verify the result
        self.assertEqual(result_dict["stdout"], "Hello World\n")
        self.assertEqual(result_dict["stderr"], "")
        
        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once_with(
            "echo 'Hello World'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Verify print was called
        mock_print.assert_called_with("[CLI CALL] Command: echo 'Hello World'")
    
    @patch('asyncio.create_subprocess_shell')
    @patch('builtins.print')
    def test_execute_with_stderr(self, mock_print, mock_subprocess):
        """Test command execution with stderr output"""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'Output\n', b'Warning: something\n')
        mock_subprocess.return_value = mock_process
        
        async def run_test():
            parameters = {"command": "some_command"}
            result = await self.cli_tool.execute(parameters)
            return result
        
        result_dict = asyncio.run(run_test())
        
        # Verify the result
        self.assertEqual(result_dict["stdout"], "Output\n")
        self.assertEqual(result_dict["stderr"], "Warning: something\n")
    
    @patch('asyncio.create_subprocess_shell')
    @patch('builtins.print')
    def test_execute_failure(self, mock_print, mock_subprocess):
        """Test command execution failure"""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'', b'Command not found\n')
        mock_subprocess.return_value = mock_process
        
        async def run_test():
            parameters = {"command": "nonexistent_command"}
            with self.assertRaises(RuntimeError) as context:
                await self.cli_tool.execute(parameters)
            return str(context.exception)
        
        error_message = asyncio.run(run_test())
        
        self.assertIn("CLI command failed: Command not found", error_message)
    
    @patch('asyncio.create_subprocess_shell')
    @patch('builtins.print')
    def test_execute_empty_output(self, mock_print, mock_subprocess):
        """Test command execution with empty output"""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'', b'')
        mock_subprocess.return_value = mock_process
        
        async def run_test():
            parameters = {"command": "true"}  # Command that produces no output
            result = await self.cli_tool.execute(parameters)
            return result
        
        result_dict = asyncio.run(run_test())
        
        # Verify the result
        self.assertEqual(result_dict["stdout"], "")
        self.assertEqual(result_dict["stderr"], "")
    
    def test_execute_missing_command_parameter(self):
        """Test execute with missing command parameter"""
        async def run_test():
            parameters = {}
            with self.assertRaises(ValueError) as context:
                await self.cli_tool.execute(parameters)
            return str(context.exception)
        
        error_message = asyncio.run(run_test())
        self.assertIn("CLI tool requires parameters: command", error_message)
    
    def test_validate_command_safety_safe_commands(self):
        """Test command safety validation for safe commands"""
        safe_commands = [
            "ls -la",
            "cat file.txt",
            "echo hello",
            "pwd",
            "whoami",
            "grep pattern file.txt"
        ]
        
        for command in safe_commands:
            self.assertTrue(self.cli_tool.validate_command_safety(command))
    
    def test_validate_command_safety_dangerous_commands(self):
        """Test command safety validation for dangerous commands"""
        dangerous_commands = [
            "rm -rf /",
            "format c:",
            "del /f *.*",
            "sudo rm -rf /home",
            "RM -RF /tmp",  # Test case insensitive
            "some command && rm -rf /important"
        ]
        
        for command in dangerous_commands:
            self.assertFalse(self.cli_tool.validate_command_safety(command))
    
    def test_validate_command_safety_edge_cases(self):
        """Test command safety validation edge cases"""
        edge_cases = [
            "",  # Empty command
            "   ",  # Whitespace only
            "echo 'rm -rf' is dangerous",  # Contains dangerous text in quotes
        ]
        
        # Empty and whitespace commands should be considered safe
        self.assertTrue(self.cli_tool.validate_command_safety(""))
        self.assertTrue(self.cli_tool.validate_command_safety("   "))
        
        # Command with dangerous text in quotes should be flagged as dangerous
        # (our simple implementation doesn't distinguish context)
        self.assertFalse(self.cli_tool.validate_command_safety("echo 'rm -rf' is dangerous"))
    
    @patch('asyncio.create_subprocess_shell')
    @patch('builtins.print')
    def test_execute_command_parameter_retrieval(self, mock_print, mock_subprocess):
        """Test that command parameter is correctly retrieved and used"""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'test output', b'')
        mock_subprocess.return_value = mock_process
        
        async def run_test():
            parameters = {"command": "test command", "extra_param": "ignored"}
            await self.cli_tool.execute(parameters)
        
        asyncio.run(run_test())
        
        # Verify that the correct command was passed to subprocess
        mock_subprocess.assert_called_once_with(
            "test command",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )


if __name__ == '__main__':
    unittest.main()
