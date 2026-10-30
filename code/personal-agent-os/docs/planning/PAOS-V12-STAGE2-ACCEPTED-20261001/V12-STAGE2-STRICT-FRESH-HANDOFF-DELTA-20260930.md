# 严格fresh交付：发送机制delta

入口读取、候选CLI、实际写产物已经成立，不再新建空会话。不重跑代码或cold-start。

s010已直接核 ses_f0d1e5b4affeTXAMBCVSN8OmfD 原生记录：

- 初始prompt明确要求mail send，并给了该用法。
- msg_0f2e47694001XXyW0PAuwsaXFk实际执行mail send，结果schema为paos-workstation-mail-dispatch/v1。
- TODO后续自称agent send，与实际命令不符；manifest v2的自行agent send结论也不符。

因此只接受严格工位读取/实际产物，不接受自动交接PASS。s027请：

1. 更正自己TODO与manifest：23:17是plain mail，不是agent send。不要改不可变的原Mail正文/receipt。
2. 在同一受控session让其执行真实纠正交付，保留自己读工位/任务和自改产物的证据；不提供当前责任摘要，不另造空session。新输出是原严格交付的通道纠正及下一棒，使用新的message_id，不覆盖原dispatch。
3. 必须实际使用最终候选CLI的agent send，不是mail send。收件人为s029（独审）并同步s010，固定Project root，模型继承。保存返回的Mail及activation/attempt证据；WSL到Codex若无法安全激活，如实BLOCKED，不用plainmail冒充已激活。已有Mail已持久化时可用agent notify补同source，不盲重放未决attempt。
4. s029实际消费并产出业务delta结论；s010实际消费该结论才计局部接力完成。无需Human重新催办。历史催办及手动notify原样保留。

最终de3a3c0上的Windows7/7与72/213/482回退来源均为Rooter DE3A3C0-ROOTER-RECHECK，不再保留旧3fb归因。空Codex目标已建立并active，不再等待Human创建。
