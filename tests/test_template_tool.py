#!/usr/bin/env python3
"""Unit tests for TemplateTool"""

import unittest
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.template_tool import TemplateTool


class TestTemplateTool(unittest.TestCase):
    """Unit tests for TemplateTool"""
    
    def setUp(self):
        """Set up test environment"""
        self.tool = TemplateTool()

    def test_basic_template_replacement(self):
        """Test basic f-string template replacement"""
        async def run_test():
            template_content = "Hello {name}! Welcome to {company}."
            parameters = {
                'template_content': template_content,
                'name': 'John Doe',
                'company': 'Acme Corp'
            }
            
            result = await self.tool.execute(parameters)
            
            # Check the result structure
            self.assertIsInstance(result, dict)
            self.assertIn('content', result)
            self.assertIn('template_variables_used', result)
            
            # Check the formatted content
            expected_content = "Hello John Doe! Welcome to Acme Corp."
            self.assertEqual(result['content'], expected_content)
            
            # Check the variables used
            self.assertSetEqual(set(result['template_variables_used']), {'name', 'company'})
            
        asyncio.run(run_test())

    def test_multiple_variable_replacement(self):
        """Test template with multiple variables"""
        async def run_test():
            template_content = """Dear {customer_name},

Your order #{order_id} for {quantity} units of {product} 
has been processed successfully.

Total amount: ${total_amount}
Delivery date: {delivery_date}

Thank you for your business!

Best regards,
{sender_name}"""
            
            parameters = {
                'template_content': template_content,
                'customer_name': 'Alice Smith',
                'order_id': 'ORD-12345',
                'quantity': '3',
                'product': 'Widget Pro',
                'total_amount': '149.97',
                'delivery_date': '2024-01-15',
                'sender_name': 'Customer Service Team'
            }
            
            result = await self.tool.execute(parameters)
            
            # Check that all variables were replaced
            expected_variables = {'customer_name', 'order_id', 'quantity', 'product', 
                                'total_amount', 'delivery_date', 'sender_name'}
            self.assertSetEqual(set(result['template_variables_used']), expected_variables)
            
            # Check specific replacements
            content = result['content']
            self.assertIn('Dear Alice Smith,', content)
            self.assertIn('order #ORD-12345', content)
            self.assertIn('3 units of Widget Pro', content)
            self.assertIn('$149.97', content)
            
        asyncio.run(run_test())

    def test_missing_template_content(self):
        """Test error when template_content is missing"""
        async def run_test():
            parameters = {
                'name': 'John Doe',
                'company': 'Acme Corp'
            }
            
            with self.assertRaises(ValueError) as context:
                await self.tool.execute(parameters)
                
            self.assertIn('template_content parameter is required', str(context.exception))
            
        asyncio.run(run_test())

    def test_missing_template_variable(self):
        """Test error when template variable is missing from parameters"""
        async def run_test():
            template_content = "Hello {name}! Your balance is ${balance}."
            parameters = {
                'template_content': template_content,
                'name': 'John Doe'
                # Missing 'balance' parameter
            }
            
            with self.assertRaises(RuntimeError) as context:
                await self.tool.execute(parameters)
                
            error_msg = str(context.exception)
            self.assertIn('Template formatting failed', error_msg)
            self.assertIn('balance', error_msg)
            
        asyncio.run(run_test())

    def test_empty_template(self):
        """Test with empty template content"""
        async def run_test():
            parameters = {
                'template_content': '',
                'name': 'John Doe'
            }
            
            result = await self.tool.execute(parameters)
            
            self.assertEqual(result['content'], '')
            self.assertEqual(result['template_variables_used'], [])
            
        asyncio.run(run_test())

    def test_template_without_variables(self):
        """Test template that has no variables"""
        async def run_test():
            template_content = "This is a static message with no variables."
            parameters = {
                'template_content': template_content
            }
            
            result = await self.tool.execute(parameters)
            
            self.assertEqual(result['content'], template_content)
            self.assertEqual(result['template_variables_used'], [])
            
        asyncio.run(run_test())

    def test_numeric_parameters(self):
        """Test template with numeric parameters"""
        async def run_test():
            template_content = "Price: ${price}, Quantity: {qty}, Total: ${total}"
            parameters = {
                'template_content': template_content,
                'price': 25.99,
                'qty': 3,
                'total': 77.97
            }
            
            result = await self.tool.execute(parameters)
            
            expected_content = "Price: $25.99, Quantity: 3, Total: $77.97"
            self.assertEqual(result['content'], expected_content)
            
        asyncio.run(run_test())

    def test_special_characters_in_template(self):
        """Test template with special characters"""
        async def run_test():
            template_content = """Subject: {subject}

Hello {name},

This is a test email with special characters:
• Bullet point
© Copyright symbol  
™ Trademark
"Quoted text"
'Single quotes'

Regards,
{sender}"""
            
            parameters = {
                'template_content': template_content,
                'subject': 'Test Email',
                'name': 'Test User',
                'sender': 'System Admin'
            }
            
            result = await self.tool.execute(parameters)
            
            # Verify special characters are preserved
            content = result['content']
            self.assertIn('•', content)
            self.assertIn('©', content)
            self.assertIn('™', content)
            self.assertIn('"Quoted text"', content)
            
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
