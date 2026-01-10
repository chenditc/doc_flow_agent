---
description: Operate the browser and do action using python code (playwright or websocket) via cdp url. Eg. Open a webpage (http/https), click the button, open a tab and etc.
aliases:
  - Open url xxx using web browser.
tool:
  tool_id: PYTHON_EXECUTOR
  parameters:
    task_description: "{current_task}"
output_description: Necessary information for user to know if the task completed successfully, and information for user to continue next step. Must include cdp url and tab target Id used in this session.
skip_new_task_generation: true
result_validation_rule: No exception during code execution.
---
## How to get ws cdp url

If the ws cdp url if not provided, get cdp url by calling HTTP GET on http://localhost:8080/v1/browser/info.

The result looks like:
```json
{
  "success": true,
  "message": "Browser info retrieved",
  "data": {
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "cdp_url": "ws://localhost:50029/cdp/devtools/browser/86d19275-bd3f-430e-8e87-a56753fb762a",
    "vnc_url": "http://localhost:50029/vnc/index.html",
    "viewport": {
      "width": 1280,
      "height": 1024
    }
  }
}
```

## Which tab to use

If tab target Id is specified, use the specified target id. If the tab target id is missing or invalid, create a new tab.

## Important

Keep the tab and browser open unless specifically asked to close after complete.