# system
import os
import time

# tool 
import subprocess
from pathlib import Path
from typing import Any

# llm client
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv(override=True)

# 如果自定义了api_url 则移除默认的 认证token 允许使用第三方兼容anthropic的服务
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

# ===== 全局常量 =====
api_url = os.getenv("ANTHROPIC_BASE_URL")
api_key = os.getenv("ANTHROPIC_API_KEY")
model = os.getenv("ANTHROPIC_MODEL")
client = Anthropic(base_url=api_url, api_key=api_key)
WORKDIR = Path.cwd() # 当前文件夹地址

# ===== 辅助函数
def safe_path(raw: str) -> Path:
    """
    将用户/模型传入的路径解析为安全的绝对路径.
    防止路径穿越: 最终路径必须在 WORKDIR 之下.
    """
    target = (WORKDIR / raw).resolve()
    if not str(target).startswith(str(WORKDIR)):
        raise ValueError(f"Path traversal blocked: {raw} resolves outside WORKDIR")
    return target

def truncate(text: str, limit: int = 50000) -> str:
    """截断过长的输出, 并附上提示."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text)} total chars]"

# ===== [func] for run
def tool_bash(command: str, timeout: int = 30, **kw) -> str:
    """执行 shell 命令并返回输出."""
    # 基础安全检查: 拒绝明显危险的命令
    dangerous = ["rm -rf /", "mkfs", "> /dev/sd", "dd if="]
    for pattern in dangerous:
        if pattern in command:
            return f"Error: Refused to run dangerous command containing '{pattern}'"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(WORKDIR),
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n--- stderr ---\n" + result.stderr) if output else result.stderr
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return truncate(output) if output else "[no output]"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s"
    except Exception as exc:
        return f"Error: {exc}"


def tool_read_file(file_path: str, **kw) -> str:
    """读取文件内容."""
    try:
        target = safe_path(file_path)
        if not target.exists():
            return f"Error: File not found: {file_path}"
        if not target.is_file():
            return f"Error: Not a file: {file_path}"
        content = target.read_text(encoding="utf-8")
        return truncate(content)
    except ValueError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error: {exc}"


def tool_write_file(file_path: str, content: str, **kw) -> str:
    """写入内容到文件. 父目录不存在时自动创建."""
    try:
        target = safe_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} chars to {file_path}"
    except ValueError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error: {exc}"


def tool_edit_file(file_path: str, old_string: str, new_string: str, **kw) -> str:
    """
    精确替换文件中的文本.
    old_string 必须在文件中恰好出现一次, 否则报错.
    这和 OpenClaw 的 edit 工具逻辑一致.
    """
    try:
        target = safe_path(file_path)
        if not target.exists():
            return f"Error: File not found: {file_path}"

        content = target.read_text(encoding="utf-8")
        count = content.count(old_string)

        if count == 0:
            return "Error: old_string not found in file. Make sure it matches exactly."
        if count > 1:
            return (
                f"Error: old_string found {count} times. "
                "It must be unique. Provide more surrounding context."
            )

        new_content = content.replace(old_string, new_string, 1)
        target.write_text(new_content, encoding="utf-8")
        return f"Successfully edited {file_path}"
    except ValueError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error: {exc}"

def tool_list_directory(directory: str = ".", **kw) -> str:
    try:
        target = safe_path(directory)
        if not target.exists():
            return f"Error: Directory not found: {directory}"
        if not target.is_dir():
            return f"Error: Not a directory: {directory}"
        entries = sorted(target.iterdir())
        lines = []
        for entry in entries:
            prefix = "[dir]  " if entry.is_dir() else "[file] "
            lines.append(prefix + entry.name)
        return "\n".join(lines) if lines else "[empty directory]"
    except ValueError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error: {exc}"

# ===== [describe] for llm -> 在llm请求中告诉模型有哪些工具

TOOLS = [
    {
        "name": "bash",
        "description": (
            "Run a shell command and return its output. "
            "Use for system commands, git, package managers, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds. Default 30.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file (relative to working directory).",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file. Creates parent directories if needed. "
            "Overwrites existing content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file (relative to working directory).",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write.",
                },
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Replace an exact string in a file with a new string. "
            "The old_string must appear exactly once in the file. "
            "Always read the file first to get the exact text to replace."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file (relative to working directory).",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact text to find and replace. Must be unique.",
                },
                "new_string": {
                    "type": "string",
                    "description": "The replacement text.",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories in a directory under workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path relative to workspace directory. Default is root.",
                },
            },
            "required": [],
        },
    },
]

# ===== [describe] map_to [func] => {name:func} -> 在执行时候的映射
TOOL_HANDLERS: dict[str, Any] = {
    "bash": tool_bash,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "list_directory": tool_list_directory,
}

''' 
状态演进
    state = {
        messages
    }

agent_loop = chat_loop(tool_loop)

chat_loop 
    query(state) - tool_loop(state)
         ↑_____________↓

tool_loop
       llm(state) = res
        ↑            ↓
        |           res.tool_call?
        |           no → (state.messages+=text) → out
        |           yes → 
        |           → run_tool(name,args)=result
        |           → state+=result
        |____________↓
'''

def query(state:dict):
    user_input = input("You: ")
    state["messages"].append({"role": "user", "content": user_input})
    return state

def run_tool(state:dict,ai_answer):
    results = []
    for block in ai_answer:
        if block.type == "tool_use": 
            handler = TOOL_HANDLERS.get(block.name)
            if handler is None:
                return f"Error: Unknown tool '{block.name}'"
            try:
                output = handler(state=state, **block.input)
            except Exception as e:
                output = f"Error: {e}"
            # 收集结果
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(output)
            })
            # 打印
            print(f'[Tool]')
            print(f'{block.name}: {block.input}')
            print(f'[Result]')
            print(f'{str(output)[:200]}')
    return results

system_prompt = f"You are a coding agent at {WORKDIR}. Use bash to solve tasks."
# system_prompt = (
#     "You are a helpful AI assistant with access to tools.\n"
#     "Use the tools to help the user with file operations and shell commands.\n"
#     "Always read a file before editing it.\n"
#     "When using edit_file, the old_string must match EXACTLY (including whitespace)."
# )
def tool_loop(state:dict):
    while True:
        # 动态合成 system_prompt
        sys = system_prompt

        # llm(state)
        res = client.messages.create(model=model,messages=state["messages"],system=sys,tools=TOOLS,max_tokens=8000,)

        # 统计 token 使用情况
        state["in_tokens"] += res.usage.input_tokens
        state["out_tokens"] += res.usage.output_tokens

        # no
        if res.stop_reason == "end_turn":
            answer = res.content[0].text # 注意:这里只取 纯文本
            state["messages"].append({"role": "assistant", "content": answer})
            return state

        # yes
        elif res.stop_reason == "tool_use":
            # 1 ai 告诉 user 使用的 工具 和 参数
            ai_answer = res.content # 注意:这个content列表包含 TextBlock 和 ToolUseBlock 工具调用必须记录这两个
            state["messages"].append({"role": "assistant", "content": ai_answer})
            # 2 user 执行工具 并返回结果 (用代码直接执行工具 无需人工)
            result = run_tool(state,ai_answer)
            state["messages"].append({"role": "user", "content": result})
            # 3 统计次数
            state["tool_use_count"] += 1

        # other
        elif res.stop_reason == "max_tokens":
            print("超出token限制")
            break
        
def chat_loop(state:dict):
    while True:
        # 统计轮次
        state["turn"] += 1
        state["start_time"] = time.time()

        # 核心循环
        state = query(state)
        print('[thinking...]')
        state = tool_loop(state)
        
        # 打印每轮ai回复
        ai_text = state["messages"][-1]["content"]
        print(f"Ai: {ai_text}")

        # 打印统计结果
        state["end_time"] = time.time()
        time_use = state["end_time"] - state["start_time"]
        state["total_time"] += time_use
        print(f'[状态] 总轮次:{state["turn"]}  工具调用总数:{state["tool_use_count"]}  输入总token:{state["in_tokens"]}  输出总token:{state["out_tokens"]}  总耗时:{state["total_time"]:.1f}秒')
        print('====================================')
        
        

# ===== 启动
system_prompt = f"You are a coding agent at {WORKDIR}. Use bash to solve tasks."
# system_prompt = (
#     "You are a helpful AI assistant with access to tools.\n"
#     "Use the tools to help the user with file operations and shell commands.\n"
#     "Always read a file before editing it.\n"
#     "When using edit_file, the old_string must match EXACTLY (including whitespace)."
# )
if __name__ == "__main__":
    state = {
        # Counter
        "turn": 0,
        "tool_use_count": 0,
        "in_tokens": 0,
        "out_tokens": 0,
        "total_time":0,
        "start_time":None,
        "end_time":None,

        # chat
        "system_prompt": system_prompt,
        "messages": [],
    }
    chat_loop(state)

''' 
数据格式

# 1 query
query = '打开浏览器'

messages = [
{'content': '打开浏览器', 'role': 'user'}
]

# 2 tool_loop
# 第一次判断是否调用工具 -> 调用
res = Message(
    id='msg_202603011701476b858d6088254719', 
    container=None, 
    content=[
        TextBlock(
            citations=None, 
            text='我来帮你打开浏览器。', 
            type='text'
        ), 
        ToolUseBlock(
            id='call_361bfdae6f254ba2bc3db030', 
            caller=None, 
            input={'command': 'start "" "https://www.google.com"'}, 
            name='bash', 
            type='tool_use'
            )
        ], 
    model='glm-5', 
    role='assistant', 
    stop_reason='tool_use', 
    stop_sequence=None, 
    type='message', 
    usage=Usage(
        cache_creation=None, 
        cache_creation_input_tokens=None, 
        cache_read_input_tokens=128, 
        inference_geo=None, 
        input_tokens=51, 
        output_tokens=23, 
        server_tool_use=ServerToolUsage(
            web_fetch_requests=None, 
            web_search_requests=0
        ), 
    service_tier='standard'
    )
)

run_tool工具执行结果
result =  [
    {
        'content': '(no output, exit code: 0)',        
        'tool_use_id': 'call_326696faba8640d49acd5908',
        'type': 'tool_result'
    }
]

messages = [
{'content': '打开浏览器', 'role': 'user'},
{'content': [TextBlock(citations=None, text='我来帮你打开浏览器。', type='text'),ToolUseBlock(id='call_326696faba8640d49acd5908', caller=None, input={'command': 'start "" "https://www.google.com"'}, name='bash', type='tool_use')],'role': 'assistant'},
{'content': [{'content': '(no output, exit code: 0)','tool_use_id': 'call_326696faba8640d49acd5908','type': 'tool_result'}],'role': 'user'}
]

第二次判断是否调用工具 -> 不调用
res = Message(
    id='msg_20260301171726f8a11008ece245ab', 
    container=None, 
    content=[
        TextBlock(
            citations=None, 
            text='我已经为你打开了浏览器,默认访问了Google首页。浏览器应该已经在你的Windows系统上启动了。\n\n如果你想要访问特定的网站，可以告诉我网址，我可以帮你打开指定的页面。', 
            type='text'
        )
    ], 
    model='glm-5', 
    role='assistant', 
    stop_reason='end_turn', 
    stop_sequence=None, 
    type='message', 
    usage=Usage(
        cache_creation=None, 
        cache_creation_input_tokens=None, 
        cache_read_input_tokens=192, 
        inference_geo=None, 
        input_tokens=23, 
        output_tokens=38, 
        server_tool_use=ServerToolUsage(
            web_fetch_requests=None, 
            web_search_requests=0
        ), 
    service_tier='standard'
    )
)

messages = [
{'content': '打开浏览器', 'role': 'user'},
{'content': [TextBlock(citations=None, text='我来帮你打开浏览器。', type='text'),ToolUseBlock(id='call_326696faba8640d49acd5908', caller=None, input={'command': 'start "" "https://www.google.com"'}, name='bash', type='tool_use')],'role': 'assistant'},
{'content': [{'content': '(no output, exit code: 0)','tool_use_id': 'call_326696faba8640d49acd5908','type': 'tool_result'}],'role': 'user'},
{'content': [TextBlock(citations=None, text='我已经为你打开了浏览器,默认访问了Google首页。浏览器应该已经在你的Windows系统上启动了。\n\n如果你想要访问特定的网站，可以告诉我网址，我可以帮你打开指定的页面。', type='text')],'role': 'assistant'}
]
'''