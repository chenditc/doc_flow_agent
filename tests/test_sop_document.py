#!/usr/bin/env python3
"""
Unit tests for sop_document.py
"""

import os
import sys
import unittest
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from sop_document import SOPDocument, SOPDocumentLoader, SOPDocumentParser


class TestSOPDocument(unittest.TestCase):
    """Test SOPDocument dataclass"""
    
    def test_sop_document_creation(self):
        """Test creating a SOPDocument instance"""
        doc = SOPDocument(
            doc_id="test/doc",
            description="Test document",
            aliases=["test", "doc"],
            tool={"tool_id": "LLM", "parameters": {"prompt": "test"}},
            input_json_path={"input": "$.test"},
            output_json_path="$.output",
            body="## Test\nContent",
            parameters={"Test": "Content"},
            input_description={"input": "Test input"},
            output_description="Test output",
            result_validation_rule="Test validation rule"
        )
        
        self.assertEqual(doc.doc_id, "test/doc")
        self.assertEqual(doc.description, "Test document")
        self.assertEqual(doc.aliases, ["test", "doc"])
        self.assertEqual(doc.tool["tool_id"], "LLM")
        self.assertEqual(doc.input_json_path["input"], "$.test")
        self.assertEqual(doc.output_json_path, "$.output")
        self.assertEqual(doc.body, "## Test\nContent")
        self.assertEqual(doc.parameters["Test"], "Content")
        self.assertEqual(doc.input_description["input"], "Test input")
        self.assertEqual(doc.output_description, "Test output")
        self.assertEqual(doc.result_validation_rule, "Test validation rule")


class TestSOPDocumentLoader(unittest.TestCase):
    """Test SOPDocumentLoader class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test documents
        self.test_dir = tempfile.mkdtemp()
        self.docs_dir = Path(self.test_dir) / "sop_docs"
        self.docs_dir.mkdir()
        
        # Create test subdirectories
        (self.docs_dir / "tools").mkdir()
        (self.docs_dir / "general").mkdir()
        
        self.loader = SOPDocumentLoader(str(self.docs_dir))
        
        # Create sample SOP documents
        self._create_test_documents()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def _create_test_documents(self):
        """Create sample SOP documents for testing"""
        # Basic document
        basic_doc = """---
description: Basic test document
aliases:
  - basic
  - test
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  task: The task to perform
output_description: The result
---
## parameters.prompt

This is a basic test prompt: {task}
"""
        
        # Complex document with parameter replacement
        complex_doc = """---
description: Complex test document
aliases:
  - complex
  - advanced
tool:
  tool_id: CLI
  parameters:
    command: "{parameters.command}"
    timeout: 30
input_json_path:
  script: "$.script"
  args: "$.args"
output_json_path: "$.result.output"
input_description:
  script: Script to execute
  args: Arguments for the script
output_description: Command execution result
---
## parameters.command

#!/bin/bash
{script} {args}

## Extra Section

This is extra content that should be parsed.
"""
        
        # Document without parameters section
        simple_doc = """---
description: Simple document without parameters
tool:
  tool_id: USER
  parameters:
    message: "Simple message"
---
# Simple Document

This document has no parameters sections.
"""
        
        # Write test documents
        with open(self.docs_dir / "basic.md", 'w') as f:
            f.write(basic_doc)
        
        with open(self.docs_dir / "tools" / "complex.md", 'w') as f:
            f.write(complex_doc)
        
        with open(self.docs_dir / "general" / "simple.md", 'w') as f:
            f.write(simple_doc)
    
    def test_load_basic_document(self):
        """Test loading a basic SOP document"""
        doc = self.loader.load_sop_document("basic")
        
        self.assertEqual(doc.doc_id, "basic")
        self.assertEqual(doc.description, "Basic test document")
        self.assertEqual(doc.aliases, ["basic", "test"])
        self.assertEqual(doc.tool["tool_id"], "LLM")
        self.assertEqual(doc.tool["parameters"]["prompt"], "This is a basic test prompt: {task}")
        self.assertIn("parameters.prompt", doc.parameters)
        self.assertEqual(doc.input_description["task"], "The task to perform")
        self.assertEqual(doc.output_description, "The result")
    
    def test_load_nested_document(self):
        """Test loading a document from subdirectory"""
        doc = self.loader.load_sop_document("tools/complex")
        
        self.assertEqual(doc.doc_id, "tools/complex")
        self.assertEqual(doc.description, "Complex test document")
        self.assertEqual(doc.aliases, ["complex", "advanced"])
        self.assertEqual(doc.tool["tool_id"], "CLI")
        self.assertEqual(doc.input_json_path["script"], "$.script")
        self.assertEqual(doc.output_json_path, "$.result.output")
        self.assertIn("parameters.command", doc.parameters)
        self.assertIn("Extra Section", doc.parameters)
    
    def test_load_nonexistent_document(self):
        """Test loading a non-existent document"""
        with self.assertRaises(FileNotFoundError):
            self.loader.load_sop_document("nonexistent")
    
    def test_invalid_yaml_format(self):
        """Test loading document with invalid YAML format"""
        invalid_doc = """---
invalid yaml content: [unclosed list
---
# Content
"""
        with open(self.docs_dir / "invalid.md", 'w') as f:
            f.write(invalid_doc)
        
        with self.assertRaises(Exception):  # Should raise YAML parsing error
            self.loader.load_sop_document("invalid")
    
    def test_missing_yaml_frontmatter(self):
        """Test loading document without YAML frontmatter"""
        no_yaml_doc = """# Document without YAML

This document has no frontmatter.
"""
        with open(self.docs_dir / "no_yaml.md", 'w') as f:
            f.write(no_yaml_doc)
        
        with self.assertRaises(ValueError):
            self.loader.load_sop_document("no_yaml")
    
    def test_parse_markdown_sections(self):
        """Test markdown section parsing"""
        body = """## First Section

This is the first section content.
With multiple lines.

## Second Section

This is the second section.

## Third Section
Single line section.
"""
        
        parameters = self.loader._parse_markdown_sections(body)
        
        self.assertIn("First Section", parameters)
        self.assertIn("Second Section", parameters)
        self.assertIn("Third Section", parameters)
        
        self.assertIn("This is the first section content", parameters["First Section"])
        self.assertIn("With multiple lines", parameters["First Section"])
        self.assertEqual(parameters["Second Section"], "This is the second section.")
        self.assertEqual(parameters["Third Section"], "Single line section.")
    
    def test_replace_tool_parameters(self):
        """Test tool parameter replacement with markdown sections"""
        tool_data = {
            "tool_id": "TEST",
            "parameters": {
                "prompt": "{parameters.prompt}",
                "command": "{parameters.command}",
                "unchanged": "static_value"
            }
        }
        
        parameters = {
            "parameters.prompt": "Dynamic prompt content",
            "parameters.command": "echo 'test'",
            "unused_section": "This won't be used"
        }
        
        with patch('builtins.print'):  # Suppress print statements
            result = self.loader._replace_tool_parameters_with_sections(tool_data, parameters)
        
        self.assertEqual(result["parameters"]["prompt"], "Dynamic prompt content")
        self.assertEqual(result["parameters"]["command"], "echo 'test'")
        self.assertEqual(result["parameters"]["unchanged"], "static_value")
        
        # Original tool_data should be unchanged
        self.assertEqual(tool_data["parameters"]["prompt"], "{parameters.prompt}")
    
    def test_no_tool_parameters(self):
        """Test parameter replacement when tool has no parameters"""
        tool_data = {"tool_id": "TEST"}
        parameters = {"section": "content"}
        
        result = self.loader._replace_tool_parameters_with_sections(tool_data, parameters)
        self.assertEqual(result, tool_data)


class TestSOPDocumentParser(unittest.TestCase):
    """Test SOPDocumentParser class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test documents
        self.test_dir = tempfile.mkdtemp()
        self.docs_dir = Path(self.test_dir) / "sop_docs"
        self.docs_dir.mkdir()
        
        # Create test subdirectories
        (self.docs_dir / "blog").mkdir()
        (self.docs_dir / "tools").mkdir()
        
        self.parser = SOPDocumentParser(str(self.docs_dir))
        
        # Create test documents
        self._create_test_documents()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def _create_test_documents(self):
        """Create test documents for parser testing"""
        blog_doc = """---
description: Generate blog outline
aliases:
  - blog outline
  - outline generation
tool:
  tool_id: LLM
---
# Blog Outline Generator
"""
        
        bash_doc = """---
description: Execute bash commands
aliases:
  - bash
  - terminal
  - command line
tool:
  tool_id: CLI
---
# Bash Tool
"""
        
        python_doc = """---
description: Generate and execute python code
tool:
  tool_id: PYTHON_EXECUTOR
---
# Python Tool
"""
        
        llm_doc = """---
description: General Large Language Model Text Generation
tool:
  tool_id: LLM
---
# LLM Tool
"""
        
        user_communicate_doc = """---
description: Send message to user and collect response
tool:
  tool_id: USER_COMMUNICATE
---
# User Communication Tool
"""
        
        # Create general directory for plan.md
        (self.docs_dir / "general").mkdir()
        
        plan_doc = """---
doc_id: general/plan
description: Break down complex tasks into multiple manageable substeps
tool:
  tool_id: LLM
---
# Task Planning Tool
"""
        
        with open(self.docs_dir / "blog" / "generate_outline.md", 'w') as f:
            f.write(blog_doc)
        
        with open(self.docs_dir / "tools" / "bash.md", 'w') as f:
            f.write(bash_doc)
            
        with open(self.docs_dir / "tools" / "python.md", 'w') as f:
            f.write(python_doc)
            
        with open(self.docs_dir / "tools" / "llm.md", 'w') as f:
            f.write(llm_doc)
            
        with open(self.docs_dir / "tools" / "user_communicate.md", 'w') as f:
            f.write(user_communicate_doc)
            
        with open(self.docs_dir / "general" / "plan.md", 'w') as f:
            f.write(plan_doc)
    
    def test_get_all_doc_ids(self):
        """Test getting all available document IDs"""
        doc_ids = self.parser._get_all_doc_ids()
        
        # Check for expected documents
        expected_docs = [
            "blog/generate_outline",
            "tools/bash", 
            "tools/python",
            "tools/llm", 
            "tools/user_communicate",
            "general/plan"
        ]
        
        for expected_doc in expected_docs:
            self.assertIn(expected_doc, doc_ids)
        
        self.assertEqual(len(doc_ids), len(expected_docs))
    
    def test_get_all_doc_ids_empty_directory(self):
        """Test getting doc IDs from empty directory"""
        empty_parser = SOPDocumentParser("/nonexistent/path")
        doc_ids = empty_parser._get_all_doc_ids()
        self.assertEqual(doc_ids, [])
    
    def test_validate_with_llm_success(self):
        """Test successful LLM validation"""
        # Create a mock LLMTool instance
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "<doc_id>blog/generate_outline</doc_id>",
            "tool_calls": []
        }
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            # Test data
            candidates = [("blog/generate_outline", "full_path")]
            description = "Generate a blog outline"
            all_doc_ids = ["blog/generate_outline", "tools/bash"]
            
            # Run test
            async def run_test():
                result = await self.parser._validate_with_llm(description, candidates, all_doc_ids)
                return result
            
            result = asyncio.run(run_test())
            self.assertEqual(result, "blog/generate_outline")
    
    def test_validate_with_llm_none_response(self):
        """Test LLM validation returning NONE"""
        # Create a mock LLMTool instance
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "<doc_id>NONE</doc_id>",
            "tool_calls": []
        }
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            # Test data
            candidates = [("blog/generate_outline", "full_path")]
            description = "Something unrelated"
            all_doc_ids = ["blog/generate_outline", "tools/bash"]
            
            # Run test
            async def run_test():
                result = await self.parser._validate_with_llm(description, candidates, all_doc_ids)
                return result
            
            result = asyncio.run(run_test())
            self.assertIsNone(result)
    
    def test_validate_with_llm_invalid_response(self):
        """Test LLM validation with invalid response"""
        # Create a mock LLMTool instance
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "<doc_id>invalid/document</doc_id>",
            "tool_calls": []
        }
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            # Test data
            candidates = [("blog/generate_outline", "full_path")]
            description = "Generate a blog outline"
            all_doc_ids = ["blog/generate_outline", "tools/bash"]
            
            # Run test
            async def run_test():
                result = await self.parser._validate_with_llm(description, candidates, all_doc_ids)
                return result
            
            result = asyncio.run(run_test())
            self.assertIsNone(result)
    
    def test_parse_sop_doc_id_no_candidates(self):
        """Test parsing when no candidates are found - should use tool selection"""
        # Create a mock LLMTool instance for tool selection
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "Task analysis completed.",
            "tool_calls": [{
                "name": "select_tool_for_task",
                "arguments": {
                    "can_complete_with_tool": False,
                    "selected_tool_doc": "general/plan",
                    "reasoning": "This is an unrelated task that needs breakdown"
                }
            }]
        }
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                result = await self.parser.parse_sop_doc_id_from_description("completely unrelated task")
                return result
            
            result = asyncio.run(run_test())
            sop_doc_id, doc_selection_message = result
            self.assertEqual(sop_doc_id, "general/plan")
            self.assertEqual(doc_selection_message, "")
    
    def test_parse_sop_doc_id_simple_tool_selection(self):
        """Test tool selection for simple tasks that can be completed by one tool"""
        # Create a mock LLMTool instance for tool selection
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "Task analysis completed.",
            "tool_calls": [{
                "name": "select_tool_for_task",
                "arguments": {
                    "can_complete_with_tool": True,
                    "selected_tool_doc": "tools/python",
                    "reasoning": "This task can be completed with Python code generation and execution"
                }
            }]
        }
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                result = await self.parser.parse_sop_doc_id_from_description("Calculate the factorial of 10")
                return result
            
            result = asyncio.run(run_test())
            sop_doc_id, doc_selection_message = result
            self.assertEqual(sop_doc_id, "tools/python")
            self.assertEqual(doc_selection_message, "")
    
    def test_parse_sop_doc_id_unexpected_tool_call_raises_exception(self):
        """Test that unexpected tool call raises ValueError"""
        # Create a mock LLMTool instance that returns unexpected tool call
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "Task analysis completed.",
            "tool_calls": [{
                "name": "unexpected_function_name",
                "arguments": {
                    "some_arg": "some_value"
                }
            }]
        }
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                return await self.parser.parse_sop_doc_id_from_description("some random task")
            
            with self.assertRaises(ValueError) as context:
                asyncio.run(run_test())
            
            self.assertIn("Unexpected tool call: unexpected_function_name", str(context.exception))
            self.assertIn("expected 'select_tool_for_task'", str(context.exception))
    
    def test_parse_sop_doc_id_invalid_tool_selection_raises_exception(self):
        """Test that invalid tool selection raises ValueError"""
        # Create a mock LLMTool instance that returns invalid tool selection
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "Task analysis completed.",
            "tool_calls": [{
                "name": "select_tool_for_task",
                "arguments": {
                    "can_complete_with_tool": True,
                    "selected_tool_doc": "tools/invalid_tool",
                    "reasoning": "This tool doesn't exist"
                }
            }]
        }
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                return await self.parser.parse_sop_doc_id_from_description("some task")
            
            with self.assertRaises(ValueError) as context:
                asyncio.run(run_test())
            
            self.assertIn("Invalid tool selection: tools/invalid_tool", str(context.exception))
            self.assertIn("valid options are:", str(context.exception))
    
    def test_parse_sop_doc_id_full_path_match(self):
        """Test parsing with full path match"""
        # Create a mock LLMTool instance
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "<doc_id>blog/generate_outline</doc_id>",
            "tool_calls": []
        }
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                result = await self.parser.parse_sop_doc_id_from_description("Use blog/generate_outline to create outline")
                return result
            
            result = asyncio.run(run_test())
            sop_doc_id, doc_selection_message = result
            self.assertEqual(sop_doc_id, "blog/generate_outline")
            self.assertEqual(doc_selection_message, "")
    
    def test_parse_sop_doc_id_filename_match(self):
        """Test parsing with filename match"""
        # Create a mock LLMTool instance
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "<doc_id>tools/bash</doc_id>",
            "tool_calls": []
        }
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                result = await self.parser.parse_sop_doc_id_from_description("Execute commands using bash")
                return result
            
            result = asyncio.run(run_test())
            sop_doc_id, doc_selection_message = result
            self.assertEqual(sop_doc_id, "tools/bash")
            self.assertEqual(doc_selection_message, "")
    
    def test_parse_sop_doc_id_mixed_language_boundary(self):
        """Doc ID detection should work when surrounded by Chinese characters"""
        mock_llm_tool = AsyncMock()

        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                return await self.parser.parse_sop_doc_id_from_description("根据tools/bash完成任务")

            sop_doc_id, message = asyncio.run(run_test())

        self.assertEqual(sop_doc_id, "tools/bash")
        self.assertEqual(message, "")
        mock_llm_tool.execute.assert_not_called()

    def test_parse_sop_doc_id_with_tracer(self):
        """Test parsing with tracer enabled"""
        # Create a mock LLMTool instance
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "<doc_id>blog/generate_outline</doc_id>",
            "tool_calls": []
        }
        
        # Mock tracer
        mock_tracer = MagicMock()
        mock_tracer.enabled = True
        mock_phase = MagicMock()
        mock_tracer.current_task_execution.phases.get.return_value = mock_phase
        mock_tracer._generate_id.return_value = "test-id"
        
        # Create parser with mock tracer
        parser_with_tracer = SOPDocumentParser(tracer=mock_tracer)
        
        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                # Use a description that will match the document ID
                result = await parser_with_tracer.parse_sop_doc_id_from_description("Use blog/generate_outline to create outline")
                return result
            
            result = asyncio.run(run_test())
            sop_doc_id, doc_selection_message = result
            self.assertEqual(sop_doc_id, "blog/generate_outline")
            self.assertEqual(doc_selection_message, "")
            
            # Verify tracer interactions
            self.assertIsNotNone(mock_phase.candidate_documents)


class TestSOPDocumentIntegration(unittest.TestCase):
    """Integration tests for the SOP document system"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Use the actual sop_docs directory for integration testing
        self.loader = SOPDocumentLoader()
        self.parser = SOPDocumentParser()
    
    def test_load_real_documents(self):
        """Test loading real SOP documents from the project"""
        # Test loading a document that should exist
        try:
            doc = self.loader.load_sop_document("general/fallback")
            self.assertIsNotNone(doc)
            self.assertEqual(doc.doc_id, "general/fallback")
            self.assertIsNotNone(doc.description)
            self.assertIsInstance(doc.aliases, list)
        except FileNotFoundError:
            self.skipTest("general/fallback document not found in sop_docs")
    
    def test_get_real_doc_ids(self):
        """Test getting real document IDs from the project"""
        doc_ids = self.parser._get_all_doc_ids()
        self.assertIsInstance(doc_ids, list)
        # Should find some documents if sop_docs directory exists
        if Path("sop_docs").exists():
            self.assertGreater(len(doc_ids), 0)


def run_async_test(coro):
    """Helper function to run async tests in sync test methods"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


if __name__ == '__main__':
    unittest.main()
