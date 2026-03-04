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
        res = client.chat.completions.create(model=model,messages=messages,max_tokens=8000,)
        answer = res.choices[0].message.content
        messages.append({"role": "assistant", "content": answer})

        # 3
        print(f"Ai: {answer}")


if __name__ == "__main__":
    messages = []
    chat_loop(messages)