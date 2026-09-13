# 个人 Fork 与源码更新

Status: current, 2026-09-13

首次进入 fresh clone 时，Agent 提供一次初始化选择并复用对话中的确认结果；
后续普通 Review、已有源码和直接 endpoint/container 工作不重复初始化或
完整源码准备。配套版本与目录生命周期遵循[源码合同](source-workspace.md)
和[九条设计原则](design-principles.md)。

## 首次配置与个人 Fork

首次进入 fresh clone、明确初始化或报告未完成 setup 时，读取根 `AGENTS.md` 指向的
[一次性初始化参考](../.agents/bootstrap/repo-init/SKILL.md)。它不进入自动 Skill
发现，也不因已初始化仓库的新会话、普通更新或知识 pending 而重新触发。
`vaws_init.py` 一次记录 Fork、Star 和[社区协作](community-collaboration.md)选择，
分阶段完成主仓 Fork、锁定依赖、客户端与贡献机制；失败后从未完成步骤继续。
源码在首个实际任务按需准备。写配置不等于获得原生信任或通过实际验收。

GitHub 用户名使用用户已明确确认的个人账号；`gh` 登录只是候选，不能代替选择。
确认结果保存于未跟踪的 `.vaws-local/github.json`，不含凭据。coordinator 在需要时
使用它作用户归属，显式 remote-dev endpoint 不要求该身份。既有确认重复使用，
缺失或损坏的配置按具体故障修复，不把整个仓库重新当作第一次使用。

```text
uv run --no-project python .agents/scripts/vaws_init.py status --detect-auth
uv run --no-project python .agents/scripts/vaws_init.py apply --github-user USER --fork yes --star no --community disabled
```

定向维护继续使用 `workspace_forks.py`，默认返回计划；`--repo workspace` 只配置主仓。
工具核对个人 User、实际仓库名
和 canonical fork network，拒绝组织 Fork、其他所有者的 redirect 和无关同名仓库。
`origin` 指向个人 Fork，`upstream` 保留官方来源；GitHub 分配不同 Fork 名时保留
实际地址。业务仓是普通独立 Git 仓库，其来源由 `sources.lock.json` 记录。

重复配置复用正确 remotes，保留额外 remote、脏内容和 Git HEAD。复杂 fetch/push
差异明确报告；组件只在需要贡献时 fork。公开知识贡献由 knowledge package
按既有配置管理，代码 Fork 不会启用知识发布。这些入口不拦截任意终端 Git 命令。

## 独立编辑与版本选择

| 场景 | 行为 |
|---|---|
| 已有完整准备结果 | 复用实际 workspace、已选 sources 和环境 |
| 需要独立编辑或受管准备，尚未准备 | 运行一次 `vaws_start.py --client CLIENT` |
| 普通 Review、原目录工作、直接 endpoint/container | 使用原生工具或 remote-dev，不准备两个业务仓或知识库 |
| 恢复或同一任务再次请求准备 | 沿用已保存选择，不 fetch、安装或新建目录 |
| 比较不同组合或明确 fork | 新独立目录保留所选来源，不切换正在编辑的业务分支 |

准备入口在客户端临时 worktree 清理范围之外创建独立多仓目录。根仓与选中的
业务仓均采用独立 local clone；同卷可复用对象硬链接，不使用长期 alternates。
先完成源码、环境及配置，再发布 ready。失败保留阶段与证据，不将半成品作为
下一次复用结果；不自动 stash、reset、rebase 或强推用户分支。

普通新任务以本地确定 VAWS 提交为准，先采用与它匹配的已接受准备缓存；
上游发现、GitHub 身份复核和 fork 更新不在普通新任务前台执行。明确请求最新时，
使用新任务入口的 `--latest`，或者执行下述维护更新入口。组件由选定提交的
`pyproject.toml`、`uv.lock` 和 monitor pin 固定，业务源码由 `sources.lock.json` 固定。
`development` 默认使用同一 Ascend SHA 声明的 verified vLLM commit；`release`
使用它声明的 vLLM 发布 tag 所对应的完整 SHA。后者不是完整稳定 Ascend 发布栈。
用户指定正式 release、PR 或 commit 时保留该选择及其兼容依据。

已有实际源码按任务需要复用；lock 是候选组合，不是强制物化两个仓库的任务 gate。
fork 复制实际 HEAD、本地 refs、分支配置、stash 历史、index、工作内容和普通 untracked，不跟随新的默认 lock。
只改业务源码不重装相同工具环境，只改工具不重写业务代码。网络不可用时使用
可用的已接受本地组合并报告实际 SHA；本地对象或必要依赖缺失且无法准备时明确返回失败。

主仓维护工作流统一解析和检查上游配套关系，生成源码锁更新 PR。Ascend main
只解析一次，其声明读取固定在同一 SHA；发布 tag 解析为 commit。缺失声明和
格式变化不猜测，也不从镜像名称解析 ref。兼容结论依赖相应实验；可获取性与
源码配套检查不能代替 NPU 验收。候选更新失败留在维护流程中，不成为业务 Agent
每日 setup 步骤。准备缓存目录中的 releases 名称不要求发布 GitHub Release。

## 原生目录、来源与环境

`workspace` 是实际编辑目录。启动入口与 native attachment 自动展开稳定逻辑名
`workspace` 及选中的业务源码，不让 Agent 手写 map；显式 task/run `sources={}`
始终优先。执行接纳时由 coordinator 捕获逐仓实际修改，父仓 status 不能替代它。
源码丢失不得降级为空默认。完整规则见[源码合同](source-workspace.md)。

原生入口和独立 clone 通过既有 preparation receipt 的 `project_root`、
`native_workspace`、`workspace` 与 `sources` 关联；复制 stage 不是状态所有者，
common-dir 不是独立 clone 家族的证明。task 身份仍来自明确的 native context。
稳定 MCP gateway 复用该任务的固定环境，恢复时不跳到较新的 catalog。

显式 native launcher 在实际 workspace 启动客户端进程。Kimi/Claude 支持的目录
返回回调可交回这个路径；采用结果仍需实际验收。Codex/Cursor native worktree
setup 回调不能改变父客户端 UI 根目录，只能返回实际 workspace 并接通自动 scope。
人可以打开该目录查看源码，Agent 使用其 cwd 和绝对路径；不得把 reference receipt
当作 UI 已切换。客户端具体能力见[编辑隔离合同](native-workspace-isolation.md)。

## 显式维护与证据

同一明确关联的工程共享知识配置、项目 Markdown、候选内容及包维护的模型/index
缓存；共享参考内容与 task 固定源码是不同对象。未使用的知识连接不启动后端
或维护；有效 query 或成功 capture 才按需激活，自动总结只复用已有最终文本。
活动且后端可用时，持久 3600 秒期限驱动向量审计；未使用、停止或不可用的后端
不承诺一小时内修复。pending 不阻止独立工作。见[知识合同](target-state.md#54-knowledge)。

维护由具体请求或故障触发，不要求先运行全量初始化。

| 需要处理的问题 | 入口 |
|---|---|
| 依赖或 pin 状态 | `uv run --no-project python .agents/scripts/vaws_deps.py doctor` |
| 准备当前锁定依赖 | `uv run --no-project python .agents/scripts/vaws_deps.py sync` |
| 某客户端接线修复 | `uv run --no-project python .agents/scripts/vaws_client_setup.py --client CLIENT --apply` |
| 身份或 Fork remote 故障 | 恢复既有快照，或用已确认用户名运行 workspace_forks.py 查看计划 |
| 明确的知识配置或维护 | `uv run --no-project python .agents/scripts/knowledge_setup.py` |

```text
uv run --no-project python .agents/scripts/workspace_update.py check
uv run --no-project python .agents/scripts/workspace_update.py prepare
uv run --no-project python .agents/scripts/workspace_update.py apply
```

这些是主动维护入口，普通任务无需运行。已有编辑目录不因准备新的候选而重写。
更新状态和失败命令保存在未跟踪的 `.vaws-local/updates/`；它们记录事实，不承担
task 或设备所有权。不存在每工具上游检查、常驻源码 watcher 或工作中换版本。
默认不自动删除完整任务目录，不为对象复用增设租约或回收服务。

Windows/WSL 的进程和共享目录 owner 边界见[平台合同](platform-contract.md)。
客户端信任、实际目录展示及生命周期验收单独记录；历史 worktree 实验不能作为
新多仓布局已在全部客户端完成验收的证明。
