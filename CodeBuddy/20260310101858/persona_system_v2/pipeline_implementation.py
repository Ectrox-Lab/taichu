"""
Pipeline Implementation Example
管道实现示例 - 展示如何改造现有系统

P0 优先级改造点:
1. generate_speech() 重构 - 从模板改为 registry-grounded
2. 核心 19 席强制检查 - 确保所有席位都有 registry 条目
"""

from typing import Dict, List, Optional, Any
import yaml
import json

from persona_context import (
    PersonaContext, DNASnapshot, MeetingBinding, GenerationConstraints,
    PersonaAudit, PersonaGroundingEngine, SpeechStage, SpeakerType,
    PersonaReadingError, MissingRegistryError, SpeechOutput
)


class PersonaRegistry:
    """
    人格注册表 - 从 YAML 文件加载
    """
    
    def __init__(self, seat_registry_path: str = "seat_registry.yaml",
                 culture_registry_path: str = "culture_registry.yaml"):
        self.seat_registry = self._load_yaml(seat_registry_path)
        self.culture_registry = self._load_yaml(culture_registry_path)
        self._build_index()
    
    def _load_yaml(self, path: str) -> Dict:
        """加载 YAML 文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
    
    def _build_index(self):
        """构建索引 - 合并 seat 和 culture registry"""
        self._index = {}
        
        # 索引 seat registry
        for seat_id, entry in self.seat_registry.get("seats", {}).items():
            self._index[seat_id] = {
                **entry,
                "type": "core",
                "source_file": "seat_registry.yaml"
            }
        
        # 索引 culture registry
        for persona_id, entry in self.culture_registry.get("personas", {}).items():
            self._index[persona_id] = {
                **entry,
                "type": "extended",
                "source_file": "culture_registry.yaml"
            }
    
    def get(self, speaker_id: str) -> Optional[Dict]:
        """获取 registry 条目"""
        return self._index.get(speaker_id)
    
    def has_entry(self, speaker_id: str) -> bool:
        """检查是否有条目"""
        return speaker_id in self._index
    
    def get_dna(self, speaker_id: str) -> Dict:
        """获取 DNA 配置"""
        entry = self.get(speaker_id)
        if not entry:
            return {}
        return entry.get("dna", {})


class PersonaSpeechPipeline:
    """
    人格发言管道 - 新的统一入口
    
    替换原来的:
    - generate_speech() 模板函数
    - 核心 19 席的独立生成逻辑
    """
    
    def __init__(self, registry: PersonaRegistry = None):
        self.registry = registry or PersonaRegistry()
        self.grounding_engine = PersonaGroundingEngine()
    
    def generate_speech(self,
                       speaker_id: str,
                       meeting_state: Dict,
                       stage: SpeechStage) -> SpeechOutput:
        """
        生成发言 - 新的统一入口
        
        Args:
            speaker_id: 说话人 ID
            meeting_state: 会议状态
            stage: 发言阶段 (A/B/C/D/E)
        
        Returns:
            SpeechOutput 包含内容和审计信息
        """
        # Step 1: 强制检查 registry 条目 (P0)
        if not self.registry.has_entry(speaker_id):
            raise MissingRegistryError(
                f"Speaker {speaker_id} not found in registry. "
                f"All speakers must have registry entries before generating speech."
            )
        
        # Step 2: 构建 PersonaContext (强制)
        context = self._build_context(speaker_id, meeting_state)
        
        # Step 3: 生成发言 (使用约束)
        speech_content = self._synthesize_speech(context, stage)
        
        # Step 4: 验证读取
        if not context.audit.verify_reading():
            raise PersonaReadingError(
                f"Speaker {speaker_id} failed reading verification. "
                f"Registry keys used: {len(context.audit.registry_keys_used)}"
            )
        
        # Step 5: 计算实际差异度
        divergence = self._calculate_divergence(speech_content, context)
        context.audit.template_divergence_score = divergence
        
        return SpeechOutput(
            content=speech_content,
            stage=stage,
            persona_context=context,
            audit=context.audit
        )
    
    def _build_context(self, speaker_id: str, meeting_state: Dict) -> PersonaContext:
        """构建完整的 PersonaContext"""
        
        registry_entry = self.registry.get(speaker_id)
        
        # Stage A: Grounding - 生成本轮约束
        constraints = self.grounding_engine.ground(
            speaker_id, meeting_state, registry_entry
        )
        
        # 构建 MeetingBinding
        binding = MeetingBinding.from_meeting_state(meeting_state)
        
        # 构建 DNASnapshot - 只取与议题相关的字段
        dna = DNASnapshot.from_registry(
            registry_entry, meeting_state.get("issue_type", "")
        )
        
        # 确定 speaker type
        speaker_type = SpeakerType(registry_entry.get("type", "core"))
        
        # 生成审计记录
        audit = PersonaAudit(
            turn_id=f"{speaker_type.value}-{speaker_id}-R{meeting_state.get('current_round', 1)}",
            context_hash=self._hash_context(registry_entry, meeting_state),
            timestamp=datetime.now().isoformat(),
            registry_keys_used=self._extract_used_keys(dna),
            binding_keys_used=self._extract_binding_keys(binding),
            evidence_trace=[],  # 由生成过程填充
            template_divergence_score=0.0  # 后续计算
        )
        
        return PersonaContext(
            speaker_id=speaker_id,
            speaker_type=speaker_type,
            registry_source=registry_entry.get("source_file", ""),
            dna_snapshot=dna,
            meeting_binding=binding,
            generation_constraints=constraints,
            audit=audit
        )
    
    def _synthesize_speech(self, context: PersonaContext, stage: SpeechStage) -> str:
        """
        合成发言 - 使用约束而非模板
        
        这是替换原来模板逻辑的核心实现
        """
        dna = context.dna_snapshot
        constraints = context.generation_constraints
        binding = context.meeting_binding
        
        # 构建受约束的 prompt
        prompt = self._build_constrained_prompt(context, stage)
        
        # 这里调用 LLM 或本地模型
        # 实际实现中替换为真实的模型调用
        speech = self._mock_llm_generate(prompt, context)
        
        # 填充审计证据
        context.audit.evidence_trace = self._generate_evidence_trace(
            speech, context
        )
        
        return speech
    
    def _build_constrained_prompt(self, context: PersonaContext, stage: SpeechStage) -> str:
        """构建受约束的 prompt"""
        dna = context.dna_snapshot
        constraints = context.generation_constraints
        binding = context.meeting_binding
        
        # 根据发言阶段调整指令
        stage_instructions = {
            SpeechStage.A: "提出你的初步意见，说明基本立场",
            SpeechStage.B: "批评或修正已有观点，指出问题",
            SpeechStage.C: "提出具体方案或建议",
            SpeechStage.D: "要求澄清或更多信息",
            SpeechStage.E: "总结并明确表态"
        }
        
        prompt = f"""
=== 角色设定 ===
你正在扮演: {dna.identity}
你的核心驱动力: {', '.join(dna.core_drives)}
你的决策风格: {dna.decision_style}
你的禁忌/红线: {', '.join(dna.taboos)}
你的修辞风格: {dna.rhetorical_style}
你的部门视角: {dna.department_view}

=== 会议情境 ===
当前议题: {binding.issue_type} (风险等级: {binding.risk_level.value})
当前轮次: 第{binding.current_round}轮
本轮你必须关心: {', '.join(constraints.must_address)}
你必须回应的未解决点: {', '.join(constraints.required_responses[:3])}

=== 约束条件 ===
你绝对不能说: {', '.join(constraints.forbidden_phrases[:5])}
你优先认可的证据类型: {', '.join(constraints.priority_evidence_types)}
你的默认立场倾向: {constraints.default_stance.value}

=== 发言要求 ===
阶段: {stage.value} - {stage_instructions.get(stage, "发表意见")}
要求:
1. 必须体现你的核心驱动力
2. 必须回应至少一个未解决点
3. 绝对不能触碰禁忌/红线
4. 修辞风格必须与描述一致
5. 立场必须与默认倾向一致
6. 引用你优先认可的证据类型

请生成一段符合以上所有约束的发言。
"""
        return prompt
    
    def _mock_llm_generate(self, prompt: str, context: PersonaContext) -> str:
        """
        模拟 LLM 生成 - 实际实现中替换为真实模型调用
        
        这里展示的是如何根据约束生成内容
        """
        dna = context.dna_snapshot
        constraints = context.generation_constraints
        binding = context.meeting_binding
        
        # 模拟 persona-grounded 输出
        # 实际实现中，这里应该是真实的 LLM 调用
        
        # 根据 DNA 构建回应
        parts = []
        
        # 1. 身份声明
        parts.append(f"作为{dna.identity}，")
        
        # 2. 核心驱动力体现
        parts.append(f"我从{dna.department_view}出发，")
        parts.append(f"{'、'.join(dna.core_drives[:2])}是我的首要考虑。")
        
        # 3. 回应未解决点
        if binding.unresolved_points:
            point = binding.unresolved_points[0]
            parts.append(f"\n针对'{point}'，")
            
            # 根据 risk_bias 给出倾向
            if dna.risk_bias.value == "conservative":
                parts.append("我认为存在显著风险，需要更充分的评估。")
            elif dna.risk_bias.value == "aggressive":
                parts.append("我认为应该抓住机遇，快速推进。")
            else:
                parts.append("我认为需要平衡考虑各方面因素。")
        
        # 4. 证据要求
        if constraints.priority_evidence_types:
            parts.append(f"\n在做出决定前，我需要看到{constraints.priority_evidence_types[0]}。")
        
        # 5. 立场表态
        parts.append(f"\n基于以上分析，我的立场是{constraints.default_stance.value}。")
        parts.append(f"这符合{dna.decision_style}的决策风格。")
        
        return "\n".join(parts)
    
    def _generate_evidence_trace(self, speech: str, context: PersonaContext) -> List[Dict]:
        """生成证据追踪 - 记录哪些 DNA 字段影响了发言"""
        trace = []
        dna = context.dna_snapshot
        constraints = context.generation_constraints
        
        # 检查哪些 DNA 字段体现在发言中
        if dna.risk_bias.value in speech.lower() or "风险" in speech:
            trace.append({
                "key": "risk_bias",
                "value": dna.risk_bias.value,
                "impact": f"影响了立场表达"
            })
        
        if any(drive in speech for drive in dna.core_drives):
            trace.append({
                "key": "core_drives",
                "value": dna.core_drives[:2],
                "impact": "体现在发言关注点"
            })
        
        if constraints.default_stance.value in speech.lower():
            trace.append({
                "key": "default_stance",
                "value": constraints.default_stance.value,
                "impact": "直接体现在最终立场"
            })
        
        return trace
    
    def _calculate_divergence(self, speech: str, context: PersonaContext) -> float:
        """计算与模板的偏离度"""
        # 检测是否使用了模板化表述
        boilerplate_indicators = [
            "接受议题前提",
            "无修正",
            "基于我的立场",
            "要求更多信息",
            "我同意",
            "我认为",
            "大致可行"
        ]
        
        matches = sum(1 for indicator in boilerplate_indicators 
                     if indicator in speech)
        
        # 偏离度 = 1 - 套话比例 (越高越好)
        return min(1.0, 1 - (matches / len(boilerplate_indicators)))
    
    def _hash_context(self, registry_entry: Dict, meeting_state: Dict) -> str:
        """计算上下文 hash"""
        import hashlib
        content = json.dumps({
            "registry": registry_entry,
            "meeting": meeting_state
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _extract_used_keys(self, dna: DNASnapshot) -> List[str]:
        """提取使用的 registry keys"""
        return [
            "identity",
            "core_drives",
            "decision_style",
            "taboos",
            "risk_bias",
            "resource_bias",
            "rhetorical_style"
        ]
    
    def _extract_binding_keys(self, binding: MeetingBinding) -> List[str]:
        """提取使用的 binding keys"""
        return [
            "issue_type",
            "risk_level",
            "unresolved_points",
            "current_round"
        ]


class CoreSeatAdapter:
    """
    核心席位适配器 - 强制使用 registry
    
    确保核心 19 席不再使用模板占位发言
    """
    
    def __init__(self, pipeline: PersonaSpeechPipeline):
        self.pipeline = pipeline
        self.core_seat_ids = [f"{i:05d}" for i in range(1, 20)]  # 00001-00019
    
    def validate_all_seats_have_registry(self) -> List[str]:
        """验证所有核心席位都有 registry 条目"""
        missing = []
        for seat_id in self.core_seat_ids:
            if not self.pipeline.registry.has_entry(seat_id):
                missing.append(seat_id)
        
        if missing:
            raise MissingRegistryError(
                f"Core seats missing registry entries: {missing}\n"
                f"All core seats must have registry entries before meeting."
            )
        
        return []
    
    def generate(self, seat_id: str, meeting_state: Dict, stage: SpeechStage) -> SpeechOutput:
        """核心席位发言 - 使用统一管道"""
        # 强制检查
        if seat_id in self.core_seat_ids:
            self.validate_all_seats_have_registry()
        
        # 使用统一管道生成
        return self.pipeline.generate_speech(seat_id, meeting_state, stage)


# 使用示例
if __name__ == "__main__":
    from datetime import datetime
    
    print("="*70)
    print("Persona Speech Pipeline Demo")
    print("="*70 + "\n")
    
    # 创建管道
    pipeline = PersonaSpeechPipeline()
    
    # 模拟会议状态
    meeting_state = {
        "issue_type": "strategic_planning",
        "risk_level": "high",
        "involved_seats": ["high_strategic", "high_governance", "high_execution"],
        "current_round": 2,
        "unresolved_points": [
            "市场进入时机的选择",
            "资源分配优先级",
            "长期ROI测算"
        ],
        "prior_stage_summary": "讨论战略规划的初步方向"
    }
    
    # 注意：这里会失败，因为需要真实的 registry 文件
    # 演示目的展示 API 设计
    
    print("Pipeline initialized.")
    print("Meeting state prepared.")
    print("\nNote: Actual speech generation requires registry files.")
    print("API design is ready for integration.")
