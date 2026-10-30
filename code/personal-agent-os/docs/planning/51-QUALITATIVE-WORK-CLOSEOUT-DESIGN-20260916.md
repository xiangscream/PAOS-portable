# 51 · 定性 Work 收口（Qualitative Work Closeout）设计与实现说明

日期：2026-09-16 · 执行：OpenCode p-3002-s027 · 基线：PAOS main@7d7b4104

## 目标
把"默认数字评分验收门槛"改为**定性收口**：验收/归档不再依赖 score；新流程不产生评分；
旧评分/评价数据保持只读兼容。

## 本次实现（最小正常路径）
- `attention-dashboard-v1-static/work_contracts.py`
  - `normalize_work_review_payload`：删除 "accept 必须至少提供 score 或 comment" 校验。
    accept 现在允许不带 score/comment（定性结论由 review 责任人给出）；reject 规则不变。
- `attention-dashboard-v1-static/work_workflow.py`
  - `review_work`：accept 归档时**仅在明确提供 score/comment 时**追加 evaluations 记录；
    缺省不创建评价、不写 score。touched_paths 同步只在追加时包含 `/evaluations`。
- `attention-dashboard-v1-static/tests/test_p1_ready_review.py`
  - 新增 `QualitativeWorkCloseoutTests`（3 条）：
    1. 无 score/comment → accept 成功、`status=done`、`evaluations` 为空；
    2. 仅 comment → 追加 1 条评价且 `score=None`；
    3. 旧 `score=8` 评价在定性收口后仍可读、不被改写。

## 兼容性与迁移限制
- `project_schema.py:138-147` 对 evaluations 的校验**保持不变**（score 0–10 或 comment 至少其一）：
  旧数据可读；新流程不再写入 score，因此不再产生新的分数记录。
- 未迁移/未删除任何历史 evaluations；不新增数据对象、不改 mutation 写层
  （仍走 `mutate_v2` + revision/receipt/backup）。
- 旧调用方如果依赖 "accept 必须带 score/comment" 的报错来做校验，行为改为成功；
  这是本任务的预期语义变化，已在聚焦测试中锁定。

## 尚未完成（后续最小项，待 s010 决定是否继续）
- (3) review 投影/UI 文案：把"等待评分"改为"谁在等什么"（需要定位 needs_me/office/room 投影文案）。
- (4) `close_result` 与 Coordinator closeout 的可读、可编辑/append-only 且保留历史。
- (5) Work close / Session close / standby 切换的 Ack 死锁排查与消除。

## 验证（本地，exact 改动）
- focused：`tests/test_p1_ready_review.py` → **6 passed**（3 既有 + 3 新增）。
- app 套件：`python -m unittest discover -s tests -p "test_*.py"` → **599 ran / 1 error / 1 skipped**；
  唯一 error 为既有 `test_s6_release_check` 依赖 `git ls-files`（无 git 检出环境），与本次改动无关。
