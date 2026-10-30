# cat-activation-owner-switch.patch — repo-relative, frozen, verified

- **基线 commit**: `5fa04ffe1f5cb061f9c9c07176435d3c9d711bf6`（co-agent-2；worker 需从该 commit 起，生产 dirty 不参与）
- **唯一目标文件**: `co_agent/service.py`（patch 仓库相对；无绝对路径/tmp；server.py/store.py 未动）
- 隔离验证（刚刚实录）:
  1. `git clone` co-agent-2 → checkout 5fa04ffe → clean 已读
  2. `git apply --check cat-activation-owner-switch.patch` — OK（同类）
  3. `git apply` — 单独文件脏数据增加
  4. `pytest tests/test_cat_core.py tests/test_cat_integration.py` — **24 passed**
  5. **owner 切换/恢复公共入口**（真实 Service+Store）: paos → paos（幂等） → cat → cat（幂等）；`activation_owner: "zap"` → ValidationError 拒绝
- **应用入口（Rooter 维护窗口）**: 在 co-agent-2 checkout 5fa04ffe（或如实记录当前 commit）上 `git apply --check` 然后 `git apply`
- **回退**: `git apply -R cat-activation-owner-switch.patch` 恢复 service.py；不产生 Room/Exchange 业务变化
- **不变量**: 保留所有未读/未 ACK Exchange；保留 journal/Marco/ownership 记录；Room 打开状态；历史旧 import 不启用自动激活
- **生产提交与自回滚**: Rooter 需自行从生产 service.py 复制其当前窗口期状态，或直接 `git stash` 未 dirty 文件后再考虑另存分支；s027 自身不做仓库级 reset。

**隔离验证时间**: 2026-10-05（本轮恢复后执行；见 P3-FULL-SEAMS-FROZEN-S027.md）
