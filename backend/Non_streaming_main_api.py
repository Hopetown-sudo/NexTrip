from time import time
import argparse
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from models import TripData, UserPreferences
from route_planning import get_route, modify_route_with_waypoints, find_gas_stations
from ai_agent import infer_car_specs_from_ai
from testopenai import test_openai_text, test_openai_audio
import ffmpeg
from functools import partial
from openai import OpenAI
import sys
import os
from pathlib import Path
import openai
import io
import wave
from asyncio import Queue
import noisereduce as nr
import numpy as np
from pydub import AudioSegment
from pydub.playback import play


# 判断是否为 MP4 文件
def is_mp4(buffer: io.BytesIO) -> bool:
    """
    判断是否为 MP4 文件
    """
    buffer.seek(0)
    header = buffer.read(12)
    buffer.seek(0)
    return b'ftyp' in header  # MP4 通常包含 'ftyp' 关键字

# 从 MP4 视频中提取音频并转换为 WAV 格式
def extract_audio_from_mp4(buffer: io.BytesIO) -> io.BytesIO:
    """
    使用 ffmpeg 从 MP4 视频中提取音频并转换为 WAV 格式
    """
    temp_mp4 = "temp_video.mp4"
    temp_wav = "temp_audio.wav"

    # 将 MP4 数据保存到临时文件
    with open(temp_mp4, "wb") as f:
        f.write(buffer.getvalue())

    # 使用 ffmpeg 提取音频，禁用日志输出
    try:
        ffmpeg.input(temp_mp4).output(temp_wav, acodec="pcm_s16le", ac=1, ar=16000).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        print(f"FFmpeg 提取音频失败: {e}")
        return io.BytesIO()

    # 读取转换后的 WAV 文件
    with open(temp_wav, "rb") as f:
        wav_data = f.read()

    # 清理临时文件
    #os.remove(temp_mp4)
    #os.remove(temp_wav)

    return io.BytesIO(wav_data)

VOLUME_THRESHOLD = 1000  # Adjust this value based on your needs

# 音量检测阈值
SILENCE_THRESHOLD = 0.01  # 设置音量阈值，低于这个值认为是静音,值越高，转录灵敏度和频率越高
SILENCE_DURATION = 2  # 设置静音超过2秒则停止转录

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有的来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)

@app.websocket("/asr")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 接口：支持 WebM 音频和 MP4 视频，并使用 Whisper API 进行转录
    """
    print("准备接受 WebSocket 连接...")
    await websocket.accept()
    print("WebSocket 连接已建立。")

    buffer = io.BytesIO()
    client = OpenAI()

    last_received_time = time()
    timeout_flag = False

    async def monitor_timeout():
        """
        监测超时并处理音频/视频
        """
        nonlocal buffer, last_received_time, timeout_flag
        while True:
            await asyncio.sleep(1)
            if time() - last_received_time > 0.7:  
                if buffer.tell() > 0:
                    buffer.seek(0)

                    # **检测 WebM 还是 MP4**
                    if is_mp4(buffer):
                        print("检测到 MP4 视频，提取音频...")
                        buffer = extract_audio_from_mp4(buffer)
                        buffer.name = "audio.wav"
                    else:
                        print("检测到 WebM 音频...")
                        buffer.name = "audio.webm"

                    # **调用 OpenAI Whisper API 进行转录**
                    try:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=buffer,
                            response_format="text",
                            language='en'
                        )

                        if transcription.strip() and transcription.strip().lower() not in ["you", "bye", "Oh", "bye."]:
                            print(f"Query: {transcription}")
                            response, wav_bytes = test_openai_audio(transcription)
                            print("Response: " + response)
                            await websocket.send_bytes(wav_bytes)
                    except Exception as e:
                        print(f"转录过程出错: {str(e)}")

                    buffer.seek(0)
                    buffer.truncate(0)
                    timeout_flag = False  # 重置超时标志

    asyncio.create_task(monitor_timeout())

    try:
        while True:
            try:
                data = await websocket.receive_bytes()
                last_received_time = time()
                timeout_flag = False
                buffer.write(data)
                print(f'当前数据长度: {buffer.tell()}')

            except WebSocketDisconnect:
                print("WebSocket 连接断开。")
                break
            except Exception as e:
                print(f"接收或处理数据时出错: {str(e)}")
                break

    except Exception as ex:
        print(f"websocket_endpoint 异常：{str(ex)}")
    finally:
        buffer.close()


@app.post("/plan_trip")
async def plan_trip(trip_data: TripData, preferences: UserPreferences):
    """
    根据起点和终点规划路径以及加油方案
    """
    try:
        route_data = get_route(trip_data.origin, trip_data.destination)

        if not preferences.car_make or not preferences.car_model:
            raise HTTPException(status_code=400, detail="需要提供车辆品牌和型号。")
        
        car_specs = infer_car_specs_from_ai(preferences.car_make, preferences.car_model, preferences.year)

        refuel_points = [{"lat": step['end_location']['lat'], "lng": step['end_location']['lng']} 
                         for step in route_data['legs'][0]['steps'][:2]]
        waypoints = []
        for point in refuel_points:
            location_str = f"{point['lat']},{point['lng']}"
            gas_stations = find_gas_stations(location_str)
            if gas_stations:
                waypoints.append(gas_stations[0])

        modified_route = modify_route_with_waypoints(trip_data.origin, trip_data.destination, waypoints)

        return {
            "route": modified_route,
            "waypoints": waypoints,
            "car_specs": car_specs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=9000, help="Port number")
    args = parser.parse_args()

    # 可选：执行转录功能测试
    # run_transcription()

    uvicorn.run("Non_streaming_main_api:app", host=args.host, port=args.port, reload=True, log_level="info")
    # python Non_streaming_main_api.py --host 0.0.0.0 --port 9000