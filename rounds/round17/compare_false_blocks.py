#!/usr/bin/env python3
"""
Round 17.4 Step 2: Compare live_auto vs live_manual false-block patterns
对比两种来源的误伤模式差异
"""

import json

def extract_false_blocks_by_source():
    """按来源提取false block样本并对比"""
    
    input_file = "/home/admin/CodeBuddy/20260310101858/data/shadow/SHADOW-R17-3-REAL_observations.jsonl"
    
    live_auto_fb = []
    live_manual_fb = []
    
    with open(input_file, "r") as f:
        for line in f:
            obs = json.loads(line.strip())
            if obs["false_block_detected"]:
                if obs["source_type"] == "live_auto":
                    live_auto_fb.append(obs)
                elif obs["source_type"] == "live_manual":
                    live_manual_fb.append(obs)
    
    print("="*70)
    print("Round 17.4 Step 2: False-Block Pattern Comparison")
    print("="*70)
    
    print(f"\n样本数量:")
    print(f"  live_auto: {len(live_auto_fb)}")
    print(f"  live_manual: {len(live_manual_fb)}")
    
    # 对比分析
    print("\n" + "="*70)
    print("对比分析")
    print("="*70)
    
    # 1. Gate失败模式对比
    print("\n1. Gate失败模式对比")
    print("-"*70)
    
    def analyze_gate_failures(samples, label):
        review_fail = sum(1 for obs in samples 
                         if any(c['check_name'] == 'review_minimum' and c['status'] == 'fail' 
                               for c in obs['gate_checks']))
        delib_fail = sum(1 for obs in samples 
                        if any(c['check_name'] == 'deliberation_minimum' and c['status'] == 'fail' 
                              for c in obs['gate_checks']))
        both_fail = sum(1 for obs in samples 
                       if any(c['check_name'] == 'review_minimum' and c['status'] == 'fail' for c in obs['gate_checks'])
                       and any(c['check_name'] == 'deliberation_minimum' and c['status'] == 'fail' for c in obs['gate_checks']))
        
        print(f"\n{label}:")
        print(f"  Review threshold失败: {review_fail}/{len(samples)} ({review_fail/len(samples)*100:.1f}%)")
        print(f"  Deliberation threshold失败: {delib_fail}/{len(samples)} ({delib_fail/len(samples)*100:.1f}%)")
        print(f"  两者都失败: {both_fail}/{len(samples)} ({both_fail/len(samples)*100:.1f}%)")
    
    analyze_gate_failures(live_auto_fb, "live_auto")
    analyze_gate_failures(live_manual_fb, "live_manual")
    
    # 2. 议题类型分布对比
    print("\n2. 议题类型分布对比")
    print("-"*70)
    
    def analyze_issue_types(samples, label):
        issues = {}
        for obs in samples:
            issue = obs['issue_type']
            issues[issue] = issues.get(issue, 0) + 1
        print(f"\n{label}:")
        for issue, count in sorted(issues.items(), key=lambda x: -x[1]):
            print(f"  {issue}: {count} ({count/len(samples)*100:.1f}%)")
    
    analyze_issue_types(live_auto_fb, "live_auto")
    analyze_issue_types(live_manual_fb, "live_manual")
    
    # 3. 风险等级分布对比
    print("\n3. 风险等级分布对比")
    print("-"*70)
    
    def analyze_risk_levels(samples, label):
        risks = {}
        for obs in samples:
            risk = obs['risk_level']
            risks[risk] = risks.get(risk, 0) + 1
        print(f"\n{label}:")
        for risk, count in sorted(risks.items(), key=lambda x: -x[1]):
            print(f"  {risk}: {count} ({count/len(samples)*100:.1f}%)")
    
    analyze_risk_levels(live_auto_fb, "live_auto")
    analyze_risk_levels(live_manual_fb, "live_manual")
    
    # 4. 评分特征对比
    print("\n4. 评分特征对比")
    print("-"*70)
    
    def analyze_scores(samples, label):
        delib_scores = [obs['deliberation_score'] for obs in samples]
        review_scores = [obs['review_score'] for obs in samples]
        
        print(f"\n{label}:")
        print(f"  Deliberation Score - 平均: {sum(delib_scores)/len(delib_scores):.1f}, "
              f"范围: [{min(delib_scores):.1f}, {max(delib_scores):.1f}]")
        print(f"  Review Score - 平均: {sum(review_scores)/len(review_scores):.1f}, "
              f"范围: [{min(review_scores):.1f}, {max(review_scores):.1f}]")
    
    analyze_scores(live_auto_fb, "live_auto")
    analyze_scores(live_manual_fb, "live_manual")
    
    # 5. 关键差异总结
    print("\n" + "="*70)
    print("关键差异总结")
    print("="*70)
    
    print("""
1. Review Threshold敏感度:
   - live_auto: 100% 失败 (3/3)
   - live_manual: 100% 失败 (5/5)
   → 两者都对review threshold敏感

2. Deliberation Threshold敏感度:
   - live_auto: 33% 失败 (1/3)
   - live_manual: 40% 失败 (2/5)
   → live_manual略高

3. 议题类型差异:
   - live_auto: 分散 (routine, strategic, technical各1)
   - live_manual: 集中在routine_approval (60%)

4. 风险等级差异:
   - live_auto: 66% high risk
   - live_manual: 40% medium risk, 40% high risk
   → live_auto误伤更多high risk案例

5. 评分特征:
   - live_auto review score平均更低 (75.8 vs 77.5)
   → review门槛对live_auto更严格
""")
    
    print("="*70)
    print("根因假设")
    print("="*70)
    print("""
假设1 (最可能): review_threshold对live_auto过严
  - live_auto的review评分平均比live_manual低
  - 同样threshold=80，live_auto更容易被拦截
  - 建议: live_auto使用source-aware review_threshold=78

假设2: live_auto的high risk案例评分分布不同
  - live_auto误伤中66%是high risk
  - 可能需要risk-aware调整

假设3: 两类source的评分聚合逻辑存在系统性差异
  - 需要检查评分计算时context是否完整
""")
    
    return live_auto_fb, live_manual_fb

if __name__ == "__main__":
    extract_false_blocks_by_source()
