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
from whisper_streaming_web.src.whisper_streaming.whisper_online import backend_factory, online_factory, add_shared_args


##### LOAD ARGS #####
parser = argparse.ArgumentParser(description="Whisper FastAPI Online Server")
parser.add_argument(
    "--host",
    type=str,
    default="localhost",
    help="The host address to bind the server to.",
)
parser.add_argument(
    "--port", type=int, default=8000, help="The port number to bind the server to."
)
parser.add_argument(
    "--warmup-file",
    type=str,
    dest="https://github.com/ggerganov/whisper.cpp/raw/master/samples/jfk.wav",
    help="The path to a speech audio wav file to warm up Whisper so that the very first chunk processing is fast. It can be e.g. https://github.com/ggerganov/whisper.cpp/raw/master/samples/jfk.wav .",
)

parser.add_argument(
    "--diarization",
    type=bool,
    default=False,
    help="Whether to enable speaker diarization.",
)


add_shared_args(parser)
args = parser.parse_args()

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLES_PER_SEC = SAMPLE_RATE * int(args.min_chunk_size)
BYTES_PER_SAMPLE = 2  # s16le = 2 bytes per sample
BYTES_PER_SEC = SAMPLES_PER_SEC * BYTES_PER_SAMPLE

#if args.diarization:
    #from whisper_streaming_web.src.diarization.diarization_online import DiartDiarization


##### LOAD APP #####
@asynccontextmanager
async def lifespan(app: FastAPI):
    global asr, tokenizer
    asr, tokenizer = backend_factory(args)
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
    
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
            print("ffmpeg stderr:", line.decode("utf-8").strip())
            
    asyncio.create_task(read_stderr())
    return process

@app.websocket("/asr")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection opened.")

    ffmpeg_process = await start_ffmpeg_decoder()
    pcm_buffer = bytearray()
    print("Loading online.")
    online = online_factory(args, asr, tokenizer)
    print("Online loaded.")

    #if args.diarization:
       #diarization = DiartDiarization(SAMPLE_RATE)

    # Continuously read decoded PCM from ffmpeg stdout in a background task
    async def ffmpeg_stdout_reader():
        nonlocal pcm_buffer
        loop = asyncio.get_event_loop()
        full_transcription = ""
        beg = time()
        user_finish_query = False
        
        while True:
            try:
                elapsed_time = math.floor((time() - beg) * 10) / 10 # Round to 0.1 sec
                ffmpeg_buffer_from_duration = max(int(32000 * elapsed_time), 4096)
                beg = time()
                chunk = await loop.run_in_executor(
                    None, ffmpeg_process.stdout.read, ffmpeg_buffer_from_duration
                )
                if not chunk:
                    print("FFmpeg stdout closed.")
                    break

                pcm_buffer.extend(chunk)
                if len(pcm_buffer) >= BYTES_PER_SEC:
                    # 将 int16 数据转换为 float32 数据
                    pcm_array = np.frombuffer(pcm_buffer, dtype=np.int16).astype(np.float32) / 32768.0
                    pcm_buffer = bytearray()
                    
                    # 计算音频的均方根 (RMS) 作为音量指标
                    rms = np.sqrt(np.mean(np.square(pcm_array)))
                    MIN_LOUDNESS_THRESHOLD = 0.008  # 音量阈值
                    
                    if rms > MIN_LOUDNESS_THRESHOLD:
                        online.insert_audio_chunk(pcm_array)
                        transcription = online.process_iter()
                        full_transcription += transcription.text
                        if transcription.text != '':
                            print("query:" + transcription.text)
                        buffer = online.get_buffer()
                        user_finish_query = True
                    
                        if buffer in full_transcription:  # With VAC，buffer 更新可能延迟
                            buffer = ""
                    else:
                        #如果用户完成指令，并且内容不为空
                        if user_finish_query and full_transcription != '':
                            response = test_openai(full_transcription)
                            print("response:" + response)
                            user_finish_query = False
                            full_transcription = ''

            except Exception as e:
                print(f"Exception in ffmpeg_stdout_reader: {e}")
                break

        print("Exiting ffmpeg_stdout_reader...")

    stdout_reader_task = asyncio.create_task(ffmpeg_stdout_reader())

    try:
        while True:
            # Receive incoming WebM audio chunks from the client
            message = await websocket.receive_bytes()
            # Pass them to ffmpeg via stdin
            ffmpeg_process.stdin.write(message)
            ffmpeg_process.stdin.flush()

    except WebSocketDisconnect:
        print("WebSocket connection closed.")
    except Exception as e:
        print(f"Error in websocket loop: {e}")
    finally:
        # Clean up ffmpeg and the reader task
        try:
            ffmpeg_process.stdin.close()
        except:
            pass
        stdout_reader_task.cancel()

        try:
            ffmpeg_process.stdout.close()
        except:
            pass

        ffmpeg_process.wait()
        del online
        
        #if args.diarization:
            # Stop Diart
            #diarization.close()


@app.post("/plan_trip")
async def plan_trip(trip_data: TripData, preferences: UserPreferences):
    """
    Plan the trip by generating a route and refueling plan.
    """
    try:
        route_data = get_route(trip_data.origin, trip_data.destination)

        if not preferences.car_make or not preferences.car_model:
            raise HTTPException(status_code=400, detail="Car make and model are required.")
        
        car_specs = infer_car_specs_from_ai(preferences.car_make, preferences.car_model, preferences.year)

        refuel_points = [{"lat": step['end_location']['lat'], "lng": step['end_location']['lng']} for step in route_data['legs'][0]['steps'][:2]]
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

    uvicorn.run(
        "main:app", host=args.host, port=args.port, reload=True,
        log_level="info"
    )

#python main.py --port 8000
