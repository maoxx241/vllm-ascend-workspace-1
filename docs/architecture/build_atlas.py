from __future__ import annotations

import html
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
(ROOT / 'svg').mkdir(exist_ok=True)
W, H = 1600, 1000
BLUE, INK, MUTED = '#2365d8', '#142841', '#5a7089'
COLORS = {'blue': BLUE, 'teal': '#087f87', 'purple': '#7050bf', 'amber': '#a86b19'}
BASE = 'https://github.com/vllm-ascend-workspace/'
WORKSPACE_SHA = '8d20cba36e3284ca307edfc5f7c53d045b12cad6'
PINS = {
    'workspace': (WORKSPACE_SHA, 'source snapshot'),
    'remote-dev': ('89d197ef13bcae46f7bea809c22bbb058c4edfbf', '0.9.3'),
    'vaws-coordinator': ('1b1ad5a558283307794801e778330c03b1c52cc2', '0.5.0.dev5'),
    'vaws-knowledge': ('8a5ef8abad99011c16a309133c4fb82b03c9cfbe', '0.7.5'),
    'vaws-top': ('v0.1.6', '0.1.6'),
    'vaws-diagnostics': ('96fcdfaa0f25fa59f12e948eb4e17ead775f3287', '0.2.1'),
}


def source(owner, path):
    repo = 'vllm-ascend-workspace' if owner == 'workspace' else owner
    return f'{BASE}{repo}/blob/{PINS[owner][0]}/{path}'


def units(s):
    return sum(1 if unicodedata.east_asian_width(c) in 'WF' else .57 for c in s)


def wrap(s, width, size):
    result, line = [], ''
    for ch in s:
        if ch == '\n':
            result.append(line); line = ''; continue
        if units(line + ch) * size > width and line:
            result.append(line); line = ch
        else:
            line += ch
    result.append(line)
    return result


class Drawing:
    def __init__(self, slug, number, title, subtitle, owner='workspace', color=BLUE):
        self.slug, self.number, self.title, self.subtitle = slug, number, title, subtitle
        self.owner, self.color, self.items, self.counter = owner, color, [], 0
        self.items.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000" role="img" aria-labelledby="title desc">
<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(subtitle)}。按 2026-09-14 锁定实现整理，具体职责、来源和支持边界见配套说明。</desc>
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f8fbff"/><stop offset="1" stop-color="#e6f1fa"/></linearGradient><linearGradient id="band" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#e6effb"/><stop offset="1" stop-color="#f0f6fc"/></linearGradient><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#7197c4"/></marker></defs>
<style>text{{font-family:'Microsoft YaHei','Segoe UI','Noto Sans CJK SC',sans-serif}} .label{{fill:{MUTED}}} a{{cursor:pointer}}</style>''')
        self.rect(0, 0, W, H, 'url(#bg)', radius=0)
        self.rect(64, 46, 7, 54, color, radius=3)
        self.text(88, 44, 'VAWS  /  ARCHITECTURE ATLAS', 13, MUTED, 600, spacing=2)
        self.text(88, 86, title, 35, INK, 700)
        self.text(88, 122, subtitle, 18, MUTED)
        self.text(1536, 85, f'{number:02d}', 42, '#b7cce5', 600, anchor='end')

    def rect(self, x, y, w, h, fill='white', stroke=None, radius=14, extra=''):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" {f"stroke={chr(34)}{stroke}{chr(34)}" if stroke else ""} {extra}/>')

    def text(self, x, y, value, size=20, fill=INK, weight=400, anchor='start', spacing=0, bounds=None):
        attr = f' data-bounds="{",".join(map(str,bounds))}"' if bounds else ''
        self.items.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" letter-spacing="{spacing}"{attr}>{html.escape(str(value))}</text>')

    def lines(self, x, y, values, size=18, color=MUTED, step=28, width=None, bounds=None, weight=400):
        if isinstance(values, str): values = [values]
        for value in values:
            for line in (wrap(value, width, size) if width else [value]):
                self.text(x, y, line, size, color, weight, bounds=bounds)
                y += step
        return y

    def card(self, x, y, w, h, title, body=(), color=None, fill='white', title_size=22, link=None):
        color = color or self.color
        if link: self.items.append(f'<a href="{html.escape(link, quote=True)}" target="_blank">')
        self.rect(x,y,w,h,fill, '#dbe6f2',12)
        self.rect(x+18,y+21,4,22,color,radius=2)
        bounds = (x+14,y+7,w-28,h-14)
        compact = h < 80
        self.text(x+32,y+(31 if compact else 39),title,min(title_size,20) if compact else title_size,INK,650,bounds=bounds)
        self.lines(x+22,y+(54 if compact else 67),body,16 if compact else 18,MUTED,23 if compact else 25,w-44,bounds)
        if link: self.items.append('</a>')

    def band(self, label, y, h, fill='url(#band)', x=204, width=1332):
        self.rect(x,y,width,h,fill,radius=17)
        ls=label.split('\n')
        for i,line in enumerate(ls):
            self.text(66,y+h/2+(i-(len(ls)-1)/2)*29+7,line,21,INK,650)

    def row(self, label, y, h, cards, color=None):
        self.band(label,y,h)
        n=len(cards); gap=14; x=220; cw=(1300-gap*(n-1))/n
        for i,c in enumerate(cards):
            title,body=c[0],c[1]
            self.card(x+i*(cw+gap),y+14,cw,h-28,title,body,color=color,title_size=21 if n<5 else 20)

    def arrow(self,x1,y1,x2,y2,label=None):
        self.items.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="#7197c4" stroke-width="2" marker-end="url(#arrow)"/>')
        if label:
            cx=(x1+x2)/2;cy=(y1+y2)/2
            self.rect(cx-units(label)*7-8,cy-13,units(label)*14+16,25,'#f4f8fd',radius=5)
            self.text(cx,cy+5,label,14,MUTED,anchor='middle')

    def features(self, items, note=None):
        self.rect(64,838,1472,108,'#ffffff', '#dbe6f2',16)
        cw=368
        for i,(title,body) in enumerate(items):
            x=86+i*cw
            if i:self.rect(x-19,858,1,68,'#e1eaf4',radius=0)
            self.text(x,868,title,20,self.color,650)
            self.lines(x,897,body,16,MUTED,23,cw-46,bounds=(x-3,847,cw-40,95))
        if note:self.text(64,814,note,16,MUTED)

    def save(self):
        ref,version=PINS[self.owner]
        self.text(64,979,'VAWS · 当前实现视图 · 2026-09-14',13,MUTED)
        self.text(1536,979,f'{self.owner}  {version}  /  {ref[:8]}',13,MUTED,anchor='end')
        self.items.append('</svg>')
        (ROOT/'svg'/f'{self.slug}.svg').write_text('\n'.join(self.items),encoding='utf-8')


pages=[]


def register(d, pitch, features, route, boundary, refs):
    d.save()
    pages.append(dict(slug=d.slug,number=d.number,title=d.title,subtitle=d.subtitle,owner=d.owner,
                      pitch=pitch,features=features,route=route,boundary=boundary,
                      sources=[{'title':title,'url':source(owner,path)} for owner,path,title in refs]))


d=Drawing('00-overview',0,'VAWS 总体架构','面向 Agent 的 vLLM / Ascend 开发工作区：从用户目标到可检查的代码与实验结果')
d.band('使用场景',160,60)
for i,t in enumerate(['代码理解与修改','服务部署与验证','性能与显存分析','图与分布式排障','Triton 算子开发']):
    d.text(234+i*260,198,t,21,INK,600)
d.row('Agent 入口',234,88,[(x,[]) for x in ['Codex','Cursor','Claude Code','Grok','Kimi Code']])
d.band('项目能力',338,198,width=942)
d.text(226,371,'workspace · 项目资料、客户端接线与业务 Skills',22,BLUE,650)
for i,(t,b) in enumerate([
    ('客户端接线',['原生 Hooks / MCP','配置与恢复复用']),
    ('源码与环境',['固定源码与依赖','独立多仓编辑目录']),
    ('业务 Skills',['18 个领域技能','按需提供方法与入口']),
    ('项目资料',['开发约定与配方','运行合同与验证证据'])]):
    d.card(220+i*230,388,216,132,t,b,title_size=20)
d.band('远端执行',550,148,width=942)
d.card(220,566,447,116,'remote-dev · 显式远端操作',['文件 / Shell / 作业 / 产物','保留指定容器、代码和启动命令'],color=COLORS['teal'])
d.card(681,566,449,116,'coordinator · 受管执行',['固定输入 · 准备与缓存复用','设备 / 端口分配 · 监督与回收'])
d.rect(1160,338,178,360,'white','#dbe6f2',17)
d.rect(1178,360,4,24,COLORS['purple'],radius=2)
d.text(1192,379,'知识参考',23,INK,650)
d.text(1178,413,'vaws-knowledge',16,COLORS['purple'],600)
d.lines(1180,465,['按需检索','原文与出处','Markdown 留存','本地 CPU 索引'],18,MUTED,42)
d.text(1180,673,'经验供 Agent 判断',15,COLORS['purple'])
d.rect(1352,338,184,170,'white','#dbe6f2',17)
d.text(1372,377,'集群观察',23,INK,650)
d.text(1372,411,'vaws-top',19,COLORS['teal'],650)
d.lines(1372,449,['设备与主机状态','历史趋势与看板'],17,MUTED,28)
d.rect(1352,522,184,176,'white','#dbe6f2',17)
d.text(1372,560,'统一诊断',23,INK,650)
d.text(1372,593,'vaws-diagnostics',16,COLORS['amber'],650)
d.lines(1372,630,['日志 · 分段耗时','脱敏问题与诊断'],17,MUTED,28)
d.band('运行基座',714,88)
d.text(232,751,'vLLM  ·  vLLM-Ascend  ·  PyTorch / torch_npu  ·  CANN',27,INK,650)
d.text(232,781,'业务代码与依赖运行在所选环境中；组件按职责组合。',17,MUTED)
d.band('基础资源',818,112)
for i,(t,b) in enumerate([
    ('本地客户端',['Windows / macOS / Linux']),('远端运行环境',['Linux 主机 / Docker 容器']),
    ('计算资源',['Ascend NPU / CPU']),('可复用成果',['Git 源码 / 权重 / 编译缓存'])]):
    d.card(220+i*328,832,314,84,t,b,title_size=20)
d.text(64,955,'阅读方式：层级表示职责范围。原生本地操作、显式远端操作、受管执行是按需选择的独立路径。',15,MUTED)
register(d,'把环境、资源和执行细节交给明确的组件，让 Agent 围绕真实开发目标工作。',
    ['用户表达目标，Agent 选择工具、解释结果。','项目层提供资料、业务方法与客户端接线。','显式远端和受管执行使用不同入口。','知识、监控和诊断提供参考与证据。'],
    '本地文件与 Git → 原生工具；指定 host/container/cwd/命令 → remote-dev；需要环境准备、设备与执行监督 → coordinator。',
    '图中的能力不表示所有客户端、设备和业务输入组合已经完成正式验收；分层位置也不表示每个任务必须逐层经过。',
    [('workspace','docs/target-state.md','总体运行合同'),('workspace','docs/diagnostics-system.md','跨组件诊断合同'),('workspace','README.md','项目入口与 18 个业务 Skills')])

d=Drawing('01-key-features',1,'VAWS 关键特性','以完成真实任务的总成本为尺度：减少重复准备、手工编排与故障定位成本')
feature_data=[
    ('01','按需介入','轻量任务直接开始',['本地工具直接使用','明确远端直接接入','受管能力按需调用'],BLUE),
    ('02','输入可追溯','知道实际运行了什么',['Git 提交与未提交修改快照','固定依赖与环境身份','结果保留版本与来源'],BLUE),
    ('03','有效成果复用','减少重复准备与编译',['复用兼容环境和持久容器','按输入与 ABI 复用编译产物','已有权重沿用明确路径'],COLORS['teal']),
    ('04','资源与执行受管','让资源和生命周期可检查',['设备与端口队列 / 租约','等待、停止、日志与状态','确认进程结束和资源释放'],BLUE),
    ('05','经验随用随取','查询、读原文、留存 Markdown',['关键词与向量检索结合','保留条件、出处与不确定性','维护独立于普通开发任务'],COLORS['purple']),
    ('06','问题有迹可循','看见耗时、失败与运行状态',['统一结构化日志与分段计时','主机 / NPU 观察与历史趋势','启用协作后提供脱敏问题诊断'],COLORS['amber']),
]
for i,(num,t,pitch,lines,color) in enumerate(feature_data):
    x=64+(i%3)*496;y=180+(i//3)*326
    d.rect(x,y,480,306,'white','#dbe6f2',20)
    d.rect(x+24,y+25,40,35,color,radius=9);d.text(x+44,y+49,num,17,'white',650,anchor='middle')
    d.text(x+82,y+53,t,27,INK,700)
    d.text(x+25,y+104,pitch,22,color,600)
    for j,line in enumerate(lines):
        d.rect(x+26,y+140+j*42,5,5,color,radius=2)
        d.text(x+43,y+148+j*42,line,19,MUTED)
d.rect(64,858,1472,82,'#e0ebfa',radius=17)
d.text(800,891,'工具处理边界明确的操作与记录；Agent 保留研究方法、结果解释和适用性判断。',23,INK,600,anchor='middle')
d.text(800,922,'知识供参考 · 观察供判断 · 资源分配由执行组件负责',18,MUTED,anchor='middle')
register(d,'六项特性对应开发过程中的实际成本，不给普通任务增加额外登记流程。',
    [f'{t}：{pitch}。' for _,t,pitch,_,_ in feature_data],
    '按需选能力 → 固定必要输入 → 复用有效环境 → 完成业务工作 → 检查结果与资源状态。',
    '特性描述的是已实现机制，不构成任意任务都更快、任意业务都正确或所有平台组合均已验收的保证。',
    [('workspace','docs/design-principles.md','九条设计原则'),('workspace','docs/coordinator-consumption.md','执行与复用行为'),('workspace','docs/knowledge-maintenance.md','知识参考与独立维护')])

d=Drawing('02-workspace',2,'workspace · 项目与客户端层','把源码、依赖、业务方法与原生 Agent 客户端接到一起')
d.row('原生入口',172,90,[(x,[]) for x in ['Codex','Cursor','Claude Code','Grok','Kimi Code']])
d.row('指引与接线',278,134,[('项目指引与业务 Skills',['AGENTS / 客户端投影','18 个按需业务入口']),('原生 Hooks 与 MCP',['关联当前原生任务','将调用路由到所选组件']),('一次性初始化',['本地依赖与知识准备','客户端配置与协作选择'])])
d.row('工作区准备',428,134,[('固定本地依赖',['uv.lock / 不可变环境','运行与知识依赖分别固定']),('独立多仓目录',['workspace / vllm / Ascend','保留任务实际源码与修改']),('源码选择与恢复',['sources.lock / Git 来源','同一任务恢复沿用原选择'])])
d.row('能力路由',578,114,[('原生工具',['本地文件 / Shell / Git']),('remote-dev',['显式远端与已有容器']),('coordinator',['资源与受管执行']),('knowledge',['可选查询 / 阅读 / 留存'])])
d.row('保留的事实',708,92,[('任务与环境关联',[]),('源码、配置与准备结果',[]),('组件结果与验证证据',[])])
d.features([('原生客户端优先',['沿用日常交互入口']),('准备一次，恢复复用',['任务保持原有来源与环境']),('业务方法按需提供',['技能帮助选择和使用能力']),('项目资料集中维护',['组件通过独立包交付'])])
register(d,'workspace 是项目材料与消费层，负责把各项能力接到开发任务上。',
    ['一次配置已安装客户端；原生信任与客户端能力仍按实际支持范围处理。','普通本地 review、明确 endpoint 的远端操作可直接进行。','需要独立编辑或受管准备时固定源码、依赖和实际目录。','18 个业务 Skills 覆盖服务、性能、正确性、排障、profiling 和算子工作。'],
    '用户目标 → 项目指引 / 业务 Skill → 必要的本地准备 → 原生工具或所选组件 → 代码与结果。',
    '原生界面目录、Agent 实际编辑目录和任务身份是不同事实；初始化或 Hook 成功不能推断界面已自动切换。',
    [('workspace','docs/native-workspace-isolation.md','原生目录与路由'),('workspace','docs/source-workspace.md','源码与独立多仓合同'),('workspace','.agents/lib/vaws_mcp_runtime.py','MCP 后端选择实现'),('workspace','.agents/lib/vaws_onboarding.py','初始化实现')])

d=Drawing('03-remote-dev',3,'remote-dev · 远端开发底座','让文件、命令、作业和产物在明确的远端端点上工作','remote-dev',COLORS['teal'])
d.row('调用入口',172,94,[('MCP 工具',['原生操作的远端对应入口']),('命令行 CLI',['remote-dev 命令']),('Python API',['供 coordinator 等调用'])],color=COLORS['teal'])
d.row('操作能力',282,134,[('文件与搜索',['读写 / 精确编辑 / 补丁','目录 / glob / grep']),('Shell 与作业',['Bash / PTY / stdin','状态 / 日志 / 停止']),('产物与端点事实',['manifest / push / pull','probe / context snapshot'])],color=COLORS['teal'])
d.row('公共底座',432,134,[('端点与容器身份',['host / port / user / cwd','容器解析并固定为完整 ID']),('SSH 与 stdio RPC',['复用连接 / 并发请求','取消与明确的结果边界']),('操作一致性',['可选读账本 / 写入锁','校验后原子替换产物'])],color=COLORS['teal'])
d.arrow(860,567,860,603,'SSH / Docker exec')
d.row('远端 Linux',610,174,[('目标主机或已有容器',['执行指定 Bash 与解释器','保留原代码、环境及启动脚本']),('远端 Worker 与作业监督',['RPC / 二进制传输 / 进程族','记录输出与作业终止事实'])],color=COLORS['teal'])
d.features([('端点直接可用',['调用不需要 VAWS 任务身份']),('操作语义熟悉',['远端读写、命令与搜索']),('已有容器可保留',['固定容器代次与原始命令']),('结果与产物可核查',['哈希、完整输出与作业记录'])], '调用链：Agent 或组件 → remote-dev 操作 → 端点与传输 → 远端 Worker → 结果 / 产物。')
register(d,'remote-dev 解决明确端点上的远程 I/O、命令执行与通用作业监督。',
    ['同一套公开操作提供 MCP、CLI 和 Python 使用方式。','支持远端文件、检索、补丁、Bash、PTY、输入与日志。','容器名解析为完整 ID，后续作业绑定同一代容器。','复用 SSH stdio RPC，保留并发、取消和传输诊断。','产物传输校验哈希后进行原子替换。'],
    'host / container / cwd + 操作 → 端点固定 → SSH/RPC → 目标主机或 Docker exec → 文件、作业或产物结果。',
    'remote-dev 不分配 NPU，也不推断 VAWS 任务身份。停止作业只处理已识别进程族；任意命令自身的副作用仍由该命令决定。',
    [('remote-dev','README.md','公开入口'),('remote-dev','DESIGN.md','组件设计'),('remote-dev','remote_dev/core/rpc_transport.py','RPC 连接实现'),('remote-dev','remote_dev/core/container_endpoint.py','容器身份实现')])

d=Drawing('04-coordinator',4,'vaws-coordinator · 受管执行','本地用户服务管理远端准备、资源和生命周期；执行事实保留在各自所有者','vaws-coordinator')
d.row('调用入口',172,102,[('原生任务与上下文',['context_file / 原生关联']),('MCP / CLI / TaskClient',['run · execution · finish']),('服务与协作',['任务内服务引用 / 留言'])])
d.band('本地管理',292,286)
d.text(226,326,'本地 coordinator 服务 · 任务关联、固定输入与执行记录',22,BLUE,650)
for i,(t,b) in enumerate([
    ('任务关联',['原生身份与来源默认值','服务与执行归属']),('固定源码',['Git 提交与修改快照','每次提交的独立输入']),
    ('准备与复用',['镜像 / 环境 / ABI 检查','源码与编译产物缓存']),('执行监督',['排队 / 启动 / 状态','等待 / 停止 / 回收'])]):
    d.card(220+i*328,345,314,142,t,b)
d.text(226,543,'记录实际源码、环境、运行状态和释放结果；等待超时保留同一个执行引用。',19,MUTED)
d.arrow(870,579,870,622,'经 remote-dev 执行远端操作')
d.row('远端权威',632,156,[('宿主机资源队列',['设备 / 端口 / 租约与续约','已有占用检查 · 任务间留言']),('Ascend 容器与进程监督',['所选源码 / Python 环境 / 业务命令','进程族终止确认 · 端口与资源释放'])])
d.features([('固定输入再执行',['后续编辑不改已接收输入']),('按兼容条件复用',['容器、环境与 native 产物']),('等待与控制保持独立',['长等待期间仍可观察和停止']),('回收结果可检查',['终止状态与释放事实分别保留'])], '资源位置：本地服务编排；宿主机队列授予设备；所选容器运行设备代码。')
register(d,'coordinator 把一次受管命令的来源、环境、资源和生命周期连成可检查的记录。',
    ['任务由真实原生关联确定，恢复保留已有身份与选择。','提交时固定 Git 输入与修改，支持多个来源和显式空来源。','准备或复用兼容容器、依赖、构建和源码产物。','宿主机队列负责 NPU 与端口授予，监督器管理进程族。','支持任务内服务、多个角色/主机约束、状态、等待、日志、停止和证据。','任务间留言利用既有主机队列与正常工具调用收取。'],
    '命令 + 来源 / 环境 / 资源 / 拓扑 → 固定输入 → 准备与资源授予 → 容器执行 → 确认进程终止与资源释放。',
    '这是本地用户 coordinator，不能画成托管多租户控制中心。业务 readiness、业务正确性、进程状态与资源释放分别判断；留言不会执行命令或主动唤醒原生客户端。',
    [('vaws-coordinator','README.md','公开执行合同'),('vaws-coordinator','vaws_coordinator/task_client.py','任务 API'),('vaws-coordinator','vaws_coordinator/service.py','本地服务'),('vaws-coordinator','vaws_coordinator/host_queue.py','宿主机资源 API'),('workspace','docs/coordinator-consumption.md','workspace 消费合同')])

d=Drawing('05-knowledge',5,'vaws-knowledge · 知识参考','普通 Markdown 保留经验与来源，本地 CPU 检索帮助 Agent 找到可用线索','vaws-knowledge',COLORS['purple'])
d.row('普通任务入口',172,120,[('knowledge_query',['检索相关笔记与出处']),('knowledge_explain',['阅读原文、条件和上下文']),('knowledge_capture',['标题 + Markdown 留存'])],color=COLORS['purple'])
d.row('检索与阅读',308,142,[('本地目录与词法检索',['catalog / 关键词 / 别名','保留原始内容和来源关联']),('向量检索',['OpenViking / FastEmbed','本地 CPU 文本 embedding']),('结果组织',['词法与向量结果融合','有界片段 / 引用 / 原文'])],color=COLORS['purple'])
d.row('内容来源',466,132,[('项目资料',['可配置 Markdown 挂载']),('本地留存',['任务笔记 / 私有候选']),('共享知识',['随包资料 / 已发布语料']),('独立资料流',['intake / feed 输入'])],color=COLORS['purple'])
d.row('独立维护',614,174,[('资料与代码关联',['静态 Python / C++ 代码映射','目录 / 别名 / 关系 / 检索评估']),('整理与分发',['独立 Agent / 可选 Grok 维护','版本化 Markdown / 索引维护']),('公开贡献与语料仓',['按协作选择生成脱敏副本','人工审核合并 / 共享 release'])],color=COLORS['purple'])
d.features([('三个日常入口',['查询、原文阅读、Markdown']),('经验保持上下文',['来源、条件和不确定性']),('本地 CPU 检索',['原文保留，索引可重建']),('维护与开发分开',['intake / feed 独立安装'])], '原文、代码映射和知识结论均为参考；Agent 按当前现象判断是否适用。')
register(d,'知识组件帮助找到与任务相关的经验，同时保留原文、出处和使用条件。',
    ['普通任务只需三个可选入口，不要求固定笔记模板或额外收尾。','Markdown/Git 保存内容，CPU embedding 与 OpenViking 提供可重建索引。','支持项目挂载、本地候选、包内材料及共享版本。','词法与向量检索结合，提供有界片段和原文解释。','静态代码映射、整理、检索评估和资料导入属于独立维护。','knowledge-intake、knowledge-feed 和 vaws-knowledge-corpus 是配套导入、传输和语料组件，非日常 MCP 的必经步骤。'],
    '问题 → 词法与向量检索 → 带来源片段 → explain 阅读原文 → Agent 判断；capture 写入本地 Markdown，维护在独立路径执行。',
    '初始化或显式 setup 负责依赖与知识准备；当前任务 Hook/MCP 消费已安装环境，缺失时不自行安装。关闭社区协作仍保留中央知识读取和本地日志。公开语料审核合并由人负责。',
    [('vaws-knowledge','README.md','知识组件合同'),('vaws-knowledge','vaws_knowledge/retrieval.py','检索组织'),('vaws-knowledge','vaws_knowledge/server/query.py','查询入口'),('workspace','docs/knowledge-maintenance.md','独立 intake / feed / corpus'),('workspace','.agents/lib/vaws_onboarding.py','当前初始化准备边界')])

d=Drawing('06-top',6,'vaws-top · 集群观察','本机看板与 Agent 查询共享带时间戳的主机、NPU 和历史观察','vaws-top',COLORS['teal'])
d.row('读取入口',172,110,[('浏览器看板',['主机 / NPU / 历史趋势']),('Agent CLI / MCP',['缓存或实时观察查询']),('HTTP API',['同源 API / 健康状态'])],color=COLORS['teal'])
d.row('本机服务',298,134,[('serve / API / Agent View',['单进程 HTTP 与静态前端','观察时间与数据新鲜度']),('AdaptiveScheduler',['按观看状态调整采集节奏','并发有界 / 慢周期自然降频']),('当前快照与历史',['内存中的最新观察','SQLite 历史与保留策略'])],color=COLORS['teal'])
d.row('主机访问',448,134,[('Inventory',['显式机器清单与标签','已配置的主机池来源']),('DeviceAdapter / SshAccess',['独立 SSH 采集器','专用密钥与 known_hosts']),('Probe / Parser',['快速设备与系统指标','较低频的容器和挂载信息'])],color=COLORS['teal'])
d.arrow(860,583,860,622,'SSH 无代理采集')
d.row('宿主机数据',632,156,[('Ascend NPU',['npu-smi / AICore / HBM','温度 / 功耗 / 设备进程']),('CPU 与系统内存',['/proc 计数 / 系统负载','主机内存使用']),('磁盘与 Docker',['磁盘 / 文件系统 / 挂载','容器状态与进程信息'])],color=COLORS['teal'])
d.features([('一个本地观察入口',['看板与 Agent 共享数据']),('刷新频率随需求变化',['观看期更快，空闲期巡检']),('历史趋势可回看',['聚合趋势与热力图']),('每次观察有时间',['空闲观察不等于设备预留'])], 'vaws-top 自己采集主机状态；设备授予仍由 coordinator 的宿主机队列负责。')
register(d,'vaws-top 回答主机和 NPU 当前看起来如何，以及过去一段时间发生了什么。',
    ['本机单进程提供静态看板、HTTP API、CLI 与 MCP 查询。','自适应调度按观看需求改变频率，采集并发与历史写入有界。','独立 SSH 采集器读取 npu-smi、系统计数、磁盘和 Docker。','最新数据缓存在内存中，SQLite 保存历史。','观察结果包含 observed_at、age_seconds 和 allocation_authority=false。','发布 wheel 自带前端构建产物，普通安装无需本机前端构建。'],
    '显式清单 → 调度器 → 独立 SSH 主机探测 → 内存快照 / SQLite → 看板、HTTP 或 Agent 查询。',
    '这是本机单用户、默认 loopback 的观察应用。它不读取或授予 coordinator 租约，观察到空闲不意味着资源已分配；不能画成 coordinator 的必经前置步骤。',
    [('vaws-top','docs/architecture.md','官方组件架构'),('vaws-top','vaws_top/scheduler.py','自适应调度器'),('vaws-top','vaws_top/device_adapter.py','主机访问组合'),('vaws-top','vaws_top/db.py','历史存储'),('workspace','docs/npu-fleet-monitor.md','workspace 启停接线')])

d=Drawing('07-diagnostics',7,'vaws-diagnostics · 诊断与反馈','各组件记录操作事实；独立后台服务处理脱敏问题与可选 Grok 诊断','vaws-diagnostics',COLORS['amber'])
d.row('事件来源',172,96,[(t,[]) for t in ['workspace','remote-dev','coordinator','knowledge','top']],color=COLORS['amber'])
d.row('共享诊断库',284,146,[('操作与阶段记录',['logger / operation / phase','错误因果与实际运行版本']),('上下文与输出捕获',['进程 / 线程 / RPC 关联','有界输出与原始失败保留']),('本地诊断材料',['各进程轮转 JSONL','按操作导出脱敏 bundle'])],color=COLORS['amber'])
d.band('独立后台',446,168)
for i,(t,b) in enumerate([
    ('事件读取与归并',['有界读取 / 失败指纹','重复事件聚合与保留']),('脱敏与待发队列',['字段白名单 / 泄露扫描','持久 outbox / 限流与重试']),('协作选择检查',['发送前读取当前选择','撤销、缺失或失效则停发'])]):
    d.card(220+i*438,461,424,136,t,b,color=COLORS['amber'])
d.arrow(860,615,860,655,'按配置与有效协作选择发布')
d.row('公共反馈',664,124,[('GitHub Issue',['脱敏证据 / 内容哈希 / 去重']),('独立 Grok 诊断',['事实 / 假设 / 缺失证据']),('维护者后续处理',['审查、修复和验证'])],color=COLORS['amber'])
d.features([('零运行时依赖的共享库',['所有组件使用统一格式']),('调用不用等待上报',['记录与后台发布解耦']),('本地保留原始失败',['日志故障不覆盖业务结果']),('公开内容受范围约束',['明确协作选择与字段脱敏'])], '箭头表示诊断材料的流向；Grok 回复不会自动修改代码、合并 PR、重启服务或改变任务状态。')
register(d,'诊断组件让慢操作和失败可定位，并在有效协作选择下把脱敏材料交给维护者。',
    ['共享包没有运行时依赖，组件在统一边界记录日志与耗时。','操作、阶段和运行版本可关联；诊断 ID 不赋予任务或资源权限。','每进程轮转 JSONL，日志、输出和导出材料均有大小边界。','独立 worker 负责归并、脱敏、持久队列、限流和 GitHub 对账。','发送前重新读取当前协作选择，正常调用不等待上报或模型。','Grok 只接收脱敏证据，提供有边界的诊断建议。'],
    '组件事件 → 本地 JSONL → 独立事件读取 / 脱敏 / 队列 → 当前协作选择检查 → GitHub Issue → 可选 Grok 诊断 → 维护者处理。',
    '本地记录不依赖上报授权。公开问题和 Grok 诊断按配置与有效选择运行；不自动修代码、合并、部署或改变资源状态。未知提交结果先对账，不作 exactly-once 保证。',
    [('vaws-diagnostics','README.md','共享诊断包合同'),('vaws-diagnostics','vaws_diagnostics/logging.py','操作与阶段日志'),('vaws-diagnostics','vaws_diagnostics/reporter.py','发布 worker'),('vaws-diagnostics','vaws_diagnostics/outbox.py','持久待发队列'),('workspace','docs/diagnostics-system.md','跨组件诊断架构')])


def export_documents():
    (ROOT/'atlas.json').write_text(json.dumps({'date':'2026-09-14','workspace_revision':WORKSPACE_SHA,'pins':PINS,'pages':pages},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    md=['# VAWS 架构与关键特性图册','',
        '这套图面向首次了解 VAWS 的开发者。先看总体架构与关键特性，再按任务需要阅读组件图。',
        '', '**范围：**下述基线中已实现的职责和机制；图示不是性能、业务正确性或全平台支持承诺。当前运行合同见 [target-state.md](../target-state.md)。',
        '', '**基线：**2026-09-14，workspace `'+WORKSPACE_SHA+'` 及其锁定组件。独立 runtime 包与 workspace 消费层分开表达。',
        '', '## 图册目录','', '| 图 | 内容 | 图片 | 可编辑矢量 |','|---|---|---|---|']
    for p in pages:
        md.append(f'| {p["number"]:02d} | {p["title"]} | [PNG](png/{p["slug"]}.png) | [SVG](svg/{p["slug"]}.svg) |')
    md+=['','## 一次任务怎样选择能力','',
         '- **本地代码与 Git：**使用原生工具。',
         '- **指定远端或已有容器：**remote-dev 执行明确端点上的原始操作。',
         '- **环境准备、NPU 资源和受管命令：**coordinator 固定输入、准备环境并监督执行。',
         '- **需要经验或可见性：**按需查询 knowledge 或 top；diagnostics 在组件边界自动记录。','']
    for p in pages:
        md += [f'## {p["number"]:02d} · {p["title"]}','',p['pitch'],'',f'![{p["title"]}](svg/{p["slug"]}.svg)','',
               '**关键特性**','',*['- '+f for f in p['features']],'','**主要路径**：'+p['route'],'','**职责边界**：'+p['boundary'],'',
               '**实现来源**','',*['- ['+s['title']+']('+s['url']+')' for s in p['sources']],'']
    md+=['## 组件版本与图示约定','','| 组件 | 版本 | 固定来源 |','|---|---|---|']
    for owner,(ref,version) in PINS.items():md.append(f'| {owner} | {version} | `{ref}` |')
    md+=['','- 总览中的横向层级是能力与职责分层，不是强制调用顺序。',
         '- coordinator 依赖 remote-dev；vaws-top 使用自己的 SSH 采集器。',
         '- workspace 和各 runtime 组件使用共享 diagnostics；诊断记录不替代执行状态权威。',
         '- knowledge-intake、knowledge-feed 与语料仓列为知识配套能力，不增加普通任务的 MCP 操作数。',
         '- 首版新手材料以用户目标和组件责任为主；具体参数、源码路径与验收限制保留在来源文档中。',
         '- SVG 文本与布局可编辑；PNG 为同一 SVG 的 2× 导出，不使用生成式图片中的文字。',
         '', '## 维护图稿','',
         '[build_atlas.py](build_atlas.py) 是本套图与说明的共同内容源，使用 Python 3.11+ 标准库。修改文案或结构后，在仓库根目录运行以下命令以更新 SVG、README、网页索引和 atlas.json。',
         '', '```text', 'python docs/architecture/build_atlas.py', '```',
         '', '[render_atlas.cjs](render_atlas.cjs) 使用 Playwright、sharp 和 Chromium/Edge 将 SVG 导出 PNG，并检查文字边界、图片加载和桌面/移动端横向溢出。依赖仅用于维护图稿。已有这些工具时，在仓库根目录运行；浏览器参数省略时使用 Playwright 的 Chromium。',
         '', '```text', 'node docs/architecture/render_atlas.cjs <node_modules-directory> [browser-executable]', '```',
         '', '完整图册可在本地打开 [index.html](index.html) 浏览；图片和内容索引见 [atlas.json](atlas.json)。来源固定在各图的实现链接中。渲染检查记录写入本地 evidence 目录，预览拼图写入 contact-sheet.png，均由本目录的 .gitignore 排除。','']
    (ROOT/'README.md').write_text('\n'.join(md),encoding='utf-8')
    toc=''.join(f'<a href="#{p["slug"]}"><span>{p["number"]:02d}</span>{html.escape(p["title"])}</a>' for p in pages)
    sections=[]
    for p in pages:
        sources=' · '.join(f'<a href="{s["url"]}" target="_blank" rel="noreferrer">{html.escape(s["title"])}</a>' for s in p['sources'])
        lis=''.join('<li>'+html.escape(f)+'</li>' for f in p['features'])
        sections.append(f'''<section id="{p['slug']}"><div class="section-title"><div><span class="eyebrow">{p['number']:02d} / VAWS</span><h2>{html.escape(p['title'])}</h2></div><div class="exports"><a href="svg/{p['slug']}.svg" download>SVG</a><a href="png/{p['slug']}.png" download>PNG</a></div></div><p class="pitch">{html.escape(p['pitch'])}</p><a class="diagram" href="svg/{p['slug']}.svg" target="_blank"><img src="svg/{p['slug']}.svg" width="1600" height="1000" alt="{html.escape(p['title'])}"/></a><div class="detail"><div><h3>关键特性</h3><ul>{lis}</ul></div><div><h3>主要路径</h3><p>{html.escape(p['route'])}</p><h3>职责边界</h3><p>{html.escape(p['boundary'])}</p></div></div><p class="sources">实现来源：{sources}</p></section>''')
    page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>VAWS 架构与关键特性图册</title><style>
:root{color-scheme:light}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:25px}body{margin:0;background:#f3f7fc;color:#142841;font-family:'Microsoft YaHei','Segoe UI',sans-serif}a{color:#2365d8;text-decoration:none}a:hover{text-decoration:underline}aside{position:fixed;inset:0 auto 0 0;width:266px;background:#fff;border-right:1px solid #dfe8f2;padding:38px 23px;overflow:auto}.brand{font-size:26px;font-weight:750;letter-spacing:2px}.aside-sub{color:#71859b;font-size:13px;margin:8px 0 30px}nav a{display:block;padding:13px 10px;border-radius:8px;color:#29415f;font-size:14px;line-height:1.6}nav a:hover{background:#edf4fc;text-decoration:none}nav span{display:inline-block;width:27px;color:#7994b5;font-size:12px}main{margin-left:266px;padding:40px 44px 80px;max-width:1850px}header{padding:5px 0 32px}header h1{font-size:35px;margin:7px 0 15px;letter-spacing:.5px}header p{color:#536c89;max-width:900px;line-height:1.9;margin:8px 0}.eyebrow{font-size:12px;color:#527ba9;letter-spacing:2px}.meta{font-size:13px;color:#7890a8}section{background:#fff;border:1px solid #dee8f4;border-radius:19px;padding:27px;margin:0 0 28px;scroll-margin-top:28px}.section-title{display:flex;justify-content:space-between;gap:20px;align-items:center}h2{font-size:25px;margin:9px 0}h3{font-size:16px;margin:0 0 12px}.pitch{color:#58708a;line-height:1.8;margin:7px 0 21px}.exports{display:flex;gap:9px}.exports a{border:1px solid #cfdded;border-radius:7px;font-size:13px;padding:8px 13px}.diagram{display:block;overflow:hidden;border-radius:12px;border:1px solid #e1eaf4;background:#eef5fd}.diagram img{display:block;width:100%;height:auto}.detail{display:grid;grid-template-columns:1fr 1fr;gap:45px;padding:27px 3px 4px}.detail p,li{font-size:14px;line-height:1.9;color:#4c6580}.detail ul{padding-left:20px;margin:0}.detail h3:not(:first-child){margin-top:19px}.sources{font-size:12px;line-height:2;margin:20px 0 0;padding-top:15px;border-top:1px solid #e8eef5;color:#6a809a}footer{font-size:13px;color:#7287a0;line-height:1.8}@media(max-width:1000px){aside{position:static;width:auto;padding:20px}nav{display:flex;overflow:auto}nav a{min-width:max-content}.aside-sub{margin-bottom:12px}main{margin-left:0;padding:25px 18px}.detail{gap:20px}}@media(max-width:650px){.detail{grid-template-columns:1fr}section{padding:16px}.section-title{align-items:flex-start}h2{font-size:20px}header h1{font-size:27px}.exports{flex-direction:column}}@media print{aside,header,.exports{display:none}main{margin:0;padding:0}section{break-before:page;border:0;padding:0}.diagram{border:0}.detail{font-size:12px}a{color:inherit}}
</style></head><body><aside><div class="brand">VAWS</div><div class="aside-sub">架构与关键特性图册</div><nav>TOC</nav><p class="aside-sub">当前实现快照<br>2026-09-14<br><br><a href="README.md">完整 Markdown 说明</a></p></aside><main><header><span class="eyebrow">FROM USER GOAL TO INSPECTABLE RESULTS</span><h1>看懂 VAWS 怎样工作</h1><p>先看平台分层和关键特性，再查看各组件的入口、内部结构、协作路径与职责边界。各图可以独立用于 README、技术介绍或分享材料。</p><p class="meta">基于 workspace 8d20cba 及锁定组件 · 8 张图 · SVG / PNG · 图片可点击放大</p></header>SECTIONS<footer>这些图说明当前机制与职责，不代表全部客户端、平台和业务输入已完成验收。实际行为以固定来源、组件公开 API 与对应验证证据为准。</footer></main></body></html>'''
    (ROOT/'index.html').write_text(page.replace('TOC',toc).replace('SECTIONS',''.join(sections)),encoding='utf-8')


export_documents()
print(json.dumps({'diagrams':len(pages),'output':str(ROOT)},ensure_ascii=False))
