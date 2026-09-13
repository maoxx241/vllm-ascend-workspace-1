# vllm-ascend-workspace

**中文** | **[English](README.en.md)**

完全面向 Agent 的 [vLLM](https://github.com/vllm-project/vllm) 与 [vLLM Ascend](https://github.com/vllm-project/vllm-ascend) 开发工作区。人表达目标、决定实质取舍；Agent 完成代码修改、环境准备、实验执行和证据整理。

## 从任务开始

在 Agent 客户端中打开工作区，直接说明目标，例如：

> Review 这个 PR，重点检查错误处理和兼容性。

> 这次用指定机器上的现有容器 `repro-case`，代码在 `/work/vllm`，按 `/work/start-case.sh` 复现问题。

PR review 直接使用原生 Git 和文件工具。已有容器任务直接把 host、container、cwd 和原启动命令交给 remote-dev，保留容器内代码和环境；无需先绑定模式、同步源码、拉起受管服务或准备知识库。两类任务都不因缺少 GitHub 身份配置而要求初始化。知识按需参考，缺失或未就绪不阻止独立工作。容器调用示例和边界见 [remote-dev 消费说明](docs/remote-dev-consumption.md)。

需要完整开发配置时，再明确提出：

> 初始化这个工作区，配好 vLLM Ascend 的开发环境。

初始化复用已有配置，按需准备源码与锁定依赖，并一次配置已安装的 Codex、Cursor、Claude、Grok 和 Kimi。需要完整多仓编辑时，准备整个独立目录：VAWS、`vllm/` 和 `vllm-ascend/` 都是普通独立 clone，同卷可复用对象硬链接，不依赖 alternates 或父 worktree 的清理行为。已有实际源码和准备结果直接复用，普通 Review 和直接 endpoint 任务不调用 `vaws_start`。恢复会话沿用原目录、来源和环境。版本选择见[源码合同](docs/source-workspace.md)，客户端实际目录能力见[编辑隔离合同](docs/native-workspace-isolation.md)；历史[验收记录](docs/unified-session-validation-2026-09-13.md)不代表新布局已在全部客户端通过。安装与平台行为见 [dependency-plane.md](docs/dependency-plane.md) 和 [platform-contract.md](docs/platform-contract.md)。

日常工作只需说明目标和影响结果的输入，例如：

- 用这份模型权重和启动参数拉一个四卡推理服务。
- 比较这两个 baseline/candidate 工作树的吞吐。
- 为这个 workload 采集 profiling，分析耗时算子。
- 找出 graph 与 eager 输出首次分歧的位置。
- 拉起本地 NPU 集群监控页面。

Agent 按任务选择工具或技能；执行引用、状态推进和报告由工具根据实际结果生成。缺失证据保留为未知或无法下结论。

## 设计与职责

后续变更以[九条设计原则](docs/design-principles.md)为依据：

- 代码与命令入口完全围绕 Agent 使用设计。
- 封闭世界故障进入所属组件代码与回归测试；有用经验可用普通 Markdown 留存，保留条件、证据和不确定性。知识按需参考，查库和录入不成为任务步骤。
- 生命周期、校验和记录在各 owner 内部完成；业务入口接收业务输入和真实证据。
- 从完整任务衡量简化效果。未正式发布的接口直接替换，删除旧入口与兼容别名。

工作区负责项目材料、客户端接线和业务技能。`remote-dev` 负责明确 endpoint 的远程 I/O，`vaws-coordinator` 负责托管源码、环境、NPU 与执行，`vaws-knowledge` 负责 Markdown 知识查询和捕获，`vaws-top` 负责集群观察。观察不分配设备；任务身份来自原生客户端关联。已有容器和无关工作树继续保留。

## 业务技能

首次仓库设置见一次性 [repo-init](.agents/bootstrap/repo-init/SKILL.md)；本地监控生命周期使用[监控命令](docs/npu-fleet-monitor.md)。两者均不进入业务 Skill 自动发现。

| 技能                       | 用途                                             | 何时使用               |
| ------------------------ | ---------------------------------------------- | ------------------ |
| **modelscope**           | 下载、续传、查看进度并 SHA256 校验 ModelScope 模型权重                  | 需要把模型权重下载到明确目录时 |
| **vllm-ascend-serving**  | 在远程容器上一键拉起 vLLM Ascend 推理服务，由 coordinator 管理执行和资源 | 需要在远程机器上起推理服务时     |
| **vllm-ascend-benchmark** | 在远程容器上运行 `vllm bench serve` 性能基准测试，支持多轮预热和统计聚合     | 需要测量吞吐或延迟时 |
| **ascend-memory-profiling** | 采集并分析昇腾 NPU 的 HBM 显存占用，按组件拆分并溯源 | 需要分析 vLLM 推理服务的显存占用时 |
| **ascend-profiling-collection** | 采集 Ascend torch profiler：起服务、控制 profile 窗口、运行 workload、远端 analyse 并写 manifest | 需要采集 kernel_details/trace_view 时 |
| **ascend-profiling-analysis** | 分析已采集的 profiler root/manifest，生成 step/layer/operator/cross-rank 诊断报告 | 需要分析 profiling 结果或生成报告时 |
| **vllm-ascend-graph-debug** | 定位图编译、捕获、重放及 graph/eager 正确性分歧 | 图模式失败或与 eager 结果不一致时 |
| **vllm-ascend-correctness-validation** | 对比 baseline/candidate、eager/graph、离线/在线和 AISBench 正确性 | 需要精度验证或输出对拍时 |
| **vllm-ascend-change-validation** | 对照代码 diff 汇总已执行的验证证据和报告 | 明确要求汇总验证结果或生成正式报告时 |
| **vllm-ascend-performance-regression** | 运行交替 A/B 实验并分析波动和回退阈值 | 判断吞吐或延迟是否回退时 |
| **vllm-ascend-distributed-debug** | 从拓扑、端点、collective 和逐 rank 事件诊断分布式故障 | 故障依赖多卡、多机或 rank 时 |
| **ascend-tensor-dump** | 有界采集中间张量并定位首个数值分叉的 stage，覆盖 eager 与图模式 | 输出错误或两个配置结果不一致，需要定位到层、stage 或单算子时 |
| **ascend-operator-debug** | 将模型故障缩减为单算子并运行 dtype/shape/layout/mode 矩阵 | 需要最小化算子复现时 |
| **ascend-triton-operator-development** | 从 PyTorch 或 GPU Triton 语义生成首个正确的 Ascend Triton 实现 | 新建或迁移 Triton 算子时 |
| **ascend-triton-kernel-validation** | 检测 PyTorch fallback 并执行显式正确性矩阵 | 验证 Triton 候选实现时 |
| **ascend-triton-kernel-optimization** | 根据正确性和 profiler 证据优化已选 kernel | 优化已正确的 Triton kernel 时 |
| **ascend-triton-workflow** | 汇总已有 Triton 阶段证据并检查关联 | 明确要求阶段汇总报告时 |
| **vllm-ascend-pd-serving** | 启动和观察一个 prefill/decode 拓扑，并做 HTTP smoke | 部署 PD 分离服务时 |

技能按任务选用。详细输入和方法位于对应 `SKILL.md` 的参考资料；普通本地文件与 Git 操作使用原生工具。[AGENTS.md](AGENTS.md) 是客户端入口，[文档索引](docs/README.md) 区分当前契约和历史验收证据。

## 仓库与本地状态

规范仓库是 `vllm-ascend-workspace/vllm-ascend-workspace`。`vllm/`、`vllm-ascend/` 是按需准备的普通独立 Git 仓库，仍可直接查看和修改。`sources.lock.json` 固定官方来源与精确组合：默认 `development` 使用同一 Ascend SHA 声明的 verified vLLM commit，`release` 使用其发布 tag 对应的完整 SHA；后者不代表完整稳定 Ascend 发布栈。人可以分别运行 `git -C vllm diff` 和 `git -C vllm-ascend diff`，父 status 不能代表内仓修改。

首次初始化由 AGENTS 指向一次性的 [repo-init](.agents/bootstrap/repo-init/SKILL.md)。明确初始化，或受管操作真正需要尚未确认的个人容器身份时，才确认 GitHub 身份；普通 review 和显式远端 I/O 不触发这套流程。开发 Fork 必须属于个人账号，`origin` 指向个人 Fork，`upstream` 保留官方来源。

需要独立编辑或受管准备时，新任务一次选择精确主仓、组件与实际源码，准备入口和 native attachment 自动展开 sources；显式 `sources={}` 保持优先。MCP gateway 固定该任务的组件环境，恢复时不改版本。原生 launcher 在实际目录启动进程；Codex/Cursor worktree 回调只能返回实际 workspace 并接通 scope，不能声称替父 UI 切换目录。人可打开返回目录查看源码，Agent 使用实际 cwd 和绝对路径。知识配置、内容和模型/index 缓存按明确的工程关联复用。见[个人 Fork 与自动更新](docs/forks-and-updates.md)。共享 root 下的容器命名、留言和算子产物缓存由组件处理，权重沿用服务器现有路径，无需 Agent 填写身份或登记成果。见[身份与协调](docs/identity-and-agent-coordination.md)。

`.agents/skills/` 保存业务技能，`.agents/lib/` 保存共享消费代码，`.agents/scripts/` 保存客户端接线和维护工具。客户端投影统一指向规范技能。运行状态和私人配置放在未跟踪的 `.vaws-local/`，凭据不入库。公开知识只使用包生成的脱敏副本。

工作区许可证独立于两个业务仓库；它们分别遵循各自上游许可证。
