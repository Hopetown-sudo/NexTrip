import openai
import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 全局会话记录，初始化时包含系统角色信息
conversation_history = [
    {"role": "system", "content": "You are a smart navigation assistant designed for driver. Please provide concise answers and avoid long explanations. Focus only on the key points without going into unnecessary details."}
]

def test_openai_text(query):
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


def test_openai_audio(query):
    global conversation_history
    
    # 添加用户新输入的消息到会话记录中
    conversation_history.append({"role": "user", "content": query})
    
    client = OpenAI()
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini-audio-preview",
            modalities=["text", "audio"],
            audio={"voice": "alloy", "format": "wav"},
            messages=conversation_history
        )
    
        reply = completion.choices[0].message.audio.transcript
    
        # 将助手的回复加入全局会话记录
        conversation_history.append({"role": "assistant", "content": reply})

        wav_bytes = base64.b64decode(completion.choices[0].message.audio.data)
        #with open("./Audio_cache/cache.wav", "wb") as f:
            #f.write(wav_bytes)
            
        return reply, wav_bytes
    
    except openai.AuthenticationError:
        print("Authentication failed. Check your API key.")
    except openai.OpenAIError as e:
        print("An error occurred:", str(e))