# Persona System v2 接入改造清单
# Integration Guide for Existing Taichu System

**目标**: 将 v2 管道无缝接入现有 taichu 发言路径，不改整体架构，只替换生成逻辑

---

## 现状确认 (基于仓库分析)

| 组件 | 状态 | 位置 |
|------|------|------|
| Runtime Activation | ✅ 已存在 | 第十轮修复 |
| Registry Read | ✅ 已存在 | `seat_registry.yaml`, `culture_registry.yaml` |
| Seat 真名注入 | ✅ 已存在 | Transcript 输出 |
| **核心 19 席发言** | ❌ **模板化** | 统一骨架 A/B/C/D/E |
| **扩展人格发言** | ❌ **规则化** | `generate_speech()` 名字映射 |
| Stage Summary | ✅ 已修复 | 基于实际发言生成 |

**核心问题**: Registry 已接入，但 speech generation 仍是模板驱动

---

## 改造总览

```
现有调用链:
MeetingController -> Speaker.turn() -> generate_speech() -> 模板输出

改造后调用链:
MeetingController -> Speaker.turn() -> PersonaSpeechPipeline.generate_speech() 
                                   -> Stage A: Grounding (读取 registry)
                                   -> Stage B: Synthesis (约束生成)
                                   -> 审计验证
```

---

## P0 改造点 (必须完成)

### P0.1 替换 generate_speech() 入口

**文件**: 找到现有的 `generate_speech()` 函数定义
**常见位置**: 
- `taichu/persona/speech_generator.py`
- `taichu/council/speaker.py`
- `taichu/core/speech.py`

**改造前**:
```python
def generate_speech(persona_name: str, stage: str, context: dict) -> str:
    """模板化发言生成"""
    if persona_name == "鬼谷子":
        return "...鬼谷子固定文案..."
    elif persona_name == "华佗":
        return "...华佗固定文案..."
    # ... 更多 elif
```

**改造后**:
```python
from persona_system_v2.pipeline_implementation import PersonaSpeechPipeline, SpeechStage
from persona_system_v2.persona_context import MissingRegistryError

# 全局初始化 (应用启动时)
_pipeline = None

def init_pipeline(registry_path: str = None):
    """初始化管道"""
    global _pipeline
    from persona_system_v2.pipeline_implementation import PersonaRegistry
    registry = PersonaRegistry(
        seat_registry_path=registry_path or "config/seat_registry.yaml",
        culture_registry_path=registry_path or "config/culture_registry.yaml"
    )
    _pipeline = PersonaSpeechPipeline(registry)

def generate_speech(persona_id: str, stage: str, meeting_context: dict) -> dict:
    """
    新的发言生成入口 - Registry-grounded
    
    Returns:
        dict: {
            "content": str,           # 发言内容
            "persona_context": dict,   # 人格上下文 (用于审计)
            "audit": dict              # 读取证明
        }
    """
    global _pipeline
    if _pipeline is None:
        init_pipeline()
    
    # 转换 stage 字符串为枚举
    stage_enum = SpeechStage(stage) if stage else SpeechStage.B
    
    # 构建 meeting_state
    meeting_state = {
        "issue_type": meeting_context.get("issue_type", "general"),
        "risk_level": meeting_context.get("risk_level", "medium"),
        "involved_seats": meeting_context.get("involved_seats", []),
        "current_round": meeting_context.get("current_round", 1),
        "unresolved_points": meeting_context.get("unresolved_points", []),
        "prior_stage_summary": meeting_context.get("prior_stage_summary", "")
    }
    
    try:
        # 调用 v2 管道
        output = _pipeline.generate_speech(
            speaker_id=persona_id,
            meeting_state=meeting_state,
            stage=stage_enum
        )
        
        # 返回结构化结果
        return {
            "content": output.content,
            "persona_context": output.persona_context.to_dict(),
            "audit": output.audit.to_dict(),
            "verified": output.audit.verify_reading()
        }
        
    except MissingRegistryError as e:
        # 如果 registry 缺失，回退到模板 (带警告)
        import warnings
        warnings.warn(f"Registry missing for {persona_id}, falling back to template: {e}")
        return _fallback_template_generate(persona_id, stage, meeting_context)
```

---

### P0.2 改造核心 19 席发言路径

**文件**: 找到核心席位的 turn/speak 方法
**常见位置**:
- `taichu/council/core_speaker.py`
- `taichu/seats/core_seat.py`
- `taichu/core/participant.py`

**改造前**:
```python
class CoreSpeaker:
    def turn(self, round_num: int, stage: str) -> str:
        """核心席位发言 - 统一骨架"""
        seat_name = self.get_seat_name()  # 如 "技术官"
        
        if stage == "A":
            return f"接受议题前提。我是{seat_name}，基于我的专业领域..."
        elif stage == "B":
            return f"无修正。{seat_name}认为当前方案..."
        elif stage == "C":
            return f"基于{seat_name}的立场，我建议..."
        elif stage == "D":
            return f"{seat_name}要求更多信息..."
        elif stage == "E":
            return f"{seat_name}的最终立场是..."
```

**改造后**:
```python
from persona_system_v2.pipeline_implementation import CoreSeatAdapter, SpeechStage

class CoreSpeaker:
    def __init__(self, seat_id: str, seat_name: str):
        self.seat_id = seat_id      # 如 "00001"
        self.seat_name = seat_name  # 如 "技术官"
        self._adapter = None
    
    def init_adapter(self, pipeline):
        """初始化适配器 (会议启动时)"""
        from persona_system_v2.pipeline_implementation import CoreSeatAdapter
        self._adapter = CoreSeatAdapter(pipeline)
    
    def turn(self, round_num: int, stage: str, meeting_state: dict) -> dict:
        """
        核心席位发言 - Registry-grounded
        
        关键改变: 
        1. 使用 seat_id (00001) 而非 seat_name 查询 registry
        2. 强制检查 registry 条目存在
        3. 返回结构化结果 (含审计)
        """
        if self._adapter is None:
            raise RuntimeError("CoreSeatAdapter not initialized. Call init_adapter() first.")
        
        stage_enum = SpeechStage(stage)
        
        # 关键: 使用 seat_id (如 "00001") 而非 seat_name
        output = self._adapter.generate(
            seat_id=self.seat_id,
            meeting_state=meeting_state,
            stage=stage_enum
        )
        
        return {
            "speaker_id": self.seat_id,
            "speaker_name": self.seat_name,
            "content": output.content,
            "stage": stage,
            "audit": output.audit.to_dict()
        }
```

---

### P0.3 会议启动时强制检查

**文件**: `MeetingController` 或 `Council` 初始化
**常见位置**:
- `taichu/council/controller.py`
- `taichu/meeting/manager.py`

**新增代码**:
```python
from persona_system_v2.pipeline_implementation import PersonaRegistry, CoreSeatAdapter

class MeetingController:
    def __init__(self, config: dict):
        # 初始化 registry
        self.registry = PersonaRegistry(
            seat_registry_path=config.get("seat_registry"),
            culture_registry_path=config.get("culture_registry")
        )
        
        # 初始化管道
        from persona_system_v2.pipeline_implementation import PersonaSpeechPipeline
        self.pipeline = PersonaSpeechPipeline(self.registry)
        
        # P0: 强制检查所有核心席位都有 registry 条目
        self._validate_core_seats()
        
        # P0: 为所有 speaker 初始化 adapter
        self._init_speaker_adapters()
    
    def _validate_core_seats(self):
        """强制检查: 所有核心席位必须有 registry 条目"""
        core_seat_ids = [f"{i:05d}" for i in range(1, 20)]  # 00001-00019
        
        missing = []
        for seat_id in core_seat_ids:
            if not self.registry.has_entry(seat_id):
                missing.append(seat_id)
        
        if missing:
            from persona_system_v2.persona_context import MissingRegistryError
            raise MissingRegistryError(
                f"CRITICAL: Core seats missing registry entries: {missing}\n"
                f"All 19 core seats must have entries in seat_registry.yaml before meeting can start.\n"
                f"Please add registry entries for these seats."
            )
        
        print(f"✅ All {len(core_seat_ids)} core seats validated in registry")
    
    def _init_speaker_adapters(self):
        """为所有 speaker 初始化适配器"""
        for speaker in self.participants:
            if hasattr(speaker, 'init_adapter'):
                speaker.init_adapter(self.pipeline)
```

---

## P1 改造点 (推荐完成)

### P1.1 修改发言输出格式 (携带审计)

**文件**: Transcript/Meeting Record 输出

**改造**: 在发言记录中加入审计字段

```python
# 改造前
transcript.add({
    "speaker": "00001",
    "content": "发言内容..."
})

# 改造后
transcript.add({
    "speaker": output["speaker_id"],
    "content": output["content"],
    "persona_context_hash": output["audit"]["context_hash"],
    "registry_keys_used": output["audit"]["registry_keys_used"],
    "verified": output["audit"].get("verified", False)
})
```

---

### P1.2 添加运行时审计日志

**文件**: 日志记录模块

```python
import json

class PersonaAuditLogger:
    """人格调用审计日志"""
    
    def __init__(self, log_path: str = "logs/persona_audit.jsonl"):
        self.log_path = log_path
    
    def log_speech_generation(self, output: dict):
        """记录每次发言生成"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "turn_id": output["audit"]["turn_id"],
            "speaker_id": output["speaker_id"],
            "registry_keys_used": output["audit"]["registry_keys_used"],
            "template_divergence": output["audit"]["template_divergence_score"],
            "verified": output["audit"].get("verified", False)
        }
        
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
```

---

### P1.3 添加 LLM 调用点

**文件**: `pipeline_implementation.py` 中的 `_mock_llm_generate()`

**改造**: 替换为真实 LLM 调用

```python
# 当前 (模拟)
def _mock_llm_generate(self, prompt: str, context: PersonaContext) -> str:
    # 模拟生成
    return "..."

# 改造后 (真实 LLM)
def _llm_generate(self, prompt: str, context: PersonaContext) -> str:
    """调用真实 LLM 生成发言"""
    
    # 选项 1: OpenAI API
    import openai
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a persona-based speech generator."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content
    
    # 选项 2: 本地模型 (vLLM/Ollama)
    import requests
    response = requests.post(
        "http://localhost:8000/v1/chat/completions",
        json={
            "model": "qwen2.5-72b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
    )
    return response.json()["choices"][0]["message"]["content"]
```

---

## 验证清单 (接入后必做)

### 立即验证 (单条发言)

```python
# 测试单个发言
def test_single_speech():
    from persona_system_v2.pipeline_implementation import PersonaSpeechPipeline
    
    pipeline = PersonaSpeechPipeline()
    
    meeting_state = {
        "issue_type": "strategic_planning",
        "risk_level": "high",
        "unresolved_points": ["时机选择", "资源分配"]
    }
    
    # 测试核心席位
    output = pipeline.generate_speech("00001", meeting_state, SpeechStage.B)
    
    print(f"Content: {output.content[:100]}...")
    print(f"Verified: {output.audit.verify_reading()}")
    print(f"Keys used: {output.audit.registry_keys_used}")
    print(f"Divergence: {output.audit.template_divergence_score:.1%}")
```

### 3×3 实验验证 (完整回归)

```python
# 运行完整实验
from persona_system_v2.experiment_3x3 import MinimalReproducibilityExperiment

experiment = MinimalReproducibilityExperiment()
result = experiment.run(your_pipeline_instance)

assert result.overall_passed, "Experiment failed!"
print(f"✅ All gates pass:")
print(f"  - Distinguishability: {result.role_distinguishability:.1%}")
print(f"  - Coverage increase: {result.coverage_increase:+.1%}")
print(f"  - Boilerplate reduction: {result.boilerplate_reduction:.1%}")
```

---

## 回滚策略

如果接入后出现问题，快速回滚方案:

```python
# 在 generate_speech() 中添加特性开关
import os

USE_V2_PIPELINE = os.getenv("USE_V2_PERSONA", "true").lower() == "true"

def generate_speech(persona_id: str, stage: str, context: dict) -> dict:
    if USE_V2_PIPELINE:
        return _generate_v2(persona_id, stage, context)
    else:
        return _generate_legacy(persona_id, stage, context)  # 原模板逻辑
```

---

## 最小改造路径总结

| 步骤 | 文件 | 改动 | 验证 |
|------|------|------|------|
| 1 | `generate_speech()` | 替换入口，调用 v2 管道 | 单条发言测试 |
| 2 | `CoreSpeaker.turn()` | 使用 seat_id 查询，返回审计 | 核心席位发言测试 |
| 3 | `MeetingController.__init__` | 添加强制检查 | 启动时验证 |
| 4 | `_mock_llm_generate()` | 替换为真实 LLM | 生成质量检查 |
| 5 | 运行 `experiment_3x3.py` | 完整回归 | 三项指标达标 |

---

## 直接可用的代码块

### 快速接入模板

```python
# 在现有系统入口添加
from persona_system_v2.pipeline_implementation import (
    PersonaSpeechPipeline, PersonaRegistry, CoreSeatAdapter, SpeechStage
)

# 1. 初始化 (应用启动)
registry = PersonaRegistry(
    seat_registry_path="path/to/seat_registry.yaml",
    culture_registry_path="path/to/culture_registry.yaml"
)
pipeline = PersonaSpeechPipeline(registry)

# 2. 验证核心席位
adapter = CoreSeatAdapter(pipeline)
adapter.validate_all_seats_have_registry()  # 会抛出异常如果缺失

# 3. 替换 generate_speech
# (见上文 P0.1 代码)

# 4. 为 speaker 初始化
for speaker in speakers:
    if hasattr(speaker, 'seat_id'):
        speaker.init_adapter(pipeline)
```

---

## 结论

**不是再加一套新设计，而是把当前 persona activation 真正推进到 persona-grounded generation。**

**下一步动作**:
1. 确认上述 P0 改造点在你的代码库中的具体文件位置
2. 应用 P0.1-P0.3 改造
3. 立即运行 3×3 实验验证三项指标
4. 根据实验结果调优
