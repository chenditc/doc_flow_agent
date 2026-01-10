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
        self.assertFalse(doc.requires_planning_metadata)
    
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
        self.assertFalse(doc.requires_planning_metadata)
    
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
        async def _no_vector_search(_self, description: str, k: int = 5):
            return []
        self._vector_patch = patch.object(SOPDocumentParser, "_get_vector_search_candidates", new=_no_vector_search)
        self._vector_patch.start()
        
        # Create test documents
        self._create_test_documents()
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            self._vector_patch.stop()
        except RuntimeError:
            # Patch may have been stopped early by a test that exercises real vector search.
            pass
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
requires_planning_metadata: true
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
    
    def test_plan_document_requires_metadata_flag(self):
        """Ensure plan SOP is marked for planning metadata injection."""
        doc = self.parser.loader.load_sop_document("general/plan")
        self.assertTrue(doc.requires_planning_metadata)
    
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

    def test_vector_search_candidates_are_included_in_valid_docs(self):
        """Ensure vector search suggestions are added ahead of standard tools (real path via cache)."""
        from pathlib import Path

        # This test exercises the real vector-search path, so disable the default
        # test-wide patch that forces vector search to return [].
        self._vector_patch.stop()

        project_root = Path(__file__).resolve().parents[1]
        docs_dir = project_root / "sop_docs"

        mock_llm_tool = AsyncMock()

        async def choose_first_enum(payload):
            enum_values = payload["tools"][0]["function"]["parameters"]["properties"]["selected_tool_doc"]["enum"]
            selected = enum_values[0]
            return {
                "content": "Task analysis completed.",
                "tool_calls": [{
                    "name": "select_tool_for_task",
                    "arguments": {
                        "can_complete_with_tool": True,
                        "selected_tool_doc": selected,
                        "reasoning": "Pick first valid option for determinism in unit tests",
                    }
                }]
            }

        mock_llm_tool.execute.side_effect = choose_first_enum

        # Use real SOP corpus and real embedding cache/model configured by tests/conftest.py.
        parser = SOPDocumentParser(docs_dir=str(docs_dir), llm_tool=mock_llm_tool)

        # Use a query string that is guaranteed to be present in the committed embedding cache
        # (it matches one SOP doc's embedded text), so this test can run offline.
        query = "blog/generate_outline: Generate blog outline structure"
        with patch.dict(os.environ, {"SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE": "off"}):
            metadata = asyncio.run(parser.get_planning_metadata(query, include_vector_candidates=True))
        self.assertGreater(len(metadata["vector_candidates"]), 0)
        self.assertEqual(metadata["vector_candidates"][0]["doc_id"], "blog/generate_outline")

        async def run_test():
            with patch.dict(os.environ, {"SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE": "off"}):
                return await parser._select_tool_for_task(query)

        result = asyncio.run(run_test())

        call_payload = mock_llm_tool.execute.call_args[0][0]
        enum_values = call_payload["tools"][0]["function"]["parameters"]["properties"]["selected_tool_doc"]["enum"]
        self.assertEqual(result[0], enum_values[0])
        prompt_text = call_payload["prompt"]
        self.assertIn("<available_tools>", prompt_text)
        self.assertIn(f"<doc_id>{enum_values[0]}</doc_id>", prompt_text)

    def test_vector_search_auto_triggers_rewrite_when_score_low(self):
        """Auto mode should rewrite and re-search when the best score is below threshold."""
        from dataclasses import dataclass

        # We need the real _get_vector_search_candidates implementation.
        self._vector_patch.stop()

        @dataclass
        class FakeResult:
            doc_id: str
            description: str
            score: float
            metadata: dict

        description = "Open https://example.com/user/123 and click the blue button"
        rewritten_query = "browser click button"

        first = [FakeResult(doc_id="raw/doc", description="raw/doc: Raw", score=0.2, metadata={})]
        second = [FakeResult(doc_id="rewritten/doc", description="rewritten/doc: Rewritten", score=0.9, metadata={})]

        fake_store = MagicMock()

        async def search_side_effect(query: str, k: int = 5):
            if query == description:
                return first
            if query == rewritten_query:
                return second
            return []

        fake_store.similarity_search = AsyncMock(side_effect=search_side_effect)

        mock_llm_tool = AsyncMock()
        mock_llm_tool.small_model = "mock-small"
        mock_llm_tool.execute = AsyncMock(
            return_value={
                "content": "ok",
                "tool_calls": [{"name": "rewrite_sop_vector_query", "arguments": {"query": rewritten_query}}],
            }
        )

        parser = SOPDocumentParser(docs_dir=str(self.docs_dir), llm_tool=mock_llm_tool)

        with patch.dict(
            os.environ,
            {
                "SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE": "auto",
                "SOP_VECTOR_SEARCH_QUERY_REWRITE_THRESHOLD": "0.5",
            },
        ), patch.object(parser, "_ensure_vector_store", new=AsyncMock(return_value=fake_store)):
            candidates = asyncio.run(parser._get_vector_search_candidates(description, k=5))

        mock_llm_tool.execute.assert_awaited_once()
        self.assertEqual(fake_store.similarity_search.await_count, 2)
        self.assertEqual(fake_store.similarity_search.await_args_list[0].args[0], description)
        self.assertEqual(fake_store.similarity_search.await_args_list[1].args[0], rewritten_query)
        self.assertGreater(len(candidates), 0)
        self.assertEqual(candidates[0]["doc_id"], "rewritten/doc")

    def test_vector_search_auto_skips_rewrite_when_score_high(self):
        """Auto mode should not rewrite when the best score is above threshold."""
        from dataclasses import dataclass

        self._vector_patch.stop()

        @dataclass
        class FakeResult:
            doc_id: str
            description: str
            score: float
            metadata: dict

        description = "List all blog outline SOPs"
        first = [FakeResult(doc_id="raw/doc", description="raw/doc: Raw", score=0.8, metadata={})]

        fake_store = MagicMock()
        fake_store.similarity_search = AsyncMock(return_value=first)

        mock_llm_tool = AsyncMock()
        mock_llm_tool.small_model = "mock-small"
        mock_llm_tool.execute = AsyncMock()

        parser = SOPDocumentParser(docs_dir=str(self.docs_dir), llm_tool=mock_llm_tool)

        with patch.dict(
            os.environ,
            {
                "SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE": "auto",
                "SOP_VECTOR_SEARCH_QUERY_REWRITE_THRESHOLD": "0.5",
            },
        ), patch.object(parser, "_ensure_vector_store", new=AsyncMock(return_value=fake_store)):
            candidates = asyncio.run(parser._get_vector_search_candidates(description, k=5))

        mock_llm_tool.execute.assert_not_called()
        self.assertEqual(fake_store.similarity_search.await_count, 1)
        self.assertGreater(len(candidates), 0)
        self.assertEqual(candidates[0]["doc_id"], "raw/doc")

    def test_vector_search_mode_always_forces_rewrite(self):
        """Always mode should rewrite even when the best score is high."""
        from dataclasses import dataclass

        self._vector_patch.stop()

        @dataclass
        class FakeResult:
            doc_id: str
            description: str
            score: float
            metadata: dict

        description = "Open https://example.com and login as Alice"
        rewritten_query = "browser login"

        first = [FakeResult(doc_id="raw/doc", description="raw/doc: Raw", score=0.9, metadata={})]
        second = [FakeResult(doc_id="rewritten/doc", description="rewritten/doc: Rewritten", score=0.95, metadata={})]

        fake_store = MagicMock()

        async def search_side_effect(query: str, k: int = 5):
            if query == description:
                return first
            if query == rewritten_query:
                return second
            return []

        fake_store.similarity_search = AsyncMock(side_effect=search_side_effect)

        mock_llm_tool = AsyncMock()
        mock_llm_tool.small_model = "mock-small"
        mock_llm_tool.execute = AsyncMock(
            return_value={
                "content": "ok",
                "tool_calls": [{"name": "rewrite_sop_vector_query", "arguments": {"query": rewritten_query}}],
            }
        )

        parser = SOPDocumentParser(docs_dir=str(self.docs_dir), llm_tool=mock_llm_tool)

        with patch.dict(os.environ, {"SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE": "always"}), patch.object(
            parser, "_ensure_vector_store", new=AsyncMock(return_value=fake_store)
        ):
            candidates = asyncio.run(parser._get_vector_search_candidates(description, k=5))

        mock_llm_tool.execute.assert_awaited_once()
        self.assertEqual(fake_store.similarity_search.await_count, 2)
        self.assertEqual(candidates[0]["doc_id"], "rewritten/doc")

    def test_vector_search_deduplicates_existing_docs(self):
        """Ensure vector search entries aren't duplicated when already a tool."""
        mock_llm_tool = AsyncMock()
        mock_llm_tool.execute.return_value = {
            "content": "Task analysis completed.",
            "tool_calls": [{
                "name": "select_tool_for_task",
                "arguments": {
                    "can_complete_with_tool": True,
                    "selected_tool_doc": "tools/python",
                    "reasoning": "Python fits"
                }
            }]
        }

        parser = SOPDocumentParser(llm_tool=mock_llm_tool)

        async def fake_vector_candidates(self, description: str, k: int = 5):
            return [{"doc_id": "tools/python", "description": "Vector hit"}]

        available_tools = [{
            "doc_id": "tools/python",
            "description": "Python executor",
            "use_case": "Automate tasks"
        }]

        with patch.object(SOPDocumentParser, "_get_vector_search_candidates", new=fake_vector_candidates), \
             patch.object(SOPDocumentParser, "_get_available_tools", return_value=available_tools):
            async def run_test():
                return await parser._select_tool_for_task("Need python tool")

            result = asyncio.run(run_test())

        self.assertEqual(result[0], "tools/python")
        call_payload = mock_llm_tool.execute.call_args[0][0]
        enum_values = call_payload["tools"][0]["function"]["parameters"]["properties"]["selected_tool_doc"]["enum"]
        self.assertEqual(enum_values.count("tools/python"), 1)
    
    def test_get_planning_metadata_combines_sources(self):
        """Ensure helper returns combined metadata for planners."""
        parser = self.parser

        async def fake_vector_candidates(self, description: str, k: int = 5):
            return [{"doc_id": "custom/doc", "description": "Custom doc description"}]

        available_tools = [{
            "doc_id": "tools/python",
            "description": "Python executor",
            "use_case": "Automate tasks"
        }]

        with patch.object(SOPDocumentParser, "_get_vector_search_candidates", new=fake_vector_candidates), \
             patch.object(SOPDocumentParser, "_get_available_tools", return_value=available_tools):
            metadata = asyncio.run(parser.get_planning_metadata("Need a custom doc"))

        self.assertEqual(metadata["available_tools"], available_tools)
        self.assertEqual(metadata["vector_candidates"][0]["doc_id"], "custom/doc")
        self.assertEqual(metadata["valid_doc_ids"][0], "custom/doc")
        self.assertIn("Available tools (SOP references):", metadata["available_tools_markdown"])
        self.assertIn("<tool_id>tools/python</tool_id>", metadata["available_tools_markdown"])
        self.assertIn("<tool_description>Python executor</tool_description>", metadata["available_tools_markdown"])
        self.assertIn("Vector-recommended tools:", metadata["vector_candidates_markdown"])
        self.assertIn("<tool_id>custom/doc</tool_id>", metadata["vector_candidates_markdown"])
        self.assertIn("<tool_description>Custom doc description</tool_description>", metadata["vector_candidates_markdown"])
        self.assertIn("custom/doc", metadata["vector_candidates_json"])
        self.assertIn("tools/python", metadata["available_tools_json"])

    def test_get_planning_metadata_without_description_skips_vector(self):
        """Ensure helper can skip vector suggestions when description missing."""
        parser = self.parser

        async def failing_vector_candidates(self, description: str, k: int = 5):
            raise AssertionError("Vector search should not run without description")

        available_tools = [{
            "doc_id": "tools/python",
            "description": "Python executor",
            "use_case": "Automate tasks"
        }]

        with patch.object(SOPDocumentParser, "_get_vector_search_candidates", new=failing_vector_candidates), \
             patch.object(SOPDocumentParser, "_get_available_tools", return_value=available_tools):
            metadata = asyncio.run(parser.get_planning_metadata(None))

        self.assertEqual(metadata["vector_candidates"], [])
        self.assertIn("<tool_id>NONE</tool_id>", metadata["vector_candidates_markdown"])
        self.assertIn("general/plan", metadata["valid_doc_ids"])

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

        async def no_vector_candidates(self_instance, description: str, k: int = 5):
            return []

        # Temporarily patch the LLMTool class
        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                return await self.parser.parse_sop_doc_id_from_description("some task")

            with patch.object(SOPDocumentParser, "_get_vector_search_candidates", new=no_vector_candidates):
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
        # Filenames that are strictly alphanumeric (e.g. "bash") are considered too generic
        # for implicit filename matching. Use a non-alphanumeric tool filename here.
        mock_llm_tool = AsyncMock()

        with patch('tools.llm_tool.LLMTool', return_value=mock_llm_tool):
            async def run_test():
                return await self.parser.parse_sop_doc_id_from_description(
                    "Follow user_communicate to ask the user for missing information"
                )

            sop_doc_id, doc_selection_message = asyncio.run(run_test())

        self.assertEqual(sop_doc_id, "tools/user_communicate")
        self.assertEqual(doc_selection_message, "")
        mock_llm_tool.execute.assert_not_called()
    
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
