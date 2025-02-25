"use client"; 
import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { AuroraText } from "../components/aurora-text";
import { InteractiveHoverButton } from "../components/magicui/interactive-hover-button";
import "./main_page.css";

export default function AudioReactiveBall() {
    const [scale, setScale] = useState(1);
    const [isRecording, setIsRecording] = useState(false); // Track whether the recording has started
    const [isAudioStarted, setIsAudioStarted] = useState(false); // Track if audio processing has started
    const maxScale = 1.2;
    const websocketRef = useRef(null); // 使用 useRef 来存储 websocket
    const recorderRef = useRef(null); // 用于存储当前的 MediaRecorder 实例
    const audioRef = useRef(new Audio()); // 用来存储音频对象

    useEffect(() => {
        const ws = new WebSocket('wss://096f-24-213-201-196.ngrok-free.app/asr');

        ws.onopen = () => {
            console.log('WebSocket connected');
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
        };

        websocketRef.current = ws; // 存储 WebSocket 到 useRef

        const SILENT_THRESHOLD = 0.012;
        const STOP_THRESHOLD = 0.03;

        let currentLoudness = 0;
  
        const audio = audioRef.current;
        let audioUrl = '';

        ws.onmessage = (event) => {
            const audioBlob = new Blob([event.data], { type: 'audio/wav' });
            audioUrl = URL.createObjectURL(audioBlob);   

            if (audio.paused) {
                audio.src = audioUrl;  
                audio.play()
                    .then(() => {
                        console.log('音频开始播放');
                    })
                    .catch((error) => {
                        console.error('音频播放失败:', error);
                    });

                audio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                    console.log("音频播放完毕，已释放资源");
                };
            }
        };

        navigator.mediaDevices.getUserMedia({ audio: true, video: false })
            .then((stream) => {
                if (!isAudioStarted) return; // If audio hasn't started, do nothing

                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = audioContext.createMediaStreamSource(stream);

                audioContext.audioWorklet.addModule('audio_processor.js').then(() => {
                    const processor = new AudioWorkletNode(audioContext, 'audio_processor');
                    source.connect(processor);
                    processor.connect(audioContext.destination);

                    processor.port.onmessage = (e) => {
                        const loudness = e.data.loudness;
                        currentLoudness = loudness;
                        const newScale = Math.min(1 + loudness * 3, maxScale);
                        setScale(newScale);

                        if (currentLoudness > STOP_THRESHOLD && !audio.paused) {
                            audio.pause();
                            audio.currentTime = 0;
                            console.log("响度超过阈值，停止当前音频并重置");
                        }
                    };
                })
                .catch(err => console.error("加载 AudioWorklet 失败：", err));

                //const options = { mimeType: 'audio/mp4' };

                if (MediaRecorder.isTypeSupported("video/webm;codecs=vp9")) {
                    //var options = { mimeType: "audio/webm; codecs=opus" };
                    var options = { mimeType: "video/webm;codecs=vp9" };
                    //var options = { mimeType: "video/mp4", videoBitsPerSecond: 1000000 };
                } else if (MediaRecorder.isTypeSupported("video/mp4")) {
                    var options = { mimeType: "video/webm;codecs=vp9" };
                } else {
                    console.warn("当前浏览器不支持 WebM 或 MP4 录制");
                    var options = {};
                }

                let mediaRecorder;

                try {
                    mediaRecorder = new MediaRecorder(stream, options);
                    recorderRef.current = mediaRecorder; 
                } catch (err) {
                    console.error('MediaRecorder 初始化失败:', err);
                    return;
                }

                let chunks = [];

                mediaRecorder.addEventListener("dataavailable", (event) => {
                    if (event.data && event.data.size > 0) {
                        chunks.push(event.data);
                    }
                });

                const segmentDuration = 250;

                mediaRecorder.addEventListener("stop", () => {
                    if (currentLoudness < SILENT_THRESHOLD) {
                        console.log("当前声音过低，不发送数据");
                        chunks = [];
                        startRecording();
                    } else {
                        const completeBlob = new Blob(chunks, { type: options.mimeType });
                        console.log("准备发送完整的 webm 语音数据:", completeBlob);
                        if (websocketRef.current?.readyState === WebSocket.OPEN) {
                            websocketRef.current.send(completeBlob);
                            console.log("已发送完整 webm 语音数据到后端");
                        }
                        chunks = [];
                        startRecording();
                    }
                });

                function startRecording() {
                    try {
                        mediaRecorder.start();
                        console.log("开始录制新片段");
                        setTimeout(() => {
                            mediaRecorder.stop();
                        }, segmentDuration);
                    } catch (err) {
                        console.error("录制出错:", err);
                    }
                }

                if (isRecording) {
                    startRecording();
                }
            })
            .catch((err) => {
                console.error('获取音频输入失败:', err);
            });

        return () => {
            ws.close();
        };

    }, [isRecording, isAudioStarted]); // Add isAudioStarted to the dependency array

    const handleCircleClick = () => {
        setIsRecording(true); // 开始录音
        console.log('开始接收用户语音');
        
        // 设置音频处理已开始
        setIsAudioStarted(true); 

        // 触发音频播放的“假”交互
        const audio = audioRef.current;
        audio.play()
            .then(() => {
                console.log('初次播放音频以满足浏览器交互要求');
            })
            .catch((error) => {
                console.error('初次播放音频失败:', error);
            });

        // 点击时缩小圆圈的效果
        setScale(1.5); // 圆圈缩小

        // 通过 setTimeout 恢复圆圈大小
        setTimeout(() => {
            setScale(1); // 恢复圆圈原始大小
        }, 200); // 设置圆圈缩小的持续时间
    };

    return (
        <>
            <div>
                <h1 className="text-center text-3xl pt-2 pb-2 font-bold tracking-normal sm:text-4xl md:text-5xl lg:text-6xl">
                    <AuroraText>Nex</AuroraText>trip
                </h1>
            </div>
            <div className="flex flex-col items-center justify-center min-h-screen pb-12 pt-32 px-4">
                <motion.div
                    animate={{ scale }}
                    transition={{ duration: 0.1 }}
                    className="box red-circle sm:w-150 sm:h-150 w-200 h-200"
                />
                <div className="box black-circle sm:w-150 sm:h-150 w-200 h-200" onClick={handleCircleClick} style={{ cursor: 'pointer' }}></div>
                <div>
                    <InteractiveHoverButton link="https://www.google.com/maps/dir/Ithaca,+NY/Las+Vegas,+NV/Los+Angeles,+CA/@37.7883828,-107.9600653,3649309m/">
                        View your Trip
                    </InteractiveHoverButton>
                </div>
            </div>
        </>
    );
}









