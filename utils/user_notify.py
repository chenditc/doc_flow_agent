#!/usr/bin/env python3
"""User Notification Utility for Doc Flow Agent
Handles multi-channel user notifications

Copyright 2024-2025 Di Chen

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
from typing import Dict, Any, Optional


def notify_user(message: str) -> bool:
    """Send notification to user via configured channel.
    
    Args:
        message: Complete message to send to user (should include all context like URLs, session info, etc.)
        
    Returns:
        True if notification was sent successfully, False otherwise
        
    Environment Variables:
    NOTIFICATION_CHANNEL: Channel to use ('stdout', 'slack', 'work_wechat'). Defaults to 'stdout'.
    """
    channel = get_default_channel()
    
    if channel == 'stdout':
        return _notify_stdout(message)
    elif channel == 'slack':
        return _notify_slack(message)
    elif channel == 'work_wechat':
        return _notify_work_wechat(message)
    else:
        print(f"[USER_NOTIFY] Warning: Unknown notification channel '{channel}', falling back to stdout")
        return _notify_stdout(message)


def _notify_stdout(message: str) -> bool:
    """Send notification to stdout (terminal)."""
    print(f"\n{'='*60}")
    print(f"[USER_NOTIFICATION] {message}")
    print(f"{'='*60}\n")
    return True


def _notify_slack(message: str) -> bool:
    """Send notification via Slack (future implementation)."""
    # TODO: Implement Slack webhook integration
    # Will need SLACK_WEBHOOK_URL environment variable
    print(f"[USER_NOTIFY] Slack notification not implemented yet, falling back to stdout")
    return _notify_stdout(message)


def _notify_work_wechat(message: str) -> bool:
    """Send notification via Work WeChat webhook.

    Uses environment variable WORK_WECHAT_WEBHOOK_URL. Payload per docs:
    {
        "msgtype": "text",
        "text": {"content": message}
    }
    """
    import json
    import urllib.request
    import urllib.error

    webhook = os.getenv('WORK_WECHAT_WEBHOOK_URL')
    if not webhook:
        print("[USER_NOTIFY] WORK_WECHAT_WEBHOOK_URL not set, falling back to stdout")
        return _notify_stdout(message)

    payload = {
        "msgtype": "text",
        "text": {"content": message[:2048]}  # Truncate to reasonable length
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        webhook,
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if 200 <= resp.status < 300:
                return True
            else:
                print(f"[USER_NOTIFY] Work WeChat webhook non-2xx status {resp.status}, falling back to stdout")
                return _notify_stdout(message)
    except urllib.error.URLError as e:
        print(f"[USER_NOTIFY] Work WeChat webhook error: {e}. Falling back to stdout")
        return _notify_stdout(message)


def get_available_channels() -> list[str]:
    """Get list of available notification channels."""
    return ['stdout', 'slack', 'work_wechat']


def get_default_channel() -> str:
    """Get default notification channel from environment or fallback."""
    return os.getenv('NOTIFICATION_CHANNEL', 'stdout')