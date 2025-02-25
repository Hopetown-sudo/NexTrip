"use client";
import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { AuroraText } from "../components/aurora-text";
import { Textarea } from "../components/ui/textarea";
import { InteractiveHoverButton } from "../components/magicui/interactive-hover-button";
import "./main_page.css";

export default function AudioReactiveBall() {
    const [scale, setScale] = useState(1);
    const maxScale = 1.2;
    const websocketRef = useRef(null); // 使用 useRef 来存储 websocket

    useEffect(() => {
        // 建立 WebSocket 连接
        const ws = new WebSocket('ws://localhost:8000/asr');

        ws.onopen = () => {
            console.log('WebSocket connected');
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
        };

        websocketRef.current = ws; // 存储 WebSocket 到 useRef

        // 获取音频输入
        navigator.mediaDevices.getUserMedia({ audio: true, video: false })
            .then((stream) => {
                // 利用 AudioWorklet 采集音量
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = audioContext.createMediaStreamSource(stream);

                // 加载 AudioWorkletProcessor
                audioContext.audioWorklet.addModule('audio_processor.js').then(() => {
                    const processor = new AudioWorkletNode(audioContext, 'audio_processor');
                    source.connect(processor);
                    processor.connect(audioContext.destination);

                    processor.port.onmessage = (e) => {
                        const loudness = e.data.loudness;
                        const newScale = Math.min(1 + loudness * 3, maxScale);
                        setScale(newScale);
                    };
                })
                .catch(err => console.error("加载 AudioWorklet 失败：", err));

                // 录制为 webm 格式，修改策略：手动控制录制分段
                const options = { mimeType: 'audio/webm;codecs=opus' };
                let mediaRecorder;
                try {
                    mediaRecorder = new MediaRecorder(stream, options);
                } catch (err) {
                    console.error('MediaRecorder 初始化失败:', err);
                    return;
                }

                // 用于存储当前分段的数据
                let chunks = [];

                // 收集录制数据
                mediaRecorder.addEventListener("dataavailable", (event) => {
                    if (event.data && event.data.size > 0) {
                        chunks.push(event.data);
                    }
                });

                // 当分段录音停止时，将当前分段拼接成完整 Blob 并发送给后端
                mediaRecorder.addEventListener("stop", () => {
                    const completeBlob = new Blob(chunks, { type: options.mimeType });
                    console.log("准备发送完整的 webm 语音数据:", completeBlob);
                    if (websocketRef.current?.readyState === WebSocket.OPEN) {
                        websocketRef.current.send(completeBlob);
                        console.log("已发送完整 webm 语音数据到后端");
                    }
                    // 重置数据，并重新启动录制
                    chunks = [];
                    startRecording();
                });

                // 定义每个分段的录制时长（例如1秒为一段）
                const segmentDuration = 1000;

                // 每次启动录制过程，录制 segmentDuration 毫秒后调用 stop()
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

                // 启动第一段录制
                startRecording();
            })
            .catch((err) => {
                console.error('获取音频输入失败:', err);
            });

        // 组件卸载时关闭 WebSocket 连接
        return () => {
            ws.close();
        };

    }, []);

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
                    className="box black-circle sm:w-150 sm:h-150 w-200 h-200"
                />
                <div className="box red-circle sm:w-150 sm:h-150 w-200 h-200"></div>
                <div>
                    <InteractiveHoverButton link="https://www.google.com/maps/dir/Ithaca,+NY/Las+Vegas,+NV/Los+Angeles,+CA/@37.7883828,-107.9600653,3649309m/">
                        View your Trip
                    </InteractiveHoverButton>
                </div>
            </div>
        </>
    );
}






