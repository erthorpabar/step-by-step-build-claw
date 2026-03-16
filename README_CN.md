# Claw — 渐进式构建 AI Agent Loop

[English](README.md) | 中文

> 从最简单的单次 LLM 请求出发，逐步演进到完整的 Agent 架构。

## show
自主询问 ask info

<img width="718" height="326" alt="546456" src="https://github.com/user-attachments/assets/bfc07f64-87f7-42ed-954e-8a66755d57eb" />

部署项目 devops

<img width="730" height="411" alt="4534535" src="https://github.com/user-attachments/assets/71bcb2c8-f5c0-453a-af0c-e205a01fee21" />


plan模式 plan mode

<img width="849" height="191" alt="捕获" src="https://github.com/user-attachments/assets/ae950858-28e1-4e61-9d82-afc1400c7b79" />


## 目录

| 模块 | 说明 |
|------|------|
| `a01` | 单次请求 LLM |
| `a02` | 循环写入记忆，实现对话（Chat Loop） |
| `a03` | 状态演进，最佳架构实践 |
| `a04` | Chat Loop → Tool Loop |
| `a05` | Tool Loop + 统计功能 |
| `a06` | Plan 模式 |
| `a07` | Skill 模式 |

## 设计思路

**渐进式构建 + 状态演进**

1. **State 是系统唯一数据来源** — 所有对话数据都通过 state 管理
2. **每个函数修改 state** — 生产对话数据后立即更新 state，维护聊天记录
3. **循环结构清晰** — 逻辑简洁，模块职责明确，是最佳结构实践

## 支持格式

不同厂商的交互格式各不相同（LLM 请求格式、tool_call 判断、工具请求格式），当前支持：

| 厂商 | 目录 | 说明 |
|------|------|------|
| Anthropic | `a01_claude/` | 主要实现，兼容 Skill 生态 |
| OpenAI | `a02_openai/` | 同步书写的 OpenAI 格式代码 |

---

## 架构详解

### 1 Chat Loop

**流程图**

```
query(str) → history += query → llm(history) = out → history += out
  ↑                                                        ↓
  └────────────────────────────────────────────────────────┘
```

**伪代码**

```python
while True:
    query = user_input()
    history += query
    out = llm(history)
    history += out
```

---

### 2 Chat Loop（状态演进版）

**流程图**

```
query(state) → chat(state)
  ↑                 ↓
  └────────────────┘
```

**伪代码**

```python
def query(messages):
    query = user_input()
    messages += query
    return messages

def chat(messages):
    answer = llm(messages)
    messages += answer
    return messages

while True:
    state = query(state)
    state = chat(state)
```

---

### 3 Tool Loop

**状态结构**

```python
state = { "messages": [...] }
```

**Chat Loop 流程图**

```
query(state) → tool_loop(state)
  ↑                  ↓
  └─────────────────┘
```

**Tool Loop 内部流程图**

```
        llm(state) = res
         ↑            ↓
         │        res.tool_call?
         │        ├─ No  → state.messages += text → return
         │        └─ Yes → run_tool(name, args) = result
         │                 state.messages += result
         └─────────────────────┘
```

**伪代码**

```python
def query(messages):
    query = user_input()
    messages += query
    return messages

def tool_loop(messages):
    while True:
        res = llm(messages)
        if not res.tool_call:
            messages += res.content
            return messages
        messages += res.content
        result = run_tool(res)
        messages += result

def chat_loop(state):
    while True:
        state = query(state)
        state = tool_loop(state)
```

---

### 4 Plan 模式

- Plan 本质是一个**半强制唤醒**的 tool_call
- 如果 N 轮未调用，则注入提示词提醒模型更新计划进度

---

### 5 Skill 模式

```
1. 加载 [Skill 菜单] → 放入 system_prompt
2. 用户对话 → tool_call → 决定加载哪个 Skill
3. 加载 [Skill 全文] → 放入 system_prompt
4. 正常 tool_call 流程
```

---

## 改进方向

- [ ] 当前 文件编辑 更新方式为全量替换，应增加**增量替换**以减少 token 消耗
