# system
import os
# llm client
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv(override=True)

api_url = os.getenv("OPENAI_BASE_URL")
api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL")
client = OpenAI(base_url=api_url, api_key=api_key)

# ===== chat_loop =====
'''
状态演进
    state = {
        messages: list[dict]
    }

chat_loop 
    query(state) - chat(state)
        ↑_______________↓

chat
    llm(state) = res 
                 ↓
                (state.messages+=text) → out

  
'''

def query(state:dict):
    query = input("You: ")
    state["messages"].append({"role": "user", "content": query})
    return state

def chat(state:dict):
    res = client.chat.completions.create(model=model,messages=state["messages"],max_tokens=8000,)
    answer = res.choices[0].message.content
    state["messages"].append({"role": "assistant", "content": answer})
    return state

def chat_loop(state:dict):
    while True:
        state = query(state)
        state = chat(state)

        # 打印每轮ai回复
        answer = state["messages"][-1]["content"]
        print(f"Ai: {answer}")


if __name__ == "__main__":
    state = {
        "messages": []
    }
    chat_loop(state)

''' 
为什么要用状态演进
1 无数据复制开销
2 state 作为唯一数据源
3 循环结构更清晰 模块职责明确 更改只需替换对应模块

'''