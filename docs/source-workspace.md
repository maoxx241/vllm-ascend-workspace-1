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
网络不可用时复用可用的已接受本地组合，并报告实际版本。

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
使用完整 capture，保留 HEAD、staged、working 和普通 untracked 内容；用户
忽略的私有数据不自动复制。业务仓内部自己的 upstream submodules 仍由该仓库
正常处理。两种路径的实际成本见 [dated 验证](source-workspace-validation-2026-09-13.md)。

完整任务根不能是包住 ignored 内仓的 linked worktree：父仓可能显示干净，
普通 `git worktree remove` 却删除内仓尚未提交或推送的工作。linked 内仓还会
引入移动后的注册与 prune 问题。单个业务仓可以使用客户端原生 worktree；
多仓目录默认整体独立，且位于客户端临时 worktree 清理范围之外。

父仓忽略业务仓内容，避免误提交上游源码；搜索配置允许源码，并继续尊重各
业务仓自己的 build 等忽略规则。人可以直接打开目录，分别运行：

```text
git -C vllm status
git -C vllm diff
git -C vllm-ascend status
git -C vllm-ascend diff
```

父仓 status 不能代表内仓是否干净。准备及客户端配置结果用标准
`editor_workspace` 字段返回 `.vaws-local/vaws.code-workspace`，其中列出已经
选中的实际来源，供支持该格式的编辑器打开多目录视图。它不拉取或补建源码。
多仓 Git UI、搜索发现和分仓 diff 按实际客户端能力接线与验收，不从生成
配置文件或一次 `rg` 测试推断全部客户端自动支持。

## 准备、身份与执行来源

准备先在未发布目录完成所有选定源码、组件环境和客户端配置，成功后才发布
editing workspace。任一仓库失败不得写 ready；恢复需要核实已选目录和实际
源码，不能将半成品当作可复用结果。更新不自动 stash、reset 或 rebase 用户修改。

复用 `.vaws-local/native-workspace.json` 和 task `start.json` 记录明确的
`project_root`、`native_workspace`、实际 `workspace`、逻辑 `sources` 与
`source_channel`。复制来源只是 provenance，不能把临时 stage 当状态所有者。
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

Codex/Cursor 的 native worktree setup 回调不能替父进程改变 UI 根目录。
此时结果返回实际 `workspace` 和可打开的 `editor_workspace`，已准备 roots
自动参与 scope 与工具路由，Agent
用该目录作为 shell cwd 和文件绝对路径。`native_workspace` 只是原生入口坐标，
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
