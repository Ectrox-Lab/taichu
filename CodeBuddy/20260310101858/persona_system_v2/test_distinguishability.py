"""
Role Distinguishability Test
角色可辨识性测试 - 验证发言是否真的能体现角色差异
"""

import random
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score


@dataclass
class TestResult:
    """测试结果"""
    metric_name: str
    score: float
    threshold: float
    passed: bool
    details: Dict = None
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{self.metric_name}: {self.score:.2%} (threshold: {self.threshold:.0%}) {status}"


class RoleDistinguishabilityTester:
    """
    角色可辨识性测试
    
    核心逻辑:
    1. 让多个角色对同一议题发言
    2. 打乱 speaker 名称
    3. 训练分类器从发言反推原角色
    4. 如果分类器能准确识别，说明发言确实体现了角色差异
    """
    
    def __init__(self, num_shuffles: int = 100):
        self.num_shuffles = num_shuffles
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
    
    def test(self,
             issue: str,
             speakers: List[str],
             generate_fn) -> TestResult:
        """
        运行角色可辨识性测试
        
        Args:
            issue: 测试议题
            speakers: 测试角色列表 (如 ["00001", "00012", "guiguzi", "huatuo"])
            generate_fn: 发言生成函数 (speaker_id -> speech_content)
        
        Returns:
            TestResult 包含准确率
        """
        print(f"\n{'='*60}")
        print(f"Role Distinguishability Test")
        print(f"Issue: {issue}")
        print(f"Speakers: {speakers}")
        print(f"{'='*60}\n")
        
        # 生成发言
        speeches = {}
        for speaker in speakers:
            try:
                output = generate_fn(speaker, issue)
                speeches[speaker] = output.content if hasattr(output, 'content') else output
                print(f"Generated speech for {speaker}: {len(speeches[speaker])} chars")
            except Exception as e:
                print(f"Error generating speech for {speaker}: {e}")
                speeches[speaker] = f"[Error: {e}]"
        
        if len(speeches) < 2:
            return TestResult(
                metric_name="role_identification_accuracy",
                score=0.0,
                threshold=0.80,
                passed=False,
                details={"error": "Not enough valid speeches"}
            )
        
        # 多次打乱测试
        accuracies = []
        confusion_matrix = {s: {s2: 0 for s2 in speakers} for s in speakers}
        
        for i in range(self.num_shuffles):
            # 打乱顺序
            shuffled_speakers = random.sample(speakers, len(speakers))
            shuffled_speeches = [speeches[s] for s in shuffled_speakers]
            
            # 尝试识别
            predictions = self._classify_speeches(shuffled_speeches, shuffled_speakers)
            
            # 计算准确率
            correct = sum(1 for pred, actual in zip(predictions, shuffled_speakers) if pred == actual)
            accuracy = correct / len(speakers)
            accuracies.append(accuracy)
            
            # 更新混淆矩阵
            for pred, actual in zip(predictions, shuffled_speakers):
                confusion_matrix[actual][pred] += 1
            
            if i < 3:  # 打印前3次详细结果
                print(f"\nShuffle {i+1}:")
                for pred, actual in zip(predictions, shuffled_speakers):
                    mark = "✓" if pred == actual else "✗"
                    print(f"  {mark} Predicted: {pred:12s} | Actual: {actual}")
        
        # 计算统计结果
        mean_accuracy = np.mean(accuracies)
        std_accuracy = np.std(accuracies)
        
        # 归一化混淆矩阵
        normalized_cm = {}
        for actual in speakers:
            total = sum(confusion_matrix[actual].values())
            normalized_cm[actual] = {pred: count/total for pred, count in confusion_matrix[actual].items()}
        
        print(f"\n{'='*60}")
        print(f"Results:")
        print(f"  Mean Accuracy: {mean_accuracy:.2%} ± {std_accuracy:.2%}")
        print(f"  Min Accuracy: {min(accuracies):.2%}")
        print(f"  Max Accuracy: {max(accuracies):.2%}")
        print(f"{'='*60}\n")
        
        # 打印混淆矩阵
        print("Confusion Matrix (normalized):")
        print(f"{'Actual/Pred':<15}", end="")
        for s in speakers:
            print(f"{s[:8]:<10}", end="")
        print()
        for actual in speakers:
            print(f"{actual[:14]:<15}", end="")
            for pred in speakers:
                score = normalized_cm[actual][pred]
                marker = "*" if actual == pred else " "
                print(f"{marker}{score:.2f}{marker:<3}", end="")
            print()
        
        return TestResult(
            metric_name="role_identification_accuracy",
            score=mean_accuracy,
            threshold=0.80,
            passed=mean_accuracy >= 0.80,
            details={
                "std": std_accuracy,
                "min": min(accuracies),
                "max": max(accuracies),
                "confusion_matrix": normalized_cm
            }
        )
    
    def _classify_speeches(self, speeches: List[str], speakers: List[str]) -> List[str]:
        """
        基于发言内容分类说话人
        
        简单实现: 使用 TF-IDF + 逻辑回归
        实际可用更复杂的模型
        """
        if len(speeches) < 2:
            return speakers  # 无法分类，返回原顺序
        
        try:
            # 特征提取
            X = self.vectorizer.fit_transform(speeches)
            y = list(range(len(speakers)))
            
            # 训练简单分类器
            clf = LogisticRegression(max_iter=1000, random_state=42)
            
            # 使用交叉验证预测
            predictions = []
            for i in range(len(speeches)):
                # 留一法
                train_idx = [j for j in range(len(speeches)) if j != i]
                test_idx = [i]
                
                X_train = X[train_idx]
                y_train = [y[j] for j in train_idx]
                X_test = X[test_idx]
                
                clf.fit(X_train, y_train)
                pred_idx = clf.predict(X_test)[0]
                predictions.append(speakers[pred_idx])
            
            return predictions
            
        except Exception as e:
            print(f"Classification error: {e}")
            # 失败时返回随机猜测
            return random.sample(speakers, len(speakers))


class PairwiseConfusionAnalyzer:
    """两两混淆分析 - 找出最容易被混淆的角色对"""
    
    def analyze(self, confusion_matrix: Dict[str, Dict[str, float]]) -> List[Tuple[str, str, float]]:
        """
        分析哪些角色对最容易混淆
        
        Returns:
            List of (role1, role2, confusion_score) 按混淆程度排序
        """
        confusions = []
        speakers = list(confusion_matrix.keys())
        
        for i, s1 in enumerate(speakers):
            for s2 in speakers[i+1:]:
                # 双向混淆分数
                s1_confused_as_s2 = confusion_matrix[s1][s2]
                s2_confused_as_s1 = confusion_matrix[s2][s1]
                
                avg_confusion = (s1_confused_as_s2 + s2_confused_as_s1) / 2
                confusions.append((s1, s2, avg_confusion))
        
        # 按混淆程度排序
        confusions.sort(key=lambda x: x[2], reverse=True)
        
        return confusions


def run_distinguishability_demo():
    """运行可辨识性测试演示"""
    
    # 模拟发言生成函数 (替换为实际实现)
    def mock_generate(speaker_id: str, issue: str):
        """模拟发言生成 - 用于演示"""
        
        # 不同角色应该有不同风格
        templates = {
            "high_strategic": f"""
从战略层面看，{issue}需要长期规划。
我们必须考虑未来3-5年的影响。
目前的风险评估还不够充分。
""",
            "high_governance": f"""
在治理角度，{issue}存在合规风险。
我们需要更严格的审查机制。
建议设立专门的监督小组。
""",
            "high_execution": f"""
从执行层面，{issue}的关键在于技术实现。
我们需要评估具体的资源需求。
建议先做小规模试点验证。
"""
        }
        
        # 模拟不同的角色
        return type('MockOutput', (), {
            'content': templates.get(speaker_id, f"关于{issue}，我认为...")
        })()
    
    # 运行测试
    tester = RoleDistinguishabilityTester(num_shuffles=50)
    
    result = tester.test(
        issue="strategic_planning",
        speakers=["high_strategic", "high_governance", "high_execution"],
        generate_fn=mock_generate
    )
    
    print(f"\n{'='*60}")
    print(f"FINAL RESULT: {result}")
    print(f"{'='*60}")
    
    return result


if __name__ == "__main__":
    run_distinguishability_demo()
