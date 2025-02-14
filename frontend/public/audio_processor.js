class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
    }

    process(inputs, outputs, parameters) {
        const inputData = inputs[0]; // 获取输入音频数据

        if (inputData.length > 0 && inputData[0]) {
            const audioChunk = new Float32Array(inputData[0]); // 复制音频数据
            const loudness = this.calculateLoudness(audioChunk);

            // 发送音频数据和响度信息到主线程
            this.port.postMessage({ audioChunk: audioChunk.buffer, loudness }); // 转换为 ArrayBuffer
        }

        return true;
    }

    // 计算音频响度
    calculateLoudness(data) {
        if (!data || data.length === 0) return 0;
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
            sum += Math.abs(data[i]);
        }
        return sum / data.length;
    }
}

// 注册 AudioWorkletProcessor
registerProcessor('audio_processor', AudioProcessor);