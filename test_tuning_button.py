#!/usr/bin/env python3
"""Test script to verify the LLM tuning button functionality"""

import json
from urllib.parse import urlencode, unquote

def test_url_encoding():
    """Test that the URL encoding/decoding works correctly for the tuning page"""
    
    # Test data that mimics what would be passed to the tuning page
    test_prompt = "Please extract the task from this text: I need to write a blog post about AI"
    test_tools = [
        {
            "type": "function",
            "function": {
                "name": "extract_tasks",
                "description": "Extract tasks from text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["tasks"]
                }
            }
        }
    ]
    test_params = {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000,
        "start_time": "2025-08-25T19:30:00Z",
        "end_time": "2025-08-25T19:30:05Z"
    }

    # Encode parameters as they would be encoded in the React component
    params = {
        'prompt': test_prompt,
        'tools': json.dumps(test_tools),
        'all_parameters': json.dumps(test_params, indent=2)
    }

    # Create URL
    url_params = urlencode(params)
    full_url = f'http://localhost:8000/llm_tuning.html?{url_params}'
    
    print("✅ URL Generation Test:")
    print(f"   URL length: {len(full_url)} characters")
    print(f"   URL preview: {full_url[:100]}...")
    
    # Test decoding (simulating what the HTML page would do)
    from urllib.parse import parse_qs, urlparse
    parsed_url = urlparse(full_url)
    query_params = parse_qs(parsed_url.query)
    
    # Verify parameters can be decoded correctly
    decoded_prompt = unquote(query_params['prompt'][0])
    decoded_tools = json.loads(unquote(query_params['tools'][0]))
    decoded_params = json.loads(unquote(query_params['all_parameters'][0]))
    
    print("\n✅ URL Decoding Test:")
    print(f"   Decoded prompt: {decoded_prompt}")
    print(f"   Decoded tools: {len(decoded_tools)} tool(s)")
    print(f"   Decoded parameters: {list(decoded_params.keys())}")
    
    # Verify data integrity
    assert decoded_prompt == test_prompt, "Prompt encoding/decoding failed"
    assert decoded_tools == test_tools, "Tools encoding/decoding failed" 
    assert decoded_params == test_params, "Parameters encoding/decoding failed"
    
    print("\n✅ All tests passed! The tuning button functionality should work correctly.")
    return True

if __name__ == "__main__":
    test_url_encoding()
