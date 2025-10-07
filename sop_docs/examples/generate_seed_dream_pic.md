---
description: 调用火山seed生图api生成图片并保存
tool:
  tool_id: PYTHON_EXECUTOR
  parameters:
    task_description: "请按当前任务的要求生成图片，并下载保存到本地。返回图片 url 以及本地图片路径。"
input_description:
  related_context_content: 跟当前图片生成有关的描述。A python dict type.
output_description: 本地图片路径。
result_validation_rule: a dict with local_path should be returned, local_path is the path to the image.
---
## 该 API 的 curl 调用示例

Following instruction is fetched from: https://www.volcengine.com/docs/82379/1541523

ARK_API_KEY 可以从环境变量获取

prompt 需要干净（不包含无关信息），详细（对细节描述到位）。

curl -X POST https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedream-4-0-250828",
    "prompt": "星际穿越，黑洞，黑洞里冲出一辆快支离破碎的复古列车，抢视觉冲击力，电影大片，末日既视感，动感，对比色，oc渲染，光线追踪，动态模糊，景深，超现实主义，深蓝，画面通过细腻的丰富的色彩层次塑造主体与场景，质感真实，暗黑风背景的光影效果营造出氛围，整体兼具艺术幻想感，夸张的广角透视效果，耀光，反射，极致的光影，强引力，吞噬",
    "size": "2K",
    "sequential_image_generation": "disabled",
    "stream": false,
    "response_format": "url",
    "watermark": true
}'

Example response:

{
    "model": "doubao-seedream-4-0-250828",
    "created": 1757321139,
    "data": [
        {
            "url": "https://...",
            "size": "3104x1312"
        }
    ],
    "usage": {
        "generated_images": 1,
        "output_tokens": xxx,
        "total_tokens": xxx
    }
}

## Example code

def process_step(context: dict):
    import requests
    import json
    import os 
    import json 
    import time 
    from typing import Any, Dict

    API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    MODEL_NAME = "doubao-seedream-4-0-250828"


    # ---------- 图像设计指令（如果用户上下文不是已经在描述海报） ----------
    design_addendum = (
        "设计一张竖屏学习助力海报，强调清晰排版与可读性。"
        " 主题是中考倒计时心理支持。背景为柔和米黄色或浅奶咖纯色，四角圆润卡片感。"
        " 居中放置主标题：‘距离中考最后30天’（超大黑体或深棕粗体，高对比，可读性强）。"
        " 主标题下方留出呼吸感放副标题：‘家长这10种心理助力 = 孩子少走弯路’。"
        " 右下角小字与图标：‘📌 收藏慢看 · 稳住比分不焦虑’。"
        " 左上角一个📎或📘图标（简洁扁平风），右上角贴边有一条浅色便利贴效果纸条，上面手写风或细字：‘稳情绪 > 拼时长’。"
        " 画面四周点状浅绿色或浅蓝小圆点作轻盈装饰，保持留白。"
        " 风格：清爽、舒缓、教育海报、信息层级清晰、现代扁平化、轻质感阴影、色彩层次细腻、不过度花哨。"
        " 纵向构图，竖屏 4:3（宽:高≈3:4）比例。高分辨率，干净无水印，无额外无关元素。"
        " 文本需清晰锐利，不变形。"
    )

    final_prompt = design_addendum

    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "Missing ARK_API_KEY in environment",
            "local_path": None,
            "used_size": None,
            "prompt": final_prompt,
            "model": MODEL_NAME,
        }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    last_error = None
    response_json = None
    used_size = None

    # 推荐的宽高像素值：
    # 1:1
    # 2048x2048
    # 4:3
    # 2304x1728
    # 3:4
    # 1728x2304
    # 16:9
    # 2560x1440
    # 9:16
    # 1440x2560
    # 3:2
    # 2496x1664
    # 2:3
    # 1664x2496
    # 21:9
    # 3024x1296
    size = "1728x2304"  # 3:4

    payload = {
        "model": MODEL_NAME,
        "prompt": final_prompt,
        "size": size,
        "sequential_image_generation": "disabled",
        "stream": False,
        "response_format": "url",
        "watermark": False,
    }

    resp = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=120)

    # 正常 200 响应
    response_json = resp.json()

    remote_url = response_json["data"][0].get("url")
    if not remote_url:
        return {
            "success": False,
            "error": "No URL returned in API response",
            "local_path": None,
            "used_size": used_size,
            "prompt": final_prompt,
            "model": MODEL_NAME,
        }

    # 下载图片
    local_filename = f"generated_poster_{int(time.time())}.png"
    local_path = os.path.abspath(local_filename)

    try:
        img_resp = requests.get(remote_url, timeout=120)
        if img_resp.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(img_resp.content)
        else:
            return {
                "success": False,
                "error": f"Failed to download image: HTTP {img_resp.status_code}",
                "local_path": None,
                "used_size": used_size,
                "prompt": final_prompt,
                "model": MODEL_NAME,
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception downloading image: {e}",
            "local_path": None,
            "used_size": used_size,
            "prompt": final_prompt,
            "model": MODEL_NAME,
        }

    # 成功返回
    meta = {}
    for k in ("created", "usage"):
        if isinstance(response_json, dict) and k in response_json:
            meta[k] = response_json[k]

    return {
        "success": True,
        "local_path": local_path,
        "prompt": final_prompt,
        "model": MODEL_NAME,
        "api_response_meta": meta,
    }