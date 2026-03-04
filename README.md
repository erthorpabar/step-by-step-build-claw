# Claw — Build an AI Agent Loop, Step by Step

English | [中文](README_CN.md)

> Start from a simple single LLM request and progressively evolve into a full Agent architecture.

## Modules

| Module | Description |
|--------|-------------|
| `a01` | Single LLM request |
| `a02` | Chat Loop with memory |
| `a03` | State evolution — best architecture practice |
| `a04` | Chat Loop → Tool Loop |
| `a05` | Tool Loop + statistics |
| `a06` | Plan mode |
| `a07` | Skill mode |

## Design Philosophy

**Progressive construction + State evolution**

1. **State as the single source of truth** — all conversation data is managed through state
2. **Every function updates state** — state is updated immediately after producing conversation data
3. **Clean loop structure** — simple logic, clear module responsibilities, a best-practice architecture

## Supported Formats

Different providers have different interaction formats (LLM request format, tool_call detection, tool request format). Currently supported:

| Provider | Directory | Notes |
|----------|-----------|-------|
| Anthropic | `a01_claude/` | Primary implementation, compatible with the Skill ecosystem |
| OpenAI | `a02_openai/` | OpenAI-format implementation |

---

## Architecture

### 1 Chat Loop

**Flow**

```
query(str) → history += query → llm(history) = out → history += out
  ↑                                                        ↓
  └────────────────────────────────────────────────────────┘
```

**Pseudocode**

```python
while True:
    query = user_input()
    history += query
    out = llm(history)
    history += out
```

---

### 2 Chat Loop (State Evolution)

**Flow**

```
query(state) → chat(state)
  ↑                 ↓
  └────────────────┘
```

**Pseudocode**

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

**State structure**

```python
state = { "messages": [...] }
```

**Chat Loop flow**

```
query(state) → tool_loop(state)
  ↑                  ↓
  └─────────────────┘
```

**Tool Loop internal flow**

```
        llm(state) = res
         ↑            ↓
         │        res.tool_call?
         │        ├─ No  → state.messages += text → return
         │        └─ Yes → run_tool(name, args) = result
         │                 state.messages += result
         └─────────────────────┘
```

**Pseudocode**

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

### 4 Plan Mode

- Plan is essentially a **semi-forced** tool_call
- If no plan update occurs within N turns, a prompt is injected to remind the model to update its progress

---

### 5 Skill Mode

```
1. Load [Skill menu] → inject into system_prompt
2. User message → tool_call → decide which Skill to load
3. Load [Skill full content] → inject into system_prompt
4. Continue normal tool_call flow
```

---

## Future Improvements

- [ ] Current file editing uses full replacement; should add **incremental update** to reduce token usage
