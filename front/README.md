# Portable 画板

画板沿用 WorkBuddy/S040 的拖动节点与侧栏原型，连接当前 Portable 文件底座。
仅使用 Python 标准库、HTML 和原生 JavaScript，无前端构建或额外安装步骤。

## 打开

先按包根 README 完成 `portable.py init`、项目登记和真实 Home 准备，然后运行：

```text
python portable.py serve
```

浏览器访问 `http://127.0.0.1:8780/`。需要其他端口或显式安装描述时：

```text
python portable.py serve --port 8781 --installation-file <本机安装描述的绝对路径>
```

默认配置是此 checkout 的 `config/local/installation.json`，不读取旧原型的盘符，
也不依赖当前 shell 工作目录或 WorkBuddy 自带 Python。解释器使用启动画板的 Python。
机器没有迁入项目时会显示空安装说明，不从相邻目录猜工位。

## 看什么、做什么

- 下拉菜单只列当前安装登记的项目，成员和 Coordinator 来自同一登记原件。
- 节点可拖动；节点与详情读取实际 TODO v4，显示下一步、任务统计和原文。
- Notice 统计使用现有合并读面，含 `.handled` 处理事实，不按登记文件数量推算。
- 右键选择共享方法，可向该 Agent 持久留信；此动作不自动请求原生提醒。
- 项目页读取已有 `INDEX.md`，不维护第二份项目进度或 Workbench 状态。
- 前端没有工位写者、任务引擎或后台消费者；动作通过已安装 CLI 执行。

## 可选 CAT

```text
python portable.py serve --cat-url http://127.0.0.1:8870
```

这只连接已有 CAT，不安装或启动它。未配置或连接失败会直接显示原因，文件功能继续工作。
Ctrl 多选两个或更多工位后，点击“围绕主题沟通”建立圆桌；消息使用原 CAT 的成员、
保存和单次提醒路径。发言者为页面使用者 `human`，不冒充某个 Agent。

消息保存、提醒受理与实际消费分别成立。超时保持结果未知，不自动重新提交。
连线是画板布局，业务事实在 CAT；页面刷新后仍可从房间列表进入原讨论。
画板监听仅为 `127.0.0.1`，退出该进程即可关闭，不注册任何开机任务。

## 换电脑

重新取得本仓库，在新机生成安装定位，登记选定的项目和 Home，按新机实际环境配置可选 CAT。
画板使用同一命令启动。原生会话、登录、接收器和 STOP 继续按迁移边界单独处理；
能看到节点不代表员工在线或已收到提醒。
