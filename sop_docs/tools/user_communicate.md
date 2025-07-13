---
description: Use to send message to user and collect response. The message needs to be prepared before this step. This doc is not used to generate messasge.
tool:
  tool_id: USER_COMMUNICATE
  parameters:
    message: "{parameters.message}"
input_description:
  message_to_user: The message we want to send to user.
output_description: The message we collected from user.
---
## parameters.message
Current task needs your help:

{message_to_user}