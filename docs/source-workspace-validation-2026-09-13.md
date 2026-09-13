# 独立多仓源码工作目录验证

Status: dated validation evidence, 2026-09-13

本报告记录独立源码目录的四机验证、本地复制成本、依赖同步与旧布局迁移。
功能已通过 [PR #166](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/166)
合入 canonical main，合入提交为 `a80923e6325fb53629332b4f5688fe37b28e0f3e`。
当前合同见 [source-workspace.md](source-workspace.md)。以下证据覆盖不同的有界
路径；原生客户端 UI 和完整 NPU 环境的验证边界分别标明。

## 四机固定源码传输

以下为最终已安装包的四机复验，四台机器使用同一份小型源码快照。
coordinator `0.5.0.dev1` 固定为 `9f94f27964437f962e6037529ccf2f0b1c709ede`，
remote-dev 使用已安装的 `0.8.0`，固定为
`a65362882a85b4d460be3e1d15e90de9fb507e70`；consumer 固定为
`4b11ae543ac4b9862fe6be9a4a82d14e55ecd9d8`。四台全部通过，合计 28 项核心
检查通过，使用同一份固定输入，全部自建 fixture 清理完成。

较早的 coordinator `66e2d2b3aa30512eef433e0594ebf815e574b6ce` 四机结果仍
作为历史记录保留；下表与本节结论使用上述最终包复验，不能扩展为未执行的
NPU 工作负载或后续代码版本已通过。

| 机器 | 三仓来源捕获、传输及物化 | 既有容器、源码和脚本保留 | 自建 fixture 清理 |
|---|---|---|---|
| A | 通过 | 通过 | 通过 |
| B | 通过 | 通过 | 通过 |
| C | 通过 | 通过 | 通过 |
| D | 通过 | 通过 | 通过 |

本地 fixture 包含独立的 `workspace`、`vllm` 和 `vllm-ascend` Git 仓库。
父仓忽略两个业务仓；Ascend 子仓存在 tracked 修改时，父仓仍然显示干净。
准备 receipt 将三项逻辑来源交给 native attachment，实际 `capture_sources`
捕获子仓修改。随后再次改动本地子仓，用来确认已经捕获的输入保持固定。

每台机器都复用正在运行的明确容器。先从现有配置取得 SSH endpoint，再核对
mount namespace。实际 `materialize_fixed_sources` 经 SSH/Git 传输小型 Git
对象并物化三仓；返回的 source identity 和 commits 与捕获一致。在 Ascend
源码目录执行小型 Python recipe，读到捕获时的修改及相邻源码，未读到之后的
本地改动。

前后检查确认既有源码 HEAD/status、顶层 shell 脚本哈希，以及容器身份、镜像、
配置、启动时间和重启次数保持不变。另一个受控脚本验证了 sourced 环境、
字面参数、文件哈希及输出；既有用户脚本只做哈希检查，没有执行。清理仅作用于
本次创建、带标记且经过路径与归属检查的临时目录。

这验证了来源绑定、固定输入、实际传输、物化目录和命令 cwd。它没有验证
vLLM 依赖安装、native 编译、NPU 执行、完整 managed recipe 生命周期或时延回归。

## 本地源码复制成本

以下是同一 Windows 主机上的候选路径采样，每次使用新的目标目录，各测两次。
没有清空 OS 缓存，测量期间存在并发测试。它们不是冷启动、端到端任务成本
或延迟 SLA。

| 路径 | 第一次 | 第二次 | 被测语义 |
|---|---:|---:|---|
| 三仓 linked worktree 对照 | 1.35 s | 1.37 s | 共享 Git 注册的计时对照 |
| 完整编辑状态 capture | 24.12 s | 26.78 s | 捕获并复制 HEAD、index、working 和普通 untracked 状态 |
| canonical 固定 revisions 准备 helper（最新样本） | 3.863935 s | 4.444526 s | 固定 Git checkout 配置后克隆精确提交，生成独立三仓 |

复制样本使用 workspace `43c75a1b`、vLLM `bcf2be96`、Ascend `b36dc06d`
的实际源码树。它们是复制成本样本，不是当前 `sources.lock.json` 两项基准的
NPU 兼容性证明。完整 capture 路径在这组计时中输入为干净树；有修改的 fork
语义另由真实 Git fixture 覆盖，不能将这些数值当作所有 dirty 树的固定成本。

两次 canonical helper 结果都核对了三仓精确 HEAD、干净状态、独立 `.git`
目录和无 alternates。实际源码中长度 262、268、282 字符的路径也完成检出并
保持文件哈希。linked 对照较快，但未提供完整多仓目录所需的独立清理生命周期。

因此，已验证 canonical 计划的复制步骤复用固定 revisions；现有编辑树和
conversation fork 才使用完整 capture。独立目录仍有实际复制和存储成本，
不能表述为零耗时。最新 helper 样本保留 Git 配置冻结，并包含 Git 仓库发现
边界修复；此前冻结配置后的 4.76 s / 4.76 s，以及更早的 4.10 s / 4.38 s
样本均保留在原始记录中。它们使用同一组来源，未清空 OS 缓存且存在并发负载，
不能把轮次差异直接解释为性能提升。准备缓存与锁归属 durable project，
不同来源目录只决定选中的源码，复用同一缓存；这一边界有独立回归测试。

## 依赖同步与轻量任务

`vaws_deps.py sync` 已只管理包环境，删除知识服务 import、模型/index
preparation 及知识状态输出；退役的 `--packages-only` 会在安装前被严格参数
解析拒绝。CI、native preparation 及当前文档使用同一个普通 sync 入口。
显式 `knowledge_setup.py` 和知识包 prepare API 保留；MCP 仍按实际使用启动维护。

相关测试记录为 61 passed、1 skipped，另有 3 个 native/updater 调用方测试通过。
跳过项是要求测试进程本身启用 UTF-8 模式的既有 Windows 测试。显式知识准备与
配置用例仍通过，证明这次删除没有移除用户请求知识维护的入口。

实际使用已安装 Python 3.13.12 执行 `sync --locked`：两次产品调用均退出 0，
未导入知识模块，未启动 installer、知识 backend 或 index 子进程，均只启动一条
base Python 身份查询子进程。第一次耗时 16.93 s，按当前依赖输入选中已有匹配
环境；原工作目录的选择已经过时。验收脚本最初错误地要求旧选择保持不变，
该断言随后修正，首轮原始结果保留。第二次复用同一环境，耗时 0.229 s。

0.229 s 是一次显式维护调用的采样，不是 PR review 的客户端启动时延。
普通 review、已有本地源码和明确容器任务无需调用源码准备或依赖同步。
本次未测量所有客户端的完整会话成本，也未重启已有 provider。

原主 checkout 更新后，显式依赖同步复用了最终环境 `e58a46b0`。已检测到的
五个已安装客户端均返回 `wiring_configured=true`；trust 与 connected 仍为
false。该结果证明配置写入完成，没有证明原生信任、连接成功或运行中的
hook/provider 已重新加载。

## 合入提交的三平台 CI

功能最终 HEAD `4b11ae543ac4b9862fe6be9a4a82d14e55ecd9d8` 的
[CI run 34743399890](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34743399890)
三平台全部通过，各覆盖 90 个测试入口：

| 平台 | Passed | Skipped | 核心子集 |
|---|---:|---:|---|
| Linux | 2,191 | 12 | 97 passed，0 skipped |
| macOS | 2,188 | 13 | 97 passed，0 skipped |
| Windows | 2,194 | 7 | 97 passed，0 skipped |

核心子集包含在各平台全量结果中，不重复计入总数。这些结果对应功能 PR 的
最终代码；后续自动维护 PR 的精确 head 验证作为另一条已完成的链路记录于下文。

## 已安装环境的本地测试与原生 CLI

已安装的 Windows immutable 环境 `e58a46b0` 使用 Python 3.13.12，固定
coordinator `0.5.0.dev1` 于 `9f94f27964437f962e6037529ccf2f0b1c709ede`。
该环境中的全量本地测试覆盖 90 个测试入口，结果为 2,181 passed、6 skipped，
无 failure 或 error；相关 consumer 回归另有 110 passed。这些是对应运行时
代码和环境的本地证据，不能自动覆盖后续代码；最终三平台结果独立列于上节。

官方 `vaws_client.py kimi` launcher 实际启动了已安装的 Kimi Code CLI 0.42.0，
真实 ACP `initialize`、`session/new`、SessionStart hook 和 EOF 退出完成，
共 10 项检查通过。检查覆盖原生 session 与实际 hook cwd、native identity、
三仓来源绑定、标准 `editor_workspace` 文件、独立 Git 根和源码可读性；用户
全局 Kimi 配置保持不变。

这次原生 CLI 实测使用较早的环境 `715148d8`，coordinator 固定于
`a91f19a9d7c63d8fe1228ad91aa02eecc6cd82ab`，并非上述 `9f94f279`。
测试没有发送模型 prompt、调用 LLM 或打开编辑器 UI；本地初始化使用占位值
满足配置存在性检查，没有读取或复制真实认证数据。它证明有界的原生 CLI 与
hook 行为，不能代替最终环境的原生端到端验收或其他客户端的 UI 验收。

## 合入后的实际准备与续接

原主目录更新到 `a80923e6` 后，使用最终 `e58a46b0` 环境中的官方
`AgentSessions.attach` API 创建一个独立测试 context，再执行生产
`vaws_start.py --client codex --context-file ...` 入口。实际返回
`ready` / `created`，产生独立的 workspace、vLLM、Ascend 三仓目录，workspace
HEAD 为 `a80923e6`，环境保持最终 `9f94f279` coordinator 的同一 receipt。
每个源码 HEAD 与该目录提交的锁一致，三份 Git 存储均独立且无 alternates；
来源默认值、编辑器目录、主项目归属和已确认身份核对通过。

首次准备耗时 **45.287248 s**，包含上游检查、准备缓存、配置、源码目录生成和
审计开销；这不是单纯复制计时，也不是清空所有缓存后的基准。相同 context
的续接耗时 **0.651009 s**，返回相同选择及 `reused`。续接前后检查完全一致，
审计仅记录 4 次只读 Git `rev-parse`，没有上游操作、复制、配置、网络连接、
知识维护写入或 ready 记录重发。release 选择通过官方 `show --channel release`
读取，未创建第二个任务或运行 NPU 工作负载。

首次验收脚本漏传子进程 UTF-8 参数，Windows 入口的正常解释器重启使父进程
退出时覆盖了子进程审计文件。产品准备和来源检查均成功，但这次 live 运行的
ready 发布顺序记录丢失，不能据此声称已观测到原子发布顺序。原失败验收记录
保留；脚本修正 UTF-8 参数并按进程保留审计后，只续接同一个已有任务完成
剩余检查。发布顺序的结论仍由相应 CI 测试支持。本节验证官方 attachment API
与启动入口，不代表实际 Codex 编辑器 UI 已切换目录。

自动源码锁 PR 合入、原主目录快进到 `9bf2265` 后，对同一个 context 再执行
一次启动入口，耗时 **0.620983 s**。主目录锁中的 Ascend 已为 `d4d2957`，
返回的旧任务仍为 workspace `a80923e`、Ascend `799801f`，除 `reused` 状态外
与首次结果一致，环境 receipt、context、来源 HEAD、编辑器文件和 ready 记录
哈希不变。审计仍仅有 4 次只读 Git 查询，无 fetch、复制、配置或知识维护。
这直接验证了维护更新不会改写正在复现或继续开发的旧任务。

## 旧 gitlink 布局的一次性迁移

在 Git 2.45.1.windows.1 的隔离本地 fixture 中，目标提交移除两个父仓 gitlink
和 `.gitmodules`，并忽略原路径。默认配置、`submodule.recurse=true` 和命令级
`submodule.recurse=false` 三种条件各覆盖八类状态，共 24 个案例。

24 次普通 `git merge --ff-only` 均完成并保留文件字节。18 个已初始化案例中的
两个源码仓均保留 HEAD、refs、index 哈希、staged/working diff、untracked 文件
和原 `.gitfile`，旧对象仍在 primary `.git/modules`。三个未初始化草稿案例
保留原内容；仅三个完全空的未初始化案例移除了空目录。

另有三项边界验证：

- 父仓 index 已暂存 gitlink 更新时，Git 拒绝快进；父仓 HEAD/index 与子仓状态
  保持不变，需要按实际冲突处理，不能强制覆盖。
- 从旧源码创建的活动 linked worktree 在快进后仍可用，未推送提交、自己的
  index 和 staged/working/untracked 内容保持不变。
- 新 VAWS 能识别保留旧 gitfile 的源码根，并从中复制独立多仓任务，保留代码与
  修改状态，同时使用新的独立 Git 存储。

这个布局迁移无需搬移或重新克隆仍被使用的源码。应保留 durable primary 及
其 `.git/modules`，避免打断旧活动源码。本结论只针对被测快进合并，不授权
deinit、强制 reset、递归删除或清理活动 Git 存储；真实主 checkout 未由这些
fixture 操作。

随后，真实原主 checkout 从 `e6a650b333469e83d63bc1643a4f21ab8a4604e2`
普通快进到 `a80923e6325fb53629332b4f5688fe37b28e0f3e`。前后保留核对返回
`ok=true`：两个原源码仓的 HEAD、全部 refs、index、staged/working diff、
普通 untracked、gitfile 和 common directory 均保持不变；原主仓分支及
普通文件改动状态也保留。vLLM 的 4 项、Ascend 的 6 项额外 worktree 登记
及其基线状态保持一致。这些登记数包含更新前已经不可用的登记，不表示有
10 个活动目录。原源码路径及 durable primary 的 Git 存储均保留。

## 设计审查与自动维护

审查遵循九条设计原则，重点约束如下：能力按需参与；普通 review/明确 endpoint
不增加准备 gate；固定源码声明不等于 NPU 实验结论；新多仓任务使用独立目录；
fork 保留实际修改和环境；部分失败不发布 ready；原生身份与准备归属保持区分。
这些是实现与评审要求，不是每个 Agent 需要执行的步骤清单。

Kimi K3 max + Never Ask 已完成整体收敛审查，固定 HEAD 为
`d42974b5f8ad4e529baa1370e0fe067752c550ca`，结论通过。后续 Git 仓库发现
边界审查覆盖 `6920aa8` 及审查时实际工作树 `7f5175b4`，结论同样通过。
仓库根边界审查在 `340769d826ab64b78ab840317c74bc6709716f08` 通过，耗时
268.92 s；最终增量审查固定于 `4b11ae543ac4b9862fe6be9a4a82d14e55ecd9d8`，
由实际 Kimi CLI 以 K3 max、headless auto / Never Ask 执行，62.93 s 后返回
Pass、无阻断问题。本次链路的设计与代码审查已完成。
审查确认原缺陷已修复、相关边界未引入新的阻塞问题；审查者没有执行测试，
这些结论不替代本报告中单独列出的运行证据，也不自动覆盖之后的代码变更。

首次工作流验收使用真实上游快照 `799801feef347469d5e9b39374b9210e0d4f7431`
初始化锁文件；它是当时 Ascend main `d4d2957e` 的直接父提交，两份上游声明
实际存在且解析结果相同。合入功能后已触发
[维护 run 34743891383](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34743891383)，
bot 创建了仅修改 `sources.lock.json` 的
[PR #167](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/167)，
head 为 `3f27d82fc37e8ad7504a7aefece4a5672b71987e`，将 Ascend 从 `799801f`
推进到 `d4d2957e`。三个平台的实际 checkout 和 Git 日志均确认验证的是该 PR
head，而非 dispatch 时的 main。三平台全部成功后，工作流再次检查 PR 归属、
唯一修改路径和相同 head，为该提交写入 `source-lock/CI=success`，并由
GitHub Actions 于 2026-09-13 07:04:51 UTC 自动 squash 合入
`9bf2265791bb11acf8e8bb1e22637b926d5bd350`。没有人工替代维护 PR 的合并。
原主目录随后快进到该锁更新提交，两个既有源码仓及已登记工作目录再次通过
保留核对。更新针对主仓源码锁，已有源码目录和执行输入不随锁改写。

组织策略及仓库“允许 GitHub Actions 创建和批准 PR”已启用，默认 workflow
权限仍为 read，仓库变量 `VAWS_SOURCE_AUTO_MERGE=true` 已设置。只读预检确认
当前 Actions 与 squash 合并可用，维护工作流具备分 job 的必要权限。
创建、精确提交验证、状态记录和策略合并均有上述真实运行证据。功能 PR #166
包含 workflow 修改，现有 CLI OAuth 缺少 `workflow` scope；该功能 PR 通过
已有权限的浏览器合入，没有新增令牌或扩大 CLI 授权。后续源码锁维护链路
使用工作流自己的 `GITHUB_TOKEN` 完成。

随后再次触发
[无变化 run 34744383856](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34744383856)。
refresh job 13 秒完成，源码锁与 main 无差异，未创建新 PR，未运行三平台
验证，validate 与 merge 均跳过，main 仍为 `9bf2265`。这覆盖了日常维护在
上游声明未变化时直接结束的真实路径。

准备和配置结果使用标准 `editor_workspace` 字段给出多目录编辑器文件，同时
保留实际 `workspace`、`native_workspace` 和 sources。生成文件与返回路径是
可检查的产品行为；客户端是否真正打开、搜索、显示分仓 Git、恢复和正确清理，
必须由原生 UI 验收证明，不能从配置测试推断。

## 验证边界

- 原生客户端 UI 的完整打开、搜索、分仓 diff、恢复和删除验收。
- 当前声明版本组合的 NPU 依赖兼容、模型正确性、精度或吞吐验证。

以上范围未执行。本次四机复验、真实启动与续接、自动源码锁维护、本地测试
和 Kimi 审查不构成这些 UI 或 NPU 场景已经通过的证据。

## 本地原始证据

原始文件仅保留在未跟踪的 `.vaws-local/`，包含私有基础设施坐标，不随本报告
公开，也不在此创建不可用的文件链接：

- `source-workspace-acceptance/README.md` 与其下的固定快照、四机结果和 materialize logs。
- `source-workspace-acceptance/20260913-145413-installed-479e3fc5/` 中的最终已安装包四机复验、运行版本和 28 项检查汇总。
- `vaws-copy-cost-20260913-133022-9a0d2c1c/result.json`、`prepared-helper.json`、`prepared-helper-final.json`、`git-discovery-helper.json`。
- `source-lock-validation/deps-sync-README.md`、测试 XML/text 与两次真实 sync JSON。
- `source-layout-migration/README.md`、两个 probe 脚本、`results.json` 和 `extra-results.json`。
- `source-layout-migration/primary-before.json`、`primary-after-feature.json`、`primary-after-source-lock.json` 和只读核对脚本，记录真实原主目录更新前后的保留结果。
- `source-workspace-final-environment.json`、`source-workspace-final-pin-tests.json` 及其指向的测试日志和 XML。
- `native-cli-acceptance/README.md` 与真实 ACP、hook、preparation 和核对结果。
- `source-workspace-live-start/result.md`、首次准备及同 context 续接目录，保留原验收失败、审计限制和后续检查。
- `source-layout-review/final-review/`、`source-layout-review/git-discovery-20260913-142216/` 中的固定版本审查记录。
- `source-layout-review/repository-root-20260913-143723/`、`source-layout-review/repository-root-20260913-144249/` 中的仓库根边界和最终增量审查记录。
- `source-lock-live/` 中的组织策略与仓库权限证据；配置事实与上文链接的实际 workflow/PR 状态分别记录。
