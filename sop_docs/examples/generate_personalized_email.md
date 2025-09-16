---
doc_id: examples/generate_personalized_email
description: Generate a personalized email using template formatting
aliases:
  - personalized email
  - email template
  - template email
tool:
  tool_id: TEMPLATE
  parameters: {}
input_description:
  recipient_name: The name of the email recipient
  company_name: The name of the recipient's company
  product_name: The name of the product being promoted
  discount_percentage: The discount percentage to offer
  sender_name: The name of the person sending the email
input_json_path:
  recipient_name: "$.recipient_name"
  company_name: "$.company_name"
  product_name: "$.product_name"
  discount_percentage: "$.discount_percentage"
  sender_name: "$.sender_name"
output_description: The generated personalized email content
---

Subject: Special Offer for {company_name} - {discount_percentage}% Off {product_name}!

Dear {recipient_name},

I hope this email finds you well! I'm reaching out because I believe {product_name} could be a great fit for {company_name}.

As a special offer, I'd like to extend a {discount_percentage}% discount on your first purchase of {product_name}. This is a limited-time offer that expires at the end of this month.

Here's what makes {product_name} special:
- Industry-leading features designed for companies like {company_name}
- 24/7 customer support
- Easy integration with your existing systems
- Proven ROI within the first 3 months

Would you be available for a quick 15-minute call this week to discuss how {product_name} can benefit {company_name}? I'd be happy to show you a personalized demo and answer any questions you might have.

Feel free to reply to this email or call me directly at (555) 123-4567.

Best regards,
{sender_name}

P.S. Don't forget about that {discount_percentage}% discount - it won't last long!
