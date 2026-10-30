# 独立复核 — PR #116 补窄审 `e8fa6b1..384f8d0`（Windows 宿主合同测试修正）— s029

- Reviewer：`3002-s029`。Work：`3002-w060`（沿用）。
- 依 Rooter `rooter-v12-stage3-pr116-windows-rework-20261002`（Windows 实跑 23/2 失败，输出已存档）。
- 对象：新 head `384f8d0f7154bd52aee7a1fba57886b089830c28`（**测试文件单文件修正；产品代码零改动**）。

## 1. 两项 Windows 失败的修正逐一判定

| Rooter 失败项 | 修正内容（实读） | 判定 |
|---|---|---|
| 失败1：test_windows_absolute… 无条件要求 `/mnt/c/...` | 改为宿主合同分支：`os.name == "nt"` → `C:` 开头本机绝对；POSIX/WSL → `/mnt/c/...`；`Path(resolved).is_absolute()` 全局断言 + fingerprint 段保证同一实际目录语义 | ✅ 两侧真实期望 |
| 失败2：test_posix… 硬编码正斜杠片段比较 | 改为 **Path 等值**（`Path(resolved) == Path(tmp)/"native"/"3002"/"3002-s027"/<fingerprint>`）——分隔符无关 | ✅ |
| 顺带：cwd 清点「不做 IO 不能证明无新写」 | `test_no_bogus_relative_dirs…` 增强：断言 resolved **绝对路径** + 含 `/.paos/wakeup-native/opencode` 精确前缀（POSIX 侧）+ cwd 清点无 `C…` 假目录——按必要范围，不扩全套 | ✅（最小范围） |

- 未跳过任何测试（Rooter 明令）；未动产品逻辑（`opencode.py` 零 diff——`git diff e8fa6b1..384f8d0 --stat` 仅 tests 文件）；未把 e8 的 WSL PASS 冒充 Windows PASS。

## 2. 本地复跑（WSL/P_PLATFORM 侧）

- `384f8d0` clone：`test_wake_opencode_b2b2.py` **23 passed + 2 subtests**（WindowsStateRoot 3/3）；`test_contact_surface_s2.py` 21/21 无回归；`git diff --check` clean。
- Windows 侧复跑与两环境实路径核由 Rooter 执行（其 Mail 明示），本报告不代宣称。

## 3. 结论

**总判：PR #116 新 head `384f8d0` 补窄审 — PASS（测试宿主合同修正成立，产品代码未被触碰）。** 交 Rooter 核 Windows/两环境实路径后采用；本地/WSL 侧 PASS 为本报告实跑，e8fa6b1 的 WSL PASS 仍按原文保留不转化。

---
审查人：3002-s029。证据：384f8d0 读回、diff 单文件实核、23+2/21 复跑、diff --check。未改 Source/生产/模型。
