# 02 一次请求怎么走完

以 `POST /api/projects/{id}/sessions`（开一个 Session）为例，走一遍全链路。

## 链路总览

```text
HTTP 请求
  → AttentionDashboardHandler.do_POST          local_server.py:710
  → 遍历 POST_ROUTES 找匹配                     local_server.py:154
  → handler 方法（如 handle_session_open）       local_server.py
  → 解析 JSON body、校验体积
  → WorkflowService.open_session                workflow_service.py（facade）
  → SessionWorkflowMixin.open_session           session_workflow.py:102
  → normalize_open_payload（contracts 归一化）
  → ProjectStore.mutate_v2                      project_store.py:701
  → 落盘 private-data/project-registry/<id>.json
```

读的时候抓住两个分界点：**HTTP 层不写盘**，**store 层不认识 HTTP**。

## 第一站：路由

路由不是 if-else 链，是三张表：`GET_ROUTES`（`local_server.py:125`）、`POST_ROUTES`（154）、`PUT_ROUTES`（201）。每张表是 `(编译好的正则, handler 方法名)` 的元组。

`do_POST`（710 行）做的事就是遍历这张表，命中就调用对应方法。正则的捕获组按位置传给 handler，query 串以关键字参数传入。

这里有个值得注意的设计，注释写在 `local_server.py:120-124`：

> 用 `fullmatch` 整串匹配，且 `[^/]+` 不跨斜杠 —— 所以各条互不重叠，顺序无关。

注释还把退化路径一起写了：改成 `re.match` 前缀匹配就会引入顺序依赖，那时具体路径必须排在宽松路径前面。也就是说，这张表之所以能随便排，靠的是 `fullmatch` 这个约束。改路由时如果顺手把 `fullmatch` 换成 `match`，表就得重排。

## 第二站：handler

handler 负责的是 HTTP 层面的事：读 body、限制体积（`MAX_REQUEST_BYTES = 16KB`，项目类请求放宽到 `MAX_PROJECT_REQUEST_BYTES = 256KB`，见 `local_server.py:83-84`）、调 facade、把结果序列化回 JSON、出错时映射状态码。

它不做业务判断。"Work Item 处于 done 状态能不能开 Session"这种判断不在这一层。

## 第三站：WorkflowService 是壳，行为在 mixin

`workflow_service.py` 只有 128 行，类定义本身（`36-48` 行）就是把 11 个 mixin 组合起来：

```python
class WorkflowService(
    TypedReferenceHooksMixin,
    WorkWorkflowMixin,
    CoordinatorContinuityGuardMixin,
    AgentContinuityHooksMixin,
    ArtifactRevisionHooksMixin,
    WorkingMemoryHooksMixin,
    AgentContinuityWorkflowMixin,
    SessionWorkflowMixin,
    ReviewerSetupWorkflowMixin,
    CoordinationWorkflowMixin,
    DecisionWorkflowMixin,
):
```

它自己只保留投影类方法（`mailbox`、`needs_me`、`relations`、`portfolio` 等）和一个 `_compile_context_pack`。

**所以找一个业务行为的落点，要去对应的 mixin 文件**，不是在 `workflow_service.py` 里翻。

## 第四站：mixin 里的标准写法

`SessionWorkflowMixin.open_session`（`session_workflow.py:102`）是 pattern 的样板，几乎所有写操作都长这样：

1. `normalize_open_payload(payload, project_id)` —— contracts 层做归一化与校验，产出干净的 `request`。
2. 前置校验（Identity 是否存在等）。
3. 定义闭包 `apply_open(state, store)` —— **真正改状态的地方**，接收当前项目 state 和 store。
4. 在闭包里做业务判断：Work Item 处于 `review`/`done`/`cancelled` 就抛 `ValidationError`；`request_ids` 引用不存在的 Request 也抛；处理 `continues_session_id` 的接班逻辑。
5. 把闭包连同 `operation_id`、`request_hash`、`touched_paths` 等一起交给 `mutate_v2`。

关键在第 3 步和第 5 步的分离：**业务判断写成一个函数传进去，由 store 在锁内调用**。这样"校验"和"实际写入"之间不会插进别人的写操作。

## 第五站：mutate_v2 落盘

见 [03-store-mutation.md](03-store-mutation.md)。

## 两处边界

**静态文件走另一条路。** 请求不匹配任何路由时，`do_GET` 交给父类 `SimpleHTTPRequestHandler` 当静态文件伺服。放行范围由 `ALLOWED_STATIC_PREFIXES`（`local_server.py:87-91`）决定，只有三个前缀。注释明确了这是**白名单、唯一防线**，新增静态目录要显式加，不能从黑名单里减。

**错误统一映射。** `errors.py` 提供 `error_contract`，把 store/workflow 抛的语义化异常（`NotFoundError`、`ConflictError`、`RevisionConflictError`、`ValidationError`）映射成 HTTP 状态码。异常类型不降级——`project_store.py:813-818` 明确写了：`ProjectStoreError` 子类保持原类型与 HTTP 状态，不降级为 422。
