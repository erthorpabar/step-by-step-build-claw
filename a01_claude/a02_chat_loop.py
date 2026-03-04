# system
import os
# llm client
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv(override=True)

# 如果自定义了api_url 则移除默认的 认证token 允许使用第三方兼容anthropic的服务
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

api_url = os.getenv("ANTHROPIC_BASE_URL")
api_key = os.getenv("ANTHROPIC_API_KEY")
model = os.getenv("ANTHROPIC_MODEL")
client = Anthropic(base_url=api_url, api_key=api_key)

# ===== chat_loop =====
''' 
chat_loop 
    query(str) - (messages+=query) - llm(messages)=out - (messages+=out)
      ↑______________________________________________________↓
'''
def chat_loop(messages):
    while True:
        # 1 
        query = input("You: ")
        messages.append({"role": "user", "content": query})

        # 2
        res = client.messages.create(model=model,messages=messages,max_tokens=8000,)
        answer = res.content[0].text
        messages.append({"role": "assistant", "content": answer})

        # 3
        print(f"Ai: {answer}")


if __name__ == "__main__":
    messages = []
    chat_loop(messages)

'''
数据格式

# 1 
query = '我叫美羊羊'

messages = [
{'content': '我叫美羊羊', 'role': 'user'}
]

# 2 
res = Message(
    id='msg_20260301165027f8ba16405b074b34', 
    container=None, 
    content=[TextBlock(
        citations=None, 
        text='你好，**美羊羊**！很高兴见到你！', 
        type='text'
    )], 
    model='glm-5', 
    role='assistant', 
    stop_reason='end_turn',
    stop_sequence=None, 
    type='message', 
    usage=Usage(
        cache_creation=None, 
        cache_creation_input_tokens=None, 
        cache_read_input_tokens=0, 
        inference_geo=None, 
        input_tokens=9, 
        output_tokens=38, 
        server_tool_use=ServerToolUsage(
            web_fetch_requests=None, 
            web_search_requests=0
        ), 
        service_tier='standard'
    )
)

answer = res.content[0].text = '你好，**美羊羊**！很高兴见到你！'

messages = [
{'content': '我叫美羊羊', 'role': 'user'},
{'content': '你好，**美羊羊**！很高兴见到你！', 'role': 'assistant'}
]

'''