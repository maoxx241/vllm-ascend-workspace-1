# 原生客户端与编辑隔离

Status: current, 2026-09-13

官方 Codex、Cursor、Claude Code、Grok 和 Kimi Code 使用项目短指引和各自的
原生身份。完整多仓任务的安全基底是独立 local clones；客户端原生 worktree
可用于单个业务仓。客户端接线不改变原生信任或审批，也不要求个人修改版客户端。
源码选择与目录布局详见[源码合同](source-workspace.md)。

## 按需新建与恢复

普通 PR review、已有本地目录和明确 remote-dev endpoint（含现有容器）使用
原有输入，不拉取或复制两份业务源码，不因缺失 GitHub 身份而初始化，不准备知识。
首次 setup 仅由明确初始化请求或真正需要的受管个人身份触发。

需要独立编辑或受管准备时，复用已有完整准备结果；没有结果才运行一次：

```text
uv run --no-project python .agents/scripts/vaws_start.py --client CLIENT
```

`CLIENT` 为实际客户端。原生 hook 提供的 context 不在 shell 环境中时，传已有
`--context-file PATH`。准备内部选择精确主仓与组件版本、实际需要的源码，
完成目录和环境后返回 `workspace`、`environment`、`sources` 及 `context_file`。
Agent 不先探测身份、手填 source map 或重复运行全部客户端 setup。

根仓和业务仓都采用独立 local clone，目录放在客户端临时 worktree 清理范围外。
同卷可复用对象硬链接，不使用 `--shared` 或长期 alternates。只有部分仓库准备
成功不能写 ready。fork 保留实际代码与 staged/working/untracked 修改，不追新的
lock；恢复保持原 task、源码和固定环境，不 fetch、安装或切换业务分支。

人可以直接打开实际目录，分别使用 `git -C vllm` 和 `git -C vllm-ascend` 查看修改。
父仓忽略业务仓并不代表内仓干净；多仓搜索、Git UI 和 diff 的可见性分别验收。
默认不自动删除整个任务目录。原生父 worktree 的 remove 能删除被忽略的内仓，
所以不能把这种结构作为完整多仓任务默认，也不能只凭父 status 决定清理。

## 原生 cwd 与 UI

原生入口坐标 `native_workspace`、实际编辑目录 `workspace` 和 task identity 是
不同事实。已有 preparation receipt 明确关联工程、入口和选中的源码；独立 clone
不靠 common-dir 或最近目录猜所属 task。reference receipt 不证明 UI 已切换。

| 客户端或入口 | 路径与 context 能力 | 验收边界 |
|---|---|---|
| 显式 native launcher | 在实际 workspace 启动新的原生进程，传递已有 context | 记录真实进程 cwd；不能据此推断客户端内 `/new` 或 resume 行为 |
| Codex | AGENTS 指引、真实 thread metadata、固定 hooks；native worktree setup 可返回外部 workspace 并接通 scope | setup 子进程不能改父 UI 根目录，不宣称原生多仓 UI 自动切换 |
| Cursor | AGENTS/项目规则、sessionStart/preToolUse context；worktree setup 可返回实际 workspace | 回调不能改父 UI 根目录，workspaceFolder 和源码展示需真实验收 |
| Claude Code | CLAUDE.md 引入项目指引；SessionStart/PreToolUse；支持目录返回的创建回调可交回实际 workspace | 记录客户端是否采用所返回目录，以及恢复、搜索、diff、删除行为 |
| Grok | 项目指引、原生 session identity 和工具 context；单仓原生 worktree 可用 | 显式 launcher 的 cwd 与客户端内部新会话行为分别验证 |
| Kimi Code | 官方 prompt hook 提供 context，Bash 可指定 cwd、文件工具可用绝对路径；可用目录返回回调可交回实际 workspace | 普通官方客户端不要求个人 SessionSetup 扩展；回调采用情况不能由配置测试推断 |

当 UI 仍在原生入口时，工具结果展示实际 workspace。Agent 对 shell 设置该 cwd，
对文件、搜索和 patch 使用该目录内绝对路径；向人提供实际源码目录和分仓 Git
入口。一次子进程 `cd` 不会改变父客户端或全部原生工具的默认根目录。未实际
验证打开、搜索、diff、恢复和删除，不宣称完成该客户端的原生多仓体验。

`vaws_client_setup.py --client all --apply` 一次配置已安装客户端并保留用户自定义
providers、hooks 和条件。结果保存在工程的 client-initialization 记录；它不是
每个任务的检查清单。配置写入、原生信任与真实客户端验收分开记录。

## 来源与稳定工具路由

workspace 的准备入口、native setup 和 attachment 通过同一个 helper 自动展开
已选 sources：稳定逻辑名 `workspace` 加实际业务仓。没有准备 receipt 不读取候选
lock 或扫描任意 nested `.git`。coordinator 接收普通多 root map，接纳执行时捕获
逐仓实际修改，保留固定输入；它不硬编码消费者的项目目录关系。

优先级为本次 run 显式 sources、task 显式 defaults、attachment 自动来源。
显式 `sources={}` 保持空 map。启动、恢复、subagent 或 cwd 变化不会覆盖 task
的显式选择，也不会改变已接纳的执行。已声明 child 不可用时保留来源失败，
不退化成空自动默认。

MCP gateway 根据现有 native context 或明确 `context_file` 选择该 task 的固定
组件环境。新的 catalog 不替换旧 task 的后端。普通 remote-dev/knowledge 调用
无 context 时使用其配置入口已保存环境，不读取 task registry、不做 Git 发现、
不启动完整准备；有 context 时复用该任务选择。官方 Kimi task 工具携带已有
context_file，companion 工具可选携带它。目录和最近聊天都不是身份依据。

普通 PreToolUse 在 scope、registry 或 forwarding 前返回。实际需要 context 的
工具才执行原有路由；sources 只在 attach 或 native cwd 真正变化时绑定，不在
每次工具调用重新捕获。原生 session/end/subagent 生命周期保持原有 ownership。
实际后端解释器、环境与 stderr 保留在已有本地证据路径。

## 知识、平台与证据

关联工程共享知识配置、项目 Markdown 与模型/index 缓存，task 仍保留自己固定
的包版本。知识内容仅作参考，查询和捕获按需进行，不要求第二份总结、轮询或
完成任务前查库。未使用的连接不启动后端或维护；有效 query/成功 capture 才
按需激活。explain 直接读 Markdown，自动总结复用已有最终文本。

活动且后端可用时，持久 3600 秒审计期限用于发现向量丢失；未使用、停止或后端
不可用时不承诺一小时修复，下一次实际使用继续到期工作。细节见
[知识合同](target-state.md#54-knowledge)。

Windows/WSL 延续现有进程和共享目录 owner 边界，见[平台合同](platform-contract.md)。
同卷硬链接 fixture 不等于跨卷性能，也不等于 Linux/macOS 或原生客户端验收。
[2026-09-12 原生验收](native-client-validation-2026-09-12.md)和
[统一启动验收](unified-session-validation-2026-09-13.md)是各自日期与实现范围的
证据；不能转用为本次独立多仓布局已在所有客户端通过的声明。
