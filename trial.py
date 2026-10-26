import os
import requests
key=os.environ["DEEPSEEK_API_KEY"]
resp = requests.post(
    "https://api.deepseek.com/chat/completions",
    headers={"Authorization":f"Bearer {key}"},
    json={
        "model":"deepseek-chat",
        "messages":[{"role":"user","content":"用一句话夸我坚持运动"}],
    },
    timeout=30
)
print(resp.status_code)
print(resp.json()["choices"][0]["message"]["content"])
print(resp.json()["usage"])