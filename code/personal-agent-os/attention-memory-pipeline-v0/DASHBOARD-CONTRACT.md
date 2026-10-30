# Dashboard 数据契约

`attention-state/v0` 是记忆层的通用对象；`attention-dashboard-data/v0` 是界面层适配结果。

适配层只做：

- snake_case 到 Dashboard camelCase 字段映射；
- 当前唯一问题、阶段交付物和完成定义的原样传递；
- 来源引用保留；
- 默认任务排序；
- 审核候选标题生成；
- 归档卡字段映射。

适配层不做：

- 不修改来源 Markdown；
- 不审核候选；
- 不把 Tip 转成任务；
- 不跨项目合并对象；
- 不调用模型；
- 不保存手动排序。

手动排序仍属于本机用户状态，应保存在浏览器或未来的个人操作记忆中，不能反向覆盖来源项目事实。

输出文件：

`build/dashboard-data.json`

闭环字段缺失时，适配层输出空字符串；浏览器显示“待补充”并把该卡标为未闭环，不把推断写回来源。

默认前三条应为：

1. `task-sensor-sync`
2. `task-lrc101-report`
3. `commitment-thursday-product-learning`

三条完成后，长期项目补位：

1. `task-obs-agent-recovery`
2. `task-memory-markdown-baseline`

