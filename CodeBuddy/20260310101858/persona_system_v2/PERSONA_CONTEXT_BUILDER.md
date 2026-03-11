# Persona Context Builder v2
# 人格调用显式化工件规范

**版本**: 2.0  
**目标**: 将人格调用从隐式模板改为显式上下文绑定

---

## 1. 核心数据结构

### 1.1 PersonaContext (发言前强制生成)

```python
@dataclass
class PersonaContext:
    """人格上下文 - 每次发言前强制生成"""
    
    # === 身份定位 ===
    speaker_id: str                    # 如 "00012"
    speaker_type: SpeakerType          # CORE / EXTENDED / OBSERVER
    registry_source: str               # "seat_registry.yaml" / "culture_registry.yaml"
    
    # === DNA 快照 (从 registry 抽取) ===
    dna_snapshot: DNASnapshot
    
    # === 会议绑定 (动态计算) ===
    meeting_binding: MeetingBinding
    
    # === 生成约束 (用于 Stage B) ===
    generation_constraints: GenerationConstraints
    
    # === 审计字段 (不可见，用于验证) ===
    audit: PersonaAudit
    
    def to_dict(self) -> Dict:
        return {
            "speaker_id": self.speaker_id,
            "speaker_type": self.speaker_type.value,
            "registry_source": self.registry_source,
            "dna_snapshot": self.dna_snapshot.to_dict(),
            "meeting_binding": self.meeting_binding.to_dict(),
            "generation_constraints": self.generation_constraints.to_dict(),
            "audit": self.audit.to_dict()
        }


@dataclass
class DNASnapshot:
    """DNA 人格卡片快照 - 只取与当前议题相关的字段"""
    
    identity: str                      # 身份描述
    core_drives: List[str]             # 核心驱动力
    decision_style: str                # 决策风格
    taboos: List[str]                  # 禁忌/红线
    preferred_evidence: List[str]      # 优先认可的证据类型
    rhetorical_style: str              # 修辞风格
    department_view: str               # 部门视角
    risk_bias: RiskBias                # 风险倾向 (conservative/aggressive/balanced)
    resource_bias: ResourceBias        # 资源倾向 (save/invest/balanced)
    
    # 扩展字段 (文化/原型角色特有)
    archetype_triggers: Optional[List[str]] = None
    cultural_norms: Optional[List[str]] = None
    
    @classmethod
    def from_registry(cls, registry_entry: Dict, issue_type: str) -> "DNASnapshot":
        """从 registry 抽取与议题相关的 DNA 字段"""
        # P0: 实现 - 按 issue_type 筛选 relevant_fields
        pass


@dataclass
class MeetingBinding:
    """会议状态绑定"""
    
    issue_type: str                    # 议题类型
    risk_level: RiskLevel              # 风险等级
    involved_seats: List[str]          # 参与席位
    current_round: int                 # 当前轮次
    
    # 动态计算字段
    unresolved_points: List[str]       # 未解决要点
    prior_stage_summary: str           # 前序阶段摘要
    conflict_points: List[str]         # 争议点
    consensus_points: List[str]        # 共识点
    
    @classmethod
    def from_meeting_state(cls, meeting_state: MeetingState) -> "MeetingBinding":
        """从会议状态动态计算"""
        pass


@dataclass
class GenerationConstraints:
    """生成约束 - 指导 Stage B 发言生成"""
    
    # 本轮必须关心什么
    must_address: List[str]
    
    # 哪些表述不能说
    forbidden_phrases: List[str]
    
    # 优先引用的证据类型
    priority_evidence_types: List[str]
    
    # 默认立场倾向
    default_stance: Stance
    
    # 必须回应的未解决点
    required_responses: List[str]
    
    # 修辞风格指令
    style_directive: str


@dataclass
class PersonaAudit:
    """审计字段 - 证明"真的读了卡片""""
    
    turn_id: str                       # 如 "CORE-00012-R2"
    context_hash: str                  # SHA256 of serialized context
    timestamp: str                     # ISO format
    
    # 使用了哪些 registry 字段
    registry_keys_used: List[str]
    
    # 使用了哪些 binding 字段
    binding_keys_used: List[str]
    
    # 证据追踪 - 关键决策路径
    evidence_trace: List[Dict]         # [{"key": "risk_bias", "value": "conservative", "impact": "..."}]
    
    # 与模板的偏离度 (用于检测 boilerplate)
    template_divergence_score: float   # 0.0-1.0
    
    def verify_reading(self) -> bool:
        """验证是否真的使用了人格卡片"""
        return len(self.registry_keys_used) >= 3 and self.template_divergence_score > 0.3
```

---

## 2. 两阶段生成流程

### 2.1 Stage A: Persona Grounding

```python
class PersonaGroundingEngine:
    """阶段 A: 从 registry + meeting state 生成本轮人格约束"""
    
    def ground(self, 
               speaker_id: str,
               meeting_state: MeetingState,
               registry: PersonaRegistry) -> GenerationConstraints:
        """
        输入: 说话人 + 会议状态 + 人格库
        输出: 本轮生成约束
        """
        # Step 1: 读取人格 DNA
        dna = registry.get_dna(speaker_id)
        
        # Step 2: 议题相关性匹配
        relevant_drives = self._match_drives_to_issue(dna.core_drives, meeting_state.issue_type)
        relevant_taboos = self._match_taboos_to_context(dna.taboos, meeting_state.risk_level)
        
        # Step 3: 提取必须回应的点
        must_address = self._extract_must_address(dna, meeting_state)
        
        # Step 4: 生成禁止表述
        forbidden = self._generate_forbidden_phrases(dna.taboos, meeting_state)
        
        # Step 5: 确定默认立场
        stance = self._calculate_stance(dna.risk_bias, dna.resource_bias, meeting_state)
        
        return GenerationConstraints(
            must_address=must_address,
            forbidden_phrases=forbidden,
            priority_evidence_types=dna.preferred_evidence,
            default_stance=stance,
            required_responses=meeting_state.unresolved_points,
            style_directive=dna.rhetorical_style
        )
    
    def _match_drives_to_issue(self, drives: List[str], issue_type: str) -> List[str]:
        """匹配核心驱动力与当前议题"""
        # 实现: 使用 embedding 相似度或关键词匹配
        pass
    
    def _generate_forbidden_phrases(self, taboos: List[str], meeting_state: MeetingState) -> List[str]:
        """基于禁忌生成禁止表述"""
        # 示例: taboo="no-handwave" -> forbidden=["大致可行", "应该没问题", "基本ok"]
        pass
```

### 2.2 Stage B: Structured Speech Synthesis

```python
class SpeechSynthesisEngine:
    """阶段 B: 基于约束生成结构化发言"""
    
    def synthesize(self,
                   persona_context: PersonaContext,
                   stage: SpeechStage) -> SpeechOutput:
        """
        输入: 人格上下文 + 发言阶段 (A/B/C/D/E)
        输出: 结构化发言
        """
        constraints = persona_context.generation_constraints
        dna = persona_context.dna_snapshot
        binding = persona_context.meeting_binding
        
        # 构建 prompt (不再是模板，而是约束注入)
        prompt = self._build_constrainted_prompt(
            stage=stage,
            dna=dna,
            constraints=constraints,
            binding=binding
        )
        
        # 调用 LLM (或本地模型)
        raw_output = self.llm.generate(prompt)
        
        # 后处理: 确保遵守约束
        verified_output = self._verify_constraints(raw_output, constraints)
        
        # 生成审计记录
        audit = self._generate_audit(persona_context, verified_output, prompt)
        
        return SpeechOutput(
            content=verified_output,
            stage=stage,
            persona_context=persona_context,
            audit=audit
        )
    
    def _build_constrainted_prompt(self, stage: SpeechStage, dna: DNASnapshot,
                                   constraints: GenerationConstraints,
                                   binding: MeetingBinding) -> str:
        """构建受约束的 prompt"""
        
        return f"""
你正在扮演: {dna.identity}

你的核心驱动力: {', '.join(dna.core_drives)}
你的决策风格: {dna.decision_style}
你的禁忌/红线: {', '.join(dna.taboos)}

当前议题: {binding.issue_type} (风险等级: {binding.risk_level})
本轮你必须关心: {', '.join(constraints.must_address)}
你必须回应的未解决点: {', '.join(constraints.required_responses)}

你绝对不能说: {', '.join(constraints.forbidden_phrases)}
你优先认可的证据类型: {', '.join(constraints.priority_evidence_types)}
你的默认立场倾向: {constraints.default_stance.value}
你的修辞风格: {constraints.style_directive}

发言阶段: {stage.value} (A=初步意见, B=批评修正, C=方案提议, D=要求澄清, E=总结表态)

请基于以上人格约束，生成本阶段发言。
要求:
1. 必须体现你的核心驱动力
2. 必须回应至少一个未解决点
3. 绝对不能触碰禁忌
4. 修辞风格必须与描述一致
5. 立场必须与默认倾向一致
"""
```

---

## 3. 调用流程重构

### 3.1 新调用链 (强制路径)

```python
class PersonaSpeechPipeline:
    """人格发言管道 - 强制使用 registry-grounded generation"""
    
    def __init__(self):
        self.registry = PersonaRegistry()
        self.grounding_engine = PersonaGroundingEngine()
        self.synthesis_engine = SpeechSynthesisEngine()
    
    def generate_speech(self,
                       speaker_id: str,
                       meeting_state: MeetingState,
                       stage: SpeechStage) -> SpeechOutput:
        """
        新的统一入口 - 替代原来模板化的 generate_speech()
        """
        # P0: 强制生成 PersonaContext
        context = self._build_context(speaker_id, meeting_state)
        
        # Stage B: 合成发言
        output = self.synthesis_engine.synthesize(context, stage)
        
        # 验证: 确保真的读了卡片
        if not output.audit.verify_reading():
            raise PersonaReadingError(f"Speaker {speaker_id} failed reading verification")
        
        return output
    
    def _build_context(self, speaker_id: str, meeting_state: MeetingState) -> PersonaContext:
        """构建完整的 PersonaContext"""
        
        # 读取 registry
        registry_entry = self.registry.get(speaker_id)
        
        # Stage A: Grounding
        constraints = self.grounding_engine.ground(speaker_id, meeting_state, self.registry)
        
        # 构建 MeetingBinding
        binding = MeetingBinding.from_meeting_state(meeting_state)
        
        # 构建 DNASnapshot
        dna = DNASnapshot.from_registry(registry_entry, meeting_state.issue_type)
        
        # 生成审计
        audit = PersonaAudit(
            turn_id=f"{registry_entry['type']}-{speaker_id}-R{meeting_state.current_round}",
            context_hash=self._hash_context(registry_entry, meeting_state),
            timestamp=datetime.now().isoformat(),
            registry_keys_used=self._extract_used_keys(dna),
            binding_keys_used=self._extract_binding_keys(binding),
            evidence_trace=[],  # 由 synthesis engine 填充
            template_divergence_score=0.0  # 由验证器计算
        )
        
        return PersonaContext(
            speaker_id=speaker_id,
            speaker_type=SpeakerType(registry_entry['type']),
            registry_source=registry_entry['source_file'],
            dna_snapshot=dna,
            meeting_binding=binding,
            generation_constraints=constraints,
            audit=audit
        )
```

---

## 4. 核心 19 席改造

### 4.1 当前问题

```python
# 当前实现 (问题代码示例)
def generate_core_speech(seat_id: str, stage: str) -> str:
    """核心席位发言 - 当前模板化实现"""
    
    # 所有席位共用同一套骨架！
    if stage == "A":
        return f"""
接受议题前提...  # 无修正
基于 {seat_id} 的立场...  # 仅 seat_id 不同
要求更多信息...
"""
```

### 4.2 改造后

```python
class CorePersonaAdapter:
    """核心 19 席适配器 - 强制使用 registry"""
    
    def __init__(self, pipeline: PersonaSpeechPipeline):
        self.pipeline = pipeline
    
    def generate(self, seat_id: str, meeting_state: MeetingState, stage: SpeechStage) -> SpeechOutput:
        """核心席位发言 - 使用与扩展人格相同的管道"""
        
        # 强制检查: 该席位必须有 registry 条目
        if not self.pipeline.registry.has_entry(seat_id):
            raise MissingRegistryError(f"Core seat {seat_id} missing registry entry")
        
        # 使用统一管道生成
        return self.pipeline.generate_speech(seat_id, meeting_state, stage)
```

---

## 5. 验收脚本接口

### 5.1 Role Distinguishability Test

```python
class RoleDistinguishabilityTester:
    """角色可辨识性测试"""
    
    def test(self, 
             issue: str,
             speakers: List[str],
             pipeline: PersonaSpeechPipeline) -> TestResult:
        """
        同一议题，打乱 speaker 名称，看能否从发言反推原角色
        """
        # 生成发言 (带真实 speaker_id)
        speeches = {}
        for speaker in speakers:
            output = pipeline.generate_speech(speaker, issue, SpeechStage.B)
            speeches[speaker] = output.content
        
        # 打乱测试
        results = []
        for _ in range(100):
            shuffled = random.sample(speakers, len(speakers))
            predictions = self._classify_speeches(speeches, shuffled)
            accuracy = sum(1 for p, s in zip(predictions, speakers) if p == s) / len(speakers)
            results.append(accuracy)
        
        return TestResult(
            metric_name="role_identification_accuracy",
            score=np.mean(results),
            threshold=0.80,  # 目标: >= 80%
            passed=np.mean(results) >= 0.80
        )
```

### 5.2 Incrementality Test

```python
class IncrementalityTester:
    """信息增量测试"""
    
    def test(self,
             speech_output: SpeechOutput,
             meeting_state: MeetingState,
             history: List[str]) -> TestResult:
        """
        测试发言是否有信息增量
        """
        content = speech_output.content
        
        # 1. Unresolved point coverage
        covered = sum(1 for point in meeting_state.unresolved_points 
                     if self._mentions(content, point))
        coverage = covered / len(meeting_state.unresolved_points)
        
        # 2. New claim count (vs prior stage summary)
        new_claims = self._extract_new_claims(content, meeting_state.prior_stage_summary)
        
        # 3. Boilerplate overlap (vs speaker history)
        overlap = self._calculate_boilerplate_overlap(content, history)
        
        return TestResult(
            metric_name="incrementality",
            sub_metrics={
                "unresolved_point_coverage": coverage,
                "new_claim_count": len(new_claims),
                "boilerplate_overlap": overlap
            },
            score=(coverage * 0.4 + min(len(new_claims)/3, 1.0) * 0.4 + (1-overlap) * 0.2),
            threshold=0.70,
            passed=coverage >= 0.30 and overlap <= 0.40  # 目标: coverage +30%, overlap -40%
        )
```

---

## 6. 3×3 最小可复现实验

```python
class MinimalReproducibilityExperiment:
    """3×3 最小可复现实验"""
    
    ISSUES = [
        "strategic_planning",
        "disaster_recovery", 
        "technical_refactor"
    ]
    
    ROLES = [
        "high_strategic",      # 高战略角色
        "high_governance",     # 高风控/治理角色
        "high_execution"       # 高执行/工程角色
    ]
    
    def run(self, pipeline_v2: PersonaSpeechPipeline) -> ExperimentResult:
        """运行实验"""
        results = []
        
        for issue in self.ISSUES:
            for role in self.ROLES:
                # Baseline (旧模板系统)
                baseline = self._run_baseline(issue, role)
                
                # Variant (新 persona_context 系统)
                variant = self._run_variant(pipeline_v2, issue, role)
                
                results.append({
                    "issue": issue,
                    "role": role,
                    "baseline": baseline,
                    "variant": variant
                })
        
        # 验收
        return self._evaluate(results)
    
    def _evaluate(self, results: List[Dict]) -> ExperimentResult:
        """验收指标"""
        accuracies = [r["variant"]["distinguishability"] for r in results]
        coverages = [r["variant"]["incrementality"]["coverage"] for r in results]
        overlaps = [r["variant"]["incrementality"]["overlap"] for r in results]
        
        return ExperimentResult(
            role_distinguishability=np.mean(accuracies),
            unresolved_coverage_increase=np.mean(coverages) - np.mean([r["baseline"]["coverage"] for r in results]),
            boilerplate_reduction=np.mean([r["baseline"]["overlap"] for r in results]) - np.mean(overlaps),
            passed=(
                np.mean(accuracies) >= 0.80 and
                np.mean(coverages) >= 0.30 and
                np.mean(overlaps) <= 0.40
            )
        )
```

---

## 7. 实施优先级

| 优先级 | 任务 | 影响 |
|--------|------|------|
| **P0** | `generate_speech()` 重构 | 修复模板化问题 |
| **P0** | 核心 19 席 registry 强制检查 | 消除占位发言 |
| **P1** | PersonaContext 数据结构 | 显式化工件 |
| **P1** | Stage A Grounding Engine | 议题相关性匹配 |
| **P2** | 审计字段 + 读取证明 | 可验证性 |
| **P2** | 验收脚本 (3×3 实验) | 回归测试 |
| **P3** | 两阶段生成优化 | 质量提升 |

---

## 8. 结论

> **人格 DNA 档案本体已够用；真正要补的是"发言前强制读取、绑定、审计"这一层。**

当前系统已证明:
- ✅ Runtime activation 存在
- ✅ Registry read 存在
- ❌ Speech generation 仍是模板驱动

下一步最该做:
1. 把 `generate_speech()` 改成 registry-grounded
2. 核心 19 席强制检查 registry 条目
3. 添加 PersonaContext 显式化工件
4. 跑通 3×3 实验验证改进
