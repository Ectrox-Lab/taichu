# 华夏文明谱 · Huaxia Civilizational Atlas

**A Civilizational Operating Framework for AI Governance, Personas, and Deliberation**

---

## 项目定位

华夏文明谱是一套**文明级治理操作系统**，不是单一工具，而是：
- 多 Agent 分层治理框架
- 可审计的决策链机制  
- 人机协同的议政系统

**核心原则**: 治理权力分层、决策可追溯、分歧可裁决、错误可回滚。

---

## 架构层次

### Layer 1: 治理权力层（北斗七星 + 四象 + 神话补位）

**北斗七星（核心决策）**:
- **天枢** - 终局裁决者 (final_gate, adjudication)
- **天璇** - 风险门禁 (risk_assessment, veto)
- **天玑** - 策略规划 (strategy)
- **天权** - 执行编排 (orchestration)
- **玉衡** - 质量门禁 (quality_gate, veto)
- **开阳** - 实现审查 (implementation_review)
- **瑶光** - 归档管理 (archive)

**四象（审议制衡）**:
- **青龙** - 东方审议 (east_deliberation)
- **白虎** - 西方验证 (west_validation, red_team)
- **朱雀** - 南方叙事 (south_narrative)
- **玄武** - 北方安防 (north_security)

**神话补位（专项监督）**:
- **杨戬** - 真实性核验
- **包拯** - 独立审计
- **钟馗** - 威胁清除
- **诸葛亮** - 战略规划
- **哪吒** - 快速响应
- **鲁班** - 工程实现
- **西王母** - 资源分配
- **丰都大帝** - 终止归档

### Layer 2: 执行部门层

- **engineering** - 工程开发 (kaiyang/鲁班/哪吒)
- **audit** - 审计追责 (包拯/杨戬)
- **risk_control** - 风控门禁 (白虎/钟馗)
- **monitoring** - 监控预警 (玄武)
- **platform** - 平台架构 (天权)
- **archives** - 档案管理 (瑶光/丰都大帝)

### Layer 3: 工件证据层

每个 governance run 必须产出：
- `decision_log.md` - 决策链记录
- `quality_report.md` - 质量评估
- `artifact_index.md` - 交付物索引
- `risk_register.md` - 风险登记

---

## 核心机制

| 机制 | 功能 | 触发条件 |
|------|------|----------|
| **review** | 独立审查 | 所有提交 |
| **veto** | 单方面阻断 | 质量/风险/合规不达标 |
| **escalation** | 升级争议 | 多方分歧无法共识 |
| **adjudication** | 终局裁决 | escalation 后 |
| **rollback** | 纠错回滚 | 部署后发现缺陷 |
| **archive** | 归档封存 | run 终局后 |
| **termination** | 强制终止 | 系统性失败 |

---

## 验证状态

- ✅ **Phase 1**: 核心机制真实性验证完成
- ✅ **Phase 2B**: 真实外部输入验证完成
- ✅ **Phase 2C**: 连续 10 次稳定性验证完成
- ✅ **Production**: 2026-03-20 进入受控生产阶段

**生产状态**: 🟢 受控生产中（RUN-011 ~ RUN-100 冻结观察期）

---

## 与 AXI 的关系

**AXI** 是华夏文明谱生态中的**经济子系统**，负责：
- Agent 间价值交换
- 资源 token 化
- 激励机制

**华夏文明谱** 是母工程，AXI 是其子系统之一。所有子系统必须服从母工程的治理架构。

---

## 快速开始

### 启动 Governance Run

```bash
# 创建新 run
mkdir -p STABLE_RUN/RUN-$(date +%Y%m%d)-XXX

# 执行 governance 流程
# 1. engineering 提交
# 2. 开阳/天璇/玉衡 审查
# 3. 天枢 终局裁决
# 4. 瑶光/丰都大帝 归档
```

### 查看生产状态

```bash
cat STABLE_RUN/PRODUCTION_STATUS.md
cat STABLE_RUN/PRODUCTION_LEDGER.csv
```

---

## 项目层次

```
华夏文明谱 (母工程)
├── 天枢OS - 治理核心
├── 诸神议政系统 - 多 Agent 协调
├── 华夏文明录 - Persona/记忆管理
├── 华夏文明鉴 - 审计/质量系统
│
└── 子系统层
    ├── AXI - 经济系统
    ├── ZeroClaw - 执行引擎 (Rust + tmux + worktree)
    └── [其他专项系统]
```

---

## 文档索引

- **治理架构**: `taichu/constitution/mappings/ROLE_MAPPING.md`
- **生产批准**: `STABLE_RUN/PRODUCTION_APPROVAL.md`
- **生产红线**: `STABLE_RUN/PRODUCTION_GUARDRAILS.md`
- **操作手册**: `STABLE_RUN/PRODUCTION_RUNBOOK.md`
- **生产总表**: `STABLE_RUN/PRODUCTION_LEDGER.csv`

---

## 治理原则

> **正式19席是治理权力席位，不等同于部门岗位。**  
> 部门可以按功能拆分与重组，但主管权力、审批边界、veto权和终局责任  
> 仍固定归属于正式19席。

---

**状态**: 受控生产阶段（冻结观察期至 RUN-100）  
**下次审查**: 2026-06-20 或 100 次生产 run 后
