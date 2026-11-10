/**
 * 录音工具：直接采集 PCM 并产出 8kHz 单声道 WAV。
 *
 * 为什么不用 MediaRecorder：
 * MediaRecorder 产出 webm/opus，需要先 decodeAudioData 解码再重采样。在部分浏览器里
 * （尤其「停止」时 onstop 不触发、靠定时器强制收尾的情况）拿到的 webm 是不完整的，
 * 解码后只剩接近 0 秒的空音频，上传后语音服务会返回「没有有效语音片段」。
 * 直接采集 PCM 没有这个问题：停止时同步取出已采集的样本，时长与音量都可当场校验。
 */

/** 采集到的音频：WAV blob + 时长 + 峰值（用于判断是否真的录到声音） */
export interface RecordedAudio {
  blob: Blob
  duration: number
  peak: number
}

export class PcmRecorder {
  private ctx: AudioContext | null = null
  private stream: MediaStream | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private node: ScriptProcessorNode | null = null
  private sink: GainNode | null = null
  private chunks: Float32Array[] = []
  private frames = 0
  private inputRate = 48000

  async start(): Promise<void> {
    const AC: typeof AudioContext = (window as any).AudioContext || (window as any).webkitAudioContext
    if (!AC) throw new Error('当前浏览器不支持录音（AudioContext 不可用）')

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
    })
    const ctx = new AC()
    this.ctx = ctx
    this.inputRate = ctx.sampleRate
    // 部分浏览器创建后处于 suspended，必须显式恢复，否则收不到任何音频
    if (ctx.state === 'suspended') { try { await ctx.resume() } catch { /* ignore */ } }

    this.source = ctx.createMediaStreamSource(this.stream)
    // ScriptProcessor 已废弃但兼容性最好，这里用它做最稳的 PCM 采集
    const node = ctx.createScriptProcessor(4096, 1, 1)
    this.node = node
    node.channelCount = 1
    node.channelCountMode = 'explicit'
    node.channelInterpretation = 'speakers'
    this.chunks = []
    this.frames = 0
    node.onaudioprocess = (e: AudioProcessingEvent) => {
      const buf = e.inputBuffer.getChannelData(0)
      const copy = new Float32Array(buf.length)
      copy.set(buf)
      this.chunks.push(copy)
      this.frames += copy.length
    }
    // 必须接到 destination 才会被驱动；用一个静音增益节点避免回放/回声
    const sink = ctx.createGain()
    sink.gain.value = 0
    this.sink = sink
    this.source.connect(node)
    node.connect(sink)
    sink.connect(ctx.destination)
  }

  /** 已录制时长（秒） */
  get duration(): number {
    return this.inputRate ? this.frames / this.inputRate : 0
  }

  /** 停止采集并产出 8kHz 单声道 WAV */
  stop(targetRate = 8000): RecordedAudio {
    try { this.node && (this.node.onaudioprocess = null) } catch { /* ignore */ }
    try { this.source?.disconnect() } catch { /* ignore */ }
    try { this.node?.disconnect() } catch { /* ignore */ }
    try { this.sink?.disconnect() } catch { /* ignore */ }
    try { this.stream?.getTracks().forEach((t) => t.stop()) } catch { /* ignore */ }
    try { this.ctx?.close() } catch { /* ignore */ }

    const merged = this.merge()
    const peak = peakOf(merged)
    const down = downsample(merged, this.inputRate, targetRate)
    const duration = targetRate ? down.length / targetRate : 0
    return { blob: encodeWav(down, targetRate), duration, peak }
  }

  private merge(): Float32Array {
    if (this.chunks.length === 1) return this.chunks[0]
    const all = new Float32Array(this.frames)
    let offset = 0
    for (const c of this.chunks) {
      all.set(c, offset)
      offset += c.length
    }
    return all
  }
}

function peakOf(samples: Float32Array): number {
  let peak = 0
  for (let i = 0; i < samples.length; i++) {
    const v = Math.abs(samples[i])
    if (v > peak) peak = v
  }
  return peak
}

/** 线性插值重采样（44.1k/48k → 8k），带简单低通（邻域均值）抑制混叠 */
function downsample(input: Float32Array, from: number, to: number): Float32Array {
  if (!from || from === to) return input
  const ratio = from / to
  const outLen = Math.max(0, Math.floor(input.length / ratio))
  const out = new Float32Array(outLen)
  for (let i = 0; i < outLen; i++) {
    const center = i * ratio
    let sum = 0
    let count = 0
    const lo = Math.max(0, Math.floor(center - ratio / 2))
    const hi = Math.min(input.length - 1, Math.ceil(center + ratio / 2))
    for (let j = lo; j <= hi; j++) { sum += input[j]; count++ }
    out[i] = count ? sum / count : input[Math.min(input.length - 1, Math.round(center))]
  }
  return out
}

function writeString(view: DataView, offset: number, s: string) {
  for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i))
}

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const bytesPerSample = 2
  const dataSize = samples.length * bytesPerSample
  const ab = new ArrayBuffer(44 + dataSize)
  const view = new DataView(ab)
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)                 // fmt 块长度
  view.setUint16(20, 1, true)                  // PCM
  view.setUint16(22, 1, true)                  // 单声道
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * bytesPerSample, true) // 每秒字节数
  view.setUint16(32, bytesPerSample, true)
  view.setUint16(34, 16, true)                 // 16bit
  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)
  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }
  return new Blob([ab], { type: 'audio/wav' })
}
