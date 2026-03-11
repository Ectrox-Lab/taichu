# Persona System v2 - Registry-Grounded Speech Generation

**目标**: 将人格调用从隐式模板改为显式上下文绑定

---

## 核心问题诊断

### 现状
- ✅ 人格库已结构化 (`seat_registry.yaml`, `culture_registry.yaml`)
- ✅ Runtime activation 已存在
- ❌ **发言生成仍是模板驱动** - 这是关键问题

### 当前模板化问题的具体表现
1. **核心 19 席**: 统一骨架发言 ("接受前提 / 无修正 / 要求更多信息")
2. **扩展人格**: 按名字映射固定 A/B/C/D/E 文本
3. **结果**: "像是被激活了"，但没有真正注入人格特征

---

## 解决方案

### 1. Persona Context Builder (显式化工件)

```python
# 每次发言前强制生成
persona_context = {
    "speaker_id": "00012",
    "dna_snapshot": {
        "identity": "...",
        "core_drives": [...],
        "decision_style": "...",
        "taboos": [...],
        "risk_bias": "conservative"
    },
    "meeting_binding": {
        "issue_type": "strategic_planning",
        "unresolved_points": [...]
    },
    "generation_constraints": {...},
    "audit": {...}  # 读取证明
}
```

**文件**: `persona_context.py`

### 2. 两阶段生成

#### Stage A: Persona Grounding
- 从 registry 抽取与当前议题相关的字段
- 生成本轮"人格约束"

#### Stage B: Structured Speech Synthesis
- 基于约束生成 A/B/C/D/E 五段
- 模板只保留结构，不承载内容

**文件**: `pipeline_implementation.py`

### 3. 审计字段 (读取证明)

```python
{
    "turn_id": "CORE-00012-R2",
    "registry_keys_used": ["risk_bias", "taboos", "core_drives"],
    "evidence_trace": [
        "Used risk_bias=conservative -> D_Demand asks for rollback gate",
        "Used taboos=no-handwave -> B_Correct rejects vague optimism"
    ],
    "template_divergence_score": 0.75  # 与模板的偏离度
}
```

---

## 验收指标

### A. Role Distinguishability Test
同一议题，打乱 speaker 名称，看能否从发言反推原角色

```python
# test_distinguishability.py
tester = RoleDistinguishabilityTester()
result = tester.test(
    issue="strategic_planning",
    speakers=["high_strategic", "high_governance", "high_execution"],
    generate_fn=your_generate_function
)
# Target: accuracy >= 80%
```

### B. Incrementality Test
比较发言与前序阶段总结，检测套话/模板重叠

```python
# test_incrementality.py
tester = IncrementalityTester()
result = tester.test(
    speech_content=...,
    unresolved_points=[...],
    prior_stage_summary=...,
    speaker_history=[...]
)
# Target: coverage +30%, overlap -40%
```

---

## 3×3 最小可复现实验

**文件**: `experiment_3x3.py`

### 实验设计
- **3 议题**: strategic_planning, disaster_recovery, technical_refactor
- **3 角色**: high_strategic, high_governance, high_execution
- **对照**: Baseline (模板) vs Variant (persona_context)

### 验收标准
| 指标 | Baseline | Variant (Target) | 状态 |
|------|----------|------------------|------|
| Role Distinguishability | ~50% | ≥ 80% | +30% |
| Unresolved Coverage | ~10% | ≥ 40% | +30% |
| Boilerplate Overlap | ~70% | ≤ 30% | -40% |

```python
from experiment_3x3 import MinimalReproducibilityExperiment

experiment = MinimalReproducibilityExperiment()
result = experiment.run(your_variant_pipeline)

if result.overall_passed:
    print("✅ ALL GATES PASS - Ready for deployment")
```

---

## 实施优先级

| 优先级 | 任务 | 文件 | 影响 |
|--------|------|------|------|
| **P0** | `generate_speech()` 重构 | `pipeline_implementation.py` | 修复模板化 |
| **P0** | 核心 19 席强制检查 | `CoreSeatAdapter` | 消除占位 |
| **P1** | PersonaContext 数据结构 | `persona_context.py` | 显式化工件 |
| **P1** | Grounding Engine | `PersonaGroundingEngine` | 议题相关性 |
| **P2** | 审计字段 | `PersonaAudit` | 可验证性 |
| **P2** | 验收脚本 | `test_*.py`, `experiment_3x3.py` | 回归测试 |

---

## 快速开始

### 1. 安装依赖
```bash
pip install pyyaml numpy scikit-learn
```

### 2. 运行测试演示
```bash
# 可辨识性测试
python test_distinguishability.py

# 增量性测试
python test_incrementality.py

# 3×3 实验
python experiment_3x3.py
```

### 3. 集成到现有系统

```python
from pipeline_implementation import PersonaSpeechPipeline, CoreSeatAdapter

# 创建管道
pipeline = PersonaSpeechPipeline()

# 核心席位适配器 (强制检查)
adapter = CoreSeatAdapter(pipeline)

# 生成发言
meeting_state = {
    "issue_type": "strategic_planning",
    "risk_level": "high",
    "unresolved_points": [...]
}

output = adapter.generate(
    seat_id="00012",
    meeting_state=meeting_state,
    stage=SpeechStage.B
)

# 验证读取
if output.audit.verify_reading():
    print(f"✅ Speech generated with persona context")
    print(f"   Divergence: {output.audit.template_divergence_score:.1%}")
else:
    print(f"❌ Reading verification failed")
```

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `PERSONA_CONTEXT_BUILDER.md` | 完整设计文档 |
| `persona_context.py` | 核心数据结构实现 |
| `pipeline_implementation.py` | 管道实现示例 |
| `test_distinguishability.py` | 可辨识性测试 |
| `test_incrementality.py` | 增量性测试 |
| `experiment_3x3.py` | 3×3 最小可复现实验 |
| `README.md` | 本文件 |

---

## 结论

> **人格 DNA 档案本体已够用；真正要补的是"发言前强制读取、绑定、审计"这一层。**

### 当前系统已证明
- ✅ Runtime activation 存在
- ✅ Registry read 存在
- ❌ Speech generation 仍是模板驱动

### 下一步最该做
1. 把 `generate_speech()` 改成 registry-grounded
2. 核心 19 席强制检查 registry 条目
3. 添加 PersonaContext 显式化工件
4. 跑通 3×3 实验验证改进

---

## 引用

```
Round 17.4: Verified Promote-Ready
PROMOTE ✅
```

基于已验证的门槛:
- FB Rate: 10.0% ≤ 15%
- Alignment: 86.0% ≥ 75%
- live_auto FB: 6.7% ≤ 20%
