# PAOS Agent 工作底座

这是 Portable 包的核心代码；使用入口和安装方法见[包 README](../../README.md)。

正常运行链：CLI → 本地 Project 登记 → 固定工位 → TODO / Mail / Notice。
Library 搜索直接读取已登记 Markdown。CAT / 原生 Runtime 是显式外部通道，
不是本地项目读写的前置服务。

```text
python scripts/paos.py --help
python scripts/verify.py
```

`health` 只核安装定位，不宣称模型在线或业务完成。接口以本版本 help 和
[共享接口参考](../../libraries/workflow/Guides/guide-paos-interface-reference.md)为准。

开发边界见 [AGENTS](AGENTS.md)。旧设计书用于查历史，不作为当前运行入口。
