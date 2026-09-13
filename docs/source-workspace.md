# 配套源码与多仓工作目录

Status: current, 2026-09-13

VAWS 保留可直接查看、搜索和编辑的 `vllm/` 与 `vllm-ascend/`，用精确源码锁定
表达版本组合，用普通独立 Git 仓库承载修改。源码准备、默认来源展开及执行快照
由已有入口完成；Agent 不填写组合清单、逐仓来源 map 或额外收尾记录。
本页是设计合同；配置与自动测试不能代替实际客户端、远端环境或 NPU 验收。

## 何时准备

普通 VAWS PR review 使用原生 Git 和文件工具，不拉取或复制两个业务仓库。
已有本地源码直接使用；用户指定的现有容器、代码和启动脚本直接交给 remote-dev，
不参与本地源码选择。知识仅按需参考，不是源码准备或任务完成的条件。

只有明确需要源码、独立编辑目录或受管准备时，准备入口才物化需要的仓库。
已有准备结果直接复用。候选 `sources.lock.json` 不意味着当前目录已经包含源码，
也不意味着每次会话必须准备完整开发环境。

新开发任务默认聚焦已选中的 `vllm-ascend`；没有选中它时使用 workspace 根。
明确选择 vLLM、VAWS 或现有目录时保留该选择，不从任务文字猜仓库，也不为
满足默认值补建源码。结果中的 `workspace` 是工具和配置所在的完整目录，
`cwd` 是默认 shell、文件和 Git 操作目录，`repository` 指明该普通 Git 仓库。
默认任务直接在返回的 `cwd` 使用原生 `git status/diff/add/commit`，无需先查看
父仓再切换子仓。VAWS 脚本和 Skill 仍通过 `workspace` 下的绝对路径访问。
续接保留此前选择；没有聚焦字段的旧任务仍使用原来的 workspace。
没有 task 启动记录的原生任务也使用同一选仓逻辑：明确的已选业务仓 cwd 优先，
完整目录根则保留 preparation 的选择。此路由只读，不重写共享目录的默认值。

## 精确的两个基准

`sources.lock.json` 固定官方仓库及完整 commit SHA。先取得一个 Ascend SHA，再读取
该提交自己的上游声明，得到两个离散选择：

| 选择 | vLLM 来源 | Ascend 来源 |
|---|---|---|
| `development`，默认 | 该 Ascend 提交声明的 verified development commit | 同一个固定 Ascend SHA |
| `release` | 该 Ascend 提交声明的发布 tag，解引用为完整 commit SHA | 同一个固定 Ascend SHA |

`release` 表示发布版 vLLM 基准；它仍可能搭配开发中的 Ascend，不代表完整稳定
发布栈，也不保证两项之间任意版本都兼容。正式发布环境复现使用所选 Ascend
release/tag 自己的历史声明，并保留对应 CANN、torch_npu、设备和构建条件。
标签用于说明，解析后的 SHA 才是执行身份。源码声明与精确环境已通过的实验
是不同证据；不能从可获取性测试推断 NPU 兼容性。

更新在仓库维护端进行：一次解析 Ascend，固定其 SHA 后读取两个明确声明文件，
校验官方 vLLM 对象和 tag，生成一致的源码组合更新。声明缺失、格式变化或 ref
不可取时明确失败，不泛扫 YAML 或从镜像名称猜版本。无变化不产生更新提交。
维护 PR 和已有 CI 承担组合检查；实际兼容结论仍需对应范围的实验依据。

VAWS 工具依赖继续由 `pyproject.toml` 和 `uv.lock` 固定，业务源码由 `sources.lock.json`
固定。只改业务 Python 不重装相同工具环境；只更新工具不重写已有业务分支。
新任务采用已接受的默认组合，恢复和 fork 保留原实际来源、修改及环境。
普通新任务以本地确定提交为准，复用匹配该提交的已接受准备缓存；缺缓存时准备该
提交，不主动检查上游新版本或同步个人 fork；缺失的固定源码对象和依赖按需获取。
结果报告实际版本以及
`upstream_checked: false`。明确需要最新版本时，在新任务入口使用 `--latest`；
已有任务恢复仍保留原选择。维护更新和源码锁更新继续使用各自明确入口。

## 目录与 Git

完整多仓任务使用一个独立目录：

```text
workspace/
  .git/
  sources.lock.json
  vllm/.git/
  vllm-ascend/.git/
  .agents/
  .vaws-local/
```

根仓和业务仓均为独立 local clone，具有独立 refs、index 和 Git 配置。
同卷可使用 `git clone --local` 的对象硬链接；跨卷复制对象。默认不用
`--shared` 或长期 alternates，不让活动源码依赖准备缓存的 Git 注册和 GC。
后续 repack 可能增加磁盘占用，复制时延与磁盘收益需要实际测量。
已验证的 canonical 准备计划复用其固定 revisions；复制步骤按这些精确提交
克隆独立仓库，不重新捕获 staging 目录的可变工作文件。即使准备后的工作文件
发生变化，也不能改变该计划选择的提交。现有编辑目录和 conversation fork
使用完整 capture，保留 HEAD、本地 refs、分支配置、stash 历史、staged、working 和普通 untracked 内容；用户
忽略的私有数据不自动复制。业务仓内部自己的 upstream submodules 仍由该仓库
正常处理。两种路径的实际成本见 [dated 验证](source-workspace-validation-2026-09-13.md)。
新固定版本副本的各仓创建普通可提交任务分支；客户端明确提供的分支保持其名称。
已有目录恢复和 conversation fork 保留实际分支，不重新选择默认分支。
fork 默认继承来源目录 preparation 的选仓。若调用方已有明确的父任务
`context_file`，可向复制入口传 `source_context_file`（CLI 为 `--source-context-file`），
校验它属于该来源目录后继承该任务实际选仓；显式 `--repo` 仍优先。
这只读取父任务选择，不把新任务加入父任务。现有原生回调未提供可靠父关联时，
不从最近任务或 cwd 猜父身份；也不要求 Agent 为普通 fork 补填上下文。

完整任务根不能是包住 ignored 内仓的 linked worktree：父仓可能显示干净，
普通 `git worktree remove` 却删除内仓尚未提交或推送的工作。linked 内仓还会
引入移动后的注册与 prune 问题。单个业务仓可以使用客户端原生 worktree；
多仓目录默认整体独立，且位于客户端临时 worktree 清理范围之外。

父仓忽略业务仓内容，避免误提交上游源码；搜索配置允许源码，并继续尊重各
业务仓自己的 build 等忽略规则。需要跨仓检查时，已有 `workspace_sources.py`
入口提供 `status` 与 `diff`，使用实际准备的仓库而非锁文件的候选 SHA。
它报告每仓的分支、修改和错误；已声明源码缺失或 Git 目录损坏时，不会把父仓
干净报告为全部干净。该入口仅按需运行，没有每次提示、提交或任务结束时的
自动扫描，也不成为 Agent 检查清单。`show` 仍只展示锁文件来源。

原生 Git 保持原有含义；明确操作别的仓库可以使用其绝对 cwd，或分别运行：

```text
git -C vllm status
git -C vllm diff
git -C vllm-ascend status
git -C vllm-ascend diff
```

父仓 status 不能代表内仓是否干净。聚合的 `worktree_clean` 也只表示已检查的
工作文件状态，不能证明所有本地分支、stash 或未推送提交可以删除。准备及客户端配置结果用标准
`editor_workspace` 字段返回 `.vaws-local/vaws.code-workspace`，其中列出已经
选中的实际来源，默认操作仓库列在第一位，集成终端 cwd 指向该仓库；其余仓库
仍可浏览。路径引用随整个目录移动保留。它不拉取或补建源码。
`start` 返回由同一实际选仓生成的任务编辑器文件；多个任务在相同完整目录选择
不同仓库时，其视图独立。任务覆盖不改共享 preparation 或默认编辑器文件；
恢复直接复用该任务记录，不重写其他任务的视图。
多仓 Git UI、搜索发现和分仓 diff 按实际客户端能力接线与验收，不从生成
配置文件或一次 `rg` 测试推断全部客户端自动支持。

## 准备、身份与执行来源

准备先在未发布目录完成所有选定源码、组件环境和客户端配置，成功后才发布
editing workspace。任一仓库失败不得写 ready；恢复需要核实已选目录和实际
源码，不能将半成品当作可复用结果。更新不自动 stash、reset 或 rebase 用户修改。
同一次调用直接使用已验证的准备结果及其环境 receipt，不重复执行完成验证或依赖
选择；持久缓存跨调用复用仍检查实际 Git 状态。根仓准备后，两个独立业务仓可并行
复制。`startup_timings` 返回锁等待、准备、复制与配置耗时，复制结果还返回逐仓
耗时；这些是内部观察事实，不是 Agent 需要填写的操作记录。

复用 `.vaws-local/native-workspace.json` 和 task `start.json` 记录明确的
`project_root`、`native_workspace`、实际 `workspace`、逻辑 `sources` 与
`source_channel`，以及新任务的默认 `repository` / `cwd`。
复制来源只是 provenance，不能把临时 stage 当状态所有者。
独立 clone 通过这份准备事实关联母工程，不靠 common-dir 相同或目录名猜身份。
任务身份仍来自原生 context；准备 receipt 不授权控制其他任务。

准备入口、native setup 和 attachment 使用同一个来源展开函数，自动绑定稳定
逻辑名 `workspace` 及实际选中的业务仓。没有 receipt 不扫描任意 nested `.git`，
也不因为有 lock 就补建仓库。coordinator 继续消费普通多 root map，不硬编码
这两个项目；它在接纳执行时捕获逐仓 dirty 内容并保留固定输入。

来源优先级为本次 run 的显式 `sources`、task 的显式 defaults、attachment 的
自动来源。显式 `sources={}` 保持空 map，启动或恢复不覆盖它。已声明源码丢失
时，自动默认值变为不可用，不能静默退化成无源码执行。修改 attachment cwd
不修改已经接纳的执行输入。

默认不自动删除完整任务目录。明确移动或恢复时同步已有准备引用；Git 仓库
独立不等于绝对路径 receipt 会自行改写。删除入口必须考虑各仓修改与未推送工作，
不能只检查父 status。迁移保留用户分支、index、未跟踪内容和仍被引用的旧对象；
不新增回收、租约或共享对象存储服务。

## 原生客户端边界

显式 native launcher 在所选实际目录启动客户端进程，进程 cwd 是可验收事实。
支持返回工作目录的 Kimi/Claude 创建回调可以交回实际目录；是否被客户端采用
需要实际运行证明。官方 Kimi 的普通调用不要求个人 SessionSetup 扩展。

客户端进程保留从完整 workspace 启动，以继续发现 VAWS 配置和 Skill；已加载
的 hook 返回实际业务操作 `cwd`，不向业务仓复制 VAWS 配置。Codex/Cursor 的
native worktree setup 回调不能替父进程改变 UI 根目录。
结果返回实际 `workspace`、操作 `cwd` 和可打开的 `editor_workspace`，已准备 roots
自动参与 scope 与工具路由。Agent 使用操作目录作为 shell cwd 和文件绝对路径。
`native_workspace` 只是原生入口坐标，
不证明 UI 已切换。应向人展示实际源码目录与分仓 Git 操作入口；没有真实打开、
搜索、diff、恢复和删除验收，不宣称完成原生多仓 UI 支持。

## 与九条原则的关系

| 原则 | 本合同的约束 |
|---|---|
| 完成目标的总成本优先 | 接受普通 clone 的必要存储成本，避免内嵌 worktree 生命周期平台 |
| 工具解决有边界的问题 | 解析精确 ref、复制、验证及捕获归工具；兼容结论归证据与判断 |
| 不增加 Agent 理解负担 | 自动选择和展开 sources，不要求手填 map 或准备清单 |
| 能力边界清晰 | workspace 描述源码关系，coordinator 捕获与执行，remote-dev 操作明确 endpoint |
| Skill 以信息为主 | 普通源码和 Git 工作不用管理 Skill |
| 知识仅作参考 | 未使用时保持惰性，查询与捕获不成为 gate |
| 能力按需参与 | 普通 review、已有目录和直接容器任务不触发两仓准备 |
| 复用有效工作 | 复用锁定对象、环境和已有任务，按变更范围验证 |
| 事实可观察 | 展示实际 SHA、目录、默认来源及失败；区分配置测试与原生/NPU 验收 |

这些是实现和评审约束，不是交给每个业务 Agent 的任务步骤。
