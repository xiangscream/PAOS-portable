# V1.2 文档收口与历史 PR 去向

本次从 `main@de27c07cb80c09e6066ae8cd6d9204aca58b7f91` 新建纯文档分支，按 Human 授权选择性导入最终成果。未合并任一旧分支的祖先链，未恢复旧候选代码。

## 五份 PR 的独有内容

| PR / 冻结头 | 独有内容与处置 |
| --- | --- |
| #105 · `681f29250111ecbe73dc5e25cb666f5ecb79476c` | 唯一文件 ROOTER-PHILOSOPHY。安装级身份、Human operational authority、职责分工、Home及配置优先原则保留到现行 [Rooter原则](../ROOTER-PHILOSOPHY.md)。旧claim/tenure及未实施未来机制不带回。 |
| #107 · `d7859ba05f861e7e4cfcf41fb167c892c81430f2` | Build plan、R0合同、R0/R1 handoff、R1直接入住与首责共四文件。R0复用human actor、不造Project Session，及后继取消R2/R3重复入住审批的决定保留到Rooter原则。旧阶段TODO、当时pending_ack和Cycle要求仅留历史。 |
| #108 · `8d7378a06ac0632be5fa7325aab665d87b280597` | 唯一文件为只读证据采集请求，不是未完成实现。其“不靠聊天恢复、减少维护成本”目标已进入主线产品哲学与最终审查；旧“V1.2只是小软升级/不要实施”限制已被后续授权取代。 |
| #109 · `98ab70c36991f8b2425d6d698bdf4b2eb80617e5` | 保留完整Stage2 accepted、关联Library差异/Rooter回读/可见原日志、完整Stage3 FINAL及架构审查包。产品哲学与de27同内容，未以旧分支覆盖；只在main上按Stage2已接受减法修正少量陈旧段落。其余早期调研/自查/候选/日志保留不可变来源，不作为当前指令。 |
| #110 · `61bb543d0d2ccf25aabf94f82473e01d80a86fef` | File-first plan、Pack A kickoff、Stage control、Stage2 lean plan共四文件。保留长期Agent、Working Memory退出、取消owner/instance/enter/Cycle、有界接续、完整业务验收等已接受决定于产品哲学与基线。阶段计划已经由Stage2/Stage3结果履行，不重新发布为待执行计划。 |

## 导入 PR109 的范围

以下路径直接取自冻结头，原件不改写：

- `docs/planning/PAOS-V12-STAGE2-ACCEPTED-20261001/`
- `docs/planning/PAOS-V12-STAGE3-LIVE-CUTOVER-20261001/`
- `docs/planning/PAOS-ARCHITECTURE-REVIEW-20261002/`
- `docs/planning/evidence/PAOS-V12-STAGE2-VISIBLE-LOGS-20261001/`
- `docs/planning/PAOS-V12-STAGE2-ROOTER-INSTALLATION-REVIEW-20261001.md`
- `docs/planning/PAOS-V12-LIBRARY-CANDIDATE.patch`

组件总览是s010在Project Works中的现版本文件快照，单独增加到架构审查目录；不是从记忆重写网页原文。新的基线入口与本页负责解释历史，不修改原始失败日志、验收回执或当时待办。

## 未导入 main 的历史内容仍可追溯

关闭PR不删除其历史分支。以下冻结来源可继续读取，避免把旧指令当成当前合同：

- [#105原始原则](https://github.com/xiangscream/personal-agent-os/tree/681f29250111ecbe73dc5e25cb666f5ecb79476c/docs)
- [#107入住设计与裁决](https://github.com/xiangscream/personal-agent-os/tree/d7859ba05f861e7e4cfcf41fb167c892c81430f2/docs/planning)
- [#108证据请求](https://github.com/xiangscream/personal-agent-os/blob/8d7378a06ac0632be5fa7325aab665d87b280597/docs/planning/PAOS-V1.2-ROOTER-EVIDENCE-REQUEST.md)
- [#109全部历史材料](https://github.com/xiangscream/personal-agent-os/tree/98ab70c36991f8b2425d6d698bdf4b2eb80617e5/docs/planning)，包含早期Human抱怨与可见原始日志，未丢弃。
- [#110最终阶段设计](https://github.com/xiangscream/personal-agent-os/tree/61bb543d0d2ccf25aabf94f82473e01d80a86fef/docs/planning)

文档收口正常合并后，五个PR均标记superseded并关闭，不标为代码已合并。`v1.2-baseline-20261002` 指向新的main文档提交，生产代码内容仍等于de27。以后普通缺陷从该基线单独开PR，不能以“清理”为由重开验收或合并旧候选。

## 现行入口去重

README 与 START-HERE 指向基线导航；Source 中员工指南、Coordinator 运行指南和旧 CLI 合同收缩为共享 Library 导航。Continuity V0、Working Memory V0、v0.5 架构与 v1.0 RC 支持矩阵退出当前规则，旧原文以 de27 不可变链接保留。Coordinator Work done 合同按现有实现修正，不再要求先关闭成员。产品原则、工程准则、业务权限、日常 Workflow 各维护一处。

## 跨库维护落地

Human追加要求：规则文件需要登记，升级要同时退出旧口径。已在共享 `guide-project-work-world` 增加唯一维护流程，`guide-upgrade-adoption` 将其纳入既有收口标准；Workflow/Skill README仅链接，未新增登记系统。Library `ed32316 → b40b6e8` 的[完整文档增量](PAOS-V12-BASELINE-LIBRARY-CALIBRATION.patch)随本次收口保存；重建现有Catalog，未修改Skill使用记录。生产Library尚无Git remote，因此以已提交本地版本和此补丁保持可追溯。2001/3002实际入口引用同一维护规则，不复制正文。
