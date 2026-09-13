# 独立多仓源码工作目录验证

Status: dated validation evidence, 2026-09-13

本报告记录独立源码目录候选的四机验证、本地复制成本、依赖同步与旧布局迁移。
当前合同见 [source-workspace.md](source-workspace.md)。以下证据覆盖不同的有界
路径，不代表最终提交、原生客户端 UI 或完整 NPU 环境已经验收。

## 四机固定源码传输

四台机器使用同一份小型源码快照。coordinator 实现固定为
`66e2d2b3aa30512eef433e0594ebf815e574b6ce`，包含此次 native 来源绑定改动；
remote-dev 使用已安装的 0.8.0 包。consumer 来源展开使用本次候选代码。
这些结果不自动覆盖较新的 immutable 环境或后续 coordinator 生命周期修改。

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
本地改动。机器 C 在独立计时实验释放资源后完成，复用同一快照。

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
| canonical 固定 revisions 准备 helper | 4.76 s | 4.76 s | 固定 Git checkout 配置后克隆精确提交，生成独立三仓 |

复制样本使用 workspace `43c75a1b`、vLLM `bcf2be96`、Ascend `b36dc06d`
的实际源码树。它们是复制成本样本，不是当前 `sources.lock.json` 两项基准的
NPU 兼容性证明。完整 capture 路径在这组计时中输入为干净树；有修改的 fork
语义另由真实 Git fixture 覆盖，不能将这些数值当作所有 dirty 树的固定成本。

两次 canonical helper 结果都核对了三仓精确 HEAD、干净状态、独立 `.git`
目录和无 alternates。实际源码中长度 262、268、282 字符的路径也完成检出并
保持文件哈希。linked 对照较快，但未提供完整多仓目录所需的独立清理生命周期。

因此，已验证 canonical 计划的复制步骤复用固定 revisions；现有编辑树和
conversation fork 才使用完整 capture。独立目录仍有实际复制和存储成本，
不能表述为零耗时。最终 helper 样本包含审查后补齐的 Git 配置冻结；此前
4.10 s / 4.38 s 样本保留在原始记录中。准备缓存与锁归属 durable project，
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

## 设计审查约束与待完成项

审查遵循九条设计原则，重点约束如下：能力按需参与；普通 review/明确 endpoint
不增加准备 gate；固定源码声明不等于 NPU 实验结论；新多仓任务使用独立目录；
fork 保留实际修改和环境；部分失败不发布 ready；原生身份与准备归属保持区分。
这些是实现与评审要求，不是每个 Agent 需要执行的步骤清单。

首次工作流验收使用真实上游快照 `799801feef347469d5e9b39374b9210e0d4f7431`
初始化锁文件；它是当时 Ascend main `d4d2957e` 的直接父提交，两份上游声明
实际存在且解析结果相同。合入功能后立即触发维护工作流，由正常数据 PR 将锁
推进到运行时读到的 upstream main，验证创建、精确提交 CI 与策略合入。完成
这条链路前不宣称锁已追到最新；已有源码目录和执行输入不随锁更新而改写。

准备和配置结果使用标准 `editor_workspace` 字段给出多目录编辑器文件，同时
保留实际 `workspace`、`native_workspace` 和 sources。生成文件与返回路径是
可检查的产品行为；客户端是否真正打开、搜索、显示分仓 Git、恢复和正确清理，
必须由原生 UI 验收证明，不能从配置测试推断。

截至本报告整理时，以下结果尚未纳入：

- 最终提交对应的完整 CI，以及用户指定的 Kimi K3 max + Never Ask 最终审查结论。
- GitHub 源码锁维护 workflow 的真实 dispatch、固定 PR head 三平台验证及策略合入。
- 原生客户端 UI 的完整打开、搜索、分仓 diff、恢复和删除验收。
- 当前声明版本组合的 NPU 依赖兼容、模型正确性、精度或吞吐验证。

最终 CI 和 Kimi 结论由集成验收补充；此前四机和本地结果不能代替这些待完成项。

## 本地原始证据

原始文件仅保留在未跟踪的 `.vaws-local/`，包含私有基础设施坐标，不随本报告
公开，也不在此创建不可用的文件链接：

- `source-workspace-acceptance/README.md` 与其下的固定快照、四机结果和 materialize logs。
- `vaws-copy-cost-20260913-133022-9a0d2c1c/result.json`、`prepared-helper.json`、`prepared-helper-final.json`。
- `source-lock-validation/deps-sync-README.md`、测试 XML/text 与两次真实 sync JSON。
- `source-layout-migration/README.md`、两个 probe 脚本、`results.json` 和 `extra-results.json`。
