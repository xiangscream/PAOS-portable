---
schema: paos-skill/v1
id: ffmpeg-video-clip
title: Ffmpeg Video Clip
status: active
version: 1
name: ffmpeg-video-clip
description: This skill should be used when the user asks to extract, cut, trim, or clip a segment from a video (for example "把 11-15s 提取出来"), to transcode or convert media between formats/codecs, to pull still frames or a contact sheet out of a video for inspection, to locate scene changes or keyframes, or to answer a question about what happens at a given time in a video. Covers precise re-encode cuts, fast stream-copy cuts, transcoding, hardware acceleration, frame extraction, contact-sheet generation, and sequence timing on this machine.
agent_created: true
metadata:
  tags: "ffmpeg, video, clip, trim, frames, contact sheet"
  category: "media"
---

# ffmpeg 视频切片与抽帧

## ffmpeg 在哪

**系统版 9.0.2**，2026-09-22 用 `winget install Gyan.FFmpeg` 装的，比隔离 venv 里那份新两个大版本：

```bash
FF=ffmpeg          # 直接在 PATH 上
```

装在 `C:\Users\remo\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin`，已写进用户 PATH。**ffprobe 和 ffplay 也一起有了**——查媒体信息优先用 ffprobe，比解析 `ffmpeg -i` 的 stderr 干净。

⚠️ **PATH 是 2026-09-22 才加的，在那之前启动的进程读不到它。** 如果 `command -v ffmpeg` 没结果，说明当前进程继承的是旧环境——重启该进程，或临时用全路径：

```bash
FF="C:/Users/remo/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffmpeg.exe"
```

**兜底**：隔离 venv 里还留着一份 imageio-ffmpeg 的 **7.1**，只带 ffmpeg 不带 ffprobe，且 `-vsync`、全 GPU 链行为和 9.0 不同（见下方各自标注）：

```
C:\Users\remo\.workbuddy\binaries\python\envs\default\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe
```

## 先决定产出形状

**要让 agent「看」视频内容，就不要给 mp4，给拼图。** mp4 对模型来说是无意义的二进制，抽帧成一张 PNG 才有信息量，而且体积小一个量级（实测：4 秒竖屏片段 3.7 MB vs 拼图 1.4 MB；1080p 5 秒片段 4.9 MB vs 拼图 274 KB）。

| 目的 | 产出 |
|---|---|
| agent 判读内容 / 回答「这段里发生了什么」 | 拼图 PNG |
| 看某一瞬间的细节 | 单帧 PNG |
| 交付给人 / 进剪辑软件 | mp4 片段 |
| 要文字 | 音频流单独抽出后转写 |

## 命令

```bash
# 媒体信息（9.0 起有 ffprobe，优先用它，输出干净可解析）
ffprobe -v error -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_name,width,height,r_frame_rate -of default=noprint_wrappers=1 in.mp4
# 没有 ffprobe 时退回读 stderr（Stream 行里没有 audio 就是无音轨）
"$FF" -hide_banner -i in.mp4 2>&1 | grep -E "Duration|Stream"

# 关键帧位置
"$FF" -hide_banner -loglevel info -i in.mp4 -vf "select='eq(pict_type,I)',showinfo" -an -f null - 2>&1 | grep -o "pts_time:[0-9.]*"

# 画面切换点（找「哪里发生了变化」的候选时间戳）
"$FF" -hide_banner -loglevel info -i in.mp4 -vf "select='gt(scene,0.3)',showinfo" -an -f null - 2>&1 | grep -o "pts_time:[0-9.]*"

# 拼图：从 11s 起 4 秒，2fps 共 8 帧排成 4x2（agent 首选）
"$FF" -y -hide_banner -loglevel error -ss 11 -i in.mp4 -t 4 -vf "fps=2,scale=270:-1,tile=4x2" sheet.png

# 单帧（要小数时刻）
"$FF" -y -hide_banner -loglevel error -ss 11.4 -i in.mp4 -frames:v 1 frame.png

# 按绝对帧号抽帧（比 -ss 精确，无取整歧义）
"$FF" -y -hide_banner -loglevel error -i in.mp4 -vf "select='eq(n,330)'" -fps_mode passthrough -frames:v 1 f330.png
```

⚠️ **`-vsync` 在 9.0 里被移除了**（7.1 还有）。替代是 `-fps_mode`：`-vsync 0` → `-fps_mode passthrough`，`-vsync cfr` → `-fps_mode cfr`。写 `-vsync` 会直接 `Unrecognized option` 报错退出。**`-fps_mode` 在 7.1 和 9.0 上都可用**（实测过），所以统一写 `-fps_mode` 就不用管版本。

### 切片：两种做法，先选一个

```bash
# A. 精确（重编码）。起点帧精确，帧数/时长可控
"$FF" -y -hide_banner -loglevel error -ss 11 -i in.mp4 -t 4 \
  -c:v libx264 -crf 18 -preset veryfast -pix_fmt yuv420p -movflags +faststart out.mp4
# 有音轨时再加 -c:a aac

# B. 快（秒切，不重编码）。起点同样精确对齐目标时间，代价在别处（见下）
"$FF" -y -hide_banner -loglevel error -ss 21 -i in.mp4 -t 7 \
  -c copy -movflags +faststart out.mp4
```

**`-ss` 放在 `-i` 之前**是快进 seek（秒级完成）；放在后面是逐帧解码（慢）。上面两条都是前者。

## 精度 vs 速度（实测，不是估的）

1080p30、20 秒、19 MB、关键帧间隔 8.33 秒的测试片，取 8s 起的 5 秒：

| 做法 | 起点 | 帧数 | 时长 | 体积 | 耗时 |
|---|---|---|---|---|---|
| A 重编码 | **精确 8.000s** | 150 | 5.00s | 4.88 MB | 1.49s |
| B 秒切 | **精确 8.000s** | 152 | 5.10s | 12.3 MB | **0.157s** |

真实竖屏片段（1080×1920、29.97fps、43.51s）实测：

| 做法 | 起点 | 时长 | 体积 | 耗时 |
|---|---|---|---|---|
| A 重编码（11s 起 4s） | 精确 11.000s | 4.00s / 120 帧 | 3.75 MB | 约 1.5s |
| B 秒切（10.5s 起） | 精确 10.500s | 4.95s | 4.78 MB | **0.125s** |
| B 秒切（21s 起 7s） | 精确 21.000s | 7.10s | 3.97 MB | **0.134s** |
| B 秒切（29s 起 4s） | 精确 29.000s | 4.07s | 3.48 MB | **0.145s** |

**秒切的起点是精确的，对齐到目标时间点。** PSNR 定量核过：秒切切片首帧对源目标时刻的 PSNR 是 `inf`（像素完全相同）；对**关键帧所在时刻**反而很低（10.5s 起的切片首帧 vs 源 10.143s = 13.51，vs 源 10.5s = `inf`；21s 起的切片首帧 vs 源 21.121s = 10.04，vs 源 21.0s = `inf`）。**「秒切会吸附到关键帧、差好几秒」是错的**——ffmpeg 7.x 在 seek 后会丢包对齐到目标时间点，与重编码的起点一致。

**秒切真正的代价是另外三条**：切片开头可能没有关键帧（第 0 帧不可靠）、体积反而更大、时长会略长于 `-t`。

**约定：用户对精度要求不高时，一律用 B（秒切）换 10 倍速度。**「不要求精确」指的是**不必为边界多几帧或整数秒对齐去重编码**，不是指允许起点漂移——秒切本身起点就是准的。

## 需要转码时的编解码选择（本机实测）

9.0.2 编入 **249 编码器 / 562 解码器**；7.1 是 230 / 533。**列表里有不等于能用**——硬件那几个要看机器。

本机只有 **AMD AMF** 一条路能走（显卡是 AMD；机器 PATH 里那条 NVIDIA 项只是 PhysX，不是卡）：

| 路径 | 结果 |
|---|---|
| 编码 `h264_amf` / `hevc_amf` / `av1_amf` | 可用 |
| 编码 `*_nvenc` | 失败 `Cannot load nvcuda.dll`（无 N 卡） |
| 编码 `*_qsv` | 失败 `Error creating a MFX session`（无 Intel 适配器） |
| 编码 `*_vaapi` | 失败（Linux 专用） |
| 解码 `d3d11va` / `dxva2` | 可用 |
| 解码 `qsv` / `cuda` | 不可用 |

判可用性的方法：**真跑一遍再看输出字节数**。失败时 ffmpeg 仍会留下一个 0 字节文件，不能拿「文件存在」当成功判据。

43.51s / 1080×1920 / 29.97fps / 源 1304 帧，整片转码实测：

| 做法 | 9.0.2 | 7.1 | 体积 | 帧数 |
|---|---|---|---|---|
| 软编 `libx264 -crf 18 -preset veryfast` | 16.92s | 13.32s | 46.92 MB | 1304 ✓ |
| 纯 AMF 编码 | 7.98s | 5.48s | 31.16 MB | 1304 ✓ |
| `-hwaccel d3d11va` 解码 + AMF 编码 | 5.74s | 4.57s | 31.16 MB | 1304 ✓ |
| 再加 `-hwaccel_output_format d3d11` 全 GPU 链 | 3.85s | 1.28s | 31.16 MB | 1304 ✓ / 7.1 上 **149** ❌ |

耗时随机器负载波动，别当基准用；**帧数和体积才是判据**。

**推荐配方**：

```bash
"$FF" -y -hide_banner -loglevel error -hwaccel d3d11va -i in.mp4 \
  -c:v h264_amf -quality balanced -b:v 6M out.mp4
```

### ⚠️ `-hwaccel_output_format d3d11` 的行为随版本变了

- **7.1：静默丢帧。** 只编码 149/1304 帧——不报错、文件能播、内容残缺。当时是真坑。
- **9.0.2：正常。** 1304 帧全在，输出与另外三条路径**完全等价**：全片 PSNR 都是 41.351735（同一值），第 0 / 600 / 1300 帧单帧 PSNR 43–44 dB。

所以这条在 9.0 上可以用，但**仍要核对帧数**——它坏过，而且坏的方式不报错：

```bash
"$FF" -hide_banner -i out.mp4 -f null - 2>&1 | tail -1   # 取 frame= 那个数
```
注意这里**不用** `-c copy`——见坑 2。

## 先判断：真的需要重编码吗

有些素材**本来就是通用格式**，转码纯属浪费。先查，别习惯性按模板转。

全部满足就可以直接 `-c copy`：

- 视频是 H.264/H.265 + `yuv420p`（8-bit 4:2:0）
- 容器是 mp4
- 没有 `rotation` 标记（或播放器能正确处理）
- 音轨是 AAC/MP3 这类常规格式，或者干脆没音轨
- 没有多余的 `data` 轨

实测对比（5 分 06 秒、2560×1096、VFR 手机录屏，同一段）：

| 做法 | 耗时 | 体积 | 时间戳 | 画质 |
|---|---|---|---|---|
| **`-c copy`** | **1.8s** | 1227.5 MB | 9304 个，零重复 | PSNR `inf`（像素级一致） |
| 重编码 CFR 30 | 232.6s | 383.5 MB | 9180 个，零重复 | 有约 50 ms 提前偏移 |

重编码的唯一收益是体积小三倍。**没有体积压力时就 `-c copy`**——快 130 倍，而且无损。

反例：4:2:2 10-bit + PCM 的相机素材**必须**重编码，否则一堆播放器打不开。

## 动手前先看两件事：像素格式和旋转

### 1. 旋转标记（竖拍素材必查）

相机竖着拿拍出来的文件，编码尺寸常常是**横的**（如 1920×1080），靠 `rotation` 显示矩阵标记告诉播放器转 90°。剪之前必须查：

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
  -show_entries stream_side_data=rotation -of default=noprint_wrappers=1 in.mp4
```

有 `rotation=90` 就说明是竖拍，实际观感是 1080×1920。

**两种做法出来的东西不一样**：

| 做法 | 编码尺寸 | 旋转标记 | 后果 |
|---|---|---|---|
| 重编码 | 1080×1920（**物理转好**） | 无 | 到哪都正着播 |
| `-c copy` | 1920×1080（原样） | 保留 `rotation=90` | 认标记的播放器正着放；**不认的（部分剪辑软件、网页、PPT）横躺** |

重编码会默认自动应用旋转（`-autorotate` 默认开）。**要交给别人/放进文档的，用重编码；只在自己机器上看的，`-c copy` 更保真。**

### 2. 像素格式（专业机素材别瞎 copy）

相机高码率格式常见 **10-bit 4:2:2（`yuv422p10le`）+ PCM 音轨**。这种文件直接 `-c copy` 出来的片段：

- **PCM 音轨**在 MP4 里合法，但网页播放器、微信、PPT 常常不认 → 播放变哑
- **4:2:2 10-bit H.264** 绝大多数硬件解码器不支持 → 直接黑屏
- 还常带一条 `data` 轨（相机元数据），某些播放器会因此拒绝打开

**给通用场景交付，重编码成 `-pix_fmt yuv420p` + AAC**；确实要保真就拿原码流，但同时告诉对方"这是 10-bit 4:2:2 母版，不是通用播放格式"。

```bash
# 通用播放版（竖拍会自动转正）
ffmpeg -y -hide_banner -loglevel error -ss 0 -i in.MP4 -t 15 \
  -map 0:v:0 -map 0:a:0 \
  -c:v libx264 -crf 16 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 256k -movflags +faststart out.mp4

# 保真版（原码流直切）
ffmpeg -y -hide_banner -loglevel error -ss 0 -i in.MP4 -t 15 \
  -map 0:v:0 -map 0:a:0 -c copy -movflags +faststart out_master.mp4
```

`-map 0:v:0 -map 0:a:0` 是为了**丢掉那条 data 轨**，不加会被一起带上。

## 坑

1. **秒切切片开头可能没有关键帧。** 实测某次秒切切片首帧是 `iskey:0 type:P`，重编码的是 `iskey:1 type:I`。所以**不要用秒切切片的第 0 帧**做判据，要抽帧判读就改用重编码或从切片第 1 秒后抽。
2. **帧数有两个地方会骗你。** ① `-c copy -f null -` 的 `frame=` 计数不可信——实测同一条切片这样数出 392 帧，完整解码只有 152 帧。② **`ffprobe` 报的 `nb_frames` 在 `-c copy` 产出的文件上也可能错**——实测报 451，完整解码只有 421。一律用 `"$FF" -i x.mp4 -f null -`（不加 `-c copy`）取末尾那个 `frame=` 为准。
3. **`-t` 在秒切下不严格。** 要 5 秒可能给 5.10s / 152 帧，多出的部分来自关键帧边界。
4. **秒切不省体积。** 它继承原编码在区间的局部码率，实测反而比重编码大 2.5 倍（12.3 MB vs 4.88 MB）。要小体积就得重编码。
5. **竖屏视频的拼图列数要少。** 9:16 的画面用 `tile=4x2` + `scale=270:-1`；用 `tile=5x2` 会让每格太窄。
6. **文件名带空格和括号时**用双引号整条包住路径，`-ss` 等参数照常。
7. **`-vsync` 在 9.0 里已被移除**，写了会 `Unrecognized option` 直接退出。用 `-fps_mode passthrough`（替代 `-vsync 0`）/ `-fps_mode cfr`（替代 `-vsync cfr`）。
8. **转码后一定要数帧**。`-hwaccel_output_format d3d11` 在 7.1 上曾静默把 1304 帧砍成 149 帧，不报错、能播放。9.0 上正常，但这类失败模式不报错，只能靠数帧发现。
9. **`drawtext` 在 9.0.2 这个 build 上不加 `fontfile=` 会直接段错误。** 先报 `Fontconfig error: Cannot load default config file`，然后 `Segmentation fault`，整个进程被杀。7.1 那份（imageio 内置）不加反而正常——是 build 差异，不是版本。**规避：显式指定字体文件**：
   ```bash
   -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='LABEL':fontsize=24:fontcolor=white:x=10:y=10"
   ```
   注意 Windows 路径里的冒号要写成 `\:`。**`subtitles=`（libass）不受影响**，实测正常。
10. **拼带标签的对比图别用 drawtext 试运气**，直接不带标签拼，标签写在回复里。省得一个段错误把整条命令废掉。
11. **VFR 源 + `-fps_mode passthrough` 会产出重复且乱序的时间戳。** 实测手机录屏（`r_frame_rate=90000/1`，实际约 15.5 fps）这样转出来：9304 个包里有 **3690 个重复时间戳**，PTS 还乱序（0.064496 出现三次、0.193489 排在 0.128993 前面）。文件能播，但播放时长和帧序不可信。**非要重编码 VFR 就用 `-fps_mode cfr -r 30 -video_track_timescale 90000`**——实测 9180 个包、零重复、时长精确 306.000。代价是约 50 ms 提前偏移（VFR 帧往固定格子上靠的必然结果）。**要帧级精度就别重编码，`-c copy`。**
12. **判断 VFR 看 `r_frame_rate` 和 `avg_frame_rate` 的比值**，不是看 `nb_frames`。`r_frame_rate=90000/1` 而 `avg_frame_rate≈15.5` 就是典型的 VFR 录屏。

## 核对切对了没有

不要靠肉眼看。用 PSNR 定量比：把切片首帧和源视频在候选时刻的帧比对，**PSNR 最高那个就是真实起点**（重编码约 40+，秒切可能到 `inf`）。

```bash
"$FF" -y -hide_banner -loglevel error -i out.mp4 -frames:v 1 a.png
"$FF" -y -hide_banner -loglevel error -ss 11 -i in.mp4 -frames:v 1 b.png
"$FF" -hide_banner -i a.png -i b.png -lavfi psnr -f null - 2>&1 | grep -oE "average:[0-9.inf]+"
```

注意：**画面运动剧烈时单帧 PSNR 的区分度会下降**（相邻帧本来就差很多），这时改用「按绝对帧号 `select='eq(n,N)'` 取帧」比对，避免 `-ss` 的取整歧义。

## 多机位对轨（两台机器拍同一件事）

比画质、比对同一时刻的动作之前，必须先把偏移量算出来。**别信文件名里的时间戳**——实测两台设备壁钟能差到 200 秒以上，按 creation_time 对会直接对错。

**能用的一步：逐帧灰度 NCC 的全局偏移扫描。**

```bash
# 1. 两台机器各抽 1fps 小图
"$FF" -y -hide_banner -loglevel error -hwaccel d3d11va -i A.mp4 -map 0:v:0 -vf "fps=1,scale=160:90" fr_a/%04d.png
"$FF" -y -hide_banner -loglevel error -hwaccel d3d11va -i B.mp4 -map 0:v:0 -vf "fps=1,scale=160:90" fr_b/%04d.png
```

然后 numpy 读进来、每帧做 `(x-mean)/std` 归一化，对每个候选偏移 off 算 `median(mean(A[i]*B[i+off], axis=1))`，按重叠帧数筛选，取最大值。要点：

- **用 median 不用 mean**，少数错配帧压不下去。
- **必须限制最小重叠**（建议 ≥25 帧），否则短重叠处会出假峰。
- 得到了粗偏移后，**再抽 10fps 窗口精修到 0.1s**。
- **最后必须分段复算**（把窗口切成三段各自求偏移），三段一致才说明没有时钟漂移。实测某次三段给出 +121.5 / +121.6 / +121.6，可以放心用 +121.6。

**判断真假峰的标准不是分数高低，是拿候选偏移抽两端实际帧看一眼。** 实测有个 +49s 的假峰中位分 0.28 不算低，抽帧一看：一端是院子一端是办公室，根本不是同一场景。得分来自「都是室内」这类场景类型相似。

**别用逐帧最近邻映射的单调率去判断是否同期。** 场景重复度高时它会四散（实测 60%，接近随机），会把你误导到"不是同一次拍摄"的错误结论上。对角滑动窗口均值才是对的判据。

**真峰形状很尖**：实测录屏对轨那条，峰值 0.4973，偏 1 秒就掉到 0.38。宽而平的多半是场景相似。

**音频互相关经常不可用。** 两台机器麦克风位置/降噪/AGC 都不同，实测归一化互相关只有 0.0079，等于零。有视觉就先走视觉。

**交叉验证的好办法**：如果素材里有 App 界面录屏，界面上的录制计时器可以直接读——实测 App 显示 `00:01:39` 对应的就是相机第 100 秒，两个点一对就闭合了。

## 9.0 带来的新能力（7.1 没有）

- **`whisper` 滤镜**——ffmpeg 内直接语音转写（8.0 加入，底层 whisper.cpp）。要单独下模型：`-af "whisper=model=C:/path/ggml-base.bin"`。等于不挂外部 ASR 就能出字幕。
- **`gfxcapture`**——Windows.Graphics.Capture 录屏（8.1），比老的 `gdigrab` 稳。
- **`vsrc_amf`**——AMD 显卡直接采屏（AMF 侧）。
- **`drawvg`**——矢量绘图滤镜（8.1，靠 cairo），可在画面上画示意图。
- **`vpp_amf` / `sr_amf` / `frc_amf`**——AMF 的缩放格式转换 / 超分 / 补帧。
- **ffprobe**——媒体信息结构化输出。
- 编码器里多了 `libsvtav1`、`libvvenc`、`libjxl`、`libsvtjpegxs`、`liboapv`。

**`vqe_amf`（AMF 画质增强）这个 9.0.2 build 里没有**——changelog 里列了，实际不在，别指望它。

**没变的**：`-vsync` 不会回来了，新写的命令一律用 `-fps_mode`。

切片、抽帧、拼图、转码、缩放裁切、拼接合成、烧字幕、抽音轨、混音、HLS 分段、场景检测、PSNR/VMAF 质量比对、波形与示波器图——这些在 9.0.2 上都回归验证跑通过。
