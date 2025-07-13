#!/usr/bin/env python3
import unittest
import sys
import os

from utils import set_json_path_value, get_json_path_value


class TestUtils(unittest.TestCase):
    """Test cases for utility functions in utils.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_data = {
            "title": "Existing Title",
            "blog": {
                "author": "John Doe",
                "posts": [
                    {"id": 1, "title": "First Post"},
                    {"id": 2, "title": "Second Post"}
                ]
            },
            "tags": ["python", "json"]
        }

    def test_set_json_path_value_simple_path(self):
        """Test setting value with simple path ($.key)"""
        data = {}
        set_json_path_value(data, "$.title", "My Blog Title")
        self.assertEqual(data, {"title": "My Blog Title"})

    def test_set_json_path_value_simple_path_overwrite(self):
        """Test overwriting existing value with simple path"""
        data = {"title": "Old Title"}
        set_json_path_value(data, "$.title", "New Title")
        self.assertEqual(data, {"title": "New Title"})

    def test_set_json_path_value_nested_path_new(self):
        """Test setting value with nested path when parent doesn't exist"""
        data = {}
        set_json_path_value(data, "$.blog.title", "Nested Title")
        expected = {"blog": {"title": "Nested Title"}}
        self.assertEqual(data, expected)

    def test_set_json_path_value_nested_path_existing(self):
        """Test setting value with nested path when parent exists"""
        data = {"blog": {"author": "John"}}
        set_json_path_value(data, "$.blog.title", "Another Title")
        expected = {"blog": {"author": "John", "title": "Another Title"}}
        self.assertEqual(data, expected)

    def test_set_json_path_value_deep_nested_path(self):
        """Test setting value with deep nested path"""
        data = {}
        set_json_path_value(data, "$.blog.meta.tags", ["python", "json"])
        expected = {"blog": {"meta": {"tags": ["python", "json"]}}}
        self.assertEqual(data, expected)

    def test_set_json_path_value_various_types(self):
        """Test setting different value types"""
        data = {}
        
        # String value
        set_json_path_value(data, "$.title", "String Title")
        self.assertEqual(data["title"], "String Title")
        
        # Integer value
        set_json_path_value(data, "$.count", 42)
        self.assertEqual(data["count"], 42)
        
        # List value
        set_json_path_value(data, "$.tags", ["tag1", "tag2"])
        self.assertEqual(data["tags"], ["tag1", "tag2"])
        
        # Dictionary value
        set_json_path_value(data, "$.config", {"debug": True, "timeout": 30})
        self.assertEqual(data["config"], {"debug": True, "timeout": 30})
        
        # Boolean value
        set_json_path_value(data, "$.active", True)
        self.assertEqual(data["active"], True)
        
        # None value
        set_json_path_value(data, "$.empty", None)
        self.assertEqual(data["empty"], None)

    def test_set_json_path_value_invalid_path_format(self):
        """Test error handling for invalid path formats"""
        data = {}
        
        # Path not starting with $.
        with self.assertRaises(ValueError) as cm:
            set_json_path_value(data, "title", "value")
        self.assertIn("JSON path must start with '$.'", str(cm.exception))
        
        # Empty path
        with self.assertRaises(ValueError):
            set_json_path_value(data, "", "value")

    def test_set_json_path_value_intermediate_non_dict(self):
        """Test error when intermediate path is not a dictionary"""
        data = {"blog": "string_value"}
        
        with self.assertRaises(ValueError) as cm:
            set_json_path_value(data, "$.blog.title", "value")
        self.assertIn("intermediate key 'blog' is not a dictionary", str(cm.exception))

    def test_set_json_path_value_complex_path_not_supported(self):
        """Test that complex paths with arrays raise NotImplementedError"""
        data = {}
        
        with self.assertRaises(NotImplementedError):
            set_json_path_value(data, "$.items[0].title", "value")

    def test_get_json_path_value_simple_path(self):
        """Test getting value with simple path"""
        data = {"title": "My Title"}
        result = get_json_path_value(data, "$.title")
        self.assertEqual(result, "My Title")

    def test_get_json_path_value_simple_path_not_found(self):
        """Test getting value with simple path when key doesn't exist"""
        data = {"title": "My Title"}
        result = get_json_path_value(data, "$.description")
        self.assertIsNone(result)

    def test_get_json_path_value_nested_path(self):
        """Test getting value with nested path"""
        result = get_json_path_value(self.sample_data, "$.blog.author")
        self.assertEqual(result, "John Doe")

    def test_get_json_path_value_nested_path_not_found(self):
        """Test getting value with nested path when path doesn't exist"""
        result = get_json_path_value(self.sample_data, "$.blog.nonexistent")
        self.assertIsNone(result)

    def test_get_json_path_value_deep_nested_path(self):
        """Test getting value with deep nested path using jsonpath"""
        data = {"blog": {"meta": {"tags": ["python", "json"]}}}
        result = get_json_path_value(data, "$.blog.meta.tags")
        self.assertEqual(result, ["python", "json"])

    def test_get_json_path_value_various_types(self):
        """Test getting different value types"""
        data = {
            "title": "String Title",
            "count": 42,
            "tags": ["tag1", "tag2"],
            "config": {"debug": True},
            "active": True,
            "empty": None
        }
        
        self.assertEqual(get_json_path_value(data, "$.title"), "String Title")
        self.assertEqual(get_json_path_value(data, "$.count"), 42)
        self.assertEqual(get_json_path_value(data, "$.tags"), ["tag1", "tag2"])
        self.assertEqual(get_json_path_value(data, "$.config"), {"debug": True})
        self.assertEqual(get_json_path_value(data, "$.active"), True)
        self.assertIsNone(get_json_path_value(data, "$.empty"))

    def test_get_json_path_value_invalid_path(self):
        """Test getting value with invalid path returns None"""
        data = {"title": "My Title"}
        result = get_json_path_value(data, "invalid.path")
        self.assertIsNone(result)

    def test_get_json_path_value_empty_data(self):
        """Test getting value from empty dictionary"""
        data = {}
        result = get_json_path_value(data, "$.title")
        self.assertIsNone(result)

    def test_set_and_get_integration(self):
        """Test integration between set and get functions"""
        data = {}
        
        # Set a simple value and get it back
        set_json_path_value(data, "$.title", "Integration Test")
        result = get_json_path_value(data, "$.title")
        self.assertEqual(result, "Integration Test")
        
        # Set a nested value and get it back
        set_json_path_value(data, "$.blog.author", "Jane Doe")
        result = get_json_path_value(data, "$.blog.author")
        self.assertEqual(result, "Jane Doe")
        
        # Verify the complete structure
        expected = {
            "title": "Integration Test",
            "blog": {"author": "Jane Doe"}
        }
        self.assertEqual(data, expected)

    def test_multiple_nested_operations(self):
        """Test multiple operations on the same nested structure"""
        data = {}
        
        # Build a complex structure step by step
        set_json_path_value(data, "$.blog.title", "My Blog")
        set_json_path_value(data, "$.blog.author", "John Smith")
        set_json_path_value(data, "$.blog.meta.created", "2024-01-01")
        set_json_path_value(data, "$.blog.meta.tags", ["tech", "programming"])
        set_json_path_value(data, "$.config.debug", True)
        
        # Verify all values
        self.assertEqual(get_json_path_value(data, "$.blog.title"), "My Blog")
        self.assertEqual(get_json_path_value(data, "$.blog.author"), "John Smith")
        self.assertEqual(get_json_path_value(data, "$.blog.meta.created"), "2024-01-01")
        self.assertEqual(get_json_path_value(data, "$.blog.meta.tags"), ["tech", "programming"])
        self.assertEqual(get_json_path_value(data, "$.config.debug"), True)
        
        # Verify complete structure
        expected = {
            "blog": {
                "title": "My Blog",
                "author": "John Smith",
                "meta": {
                    "created": "2024-01-01",
                    "tags": ["tech", "programming"]
                }
            },
            "config": {
                "debug": True
            }
        }
        self.assertEqual(data, expected)

    def test_overwrite_nested_values(self):
        """Test overwriting values in nested structures"""
        data = {"blog": {"title": "Old Title", "author": "Old Author"}}
        
        # Overwrite existing nested value
        set_json_path_value(data, "$.blog.title", "New Title")
        self.assertEqual(get_json_path_value(data, "$.blog.title"), "New Title")
        
        # Original author should remain unchanged
        self.assertEqual(get_json_path_value(data, "$.blog.author"), "Old Author")
        
        # Add new nested value
        set_json_path_value(data, "$.blog.published", "2024-01-01")
        self.assertEqual(get_json_path_value(data, "$.blog.published"), "2024-01-01")


if __name__ == '__main__':
    unittest.main()
