import os
import requests

# 基本設定
api_url: str = os.getenv("LLM_API_URL", "https://integrate.api.nvidia.com/v1")
api_key: str = os.getenv("LLM_API_KEY", "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")
model: str = os.getenv("LLM_MODEL", "meta/llama-3.3-70b-instruct")

# 對話函式
def chat_with_llm(messages):
    url = f"{api_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 512,
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

# 測試對話
if __name__ == "__main__":
    conversation = [
        {"role": "system", "content": "你是一個中醫師，會根據症狀給予中醫只診斷結果與生活建議。"},
        {"role": "user", "content": "我最近晚上失眠，而且常常多夢，應該怎麼辦？  請參考相似案例:症狀表現：失眠多夢 近5週入睡困難且多夢易醒，醒後難再入睡，白天倦怠乏力，偶有健忘與食慾差。； 脈象：左寸:中/遲 | 左關:無力/軟 | 左尺:無力/浮 | 右寸:中/數 | 右關:無力/遲 | 右尺:有力/數； 輔助條文：高熱、胸悶、血瘀紫斑、如胃痙攣、心悸氣促、急性炎症疼痛、急性胸痛"},
    ]
    reply = chat_with_llm(conversation)
    print("🤖 AI 回覆：", reply)
