"use client";
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { AuroraText } from "../components/aurora-text";
import { Textarea } from "../components/ui/textarea";
import { InteractiveHoverButton } from "../components/magicui/interactive-hover-button";
import "./main_page.css";

export default function AudioReactiveBall() {
    const [scale, setScale] = useState(1);
    const maxScale = 1.2; // 设置小球变大的最大上限

    useEffect(() => {
        navigator.mediaDevices.getUserMedia({ audio: true, video: false })
            .then((stream) => {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();

                // 创建音频源节点
                const source = audioContext.createMediaStreamSource(stream);

                // 创建 AudioWorkletNode
                audioContext.audioWorklet.addModule('audio_processor.js').then(() => {
                    const processor = new AudioWorkletNode(audioContext, 'audio_processor');
                    source.connect(processor);
                    processor.connect(audioContext.destination);

                    // 监听来自 AudioWorkletProcessor 的消息（响度数据）
                    processor.port.onmessage = (e) => {
                        const loudness = e.data.loudness;

                        // 根据响度值调整小球的缩放比例
                        const newScale = Math.min(1 + loudness * 3, maxScale); // 使小球缩放的变化幅度适当
                        setScale(newScale);  // 更新小球的缩放比例
                    };
                });
            })
            .catch((err) => {
                console.error('获取音频输入失败:', err);
            });

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
                    className="box black-circle sm:w-150 sm:h-150 w-200 h-200" // 调整大小，适应小屏幕
                />
                <div className="box red-circle sm:w-150 sm:h-150 w-200 h-200"></div>
                <div>
                    <InteractiveHoverButton link="https://www.google.com/maps/dir/Ithaca,+NY/Las+Vegas,+NV/Los+Angeles,+CA/@37.7883828,-107.9600653,3649309m/">View your Trip</InteractiveHoverButton>
                </div>
            </div>
        </>
    );
}




