from time import time
import argparse
import math
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from models import TripData, UserPreferences
from route_planning import get_route, modify_route_with_waypoints, find_gas_stations
from ai_agent import infer_car_specs_from_ai
from testopenai import test_openai
import ffmpeg
import numpy as np
from faster_whisper import WhisperModel
from functools import partial

import sys
import os
from pathlib import Path

def set_cuda_paths():
    venv_base = Path(sys.executable).parent.parent
    nvidia_base_path = venv_base / 'Lib' / 'site-packages' / 'nvidia'
    cuda_path = nvidia_base_path / 'cuda_runtime' / 'bin'
    cublas_path = nvidia_base_path / 'cublas' / 'bin'
    cudnn_path = nvidia_base_path / 'cudnn' / 'bin'
    paths_to_add = [str(cuda_path), str(cublas_path), str(cudnn_path)]
    env_vars = ['CUDA_PATH', 'CUDA_PATH_V12_4', 'PATH']
    
    for env_var in env_vars:
        current_value = os.environ.get(env_var, '')
        new_value = os.pathsep.join(paths_to_add + [current_value] if current_value else paths_to_add)
        os.environ[env_var] = new_value

set_cuda_paths()

SAMPLE_RATE = 16000
CHANNELS = 1

# 设置静音检测参数
SILENCE_THRESHOLD = 0.01          # 如果RMS低于此值，认为是静音（归一化后音量值）
SILENCE_DURATION_THRESHOLD = 1.0  # 连续静音超过1秒，则判断用户说完

app = FastAPI()

# 启动FFmpeg解码器
async def start_ffmpeg_decoder():
    process = (
        ffmpeg.input("pipe:0", format="webm")
        .output(
            "pipe:1",
            format="s16le",
            acodec="pcm_s16le",
            ac=CHANNELS,
            ar=str(SAMPLE_RATE),
        )
        .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
    )


    # 异步读取 ffmpeg 的 stderr 输出，以便调试时查看日志
    async def read_stderr():
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, process.stderr.readline)
            if not line:
                break
            #print("ffmpeg stderr:", line.decode("utf-8").strip())
            
    asyncio.create_task(read_stderr())
    return process

@app.websocket("/asr")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 接口：前端发送 WebM 音频数据，
    后端通过 FFmpeg 将其转换为 PCM 数据，
    使用 Faster‑Whisper 模型实时转录，
    并根据静音检测判断用户是否说完指令，再开始转录，
    最后将识别结果打印出来（不发送到前端）。
    """
    await websocket.accept()
    print("WebSocket 连接已建立。")

    # 启动 FFmpeg 解码器，接收 WebM 数据并输出 PCM 数据
    process = await start_ffmpeg_decoder()

    # 初始化 Faster‑Whisper 模型
    model_size = "large-v3"
    model = WhisperModel(model_size, device="cuda", compute_type="int8")

    # 累积的 PCM 数据缓冲区
    buffer = bytearray()

    async def receive_audio():
        """
        持续接收前端发送的 WebM 数据，并写入到 FFmpeg 的标准输入中。
        """
        try:
            while True:
                try:
                    data = await websocket.receive_bytes()
                except WebSocketDisconnect:
                    print("WebSocket 连接断开。")
                    break
                # 将接收的数据写入 FFmpeg 进程的 stdin
                process.stdin.write(data)
                process.stdin.flush()
        except Exception as ex:
            print("接收数据异常：", ex)
        finally:
            if process.stdin:
                process.stdin.close()

    async def process_audio():
        """
        从 FFmpeg 的标准输出中读取解码后的 PCM 数据，
        每读取一小块数据后进行静音检测，
        当检测到连续静音超过设定阈值时，
        将累积的音频（去除尾部静音）作为一段完整语音进行转录，
        并将转录结果打印出来，同时记录详细日志。
        """
        nonlocal buffer
        silence_duration = 0.0  # 累积的静音时长（秒）
        loop = asyncio.get_running_loop()
        try:
            while True:
                # 从 FFmpeg 的输出中读取 1024 字节数据
                chunk = await loop.run_in_executor(None, process.stdout.read, 1024)
                if not chunk:
                    break
                buffer.extend(chunk)
                # 对当前小块数据进行静音检测
                audio_chunk = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                if len(audio_chunk) > 0:
                    rms = np.sqrt(np.mean(np.square(audio_chunk)))
                    # 当前 chunk 占的音频时长（秒）
                    chunk_duration = len(audio_chunk) / SAMPLE_RATE
                    #print(f"[DEBUG] 收到音频块: 长度={len(audio_chunk)} samples, RMS={rms:.4f}, 片段时长={chunk_duration:.2f}s")
                    if rms < SILENCE_THRESHOLD:
                        silence_duration += chunk_duration
                    else:
                        silence_duration = 0.0

                #print(f"[DEBUG] 当前累计静音时长={silence_duration:.2f}s")
                # 如果累计静音超过阈值，则认为用户说完，开始转录
                if silence_duration >= SILENCE_DURATION_THRESHOLD:
                    # 剔除末尾静音部分（对应 silence_duration 的样本数）
                    trailing_samples = int(silence_duration * SAMPLE_RATE)
                    if trailing_samples < len(buffer):
                        speech_data = bytes(buffer[:-trailing_samples])
                    else:
                        speech_data = bytes(buffer)
                    
                    if len(speech_data)> 0:
                        audio_array = np.frombuffer(speech_data, dtype=np.int16).astype(np.float32) / 32768.0
                        total_samples = len(audio_array)
                        avg_rms = np.sqrt(np.mean(np.square(audio_array))) if total_samples > 0 else 0.0
                        #print(f"[INFO] 开始转录: 总采样点数={total_samples}, 累计静音时长={silence_duration:.2f}s, 平均RMS={avg_rms:.4f}")
                        # 使用线程池执行转录，避免阻塞
                        transcribe_func = partial(model.transcribe, audio_array, beam_size=5)
                        segments, info = await loop.run_in_executor(None, transcribe_func)
                        result_text = "".join(segment.text for segment in segments if segment.text)
                        if result_text and "Thank" not in result_text:
                            print("转录结果:", result_text)
                    # 清空缓冲区，重置静音计时
                    buffer = bytearray()
                    silence_duration = 0.0

        except Exception as ex:
            print("处理音频异常：", ex)
        else:
            # 当数据流结束时，处理剩余未检测到连续静音的数据
            if buffer:
                audio_array = np.frombuffer(buffer, dtype=np.int16).astype(np.float32) / 32768.0
                total_samples = len(audio_array)
                avg_rms = np.sqrt(np.mean(np.square(audio_array))) if total_samples > 0 else 0.0
                print(f"[INFO] 流结束转录: 总采样点数={total_samples}, 平均RMS={avg_rms:.4f}")
                transcribe_func = partial(model.transcribe, audio_array, beam_size=5)
                segments, info = await loop.run_in_executor(None, transcribe_func)
                result_text = "".join(segment.text for segment in segments if segment.text)
                if result_text and "Thank" not in result_text:
                    print("转录结果:", result_text)

    # 同时启动接收数据和处理音频数据的任务
    receive_task = asyncio.create_task(receive_audio())
    process_task = asyncio.create_task(process_audio())
    await asyncio.gather(receive_task, process_task)

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
    parser.add_argument("--host", type=str, default="localhost", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    args = parser.parse_args()

    # 可选：执行转录功能测试
    # run_transcription()

    uvicorn.run("Non_streaming_main_local:app", host=args.host, port=args.port, reload=True, log_level="info")
    #python Non_streaming_main_local.py --port 8000
