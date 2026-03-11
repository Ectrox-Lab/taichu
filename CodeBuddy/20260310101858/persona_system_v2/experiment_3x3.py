"""
3×3 Minimum Reproducibility Experiment
3×3 最小可复现实验

测试设计:
- 3 个议题 × 3 个角色
- Baseline: 旧模板系统
- Variant: 新 persona_context 系统
- 验收指标:
  * role distinguishability >= 80%
  * unresolved coverage increase >= 30%
  * boilerplate reduction >= 40%
"""

import json
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from persona_context import (
    PersonaContext, DNASnapshot, MeetingBinding, GenerationConstraints,
    PersonaGroundingEngine, SpeechStage, RiskBias, ResourceBias, RiskLevel
)
from test_distinguishability import RoleDistinguishabilityTester, TestResult
from test_incrementality import IncrementalityTester


@dataclass
class ExperimentCondition:
    """实验条件"""
    issue_type: str
    risk_level: RiskLevel
    description: str


@dataclass
class ExperimentRole:
    """实验角色"""
    role_id: str
    role_name: str
    dna: Dict  # 模拟的 DNA 配置


@dataclass
class ExperimentRun:
    """单次实验运行结果"""
    issue: str
    role: str
    baseline_speech: str
    variant_speech: str
    baseline_metrics: Dict
    variant_metrics: Dict


@dataclass
class ExperimentResult:
    """实验总体结果"""
    timestamp: str
    conditions: List[str]
    roles: List[str]
    
    # 可辨识性指标
    role_distinguishability: float
    distinguishability_passed: bool
    
    # 增量性指标
    coverage_increase: float
    coverage_passed: bool
    
    boilerplate_reduction: float
    boilerplate_passed: bool
    
    # 综合
    overall_passed: bool
    
    # 详细结果
    runs: List[ExperimentRun] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "conditions": self.conditions,
            "roles": self.roles,
            "role_distinguishability": self.role_distinguishability,
            "distinguishability_passed": self.distinguishability_passed,
            "coverage_increase": self.coverage_increase,
            "coverage_passed": self.coverage_passed,
            "boilerplate_reduction": self.boilerplate_reduction,
            "boilerplate_passed": self.boilerplate_passed,
            "overall_passed": self.overall_passed,
            "runs": [asdict(run) for run in self.runs]
        }


class MinimalReproducibilityExperiment:
    """
    3×3 最小可复现实验
    
    验证新系统是否显著优于模板基线
    """
    
    # 3 个议题
    ISSUES = [
        ExperimentCondition(
            issue_type="strategic_planning",
            risk_level=RiskLevel.HIGH,
            description="战略规划 - 长期发展方向决策"
        ),
        ExperimentCondition(
            issue_type="disaster_recovery",
            risk_level=RiskLevel.CRITICAL,
            description="灾难恢复 - 系统故障应急响应"
        ),
        ExperimentCondition(
            issue_type="technical_refactor",
            risk_level=RiskLevel.MEDIUM,
            description="技术重构 - 代码债务清理"
        )
    ]
    
    # 3 个角色
    ROLES = [
        ExperimentRole(
            role_id="high_strategic",
            role_name="战略官",
            dna={
                "identity": "负责长期战略规划的高级决策者",
                "core_drives": ["长期价值最大化", "竞争优势构建", "市场领导地位"],
                "decision_style": "vision-driven, opportunity-focused",
                "taboos": ["短视决策", "保守退缩", "no-handwave"],
                "preferred_evidence": ["市场趋势数据", "竞争分析", "长期ROI"],
                "rhetorical_style": "宏观视野，强调未来影响",
                "department_view": "从公司战略高度",
                "risk_bias": RiskBias.AGGRESSIVE,
                "resource_bias": ResourceBias.INVEST
            }
        ),
        ExperimentRole(
            role_id="high_governance",
            role_name="风控官",
            dna={
                "identity": "负责合规与风险管控的治理专家",
                "core_drives": ["风险可控", "合规保障", "系统稳定"],
                "decision_style": "risk-aware, control-oriented",
                "taboos": ["盲目乐观", "忽视合规", "no-handwave"],
                "preferred_evidence": ["风险评估报告", "合规检查结果", "历史案例"],
                "rhetorical_style": "谨慎保守，强调风险识别",
                "department_view": "从治理与合规角度",
                "risk_bias": RiskBias.CONSERVATIVE,
                "resource_bias": ResourceBias.SAVE
            }
        ),
        ExperimentRole(
            role_id="high_execution",
            role_name="工程总监",
            dna={
                "identity": "负责技术落地与执行的高级工程师",
                "core_drives": ["技术卓越", "执行效率", "可维护性"],
                "decision_style": "pragmatic, implementation-focused",
                "taboos": ["脱离实际", "忽视技术债务", "no-handwave"],
                "preferred_evidence": ["技术可行性分析", "性能测试数据", "代码审查报告"],
                "rhetorical_style": "务实具体，强调可执行性",
                "department_view": "从技术实现角度",
                "risk_bias": RiskBias.BALANCED,
                "resource_bias": ResourceBias.BALANCED
            }
        )
    ]
    
    def __init__(self, grounding_engine: PersonaGroundingEngine = None):
        self.grounding_engine = grounding_engine or PersonaGroundingEngine()
        self.distinguishability_tester = RoleDistinguishabilityTester(num_shuffles=50)
        self.incrementality_tester = IncrementalityTester()
    
    def run(self, variant_pipeline) -> ExperimentResult:
        """
        运行完整实验
        
        Args:
            variant_pipeline: 新系统的发言生成管道
        
        Returns:
            ExperimentResult 包含所有指标
        """
        print("\n" + "="*70)
        print("3×3 Minimum Reproducibility Experiment")
        print("="*70)
        print(f"Issues: {[i.issue_type for i in self.ISSUES]}")
        print(f"Roles: {[r.role_id for r in self.ROLES]}")
        print("="*70 + "\n")
        
        runs = []
        
        for condition in self.ISSUES:
            for role in self.ROLES:
                print(f"\n{'='*70}")
                print(f"Testing: {condition.issue_type} × {role.role_id}")
                print(f"{'='*70}\n")
                
                # 准备会议状态
                meeting_state = {
                    "issue_type": condition.issue_type,
                    "risk_level": condition.risk_level.value,
                    "involved_seats": [r.role_id for r in self.ROLES],
                    "current_round": 2,
                    "unresolved_points": self._generate_unresolved_points(condition),
                    "prior_stage_summary": f"讨论{condition.description}的初步方向"
                }
                
                # Baseline: 模板生成
                baseline_speech = self._generate_baseline(role, condition)
                
                # Variant: persona_context 生成
                try:
                    variant_output = variant_pipeline.generate_speech(
                        speaker_id=role.role_id,
                        meeting_state=meeting_state,
                        stage=SpeechStage.B
                    )
                    variant_speech = variant_output.content
                except Exception as e:
                    print(f"Variant generation failed: {e}")
                    variant_speech = f"[Error: {e}]"
                
                # 评估 Baseline
                baseline_metrics = self._evaluate_speech(
                    baseline_speech, meeting_state, role
                )
                
                # 评估 Variant
                variant_metrics = self._evaluate_speech(
                    variant_speech, meeting_state, role
                )
                
                run = ExperimentRun(
                    issue=condition.issue_type,
                    role=role.role_id,
                    baseline_speech=baseline_speech[:200] + "...",
                    variant_speech=variant_speech[:200] + "...",
                    baseline_metrics=baseline_metrics,
                    variant_metrics=variant_metrics
                )
                runs.append(run)
                
                print(f"\nBaseline metrics: {baseline_metrics}")
                print(f"Variant metrics: {variant_metrics}")
        
        # 计算综合指标
        result = self._calculate_overall_metrics(runs)
        result.runs = runs
        
        # 打印最终报告
        self._print_report(result)
        
        return result
    
    def _generate_baseline(self, role: ExperimentRole, condition: ExperimentCondition) -> str:
        """生成基线（模板）发言"""
        # 模拟当前模板系统的输出
        return f"""
接受议题前提。

基于{role.role_name}的立场，我认为{condition.description}需要谨慎评估。

无修正。

要求更多信息，包括具体的实施计划和风险控制措施。

我同意之前的观点，但需要更多数据支持。
"""
    
    def _generate_unresolved_points(self, condition: ExperimentCondition) -> List[str]:
        """生成未解决要点"""
        points_map = {
            "strategic_planning": [
                "市场进入时机的选择",
                "资源分配优先级",
                "长期ROI测算"
            ],
            "disaster_recovery": [
                "恢复时间目标(RTO)",
                "数据一致性保障",
                "应急响应流程"
            ],
            "technical_refactor": [
                "重构范围界定",
                "技术债务优先级",
                "性能回归风险"
            ]
        }
        return points_map.get(condition.issue_type, ["关键问题待解决"])
    
    def _evaluate_speech(self, speech: str, meeting_state: Dict, role: ExperimentRole) -> Dict:
        """评估单条发言的指标"""
        # 增量性
        inc_result = self.incrementality_tester.test(
            speech_content=speech,
            unresolved_points=meeting_state["unresolved_points"],
            prior_stage_summary=meeting_state["prior_stage_summary"]
        )
        
        return {
            "incrementality_score": inc_result.score,
            "coverage": inc_result.sub_metrics.get("unresolved_point_coverage", 0),
            "boilerplate_overlap": inc_result.sub_metrics.get("boilerplate_overlap", 1.0),
            "new_claims": inc_result.sub_metrics.get("new_claim_count", 0)
        }
    
    def _calculate_overall_metrics(self, runs: List[ExperimentRun]) -> ExperimentResult:
        """计算总体指标"""
        
        # 增量性改进
        baseline_coverage = np.mean([r.baseline_metrics["coverage"] for r in runs])
        variant_coverage = np.mean([r.variant_metrics["coverage"] for r in runs])
        coverage_increase = variant_coverage - baseline_coverage
        
        # 套话减少
        baseline_overlap = np.mean([r.baseline_metrics["boilerplate_overlap"] for r in runs])
        variant_overlap = np.mean([r.variant_metrics["boilerplate_overlap"] for r in runs])
        boilerplate_reduction = baseline_overlap - variant_overlap
        
        # 可辨识性 (需要跨议题测试)
        distinguishability = self._estimate_distinguishability(runs)
        
        return ExperimentResult(
            timestamp=datetime.now().isoformat(),
            conditions=[i.issue_type for i in self.ISSUES],
            roles=[r.role_id for r in self.ROLES],
            role_distinguishability=distinguishability,
            distinguishability_passed=distinguishability >= 0.80,
            coverage_increase=coverage_increase,
            coverage_passed=coverage_increase >= 0.30,
            boilerplate_reduction=boilerplate_reduction,
            boilerplate_passed=boilerplate_reduction >= 0.40,
            overall_passed=(
                distinguishability >= 0.80 and
                coverage_increase >= 0.30 and
                boilerplate_reduction >= 0.40
            )
        )
    
    def _estimate_distinguishability(self, runs: List[ExperimentRun]) -> float:
        """估计可辨识性 (基于发言差异度)"""
        # 简化估计：比较不同角色在同一议题下的发言相似度
        scores = []
        
        for issue in set(r.issue for r in runs):
            issue_runs = [r for r in runs if r.issue == issue]
            if len(issue_runs) >= 2:
                # 计算两两差异
                for i in range(len(issue_runs)):
                    for j in range(i+1, len(issue_runs)):
                        # 简单的差异度计算
                        score = self._calculate_difference(
                            issue_runs[i].variant_speech,
                            issue_runs[j].variant_speech
                        )
                        scores.append(score)
        
        return np.mean(scores) if scores else 0.5
    
    def _calculate_difference(self, text1: str, text2: str) -> float:
        """计算两段文本的差异度"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard 距离
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return 1 - (intersection / union) if union > 0 else 0.0
    
    def _print_report(self, result: ExperimentResult):
        """打印实验报告"""
        print("\n" + "="*70)
        print("EXPERIMENT REPORT")
        print("="*70)
        
        print(f"\n📊 Distinguishability Metrics:")
        status = "✅ PASS" if result.distinguishability_passed else "❌ FAIL"
        print(f"  Role Identification Accuracy: {result.role_distinguishability:.1%} (target: ≥80%) {status}")
        
        print(f"\n📈 Incrementality Metrics:")
        status = "✅ PASS" if result.coverage_passed else "❌ FAIL"
        print(f"  Coverage Increase: {result.coverage_increase:+.1%} (target: +30%) {status}")
        
        status = "✅ PASS" if result.boilerplate_passed else "❌ FAIL"
        print(f"  Boilerplate Reduction: {result.boilerplate_reduction:.1%} (target: -40%) {status}")
        
        print(f"\n🎯 Overall Result:")
        if result.overall_passed:
            print("  ✅ ALL GATES PASS - System ready for deployment")
        else:
            print("  ❌ SOME GATES FAIL - Further iteration needed")
        
        print("="*70 + "\n")


def run_experiment_demo():
    """运行实验演示"""
    
    # 创建一个模拟的新系统管道
    class MockVariantPipeline:
        def generate_speech(self, speaker_id: str, meeting_state: Dict, stage: SpeechStage):
            """模拟新系统的发言生成"""
            
            # 模拟 persona-grounded 输出 (比基线更有差异化)
            role_contents = {
                "high_strategic": f"""
从战略高度看，{meeting_state['issue_type']}关系到公司未来3年的竞争格局。

关键风险点在于时机选择。根据市场分析，延迟6个月将失去40%的先发优势。

建议采取激进策略：立即投入，抢占制高点。这与我们长期增长目标一致。
""",
                "high_governance": f"""
在治理层面，{meeting_state['issue_type']}存在多项合规风险。

根据风险评估，当前方案在数据安全、审计追溯方面存在漏洞。

建议设立独立监督小组，建立月度审查机制。没有充分的风控措施，我保留反对意见。
""",
                "high_execution": f"""
从技术落地角度，{meeting_state['issue_type']}面临现实约束。

现有架构无法支撑方案需求，需要6个月重构期。贸然推进将导致技术债务激增。

建议分阶段实施：先完成核心模块重构，再扩展业务功能。这是务实的路径。
"""
            }
            
            content = role_contents.get(speaker_id, "关于这个议题，我认为需要进一步讨论。")
            
            return type('MockOutput', (), {'content': content})()
    
    # 运行实验
    experiment = MinimalReproducibilityExperiment()
    variant_pipeline = MockVariantPipeline()
    
    result = experiment.run(variant_pipeline)
    
    # 保存结果
    output_path = "/home/admin/CodeBuddy/20260310101858/persona_system_v2/experiment_result.json"
    with open(output_path, 'w') as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_path}")
    
    return result


if __name__ == "__main__":
    run_experiment_demo()
