import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

# 全局会话记录，初始化时包含系统角色信息
conversation_history = [
    {"role": "system", "content": "You are a smart navigation assistant designed for driver. Please provide concise answers and avoid long explanations. Focus only on the key points without going into unnecessary details."}
]

def test_openai(query):
    global conversation_history

    # 添加用户新输入的消息到会话记录中
    conversation_history.append({"role": "user", "content": query})

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history
        )

        # 取出助手回复消息
        reply = response.choices[0].message.content.strip()

        # 将助手的回复加入全局会话记录
        conversation_history.append({"role": "assistant", "content": reply})

        return reply

    except openai.AuthenticationError:
        print("Authentication failed. Check your API key.")
    except openai.OpenAIError as e:
        print("An error occurred:", str(e))
