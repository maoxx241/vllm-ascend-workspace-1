# 社区协作

Status: current

首次进入 VAWS 时，Agent 会说明并询问是否开启社区协作，推荐开启。个人 Fork、
Star 和社区协作是三个独立选择。登录 GitHub、clone 仓库、使用中央知识库或没有
回答问题，都不表示同意上传。选择保存在本机工作区的未跟踪状态中，后续任务复用。

## 开启与关闭分别意味着什么

| 能力 | 开启 | 关闭或尚未选择 |
|---|---|---|
| 本地开发、受管任务、个人代码贡献 | 可用，按任务要求执行 | 可用，按任务要求执行 |
| 中央知识库读取与更新 | 可用 | 可用 |
| 本地分级日志、诊断包、经验留存 | 可用 | 可用 |
| 自动贡献脱敏开发经验 | 开启，沿用知识组件的发布审核流程 | 关闭 |
| 自动上传脱敏故障并向 VAWS 提 issue | 开启，由后台 worker 执行 | 关闭 |
| 本机配置的 Grok 自动分析与 issue 回复 | 可选，依赖模型认证 | 关闭 |
| 维护者中央 Grok 对已公开 issue 的诊断 | 由中央服务提供，新用户无需模型账号 | 不产生新的自动报告；已公开内容见下文 |
| 自动修改代码、合并、部署修复 | 尚未实现，不属于本次授权 | 尚未实现 |

参与的好处是把个人排错成果变成可复用的中央知识，故障有版本、阶段耗时和相关
日志可查，开发者无需重新整理材料。中央知识的可用性仍取决于网络、已发布内容及
本地索引状态；知识是参考，不是执行许可，也不保证问题已经被解决。

## 上传什么，交给谁

诊断上传目标是 [VAWS issues](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/issues)。
公开证据采用字段白名单、脱敏和最终扫描，包含组件版本、失败类别、调用关联、
阶段耗时及经过处理的日志。原始环境变量、凭据、命令参数、完整提示词、私有路径
和原始标准输出不直接附上。截断或缺失证据会说明；脱敏会损失信息，诊断可能需要
人工补充。知识贡献采用知识组件生成的公开副本，经既有贡献流程进入中央知识仓。

启用的 Grok worker 只接收公开脱敏证据，其执行工具关闭；诊断是模型生成的建议，
可能误判。模型账户及 GitHub 认证由部署者提供。后台服务不会从 Agent connector
中导出凭据，也不会因为用户已 clone 成功就声称拥有上传或模型调用权限。

自动报告有去重、限流、持久队列和重试；它不阻塞业务工具返回。默认每 60 秒扫描，
不承诺故障发生后立刻可在 GitHub 看到，也不把调用参数错误或用户取消当成系统故障。

## 修改选择

```text
uv run --no-project python .agents/scripts/vaws_init.py status
uv run --no-project python .agents/scripts/vaws_init.py apply --community disabled
uv run --no-project python .agents/scripts/vaws_init.py apply --community enabled
```

关闭立即使本工作区尚未发出的上传、本机模型分析和回复失去授权，不关闭其他工作区的
后台服务。本地日志和经验继续保留，中央知识读取继续可用。关闭期间的内容不会因
再次开启而自动补传。选择通过独立的短锁保存；另一个初始化正在安装或等待网络时，
关闭仍先生效并快速返回，较早的初始化不能覆盖较新的选择。授权文件缺失时不会从
初始化历史恢复上传权限，需要重新明确选择。
已经发出的请求无法撤回，已经公开的 issue、评论和知识贡献
不会自动删除；需要删除时按具体内容处理。维护者的中央 bot 对已经公开的 issue
按仓库服务规则继续处理，不受单台客户端本地选择控制。本机 worker 默认不扫描
全仓 issue；中央处理必须由维护者显式开启，并使用隔离模型环境和独立队列。

授权采用工作区标识和选择版本，独立任务沿用明确关联的主工作区选择。缺失、损坏、
过期或不属于当前选择的记录不允许自动贡献。日志关联标识不赋予设备、代码或任务
操作权限。当前尚未发布，不提供旧版本进程或状态的兼容迁移；部署前停止旧组件，
使用新版和新的后台状态。缺少有效选择不能自动贡献。

## GitHub 登录与 token

支持本机 `gh` 登录，也支持 `GH_TOKEN` / `GITHUB_TOKEN`。后者可用于没有 `gh`
的 GitHub API 操作和 HTTPS Git 凭据交互；SSH 用户保留原协议。token 不写进远端
URL、命令参数、项目文件或报告。首次 clone 发生在仓库代码可用之前，应使用已有
Git Credential Manager、`gh auth setup-git` 或平台的安全凭据机制。

GitHub connector 可向 Agent 提供登录身份并执行其提供的动作，但 connector、
本地 Git 和后台 worker 是不同认证边界，不能将其中一个的成功当成另外两个的成功。
账户还必须具备对应仓库和操作权限；受限 token 的 clone 成功不证明有 Fork、Star、
push 或提 issue 的权限。参见 [GitHub token 文档](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
和 [GitHub CLI 环境变量](https://cli.github.com/manual/gh_help_environment)。

详细日志、队列和运行保障见[诊断系统](diagnostics-system.md)。
