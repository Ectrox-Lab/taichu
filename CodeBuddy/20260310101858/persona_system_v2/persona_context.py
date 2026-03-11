"""
Persona Context Builder v2 - Implementation
人格调用显式化工件实现
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import hashlib
import json


class SpeakerType(Enum):
    CORE = "core"
    EXTENDED = "extended"
    OBSERVER = "observer"


class RiskBias(Enum):
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"


class ResourceBias(Enum):
    SAVE = "save"
    INVEST = "invest"
    BALANCED = "balanced"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Stance(Enum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    NEUTRAL = "neutral"
    CONDITIONAL = "conditional"


class SpeechStage(Enum):
    A = "A"  # 初步意见
    B = "B"  # 批评修正
    C = "C"  # 方案提议
    D = "D"  # 要求澄清
    E = "E"  # 总结表态


@dataclass
class DNASnapshot:
    """DNA 人格卡片快照"""
    identity: str
    core_drives: List[str]
    decision_style: str
    taboos: List[str]
    preferred_evidence: List[str]
    rhetorical_style: str
    department_view: str
    risk_bias: RiskBias
    resource_bias: ResourceBias
    archetype_triggers: Optional[List[str]] = None
    cultural_norms: Optional[List[str]] = None
    
    @classmethod
    def from_registry(cls, registry_entry: Dict, issue_type: str) -> "DNASnapshot":
        """从 registry 抽取与议题相关的 DNA 字段"""
        dna = registry_entry.get("dna", {})
        
        # 按 issue_type 筛选 relevant drives
        all_drives = dna.get("core_drives", [])
        relevant_drives = cls._filter_relevant_drives(all_drives, issue_type)
        
        return cls(
            identity=dna.get("identity", ""),
            core_drives=relevant_drives or all_drives[:3],  # 默认取前3
            decision_style=dna.get("decision_style", ""),
            taboos=dna.get("taboos", []),
            preferred_evidence=dna.get("preferred_evidence", []),
            rhetorical_style=dna.get("rhetorical_style", ""),
            department_view=dna.get("department_view", ""),
            risk_bias=RiskBias(dna.get("risk_bias", "balanced")),
            resource_bias=ResourceBias(dna.get("resource_bias", "balanced")),
            archetype_triggers=dna.get("archetype_triggers"),
            cultural_norms=dna.get("cultural_norms")
        )
    
    @staticmethod
    def _filter_relevant_drives(drives: List[str], issue_type: str) -> List[str]:
        """根据议题类型筛选相关驱动力"""
        # 简单的关键词匹配，可扩展为 embedding 相似度
        issue_keywords = {
            "strategic_planning": ["战略", "长期", "方向", "growth", "future"],
            "disaster_recovery": ["风险", "安全", "恢复", "resilience", "protection"],
            "technical_refactor": ["技术", "质量", "债务", "performance", "reliability"]
        }
        
        keywords = issue_keywords.get(issue_type, [])
        relevant = []
        for drive in drives:
            if any(kw in drive.lower() for kw in keywords):
                relevant.append(drive)
        
        return relevant[:3] if relevant else drives[:3]
    
    def to_dict(self) -> Dict:
        return {
            "identity": self.identity,
            "core_drives": self.core_drives,
            "decision_style": self.decision_style,
            "taboos": self.taboos,
            "preferred_evidence": self.preferred_evidence,
            "rhetorical_style": self.rhetorical_style,
            "department_view": self.department_view,
            "risk_bias": self.risk_bias.value,
            "resource_bias": self.resource_bias.value,
            "archetype_triggers": self.archetype_triggers,
            "cultural_norms": self.cultural_norms
        }


@dataclass
class MeetingBinding:
    """会议状态绑定"""
    issue_type: str
    risk_level: RiskLevel
    involved_seats: List[str]
    current_round: int
    unresolved_points: List[str]
    prior_stage_summary: str
    conflict_points: List[str] = field(default_factory=list)
    consensus_points: List[str] = field(default_factory=list)
    
    @classmethod
    def from_meeting_state(cls, meeting_state: Dict) -> "MeetingBinding":
        """从会议状态动态计算"""
        return cls(
            issue_type=meeting_state.get("issue_type", ""),
            risk_level=RiskLevel(meeting_state.get("risk_level", "medium")),
            involved_seats=meeting_state.get("involved_seats", []),
            current_round=meeting_state.get("current_round", 1),
            unresolved_points=meeting_state.get("unresolved_points", []),
            prior_stage_summary=meeting_state.get("prior_stage_summary", ""),
            conflict_points=meeting_state.get("conflict_points", []),
            consensus_points=meeting_state.get("consensus_points", [])
        )
    
    def to_dict(self) -> Dict:
        return {
            "issue_type": self.issue_type,
            "risk_level": self.risk_level.value,
            "involved_seats": self.involved_seats,
            "current_round": self.current_round,
            "unresolved_points": self.unresolved_points,
            "prior_stage_summary": self.prior_stage_summary,
            "conflict_points": self.conflict_points,
            "consensus_points": self.consensus_points
        }


@dataclass
class GenerationConstraints:
    """生成约束"""
    must_address: List[str]
    forbidden_phrases: List[str]
    priority_evidence_types: List[str]
    default_stance: Stance
    required_responses: List[str]
    style_directive: str
    
    def to_dict(self) -> Dict:
        return {
            "must_address": self.must_address,
            "forbidden_phrases": self.forbidden_phrases,
            "priority_evidence_types": self.priority_evidence_types,
            "default_stance": self.default_stance.value,
            "required_responses": self.required_responses,
            "style_directive": self.style_directive
        }


@dataclass
class PersonaAudit:
    """审计字段 - 证明"真的读了卡片""""
    turn_id: str
    context_hash: str
    timestamp: str
    registry_keys_used: List[str]
    binding_keys_used: List[str]
    evidence_trace: List[Dict]
    template_divergence_score: float
    
    def verify_reading(self) -> bool:
        """验证是否真的使用了人格卡片"""
        return len(self.registry_keys_used) >= 3 and self.template_divergence_score > 0.3
    
    def to_dict(self) -> Dict:
        return {
            "turn_id": self.turn_id,
            "context_hash": self.context_hash,
            "timestamp": self.timestamp,
            "registry_keys_used": self.registry_keys_used,
            "binding_keys_used": self.binding_keys_used,
            "evidence_trace": self.evidence_trace,
            "template_divergence_score": self.template_divergence_score
        }


@dataclass
class PersonaContext:
    """人格上下文 - 每次发言前强制生成"""
    speaker_id: str
    speaker_type: SpeakerType
    registry_source: str
    dna_snapshot: DNASnapshot
    meeting_binding: MeetingBinding
    generation_constraints: GenerationConstraints
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
    
    def serialize_for_hash(self) -> str:
        """序列化用于计算 hash"""
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)


@dataclass
class SpeechOutput:
    """发言输出"""
    content: str
    stage: SpeechStage
    persona_context: PersonaContext
    audit: PersonaAudit
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "stage": self.stage.value,
            "persona_context": self.persona_context.to_dict(),
            "audit": self.audit.to_dict()
        }


class PersonaGroundingEngine:
    """阶段 A: Persona Grounding"""
    
    def ground(self, speaker_id: str, meeting_state: Dict, registry_entry: Dict) -> GenerationConstraints:
        """从 registry + meeting state 生成本轮人格约束"""
        
        dna = DNASnapshot.from_registry(registry_entry, meeting_state.get("issue_type", ""))
        binding = MeetingBinding.from_meeting_state(meeting_state)
        
        # 匹配核心驱动力
        relevant_drives = dna.core_drives
        
        # 提取必须关心的事项
        must_address = self._extract_must_address(dna, binding)
        
        # 生成禁止表述
        forbidden = self._generate_forbidden_phrases(dna.taboos, binding)
        
        # 确定默认立场
        stance = self._calculate_stance(dna.risk_bias, dna.resource_bias, binding)
        
        return GenerationConstraints(
            must_address=must_address,
            forbidden_phrases=forbidden,
            priority_evidence_types=dna.preferred_evidence,
            default_stance=stance,
            required_responses=binding.unresolved_points,
            style_directive=dna.rhetorical_style
        )
    
    def _extract_must_address(self, dna: DNASnapshot, binding: MeetingBinding) -> List[str]:
        """提取本轮必须关心的事项"""
        must_address = []
        
        # 基于 risk_bias 添加风险关注点
        if dna.risk_bias == RiskBias.CONSERVATIVE:
            must_address.append("风险评估")
        elif dna.risk_bias == RiskBias.AGGRESSIVE:
            must_address.append("机会识别")
        
        # 基于 resource_bias 添加资源关注点
        if dna.resource_bias == ResourceBias.SAVE:
            must_address.append("成本控制")
        elif dna.resource_bias == ResourceBias.INVEST:
            must_address.append("增长潜力")
        
        # 基于议题类型
        if binding.issue_type == "strategic_planning":
            must_address.append("长期影响")
        elif binding.issue_type == "disaster_recovery":
            must_address.append("恢复时间")
        
        return must_address
    
    def _generate_forbidden_phrases(self, taboos: List[str], binding: MeetingBinding) -> List[str]:
        """基于禁忌生成禁止表述"""
        forbidden_map = {
            "no-handwave": ["大致可行", "应该没问题", "基本ok", "差不多", "粗略看"],
            "no-optimism": ["肯定能成", "绝对没问题", "必然成功", "毫无疑问"],
            "no-pessimism": ["肯定不行", "绝对失败", "毫无希望", "注定失败"],
            "no-silence": ["我没意见", "无所谓", "都可以", "听大家的"]
        }
        
        forbidden = []
        for taboo in taboos:
            if taboo in forbidden_map:
                forbidden.extend(forbidden_map[taboo])
        
        # 基于风险等级添加额外约束
        if binding.risk_level == RiskLevel.CRITICAL:
            forbidden.extend(["风险不大", "问题不大", "基本安全"])
        
        return forbidden
    
    def _calculate_stance(self, risk_bias: RiskBias, resource_bias: ResourceBias, 
                         binding: MeetingBinding) -> Stance:
        """确定默认立场"""
        
        # 保守 + 议题高风险 = 反对或条件支持
        if risk_bias == RiskBias.CONSERVATIVE and binding.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return Stance.CONDITIONAL
        
        # 激进 + 议题战略型 = 支持
        if risk_bias == RiskBias.AGGRESSIVE and binding.issue_type == "strategic_planning":
            return Stance.SUPPORT
        
        # 节省 + 议题高成本 = 反对
        if resource_bias == ResourceBias.SAVE and "高成本" in str(binding.unresolved_points):
            return Stance.OPPOSE
        
        return Stance.NEUTRAL


class PersonaReadingError(Exception):
    """人格读取验证失败错误"""
    pass


class MissingRegistryError(Exception):
    """Registry 条目缺失错误"""
    pass
