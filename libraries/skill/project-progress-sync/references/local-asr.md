# 本地音频转写管线（不联网、不外传）

## 为什么本地

录音是原始事实材料，长期积累经验要能反复回看。**不上传云端、不走飞书妙记等外部服务**——数据留在本机，管线可复现，十年后还能重跑。

## 组件（一次性装好，之后离线）

| 组件 | 版本参考 | 作用 |
|-|-|-|
| `faster-whisper` | 1.2.1 | 本地 Whisper 推理（CTranslate2） |
| `ctranslate2` | 4.8.3 | 推理后端 |
| **`av` (PyAV)** | **必须 < 14**（实测 13.1.0） | 音频解码。av 19 移除了 `metadata_errors` 参数，会导致 `TypeError` |
| `opencc-python-reimplemented` | — | 繁 → 简（whisper 中文常输出繁体） |
| `ffmpeg` | 任意近版 | 切片、重采样、探测时长 |

安装到隔离 venv（不要污染系统 Python）：

```bash
<python> -m pip install faster-whisper "av<14" opencc-python-reimplemented
```

首次下载模型需网络，用国内镜像：`HF_ENDPOINT=https://hf-mirror.com`。模型缓存后**完全离线**。

## 脚本

`tools/transcribe.py`（项目侧）要点：

- **分块**：长音频按 `--chunk-min` 切片转写、拼接绝对时间戳，避免一次性解码占内存。
- **断点续跑**：每块写 `<stem>.partNNN.txt`，中断后 `--resume` 跳过已完成块。
- **繁转简**：逐段 `OpenCC('t2s')`。
- **VAD**：`vad_filter=True`、`min_silence_duration_ms=500`，过滤静音段。
- **提示词**：用领域相关的简体中文 `initial_prompt`（如"机器人、电机、结构、控制、调试"）能明显改善术语识别。

```bash
FFMPEG=<ffmpeg路径> HF_ENDPOINT=https://hf-mirror.com \
  <venv python> transcribe.py <音频> --model medium --chunk-min 30 --resume
```

## 实测数据（CPU，无 GPU）

| 模型 | 加载 | 转写 RTF | 5 小时音频预计耗时 | 备注 |
|-|-|-|-|-|
| `small` | 5 s | ~0.40 | ~2 h | 中文**繁体 + 明显乱码**，不可用于归档 |
| `medium` | 9 s（缓存后） | **0.39** | **~2 h** | 简体通顺，可用；人名与专业术语仍会错 |

结论：**默认用 `medium`**；追求更高质量可换 `large-v3`（预计 RTF ~1.0+，5 小时约 5–6 小时 CPU）。

## 已知问题与对策

| 问题 | 现象 | 对策 |
|-|-|-|
| 繁体输出 | 全篇繁体 | OpenCC `t2s` |
| 人名/型号错 | "浩翔"→"伟秀"之类 | 转写后人工校对；关键条目回听原音 |
| 静音段 0 段 | 某段完全无输出 | 先做能量扫描定位有声区间；空段属正常 |
| VAD 过严 | 整段被判无语音 | 关掉 `vad_filter` 或降阈值再试 |
| 5 小时单文件 | 解码占内存 | 必须分块（`--chunk-min`） |
| 采样率/声道 | 部分录音 16 kHz 单声道 | ffmpeg 统一 `-ac 1 -ar 16000` |

## 质量校验（归档前必做）

1. **抽样复听**：随机取 3–5 处（开头、中段、结尾、含数字与型号处），与原文核对。
2. **关键数字核对**：扭矩、电压、版本号、日期——这些错了会污染后续结论。
3. **说话人归属**：本地 whisper 不做说话人分离；多人录音要靠内容线索归属，不确定的标「待确认」。
4. **隐私**：录音里若混入私人谈话，**不进入工作文档**，也不做摘要外传。
