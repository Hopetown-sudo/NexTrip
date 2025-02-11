// audio-processor.js
class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
    }

    process(inputs, outputs, parameters) {
        const inputData = inputs[0]; // 获取输入音频数据
        const outputData = outputs[0]; // 获取输出音频数据

        // 将音频数据发送给主线程
        // 发送第一个音频通道的数据
        if (inputData[0]) {
            const loudness = this.calculateLoudness(inputData[0]);
            this.port.postMessage({ loudness });
        }

        // 返回 true 以继续处理
        return true;
    }

    // 计算音频响度（简单示例）
    calculateLoudness(data) {
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
            sum += Math.abs(data[i]);
        }
        return sum / data.length;
    }
}

// 注册 AudioWorkletProcessor
registerProcessor('audio_processor', AudioProcessor);