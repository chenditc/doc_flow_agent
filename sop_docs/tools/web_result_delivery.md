---
description: Use to deliver task results to users through dynamically generated web pages. The LLM will create an appropriate result page based on the content type (text, JSON, files, images). Unlike WEB_USER_COMMUNICATE, this tool does not wait for user response and returns immediately.
tool:
  tool_id: WEB_RESULT_DELIVERY
input_description:
  result_data: The result to display to the user. A dictionary object, key is the meaning of the data. If there are local file or image needs to be delivered, use the file path as the value.
output_description: JSON object containing the result URL where user can view the results, status ("ok"), and whether the page already existed (existing boolean).
---