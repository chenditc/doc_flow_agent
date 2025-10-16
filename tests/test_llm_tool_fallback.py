import asyncio
import json
import os
import pytest
from tools.llm_tool import LLMTool


def test_xml_fallback_parsing(monkeypatch):
    """Test that when no native tool_calls returned, fallback XML parsing works.

    We simulate two sequential streaming calls:
      1. Returns no tool_calls and some irrelevant content.
      2. Returns XML-wrapped JSON arguments.
    """
    monkeypatch.setenv("INTEGRATION_TEST_MODE", "MOCK")
    tool = LLMTool()

    # Tool schema similar to real usage
    tools = [
        {
            "type": "function",
            "function": {
                "name": "generate_python_code",
                "description": "Generate Python code for the process_step function",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"],
                },
            },
        }
    ]

    class DummyDelta:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls

    class DummyChoice:
        def __init__(self, delta):
            self.delta = delta

    class DummyChunk:
        def __init__(self, content=None, tool_calls=None):
            self.choices = [DummyChoice(DummyDelta(content=content, tool_calls=tool_calls))]

    class FirstStream:
        def __init__(self):
            self._i = 0
        def __aiter__(self):
            return self
        async def __anext__(self):
            if self._i > 0:
                raise StopAsyncIteration
            self._i += 1
            return DummyChunk(content="No tool call here.")

    class SecondStream:
        def __init__(self):
            self._i = 0
        def __aiter__(self):
            return self
        async def __anext__(self):
            if self._i > 0:
                raise StopAsyncIteration
            self._i += 1
            # Provide final XML block
            return DummyChunk(content='<generate_python_code>{"code": "print(\\"hi\\")"}</generate_python_code>')

    call_count = {"n": 0}

    async def fake_create(**kwargs):  # type: ignore
        # First invocation -> first stream, second -> second stream
        call_count["n"] += 1
        if call_count["n"] == 1:
            return FirstStream()
        return SecondStream()

    monkeypatch.setattr(tool.client.chat.completions, "create", fake_create)

    async def run():
        result = await tool.execute({"prompt": "Test fallback", "tools": tools})
        return result

    try:
        result = asyncio.run(run())
    except RuntimeError as e:
        if "asyncio.run() cannot be called" in str(e):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(run())
            finally:
                loop.close()
        else:
            raise

    assert call_count["n"] == 2, "Should have made two LLM calls (original + fallback)"
    assert result["tool_calls"], "Fallback should produce tool_calls"
    assert result["tool_calls"][0]["name"] == "generate_python_code"
    assert result["tool_calls"][0]["arguments"]["code"].startswith("print"), "Parsed code argument missing or incorrect"


def test_public_parse_helper():
    tool = LLMTool()
    tools = [
        {"type": "function", "function": {"name": "foo", "parameters": {"type": "object", "properties": {"a": {"type": "number"}}, "required": ["a"]}}}
    ]
    content = '<foo>{"a": 3}</foo>'
    calls = tool.parse_tool_call_from_content(content, tools)
    assert calls and calls[0]["arguments"]["a"] == 3


@pytest.mark.skipif(os.getenv("INTEGRATION_TEST_MODE", "").lower() != "real", reason="Runs only in REAL integration mode due to real LLM call + long prompt size")
@pytest.mark.asyncio
async def test_long_prompt_real_mode_extraction():
    """Stress test: ensure long prompt with complex embedded XML-like content still yields tool call.

    This replicates a special case where some models fail to return proper tool_calls
    for long, instruction-heavy prompts (like the one seen in test.py stream_real). We
    send a condensed but still sizable prompt plus a tool schema and assert that a
    native tool call OR a fallback-parsed tool call is produced.

    Only executes when INTEGRATION_TEST_MODE=REAL to avoid network usage in MOCK mode.
    """
    from dotenv import load_dotenv
    load_dotenv()
    tool = LLMTool()

    long_prompt = """
You are a Python code generation assistant.
Your task is to write a single Python function named `process_step` that takes one argument: `context: dict`.
This function will be executed to perform following specific task. Import necessary library if you used any.
The context object will contain all the necessary data. The json serialized context object has been attached here for you to understand the input data structure.
The function should return a JSON-serializable value.

<available library>
aiohappyeyeballs
aiohttp
aiosignal
annotated-types
anyio
attrs
azure-core
azure-identity
certifi
cffi
charset-normalizer
click
cryptography
distro
fastapi
frozenlist
genson
h11
httpcore
httptools
httpx
idna
iniconfig
jiter
json_repair
jsonpath-ng
msal
msal-extensions
multidict
openai
packaging
pip
pluggy
ply
propcache
pycparser
pydantic
pydantic_core
PyJWT
pytest
pytest-asyncio
PyYAML
requests
six
sniffio
starlette
tqdm
typing-inspection
typing_extensions
urllib3
uvicorn
uvloop
watchdog
watchfiles
websockets
yarl
</available library>

<Task Description>
请按当前任务的要求生成图片，并下载保存到本地。返回图片 url 以及本地图片路径。
</Task Description>
<Document Guidance>
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
</Document Guidance>

<context object type>dict</context object type>
<Json serialized context object>
{
  "main_title": "万能结构逆袭",
  "description": "亮黄底，中心大号手写主标题白字红描边微倾，周围粉蓝涂鸦云。左上红便签：期中最后1个月；右上蓝圆框：先抢结构分；下方S形箭头三步：①审题抓点 ②万能结构搭骨架 ③开头结尾+细节周攻。左下橙圈：告别流水账。右下粉火焰+✨：稳步提分。散布📌💡❤️🔥✨。手绘下划线强调“结构”。底部小签：辰辰老师。整体高对比手帐涂鸦感冲刺氛围。",
  "prompt": "主标题：万能结构逆袭 封面描述：亮黄底，中心大号手写主标题白字红描边微倾，周围粉蓝涂鸦云。左上红便签：期中最后1个月；右上蓝圆框：先抢结构分；下方S形箭头三步：①审题抓点 ②万能结构搭骨架 ③开头结尾+细节周攻。左下橙圈：告别流水账。右下粉火焰+✨：稳步提分。散布📌💡❤️🔥✨。手绘下划线强调“结构”。底部小签：辰辰老师。整体高对比手帐涂鸦感冲刺氛围。",
  "raw": "主标题：万能结构逆袭\n封面描述：亮黄底，中心大号手写主标题白字红描边微倾，周围粉蓝涂鸦云。左上红便签：期中最后1个月；右上蓝圆框：先抢结构分；下方S形箭头三步：①审题抓点 ②万能结构搭骨架 ③开头结尾+细节周攻。左下橙圈：告别流水账。右下粉火焰+✨：稳步提分。散布📌💡❤️🔥✨。手绘下划线强调“结构”。底部小签：辰辰老师。整体高对比手帐涂鸦感冲刺氛围。"
}
</Json serialized context object>
"""

    tools = [
  {
    "type": "function",
    "function": {
      "name": "generate_python_code",
      "description": "Generate Python code for the process_step function",
      "parameters": {
        "type": "object",
        "properties": {
          "python_code": {
            "type": "string",
            "description": "Complete Python function definition for function `process_step` that performs the requested task"
          }
        },
        "required": [
          "python_code"
        ]
      }
    }
  }
]

    # Execute real call (streaming internally). We allow either native tool_calls or fallback XML parse.
    result = await tool.execute({"prompt": long_prompt, "tools": tools, "max_tokens": 4000})

    # If no native tool_calls, try fallback parse manually (model might have emitted raw XML form)
    if not result.get("tool_calls"):
        parsed = tool.parse_tool_call_from_content(result.get("content", ""), tools)
        if parsed:
            result["tool_calls"] = parsed

    assert result.get("tool_calls"), "Expected at least one tool call (native or fallback parsed) in REAL mode long prompt test"
    assert result["tool_calls"][0]["name"] == "generate_python_code"
    assert result["tool_calls"][0]["arguments"]["python_code"].startswith("def process_step"), "Parsed python_code argument missing or incorrect"
    # Compile to ensure valid code
    code_str = result["tool_calls"][0]["arguments"]["python_code"]
    try:
        compiled = compile(code_str, "<string>", "exec")
    except SyntaxError as e:
        pytest.fail(f"Generated python_code has syntax error: {e}")