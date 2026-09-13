# VAWS performance mechanism review

Status: dated evidence and proposals, 2026-09-13. Audited consumer main `e09972c35f2ba8eb68377ea5af965bb54e2bc5c6`, coordinator main `3f9cdbdc631fdb3a710e08b37b29e04c3d25b85e` and remote-dev `4da7bbdd6b1a5d809d53522c9ee0b0b1d7d2e83c`. Local control-plane and Git probes only; no new remote/NPU performance experiment. Recommendations below are not current commands or new workflow requirements.

主要机会是缩短必经路径、按本次变化复用证据，以及让工具直接返回足够使用的结果。组件数量或统一接口本身不是优化目标。先删除重复工作、缩小锁和失效范围，再并行剩余的独立工作，最后才考虑新的长期缓存或调度机制。

审查进行时已有并行交付：[coordinator #30](https://github.com/vllm-ascend-workspace/vaws-coordinator/pull/30) 已合入静默 prompt hook 和普通 PreToolUse 提前返回；[consumer #159](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/159) 正在简化一次性初始化及 Agent 指引，[consumer #160](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/160) 正在让已有容器/显式 endpoint 和普通 review 按需绕过 managed startup。这些工作与本次“轻任务不承担全套入口”的方向重合，应复用其实现。下文启动锁和知识准备分析针对明确调用 managed startup 的内部依赖；不把其他 PR 的工作记为本次新增，也不在这里重新实现它们。

## Evidence boundaries

此前 [fresh xhigh comparison](fresh-xhigh-six-comparison-2026-09-13.md) 中，managed 首个工具调用至业务退出并观察到释放为 243.363 秒，其中提交前 126.360 秒、提交至观察到释放 117.003 秒；随后取证 203.268 秒、形成完整实验报告 115.915 秒。提交前已记录命令的进程耗时合计约 2.36 秒，取证区间的 tail 和两次定向 SSH 读取合计约 7.31 秒。其余包含 Agent 阅读、发现、编写脚本、工具间隙和报告，不能全部归因于后端或模型思考。实验要求的逐项编译证明和正式报告也不能成为日常拉服务的必经步骤。

同一 owner 时钟下，fresh 的 created → released 为 106.390 秒，受控 recipe 样本为 87.186 秒。fresh 的 created → incremental-start 多 20.238 秒，而编译开始以后的合计反而少约 1.034 秒。最大的相邻区间差异在首次源码物化报告 missing → 物化成功：17.781 对 3.301 秒，差 14.480 秒。没有该区间逐个 RPC/Git/传输的耗时，不把整个差额指定给某一个操作。

本次包含三个真实 OPC 变体及收尾的增量构建阶段约 40 秒；最终业务内部计时约 7.34 秒。实际编译与业务执行不能当作可直接删掉的记录成本。新任务入口的版本选择、知识准备及全局锁不在上述首个工具计时范围内，下面只确认其依赖关系，不为它们编造生产时延。

[六场景记录](six-scenario-performance-2026-09-13.md) 中，热 Python/不变源码的 managed 提交至释放仍约 24–25 秒，直接成功 SSH 约 15–16 秒。这是尚未消除的工具区间差距，不能用一次 fresh Agent 总目标更快来覆盖；反过来，这两个工具区间也不是完整 Agent 目标计时。下一批收尾与入口优化仍需分别验证这两种成本。

## Priorities

| 顺序 | 已确认的问题 | 建议的机制变化 | 验证边界 |
| --- | --- | --- | --- |
| 先修窄缺陷 | fresh clone 有共同基线对象，但没有历史管理 refs，现有候选发现无法利用它 | 从 admission 固定输入派生一个保守的 clean baseline hint，继续由接收端验证共同对象 | 本地真实输入包对照已通过；远端端到端收益未测 |
| 先修窄缺陷 | compact preparation tail 丢正文；过大结果兜底丢释放/quiet 等完成事实 | 在现有投影中限制日志量，同时保留操作判断所需事实和原始记录 | 保存的真实响应及本地回归；不改变原始 Python API |
| 下一批优先 | 已准备任务读取完成记录前先等全仓库更新锁；可选知识维护仍在锁内 | 恢复先读有效完成记录；同任务首次创建去重；共享锁只保护真正共享的准备/发布 | 本地双任务调用真实入口已复现阻塞，未修改启动合同 |
| 下一批优先 | 同一次构建收尾反复算相同产物哈希，并拆成小 job | 合并 managed 收尾，在函数内部复用刚得到的哈希；复制目的地仍验证 | 1104 个产物在 capture → store 共哈希 4416 次；这只是结构计数 |
| 下一批优先 | 普通脚本调用仍可能需 Agent 自写 run/wait/tail 包装及解码取证 | 既有 CLI/MCP 增加有界等待和按需可读证据，复用 Python wait/现有记录 | serving 已有一条命令的等待和 readiness；不再造业务框架 |
| 按测量推进 | 冷源码候选依赖本地历史，重复复制相同 native bytes | 先衡量剩余 miss、hash/copy/smoke；再决定内容索引或 COW/只读产物层 | 会涉及身份兼容、loader、GC 和隔离，不是换一个缓存键 |

## Source transfer: separate discovery from provenance

当前 source identity 已独立于 clone 的绝对路径，包含固定 commit/tree、SCM、子模块和构建语义；native compatibility 也已有自己的内容归一化。问题不是“换目录必然换源码身份”，而是共同传输基线主要从 retained refs 中发现。普通共享克隆继承 Git 对象，不继承这些 refs。

本地用真实已固定的单 CPP 改动验证：完整闭包包为 16,494,083 / 16,488,889 字节；加入正确共同基线后，两次增量包均为 **4,751 字节**。独立 bare 接收端原先只有基线、没有目标 commit，接收后通过 index-pack、严格 fsck、目标 tree 和 CPP bytes 校验。小 fixture 另测的 525 KB → 411 B 不能替代这个真实输入结果。

本地 pack 本体约 0.87–0.89 秒降到 0.04 秒，派生 hint 本身约 0.39 秒，carrier 创建约 0.36 秒；这些不是网络或完整物化计时。完整包是本次本地对照构造的包，不是原远端试验抓到的网络包。原远端是否仍有该基线未重新观测，不能声称已节省 14.48 秒。

窄方案只使用 admission 固定的 source_head、已录 parentless commit metadata 和固定子模块对象；不读取后来修改的工作文件，不改当前 HEAD/index/refs，不改来源身份或 author 规则。已有候选时不为热路径额外派生。缺失对象或不认识的结构视为 hint miss，原来的完整传输继续可用；接收端的对象闭包和固定 tree 校验不变。

长期可让运输层按内容发现共同对象，同时保留来源/SCM 身份。但子模块 synthetic commit metadata 可以传播到父 tree，跨 author 复用需要处理这些语义，不能直接重写所有 source IDs。先证实剩余 misses 的规模，再决定是否值得引入内部内容索引。

## Startup: narrow the critical path and locks

当前新任务入口在读取已保存的 start result 前取得仓库级 update lock。锁覆盖上游发现、环境准备、worktree、客户端配置、知识准备、绑定和保存。对两个任务调用真实入口、只替换外部依赖的本地模拟确认：已有完整记录的恢复任务，会等待另一任务的可选知识准备完成。注入的短延迟只验证阻塞关系，不是生产基准。

新 workspace 尚未保存知识准备结果时，知识准备同步运行一次强制更新及维护，之后才绑定 sources；入口 subprocess 没有自己的 timeout。之后能够返回 pending，不能说明前面的等待是可选的。已有选择会复用结果，因此不能描述成每次命令都重新建索引。

优先让有效恢复记录走快速路径，同一任务首次创建用任务级互斥；共享环境/目标版本准备合并执行，发布时再使用短锁。知识复用已有配置/索引，由现有 owner 后台或首次实际查询时维护，普通代码工作先可用。新任务检查上游一次仍是当前明确合同；身份、fork 镜像同步与可选索引维护可从“选定本任务版本”中分离。离线旧版选择是产品策略变化，不能通过静默缓存擅自改变。

## Preparation: reuse within the operation before adding a cache

同 native 的 Python 改动路径已经合并源码物化与 native view 发布、复用原始 smoke，并直接绑定 prepared receipt；运行前容器与 manifest 读取也已经并行。不能再次提议删除不存在的全量注册验收。

仍确定存在的重复在新 native 的 capture → store：capture 哈希、capture 后 verify、独立 publish 再验源、复制后验目的地，1104 个产物共四遍。shared restore 另有验 bundle 与验复制目的地两遍。结构探针使用实际产物名称、合成内容及局部环境 stub 调用原函数，只证明读取次数，不证明时延或新的校验实现正确。

建议先把 marker、capture 和可选 store 合并到同一个 owned 收尾作业，再复用这个函数内刚建立的源哈希事实。公开 publish/adoption 仍完整验证外来输入；复制到临时目的地后仍验证实际字节再原子发布。不要增加跨调用 `already_verified` 参数，也不要跨排队等待复用可变运行环境检查。

现有观测中 marker 独立 job 约 0.52 秒，profile 约 13.2–13.7 秒，profile quiet → stored 约 1.91–1.96 秒。store 不是整个 15 秒的原因。新 native 或新 recipient 在最终 loader 中的一次真实 smoke 仍必要；冷构建前置 verify-imports 可以并入最终 smoke，但 shared-hit 增量路径已经跳过前置 import，它不会加速本次两条 recipe 样本。

先测 capture 内 smoke、哈希、源输入和复制各自耗时，再考虑并行无依赖的只读工作。venv 与源码物化可以在 root 准备后重叠，但需要失败时取消并等待 sibling，现有 venv 约两秒级，优先级低于删除重复作业。只读连接/placement 可提前；CPU 准备阶段提前占 NPU 会增加共享资源总成本。

每个执行的 source/output 隔离仍必要，相同 native bytes 是否每次物理复制则可改变。COW 或只读内容层需要实际文件系统支持、写隔离、loader 路径、引用保活与坏缓存恢复的完整设计；不要直接硬链接可写 donor，也不要为几秒复制先建立一个新常驻控制面。

## Agent interaction: finish the existing operation

CLI/MCP 已默认保存完整 record 并返回 compact；把 Python 原始 TaskClient 返回全部打印出来是先前实验 runner 的选择。保存的真实释放响应约 35 KB 经已有投影约 2.4 KB，tail 约 43 KB → 6.6 KB；投影测试省略包络版本字段，不是完整线上字节计量。真正的缺口是 compact 丢必要事实、CLI/MCP 无现成有界 wait，以及已有证据难以直接阅读。

先让普通脚本一次提交并有界等到目标条件，超时保留同一 execution reference，不重提、不停止。内部可以直接复用已有 TaskClient.wait；事件/长轮询优化在测到实际 IPC 成本之后再做。serving start 已包含 prepare → running → HTTP/models/first-token，有 no-wait 和一次失败 tail，应继续复用。通用 coordinator 不负责猜业务 readiness。

默认返回状态、是否释放、必要输出/错误和原始记录引用。只有明确要求解释构建/复用时，才读取现有 owner 记录并内部解码，返回按主题可读的依据。普通 Agent 不应为拿到一次构建结果检索目录、解压 manifest、手写多个取证脚本；也不需要每次填写阶段表、重复摘要或提交知识。

本地 cached observe、已准备目标的响应和必要管理往返可以把 1 秒作为优化目标；包含首次源码传输、真实编译、框架 import 或模型加载的全流程需要分别衡量。验收同时保留直接操作对照、提交至结果和 Agent 完整目标三个端点，保留冷/热状态与失败尝试，不用最短单次样本承诺所有场景。

## Transport: keep the optimizations already present

固定 remote-dev 已按 host/port/user/identity/连接超时复用 SSH，会话键不含 execution root/cwd；不同 key 的建联不占全局锁，同 key 的并发建联合并，闲置连接有回收。已有代码摘要缓存也会减少重复 payload。新 execution root 不意味着必定新建 SSH，当前没有必要另造跨 CLI 常驻 transport。

owned launch 已合并 prepare/go/exchange，等待会响应取消并确认 quiet、后代清空及剩余输出。不能为省一个 poll 只看 leader exit，也不能重放结果不确定的 launch。剩余明确机会在调用方：把几个 package-owned 小写入并入同一作业，减少每次 Python/Bash 启动；这正好支持上面的 finalize 合并。普通 shell 与显式 runtime environment 初始化仍有语义，不能全局绕过或长期缓存用户 shell 函数来制造快路径。本次没有运行新的 transport 延迟基准。
