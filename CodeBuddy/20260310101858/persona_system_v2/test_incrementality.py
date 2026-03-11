"""
Incrementality Test
信息增量测试 - 验证发言是否有信息增量
"""

import re
import numpy as np
from typing import List, Dict, Set
from dataclasses import dataclass, field
from collections import Counter
from difflib import SequenceMatcher


@dataclass
class IncrementalityMetrics:
    """增量性指标"""
    unresolved_point_coverage: float  # 未解决点覆盖率
    new_claim_count: int              # 新主张数量
    contradiction_resolved: int       # 解决的矛盾数
    contradiction_introduced: int     # 引入的矛盾数
    boilerplate_overlap: float        # 套话重叠率
    evidence_cited: int               # 引用的证据数
    
    def overall_score(self) -> float:
        """综合增量分数"""
        return (
            self.unresolved_point_coverage * 0.4 +
            min(self.new_claim_count / 3, 1.0) * 0.3 +
            (1 - self.boilerplate_overlap) * 0.3
        )


@dataclass
class TestResult:
    """测试结果"""
    metric_name: str
    score: float
    threshold: float
    passed: bool
    sub_metrics: Dict = field(default_factory=dict)
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{self.metric_name}: {self.score:.2%} (threshold: {self.threshold:.0%}) {status}"


class IncrementalityTester:
    """
    信息增量测试
    
    核心逻辑:
    1. 比较发言与前序阶段总结
    2. 检查未解决要点的覆盖
    3. 检测套话/模板重叠
    4. 统计新主张和矛盾解决
    """
    
    def __init__(self):
        # 常见的套话/模板短语
        self.boilerplate_phrases = [
            "接受议题前提",
            "无修正",
            "基于我的立场",
            "要求更多信息",
            "我认为",
            "我觉得",
            "大致可行",
            "应该没问题",
            "基本同意",
            "原则上支持"
        ]
    
    def test(self,
             speech_content: str,
             unresolved_points: List[str],
             prior_stage_summary: str,
             speaker_history: List[str] = None) -> TestResult:
        """
        测试单条发言的增量性
        
        Args:
            speech_content: 发言内容
            unresolved_points: 当前未解决要点
            prior_stage_summary: 前序阶段总结
            speaker_history: 该角色历史发言 (用于检测套话)
        
        Returns:
            TestResult 包含增量性评分
        """
        print(f"\n{'='*60}")
        print(f"Incrementality Test")
        print(f"Speech length: {len(speech_content)} chars")
        print(f"Unresolved points: {len(unresolved_points)}")
        print(f"{'='*60}\n")
        
        # 1. 未解决点覆盖率
        coverage = self._calculate_coverage(speech_content, unresolved_points)
        print(f"Unresolved point coverage: {coverage:.1%}")
        print(f"  Covered: {int(coverage * len(unresolved_points))}/{len(unresolved_points)}")
        
        # 2. 新主张数量
        new_claims = self._extract_new_claims(speech_content, prior_stage_summary)
        print(f"\nNew claims: {len(new_claims)}")
        for i, claim in enumerate(new_claims[:5], 1):
            print(f"  {i}. {claim[:60]}...")
        
        # 3. 矛盾解决/引入
        contradictions = self._analyze_contradictions(speech_content, prior_stage_summary)
        print(f"\nContradictions:")
        print(f"  Resolved: {contradictions['resolved']}")
        print(f"  Introduced: {contradictions['introduced']}")
        
        # 4. 套话重叠率
        overlap = self._calculate_boilerplate_overlap(speech_content, speaker_history or [])
        print(f"\nBoilerplate overlap: {overlap:.1%}")
        
        # 5. 证据引用
        evidence_count = self._count_evidence_citations(speech_content)
        print(f"Evidence citations: {evidence_count}")
        
        # 计算综合评分
        metrics = IncrementalityMetrics(
            unresolved_point_coverage=coverage,
            new_claim_count=len(new_claims),
            contradiction_resolved=contradictions['resolved'],
            contradiction_introduced=contradictions['introduced'],
            boilerplate_overlap=overlap,
            evidence_cited=evidence_count
        )
        
        score = metrics.overall_score()
        
        print(f"\n{'='*60}")
        print(f"Overall incrementality score: {score:.2%}")
        print(f"{'='*60}\n")
        
        # 验收标准
        passed = (
            coverage >= 0.30 and           # 覆盖至少30%未解决点
            overlap <= 0.40                 # 套话重叠不超过40%
        )
        
        return TestResult(
            metric_name="incrementality",
            score=score,
            threshold=0.70,
            passed=passed,
            sub_metrics={
                "unresolved_point_coverage": coverage,
                "new_claim_count": len(new_claims),
                "contradiction_resolved": contradictions['resolved'],
                "contradiction_introduced": contradictions['introduced'],
                "boilerplate_overlap": overlap,
                "evidence_cited": evidence_count
            }
        )
    
    def _calculate_coverage(self, speech: str, unresolved_points: List[str]) -> float:
        """计算未解决点覆盖率"""
        if not unresolved_points:
            return 1.0
        
        covered = 0
        for point in unresolved_points:
            # 检查发言是否提到该要点
            if self._mentions(speech, point):
                covered += 1
        
        return covered / len(unresolved_points)
    
    def _mentions(self, text: str, point: str) -> bool:
        """检查文本是否提到要点"""
        # 简单的关键词匹配
        point_keywords = set(point.lower().split())
        text_lower = text.lower()
        
        # 至少匹配50%的关键词
        matched = sum(1 for kw in point_keywords if kw in text_lower)
        return matched >= len(point_keywords) * 0.5
    
    def _extract_new_claims(self, speech: str, prior_summary: str) -> List[str]:
        """提取新主张 (不在前序总结中的内容)"""
        # 分句
        sentences = re.split(r'[。！？\n]+', speech)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        new_claims = []
        for sentence in sentences:
            # 如果句子与前序总结的相似度低，认为是新主张
            similarity = SequenceMatcher(None, sentence.lower(), prior_summary.lower()).ratio()
            if similarity < 0.5:  # 相似度阈值
                # 检查是否是主张性语句
                if self._is_claim_sentence(sentence):
                    new_claims.append(sentence)
        
        return new_claims
    
    def _is_claim_sentence(self, sentence: str) -> bool:
        """判断是否是主张性语句"""
        claim_indicators = [
            "应该", "需要", "必须", "建议", "要求",
            "关键", "核心", "重点", "首要",
            "风险", "问题", "机会", "优势", "劣势"
        ]
        return any(indicator in sentence for indicator in claim_indicators)
    
    def _analyze_contradictions(self, speech: str, prior_summary: str) -> Dict[str, int]:
        """分析矛盾解决/引入"""
        # 简化实现：检测观点方向的变化
        
        positive_indicators = ["支持", "赞成", "同意", "可行", "优势"]
        negative_indicators = ["反对", "质疑", "风险", "问题", "不可行"]
        
        prior_positive = sum(1 for ind in positive_indicators if ind in prior_summary)
        prior_negative = sum(1 for ind in negative_indicators if ind in prior_summary)
        prior_stance = "positive" if prior_positive > prior_negative else "negative"
        
        speech_positive = sum(1 for ind in positive_indicators if ind in speech)
        speech_negative = sum(1 for ind in negative_indicators if ind in speech)
        speech_stance = "positive" if speech_positive > speech_negative else "negative"
        
        if prior_stance != speech_stance:
            # 立场转变，可能是解决或引入矛盾
            return {"resolved": 1, "introduced": 0}
        
        return {"resolved": 0, "introduced": 0}
    
    def _calculate_boilerplate_overlap(self, speech: str, history: List[str]) -> float:
        """计算套话重叠率"""
        # 1. 与内置套话模板的重叠
        boilerplate_matches = sum(1 for phrase in self.boilerplate_phrases 
                                  if phrase in speech)
        
        # 2. 与历史发言的重叠
        history_overlap = 0.0
        if history:
            similarities = []
            for hist_speech in history[-5:]:  # 最近5条
                sim = SequenceMatcher(None, speech, hist_speech).ratio()
                similarities.append(sim)
            history_overlap = max(similarities) if similarities else 0.0
        
        # 综合重叠率
        template_ratio = boilerplate_matches / len(self.boilerplate_phrases)
        combined_overlap = max(template_ratio, history_overlap)
        
        return min(combined_overlap, 1.0)
    
    def _count_evidence_citations(self, speech: str) -> int:
        """统计证据引用"""
        evidence_patterns = [
            r'\d+[%％]',  # 百分比
            r'\d+[万亿]',  # 金额
            r'20\d{2}年?',  # 年份
            r'根据.*?报告',
            r'数据显示',
            r'统计表明',
            r'调研发现',
            r'案例分析'
        ]
        
        count = 0
        for pattern in evidence_patterns:
            count += len(re.findall(pattern, speech))
        
        return count


class CrossTopicConsistencyTester:
    """跨议题一致性测试 - 同一角色在不同议题下应保持一致的核心特征"""
    
    def test(self,
             speaker_id: str,
             issues: List[str],
             generate_fn) -> TestResult:
        """
        测试同一角色在不同议题下的一致性
        
        Returns:
            TestResult 包含一致性评分
        """
        print(f"\n{'='*60}")
        print(f"Cross-Topic Consistency Test")
        print(f"Speaker: {speaker_id}")
        print(f"Issues: {issues}")
        print(f"{'='*60}\n")
        
        # 生成不同议题的发言
        speeches = []
        for issue in issues:
            output = generate_fn(speaker_id, issue)
            content = output.content if hasattr(output, 'content') else output
            speeches.append(content)
            print(f"Generated for {issue}: {len(content)} chars")
        
        # 分析一致性特征
        consistent_features = self._extract_consistent_features(speeches)
        
        print(f"\nConsistent features across topics:")
        for feature, score in consistent_features.items():
            print(f"  {feature}: {score:.2%}")
        
        # 计算一致性分数
        consistency_score = np.mean(list(consistent_features.values()))
        
        print(f"\n{'='*60}")
        print(f"Overall consistency: {consistency_score:.2%}")
        print(f"{'='*60}\n")
        
        return TestResult(
            metric_name="cross_topic_consistency",
            score=consistency_score,
            threshold=0.60,
            passed=consistency_score >= 0.60
        )
    
    def _extract_consistent_features(self, speeches: List[str]) -> Dict[str, float]:
        """提取跨议题一致的特征"""
        features = {}
        
        # 1. 词汇风格一致性
        all_words = []
        for speech in speeches:
            words = set(re.findall(r'\w+', speech.lower()))
            all_words.append(words)
        
        # Jaccard 相似度
        similarities = []
        for i in range(len(all_words)):
            for j in range(i+1, len(all_words)):
                intersection = len(all_words[i] & all_words[j])
                union = len(all_words[i] | all_words[j])
                if union > 0:
                    similarities.append(intersection / union)
        
        features["vocabulary_consistency"] = np.mean(similarities) if similarities else 0.0
        
        # 2. 句式风格一致性
        sentence_patterns = []
        for speech in speeches:
            patterns = Counter(re.findall(r'[应该|需要|必须|建议].*?[。！]', speech))
            sentence_patterns.append(patterns)
        
        # 3. 立场倾向一致性
        stance_keywords = {
            "conservative": ["谨慎", "风险", "保守", "稳健"],
            "aggressive": ["机会", "突破", "创新", "激进"]
        }
        
        stance_scores = []
        for speech in speeches:
            conservative = sum(1 for kw in stance_keywords["conservative"] if kw in speech)
            aggressive = sum(1 for kw in stance_keywords["aggressive"] if kw in speech)
            stance_scores.append("conservative" if conservative > aggressive else "aggressive")
        
        # 检查立场是否一致
        features["stance_consistency"] = 1.0 if len(set(stance_scores)) == 1 else 0.5
        
        return features


def run_incrementality_demo():
    """运行增量性测试演示"""
    
    tester = IncrementalityTester()
    
    # 测试高增量发言
    high_increment_speech = """
针对当前战略规划的三个未解决点，我逐一回应：

第一，关于市场进入时机的风险评估，数据显示竞争对手已在东南亚布局（2023年市场份额增长15%），
我们若延迟至Q3启动，将失去先发优势。建议立即成立专项小组。

第二，资源分配方案需要调整。根据财务测算，原方案在第二年度会出现30%的资金缺口，
必须重新评估各业务线的投入比例。

第三，技术实现路径存在风险。现有架构无法支撑百万级并发，需要重构核心模块。
建议引入外部技术顾问进行独立评估。

我的核心主张是：在确保风险可控的前提下，优先保障技术债务清理，而非盲目扩张。
这与我们部门一贯的稳健风格一致。
"""
    
    # 测试低增量发言 (模板化)
    low_increment_speech = """
接受议题前提。

无修正。

基于我的立场，我认为这个议题需要更多信息。

我同意之前的观点，大致可行。

要求更多信息后再做决定。
"""
    
    unresolved = [
        "市场进入时机的风险评估",
        "资源分配方案的可行性",
        "技术实现路径的可行性"
    ]
    
    prior_summary = "会议讨论了战略规划的初步方向，认为需要进一步评估风险和资源需求。"
    
    print("="*60)
    print("Testing HIGH incrementality speech:")
    print("="*60)
    result_high = tester.test(high_increment_speech, unresolved, prior_summary)
    print(f"\nResult: {result_high}")
    
    print("\n" + "="*60)
    print("Testing LOW incrementality speech:")
    print("="*60)
    result_low = tester.test(low_increment_speech, unresolved, prior_summary)
    print(f"\nResult: {result_low}")
    
    return result_high, result_low


if __name__ == "__main__":
    run_incrementality_demo()
