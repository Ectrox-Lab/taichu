#!/usr/bin/env python3
"""
Round 17.4 Step 1: Extract live_auto false-block samples
提取 live_auto 误伤样本进行分型分析
"""

import json

def extract_live_auto_false_blocks():
    """提取所有 live_auto 且 false_block_detected 为 true 的样本"""
    
    input_file = "/home/admin/CodeBuddy/20260310101858/data/shadow/SHADOW-R17-3-REAL_observations.jsonl"
    output_file = "/home/admin/CodeBuddy/20260310101858/data/shadow/live_auto_false_blocks.json"
    
    false_blocks = []
    
    with open(input_file, "r") as f:
        for line in f:
            obs = json.loads(line.strip())
            if obs["source_type"] == "live_auto" and obs["false_block_detected"]:
                false_blocks.append(obs)
    
    # 保存提取的样本
    with open(output_file, "w") as f:
        json.dump(false_blocks, f, indent=2, ensure_ascii=False)
    
    # 打印分析报告
    print("="*70)
    print("Round 17.4 Step 1: live_auto False-Block Sample Extraction")
    print("="*70)
    print(f"\n提取样本数: {len(false_blocks)}")
    
    if false_blocks:
        print("\n样本详情:")
        print("-"*70)
        
        # 按议题类型分组
        by_issue = {}
        by_risk = {}
        
        for i, obs in enumerate(false_blocks, 1):
            print(f"\n样本 {i}: {obs['meeting_id']}")
            print(f"  议题类型: {obs['issue_type']}")
            print(f"  风险等级: {obs['risk_level']}")
            print(f"  旧系统决策: {obs['legacy_decision']}")
            print(f"  影子系统决策: {obs['shadow_decision']}")
            print(f"  Deliberation Score: {obs['deliberation_score']}")
            print(f"  Review Score: {obs['review_score']}")
            print(f"  Shadow Confidence: {obs['shadow_confidence']}")
            
            # 检查哪个gate失败了
            for check in obs['gate_checks']:
                if check['status'] == 'fail':
                    print(f"  ❌ Failed: {check['check_name']} ({check['score']:.1f} < {check['threshold']})")
            
            # 分类统计
            issue = obs['issue_type']
            risk = obs['risk_level']
            by_issue[issue] = by_issue.get(issue, 0) + 1
            by_risk[risk] = by_risk.get(risk, 0) + 1
        
        print("\n" + "="*70)
        print("分型统计")
        print("="*70)
        
        print("\n按议题类型:")
        for issue, count in sorted(by_issue.items(), key=lambda x: -x[1]):
            print(f"  {issue}: {count}")
        
        print("\n按风险等级:")
        for risk, count in sorted(by_risk.items(), key=lambda x: -x[1]):
            print(f"  {risk}: {count}")
        
        # 根因初步归类
        print("\n" + "="*70)
        print("根因初步归类")
        print("="*70)
        
        review_failures = sum(1 for obs in false_blocks 
                             if any(c['check_name'] == 'review_minimum' and c['status'] == 'fail' 
                                   for c in obs['gate_checks']))
        deliberation_failures = sum(1 for obs in false_blocks 
                                   if any(c['check_name'] == 'deliberation_minimum' and c['status'] == 'fail' 
                                         for c in obs['gate_checks']))
        
        print(f"\nReview threshold 失败: {review_failures}/{len(false_blocks)}")
        print(f"Deliberation threshold 失败: {deliberation_failures}/{len(false_blocks)}")
        
        # 检查是否有accepted_risk标记
        accepted_risk_count = sum(1 for obs in false_blocks if obs['accepted_risk_detected'])
        print(f"\nAccepted-risk 标记: {accepted_risk_count}/{len(false_blocks)}")
        
    print(f"\n📄 样本已保存: {output_file}")
    print("\n下一步: 与 live_manual false-block 样本对比，识别差异模式")
    
    return false_blocks

if __name__ == "__main__":
    extract_live_auto_false_blocks()
