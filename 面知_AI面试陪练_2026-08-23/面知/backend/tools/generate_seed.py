# -*- coding: utf-8 -*-
"""面知 种子数据生成器：一次定义 104 条「企业 × 岗位」配置与 124 道面试题，
输出后端 JSON（app/seed_data/*.json）与前端 TS（frontend/src/mock/seed_data.ts），
保证前后端数据完全一致，也便于后续用 CSV/JSON 导入合并。

题目来源：q1–q35 为通用题型基座；q36+ 参考公开面经按企业与岗位风格撰写，
非企业官方真题原文，对外表述统一为「按企业岗位标注的面试题」。

用法：python tools/generate_seed.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# 一、企业岗位池（企业 → 岗位配置 + 岗位名列表）
# 字段：industry 行业 / duration 分钟 / total 题量 / mode 模式 / answer_mode 答题方式 / types 题型
# ============================================================
COMPANIES = {
    # ---------- 互联网（47） ----------
    "字节跳动": {"industry": "互联网", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "text",
               "types": ["技术深挖", "行为面试 STAR", "项目经历"],
               "roles": ["后端开发工程师", "算法工程师", "前端开发工程师", "客户端开发工程师",
                         "测试开发工程师", "大数据开发工程师", "产品经理", "数据分析师"]},
    "腾讯": {"industry": "互联网", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "text",
            "types": ["AI全栈", "技术深挖", "产品分析", "行为面试 STAR"],
            "roles": ["AI全栈工程师", "后端开发工程师", "前端开发工程师", "产品经理",
                      "游戏策划", "游戏客户端开发工程师", "云产品经理", "内容运营"]},
    "阿里巴巴": {"industry": "互联网", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "text",
               "types": ["技术深挖", "电商运营", "行为面试 STAR"],
               "roles": ["Java开发工程师", "算法工程师", "前端开发工程师", "产品经理", "电商运营"]},
    "美团": {"industry": "互联网", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "text",
            "types": ["技术深挖", "行为面试 STAR", "情景模拟"],
            "roles": ["后端开发工程师", "算法工程师", "产品经理", "配送运营专员"]},
    "百度": {"industry": "互联网", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "text",
            "types": ["技术深挖", "算法题", "行为面试 STAR"],
            "roles": ["算法工程师", "后端开发工程师", "自动驾驶工程师"]},
    "京东": {"industry": "互联网", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "text",
            "types": ["技术深挖", "物流运营", "行为面试 STAR"],
            "roles": ["Java开发工程师", "产品经理", "物流管培生"]},
    "网易": {"industry": "互联网", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "text",
            "types": ["游戏策划", "产品分析", "行为面试 STAR"],
            "roles": ["游戏策划", "游戏开发工程师", "产品经理"]},
    "拼多多": {"industry": "互联网", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "text",
              "types": ["技术深挖", "电商运营"],
              "roles": ["后端开发工程师", "电商运营专员"]},
    "快手": {"industry": "互联网", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "text",
            "types": ["技术深挖", "产品分析"],
            "roles": ["后端开发工程师", "算法工程师"]},
    "小红书": {"industry": "互联网", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "text",
              "types": ["产品分析", "社区运营", "情景模拟"],
              "roles": ["产品经理", "内容运营专员"]},
    "哔哩哔哩": {"industry": "互联网", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "voice",
               "types": ["内容运营", "产品分析"],
               "roles": ["内容运营专员", "产品经理"]},
    "滴滴出行": {"industry": "互联网", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "text",
               "types": ["技术深挖"],
               "roles": ["后端开发工程师"]},
    "小米": {"industry": "互联网", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "text",
            "types": ["技术深挖", "硬件基础", "行为面试 STAR"],
            "roles": ["安卓开发工程师", "MIUI产品经理", "硬件测试工程师", "嵌入式开发工程师"]},
    # ---------- 国企央企（18） ----------
    "国家电网": {"industry": "国企", "duration": 25, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["综合素养", "专业基础", "时政认知"],
               "roles": ["电气工程岗", "信息通信岗", "财务管理岗", "综合管理岗"]},
    "中国移动": {"industry": "国企", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["综合素养", "专业基础", "时政认知"],
               "roles": ["网络工程师", "市场运营岗", "信息技术岗"]},
    "中国石油": {"industry": "国企", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["综合素养", "专业基础", "情景模拟"],
               "roles": ["油气储运岗", "安全管理岗"]},
    "中国石化": {"industry": "国企", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["综合素养", "专业基础", "情景模拟"],
               "roles": ["化工工艺岗", "安全环保岗"]},
    "中国建筑": {"industry": "国企", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["专业基础", "工程管理", "情景模拟"],
               "roles": ["土木工程师", "工程管理岗"]},
    "中国烟草": {"industry": "国企", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "text",
               "types": ["综合素养", "情景模拟"],
               "roles": ["综合管理岗", "市场营销岗"]},
    "工商银行": {"industry": "国企", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["综合素养", "金融科技", "情景模拟"],
               "roles": ["金融科技岗", "综合业务岗", "客户经理岗"]},
    # ---------- 外企（12） ----------
    "微软中国": {"industry": "外企", "duration": 25, "total": 8, "mode": "normal", "answer_mode": "text",
               "types": ["英文面试", "技术深挖", "系统设计"],
               "roles": ["软件开发工程师", "云计算工程师"]},
    "苹果中国": {"industry": "外企", "duration": 25, "total": 8, "mode": "normal", "answer_mode": "text",
               "types": ["英文面试", "技术深挖", "硬件基础"],
               "roles": ["软件工程师"]},
    "特斯拉中国": {"industry": "外企", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "text",
                 "types": ["英文面试", "专业基础", "供应链"],
                 "roles": ["工艺工程师"]},
    "宝洁": {"industry": "外企", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "voice",
            "types": ["行为面试 STAR", "英文面试", "供应链"],
            "roles": ["供应链管培生", "市场管培生"]},
    "联合利华": {"industry": "外企", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "voice",
               "types": ["行为面试 STAR", "市场分析"],
               "roles": ["市场管培生", "销售管培生"]},
    "欧莱雅中国": {"industry": "外企", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "voice",
                 "types": ["市场分析", "行为面试 STAR"],
                 "roles": ["市场管培生"]},
    "四大会计师事务所": {"industry": "外企", "duration": 25, "total": 10, "mode": "pressure", "answer_mode": "text",
                    "types": ["案例分析", "英文面试", "专业基础"],
                    "roles": ["审计助理", "咨询顾问", "税务助理"]},
    # ---------- 金融（6） ----------
    "蚂蚁集团": {"industry": "互联网", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "text",
               "types": ["技术深挖", "金融风控"],
               "roles": ["后端开发工程师", "算法工程师", "金融风控岗"]},
    "招商银行": {"industry": "国企", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["综合素养", "金融科技", "情景模拟"],
               "roles": ["金融科技岗", "零售客户经理"]},
    "中金公司": {"industry": "外企", "duration": 25, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["专业基础", "案例分析", "英文面试"],
               "roles": ["投行分析员"]},
    # ---------- 制造/科技（13） ----------
    "华为": {"industry": "制造业", "duration": 25, "total": 10, "mode": "pressure", "answer_mode": "text",
            "types": ["AI全栈", "技术深挖", "综合素养", "压力测试"],
            "roles": ["AI全栈工程师", "通信研发工程师", "嵌入式软件工程师", "硬件工程师", "海外销售经理"]},
    "大疆": {"industry": "制造业", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
            "types": ["技术深挖", "专业基础"],
            "roles": ["嵌入式软件工程师", "算法工程师"]},
    "比亚迪": {"industry": "制造业", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
              "types": ["技术深挖", "专业基础", "市场分析"],
              "roles": ["电池研发工程师", "整车研发工程师"]},
    "宁德时代": {"industry": "制造业", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["技术深挖", "专业基础"],
               "roles": ["电池系统工程师", "材料研发工程师"]},
    "海康威视": {"industry": "制造业", "duration": 20, "total": 10, "mode": "pressure", "answer_mode": "text",
               "types": ["技术深挖", "算法基础"],
               "roles": ["算法工程师", "嵌入式工程师"]},
    # ---------- 快消/医药/文职（8） ----------
    "伊利集团": {"industry": "快消", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "voice",
               "types": ["市场分析", "情景模拟"],
               "roles": ["市场管培生", "销售管培生"]},
    "玛氏中国": {"industry": "快消", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "voice",
               "types": ["行为面试 STAR", "供应链"],
               "roles": ["销售管培生", "供应链管培生"]},
    "药明康德": {"industry": "医药", "duration": 20, "total": 8, "mode": "normal", "answer_mode": "text",
               "types": ["专业基础", "行为面试 STAR"],
               "roles": ["药物研发岗", "分析化学岗"]},
    "通用行政": {"industry": "文职", "duration": 15, "total": 8, "mode": "normal", "answer_mode": "text",
               "types": ["情景模拟", "行为面试 STAR"],
               "roles": ["人力资源专员", "行政管理专员"]},
}

# 企业英文 id 前缀
EN_ID = {
    "字节跳动": "bytedance", "腾讯": "tencent", "阿里巴巴": "alibaba", "美团": "meituan",
    "百度": "baidu", "京东": "jd", "网易": "netease", "拼多多": "pdd", "快手": "kuaishou",
    "小红书": "xiaohongshu", "哔哩哔哩": "bilibili", "滴滴出行": "didi", "小米": "xiaomi",
    "国家电网": "sgcc", "中国移动": "cmcc", "中国石油": "petrochina", "中国石化": "sinopec",
    "中国建筑": "cscec", "中国烟草": "tobacco", "工商银行": "icbc", "微软中国": "microsoft",
    "苹果中国": "apple", "特斯拉中国": "tesla", "宝洁": "pg", "联合利华": "unilever",
    "欧莱雅中国": "loreal", "四大会计师事务所": "big4", "蚂蚁集团": "ant", "招商银行": "cmb",
    "中金公司": "cicc", "华为": "huawei", "大疆": "dji", "比亚迪": "byd", "宁德时代": "catl",
    "海康威视": "hikvision", "伊利集团": "yili", "玛氏中国": "mars", "药明康德": "wuxiapptec",
    "通用行政": "admin",
}


# 岗位级题型覆盖
# 企业默认 types 是按技术岗设计的，套用到产品/运营/销售/职能岗位会出现
# 「产品经理被抽到缓存架构」「销售岗被抽到电池热管理」这类岗位与题目错位。
# 这里按 (企业, 岗位) 单独声明题型，优先级高于企业默认值。
ROLE_TYPE_OVERRIDES = {
    # --- 互联网：产品 / 运营 / 职能 ---
    ("字节跳动", "产品经理"): ["产品分析", "行为面试 STAR", "项目经历"],
    ("腾讯", "游戏策划"): ["游戏策划", "产品分析", "行为面试 STAR"],
    ("腾讯", "内容运营"): ["内容运营", "产品分析", "行为面试 STAR"],
    ("阿里巴巴", "产品经理"): ["产品分析", "电商运营", "行为面试 STAR"],
    ("阿里巴巴", "电商运营"): ["电商运营", "产品分析", "情景模拟"],
    ("美团", "产品经理"): ["产品分析", "情景模拟", "行为面试 STAR"],
    ("美团", "配送运营专员"): ["情景模拟", "物流运营", "行为面试 STAR"],
    ("京东", "产品经理"): ["产品分析", "物流运营", "行为面试 STAR"],
    ("京东", "物流管培生"): ["物流运营", "情景模拟", "行为面试 STAR"],
    ("网易", "游戏开发工程师"): ["技术深挖", "游戏策划", "行为面试 STAR"],
    ("拼多多", "电商运营专员"): ["电商运营", "产品分析", "情景模拟"],
    ("小米", "MIUI产品经理"): ["产品分析", "技术深挖", "行为面试 STAR"],
    ("小米", "硬件测试工程师"): ["硬件基础", "专业基础", "行为面试 STAR"],
    ("哔哩哔哩", "产品经理"): ["产品分析", "内容运营", "行为面试 STAR"],
    ("小红书", "产品经理"): ["产品分析", "社区运营", "行为面试 STAR"],
    # --- 互联网：研发岗去掉与本岗位无关的运营题型 ---
    ("阿里巴巴", "Java开发工程师"): ["技术深挖", "行为面试 STAR", "系统设计"],
    ("阿里巴巴", "算法工程师"): ["技术深挖", "算法基础", "行为面试 STAR"],
    ("阿里巴巴", "前端开发工程师"): ["技术深挖", "行为面试 STAR", "系统设计"],
    ("拼多多", "后端开发工程师"): ["技术深挖", "行为面试 STAR", "系统设计"],
    ("京东", "Java开发工程师"): ["技术深挖", "行为面试 STAR", "系统设计"],
    ("快手", "算法工程师"): ["技术深挖", "算法基础", "行为面试 STAR"],
    ("快手", "后端开发工程师"): ["技术深挖", "行为面试 STAR", "系统设计"],
    ("滴滴出行", "后端开发工程师"): ["技术深挖", "行为面试 STAR", "系统设计"],
    # --- 国企：职能/市场岗不用工程类专业题 ---
    ("国家电网", "信息通信岗"): ["技术深挖", "专业基础", "综合素养"],
    ("国家电网", "财务管理岗"): ["专业基础", "综合素养", "案例分析"],
    ("中国移动", "市场运营岗"): ["市场分析", "综合素养", "情景模拟"],
    ("中国移动", "信息技术岗"): ["技术深挖", "综合素养", "专业基础"],
    ("中国烟草", "市场营销岗"): ["市场分析", "情景模拟", "综合素养"],
    ("工商银行", "客户经理岗"): ["情景模拟", "金融科技", "综合素养"],
    ("招商银行", "零售客户经理"): ["情景模拟", "综合素养", "金融科技"],
    # --- 外企 / 制造：软件岗不问硬件、销售岗不问研发 ---
    ("苹果中国", "软件工程师"): ["英文面试", "技术深挖", "系统设计"],
    ("华为", "硬件工程师"): ["硬件基础", "技术深挖", "专业基础"],
    ("华为", "海外销售经理"): ["情景模拟", "综合素养", "压力测试"],
    ("大疆", "算法工程师"): ["技术深挖", "算法基础", "算法题"],
    ("比亚迪", "电池研发工程师"): ["技术深挖", "专业基础"],
    ("比亚迪", "整车研发工程师"): ["技术深挖", "专业基础"],
    ("海康威视", "嵌入式工程师"): ["技术深挖", "硬件基础", "专业基础"],
    ("蚂蚁集团", "金融风控岗"): ["金融风控", "技术深挖", "案例分析"],
}


def build_jobs():
    jobs = []
    for company, cfg in COMPANIES.items():
        en = EN_ID[company]
        for i, role in enumerate(cfg["roles"], 1):
            jobs.append({
                "id": f"{en}-{i:02d}",
                "name": role,
                "company": company,
                "industry": cfg["industry"],
                "duration": cfg["duration"],
                "question_types": ROLE_TYPE_OVERRIDES.get((company, role), cfg["types"]),
                "answer_mode": cfg["answer_mode"],
                "mode": cfg["mode"],
                "total_questions": cfg["total"],
            })
    return jobs


# ============================================================
# 二、企业与岗位向面试题（q36+，参考公开面经撰写；q1–q35 为通用题型基座，
#     已存在于 seed_data/questions.json，生成器按 id 幂等合并、不会覆盖）
# ============================================================
EXTRA_QUESTIONS = [
    # 腾讯
    {"id": "q36", "title": "（腾讯）如何设计一个端到端的 AI 应用（从数据到模型部署）？", "type": "AI全栈", "difficulty": "困难", "industry": "互联网", "company": "腾讯",
     "reference_answer": "业务定义 → 数据获取与标注 → 模型选型与训练 → 评估 → 部署与监控 → 迭代闭环。", "template": "数据 → 模型 → 部署 → 监控闭环"},
    {"id": "q37", "title": "（腾讯）如何设计一个付费点，让玩家愿意买单又不破坏平衡？", "type": "游戏策划", "difficulty": "困难", "industry": "互联网", "company": "腾讯",
     "reference_answer": "明确付费目标与玩家分层 → 非数值型付费(皮肤/外观)优先 → 数值付费做上限保护 → 小额高频降低门槛。", "template": "目标分层 → 非数值优先 → 上限保护"},
    {"id": "q38", "title": "（腾讯）如何设计一个高可用的消息队列方案？", "type": "技术深挖", "difficulty": "困难", "industry": "互联网", "company": "腾讯",
     "reference_answer": "集群与主从 → 数据多副本(同步/异步) → 消费端幂等与重试 → 降级与限流 → 故障演练。", "template": "集群 → 副本 → 幂等 → 演练"},
    # 字节
    {"id": "q39", "title": "（字节跳动）广告点击率低，你会如何分析与优化？", "type": "产品分析", "difficulty": "中等", "industry": "互联网", "company": "字节跳动",
     "reference_answer": "拆漏斗(曝光/点击/转化) → 素材/定向/出价归因 → A/B 实验验证 → 放量。", "template": "漏斗拆解 → 归因 → A/B → 放量"},
    {"id": "q40", "title": "（字节跳动）如何提升直播间的停留时长？", "type": "产品分析", "difficulty": "中等", "industry": "互联网", "company": "字节跳动",
     "reference_answer": "内容节奏(留人钩子) → 互动玩法(福袋/连麦) → 算法推荐优化 → 数据验证。", "template": "内容 → 玩法 → 推荐 → 验证"},
    # 阿里
    {"id": "q41", "title": "（阿里巴巴）双11 大促系统如何保障稳定性？", "type": "技术深挖", "difficulty": "困难", "industry": "互联网", "company": "阿里巴巴",
     "reference_answer": "容量预估与压测 → 限流/降级/熔断 → 缓存与异步化 → 预案与演练 → 监控告警。", "template": "预估 → 限流降级 → 异步 → 演练"},
    {"id": "q42", "title": "（阿里巴巴）如何设计一个「猜你喜欢」推荐位？", "type": "产品分析", "difficulty": "中等", "industry": "互联网", "company": "阿里巴巴",
     "reference_answer": "目标指标(点击/转化) → 冷启动策略 → 召回/排序 → 业务规则干预 → 效果评估。", "template": "指标 → 冷启动 → 召回排序 → 评估"},
    # 美团
    {"id": "q43", "title": "（美团）高峰期骑手运力不足，如何调度？", "type": "情景模拟", "difficulty": "中等", "industry": "互联网", "company": "美团",
     "reference_answer": "需求预测与提前调度 → 动态定价激励 → 单量熔断与时效兜底 → 事后复盘。", "template": "预测 → 激励 → 熔断 → 复盘"},
    # 百度
    {"id": "q44", "title": "（百度）如何评估自动驾驶系统的安全性？", "type": "技术深挖", "difficulty": "困难", "industry": "互联网", "company": "百度",
     "reference_answer": "场景覆盖度与仿真测试 → 实车路测里程 → 安全冗余设计(失效降级) → 事故归因体系。", "template": "仿真 → 路测 → 冗余 → 归因"},
    # 京东
    {"id": "q45", "title": "（京东）如何优化仓库拣货效率？", "type": "情景模拟", "difficulty": "中等", "industry": "互联网", "company": "京东",
     "reference_answer": "波次与路径优化 → 货位布局(ABC分类) → 设备/系统辅助 → 数据指标监控。", "template": "路径 → 布局 → 工具 → 指标"},
    # 网易
    {"id": "q46", "title": "（网易）MMO 新版本如何做留存提升？", "type": "游戏策划", "difficulty": "中等", "industry": "互联网", "company": "网易",
     "reference_answer": "分析流失节点 → 前期目标感与新手引导 → 中后期社交与目标线 → A/B 验证。", "template": "流失分析 → 新手 → 社交 → 验证"},
    # 拼多多
    {"id": "q47", "title": "（拼多多）如何理解极致低价策略的可持续性？", "type": "产品分析", "difficulty": "中等", "industry": "互联网", "company": "拼多多",
     "reference_answer": "供给端(白牌/工厂直供) → 需求端(下沉市场) → 平台补贴与广告变现平衡 → 长期壁垒。", "template": "供给 → 需求 → 变现 → 壁垒"},
    # 快手
    {"id": "q48", "title": "（快手）如何平衡流量分发与创作者生态？", "type": "产品分析", "difficulty": "中等", "industry": "互联网", "company": "快手",
     "reference_answer": "普惠分发 vs 头部效应 → 创作者成长阶梯 → 流量与商业激励 → 生态指标监控。", "template": "分发 → 成长 → 激励 → 监控"},
    # 小红书
    {"id": "q49", "title": "（小红书）如何治理社区虚假种草？", "type": "情景模拟", "difficulty": "中等", "industry": "互联网", "company": "小红书",
     "reference_answer": "识别(内容/行为特征) → 处置(限流/标注) → 平台规则与公示 → 用户教育。", "template": "识别 → 处置 → 规则 → 教育"},
    # 小米
    {"id": "q50", "title": "（小米）如何优化安卓应用的内存占用？", "type": "技术深挖", "difficulty": "中等", "industry": "互联网", "company": "小米",
     "reference_answer": "内存泄漏定位(Mat/LeakCanary) → 图片与缓存策略 → 生命周期管理 → 压测对比。", "template": "定位 → 缓存 → 生命周期 → 对比"},
    # 国企
    {"id": "q51", "title": "（国家电网）什么是源网荷储一体化？", "type": "时政认知", "difficulty": "中等", "industry": "国企", "company": "国家电网",
     "reference_answer": "电源/电网/负荷/储能协同互动 → 提升新能源消纳与系统灵活性 → 结合岗位谈实践。", "template": "概念 → 作用 → 岗位结合"},
    {"id": "q52", "title": "（中国移动）谈谈 5G 在垂直行业的典型应用。", "type": "时政认知", "difficulty": "中等", "industry": "国企", "company": "中国移动",
     "reference_answer": "大带宽/低时延/大连接特性 → 工业互联网/车联网/远程医疗等场景 → 商业模式。", "template": "特性 → 场景 → 商业"},
    {"id": "q53", "title": "（中国石油）如何理解安全生产「一岗双责」？", "type": "综合素养", "difficulty": "简单", "industry": "国企", "company": "中国石油",
     "reference_answer": "岗位职责与安全责任并重 → 谁主管谁负责 → 结合本岗位风险点举例。", "template": "概念 → 原则 → 岗位结合"},
    {"id": "q54", "title": "（中国建筑）如何理解工程项目的安全管理体系？", "type": "专业基础", "difficulty": "中等", "industry": "国企", "company": "中国建筑",
     "reference_answer": "安全责任制 → 教育培训与交底 → 隐患排查治理 → 应急管理 → 复盘改进。", "template": "责任 → 教育 → 排查 → 应急"},
    {"id": "q55", "title": "（工商银行）柜面如何防范电信网络诈骗风险？", "type": "情景模拟", "difficulty": "中等", "industry": "国企", "company": "工商银行",
     "reference_answer": "转账场景识别异常特征 → 风险提示与核实 → 触发限额/暂停 → 上报联动反诈。", "template": "识别 → 提示 → 管控 → 联动"},
    {"id": "q56", "title": "（中国烟草）专卖体制下如何做好客户服务？", "type": "综合素养", "difficulty": "中等", "industry": "国企", "company": "中国烟草",
     "reference_answer": "合规前提下提升服务 → 客户分层与需求分析 → 配送与售后标准化 → 满意度闭环。", "template": "合规 → 分层 → 服务 → 闭环"},
    # 外企
    {"id": "q57", "title": "（微软）Describe a highly available system you have designed. (English)", "type": "英文面试", "difficulty": "困难", "industry": "外企", "company": "微软中国",
     "reference_answer": "Use STAR: context → architecture (redundancy/load balance) → failure handling → measurable SLA.", "template": "Context → Architecture → Failure → SLA"},
    {"id": "q58", "title": "（苹果）如何平衡产品散热与续航？", "type": "技术深挖", "difficulty": "困难", "industry": "外企", "company": "苹果中国",
     "reference_answer": "功耗评估 → 散热结构设计 → 软件功耗优化 → 温控策略 → 实测验证。", "template": "功耗 → 散热 → 软件 → 温控"},
    {"id": "q59", "title": "（特斯拉）如何评估一条产线的节拍与瓶颈？", "type": "专业基础", "difficulty": "中等", "industry": "外企", "company": "特斯拉中国",
     "reference_answer": "测节拍时间 → 瓶颈工序识别(节拍最长) → 消除瓶颈(并行/优化) → 平衡率指标。", "template": "测节拍 → 找瓶颈 → 消除 → 平衡率"},
    {"id": "q60", "title": "（宝洁）如何降低供应链库存成本？", "type": "情景模拟", "difficulty": "中等", "industry": "外企", "company": "宝洁",
     "reference_answer": "需求预测优化 → ABC 分类与安全库存 → 供应商协同(VMI) → 周转率监控。", "template": "预测 → 分类 → 协同 → 监控"},
    {"id": "q61", "title": "（联合利华）如何为一款新品制定上市计划？", "type": "情景模拟", "difficulty": "中等", "industry": "外企", "company": "联合利华",
     "reference_answer": "目标人群与定位 → 定价与渠道 → 营销节奏(预热/首发/持续) → 效果复盘。", "template": "定位 → 渠道 → 节奏 → 复盘"},
    {"id": "q62", "title": "（欧莱雅）如何策划美妆新品的社媒种草？", "type": "情景模拟", "difficulty": "中等", "industry": "外企", "company": "欧莱雅中国",
     "reference_answer": "人设与卖点提炼 → KOL 矩阵与内容策略 → 话题与活动 → 转化与数据复盘。", "template": "卖点 → 矩阵 → 话题 → 复盘"},
    {"id": "q63", "title": "（四大）如何设计一个舞弊风险识别方案？", "type": "案例分析", "difficulty": "困难", "industry": "外企", "company": "四大会计师事务所",
     "reference_answer": "风险信号识别 → 数据抽样与异常分析 → 穿行测试 → 与管理层沟通 → 出具意见。", "template": "信号 → 分析 → 测试 → 沟通"},
    {"id": "q64", "title": "（四大）客户利润下滑，请给出诊断框架。", "type": "案例分析", "difficulty": "中等", "industry": "外企", "company": "四大会计师事务所",
     "reference_answer": "收入/成本拆解 → 对标竞品与行业 → 内部流程与效率 → 提出改善优先级。", "template": "拆解 → 对标 → 内部分析 → 改善"},
    # 金融
    {"id": "q65", "title": "（蚂蚁集团）如何识别电商交易中的刷单行为？", "type": "技术深挖", "difficulty": "中等", "industry": "互联网", "company": "蚂蚁集团",
     "reference_answer": "特征工程(频次/设备/时间) → 规则+模型双通道 → 团伙识别(图算法) → 误伤控制与申诉。", "template": "特征 → 模型 → 团伙 → 误伤控制"},
    {"id": "q66", "title": "（招商银行）如何理解零售银行的数字化运营？", "type": "综合素养", "difficulty": "中等", "industry": "国企", "company": "招商银行",
     "reference_answer": "数据驱动客户分层 → 场景化营销 → 线上渠道与 App 运营 → 风控与合规并重。", "template": "数据 → 场景 → 渠道 → 风控"},
    {"id": "q67", "title": "（中金公司）如何对一家公司做 DCF 估值？", "type": "专业基础", "difficulty": "困难", "industry": "外企", "company": "中金公司",
     "reference_answer": "预测自由现金流 → 确定折现率(WACC) → 终值假设 → 敏感性分析 → 交叉验证。", "template": "现金流 → WACC → 终值 → 敏感性"},
    # 制造
    {"id": "q68", "title": "（华为）如何把大模型落地到行业场景？", "type": "AI全栈", "difficulty": "困难", "industry": "制造业", "company": "华为",
     "reference_answer": "场景价值评估 → 数据与算力准备 → 微调/RAG/Agent 选型 → 部署与成本 → 效果度量。", "template": "场景 → 数据 → 技术选型 → 落地"},
    {"id": "q69", "title": "（华为）如何优化 5G 基站覆盖与能耗的平衡？", "type": "技术深挖", "difficulty": "困难", "industry": "制造业", "company": "华为",
     "reference_answer": "网络规划与站址优化 → 功率与波束管理 → 节能技术(休眠/符号关断) → 实测验证。", "template": "规划 → 功率 → 节能 → 验证"},
    {"id": "q70", "title": "（大疆）如何保证无人机飞行稳定性？", "type": "技术深挖", "difficulty": "困难", "industry": "制造业", "company": "大疆",
     "reference_answer": "传感器融合(IMU/GPS/视觉) → 控制算法(姿态/位置环) → 抗风与容错 → 实飞验证。", "template": "感知 → 控制 → 容错 → 实飞"},
    {"id": "q71", "title": "（比亚迪）如何理解整车热管理系统设计？", "type": "技术深挖", "difficulty": "困难", "industry": "制造业", "company": "比亚迪",
     "reference_answer": "乘员舱/电池/电机热管理协同 → 集成热泵方案 → 能耗与性能平衡 → 试验验证。", "template": "协同 → 方案 → 平衡 → 验证"},
    {"id": "q72", "title": "（宁德时代）如何提升电池包能量密度？", "type": "技术深挖", "difficulty": "困难", "industry": "制造业", "company": "宁德时代",
     "reference_answer": "电芯材料升级(高镍/硅碳) → 结构创新(CTP/CTC) → 减重与集成 → 安全与寿命权衡。", "template": "材料 → 结构 → 集成 → 权衡"},
    {"id": "q73", "title": "（海康威视）如何设计城市级视频分析系统？", "type": "技术深挖", "difficulty": "困难", "industry": "制造业", "company": "海康威视",
     "reference_answer": "海量视频接入与存储 → 分布式计算与推理 → 算法(检测/跟踪/检索) → 业务应用与运维。", "template": "接入 → 计算 → 算法 → 应用"},
    # 快消/医药/文职
    {"id": "q74", "title": "（伊利）如何做一款新品的地推冷启动？", "type": "情景模拟", "difficulty": "中等", "industry": "快消", "company": "伊利集团",
     "reference_answer": "选点(人流/目标人群) → 试饮与促销组合 → 导购话术培训 → 数据回收与调整。", "template": "选点 → 组合 → 培训 → 调整"},
    {"id": "q75", "title": "（玛氏）如何管理多渠道价盘冲突？", "type": "情景模拟", "difficulty": "中等", "industry": "快消", "company": "玛氏中国",
     "reference_answer": "统一价盘规则 → 渠道差异化产品/包装 → 窜货监控与处罚 → 渠道利润保护。", "template": "规则 → 差异化 → 监控 → 保护"},
    {"id": "q76", "title": "（药明康德）如何保证实验室数据的完整性？", "type": "专业基础", "difficulty": "中等", "industry": "医药", "company": "药明康德",
     "reference_answer": "ALCOA+ 原则(可归属/清晰/同步/原始/准确) → 电子记录与审计追踪 → 双人复核。", "template": "ALCOA+ → 电子记录 → 复核"},
    {"id": "q77", "title": "（通用）如何组织一场大型校招宣讲会？", "type": "情景模拟", "difficulty": "中等", "industry": "文职", "company": "通用行政",
     "reference_answer": "目标院校与排期 → 场地物料与嘉宾 → 报名与到场管理 → 现场执行与复盘转化。", "template": "排期 → 物料 → 执行 → 复盘"},
    {"id": "q78", "title": "（通用）如何设计应届生入职培训体系？", "type": "情景模拟", "difficulty": "中等", "industry": "文职", "company": "通用行政",
     "reference_answer": "需求调研 → 课程模块(文化/技能/导师制) → 考核与反馈 → 90天留存跟踪。", "template": "调研 → 模块 → 考核 → 跟踪"},

    # ========================================================
    # 三、题型补全（q79+，2026-11 新增）
    # 背景：岗位配置 question_types 里声明了 14 类题型，但题库中一道都没有，
    #      导致抽题只能退化成「按企业/行业全量取题」，岗位与题目错位。
    # 此处按声明该题型的岗位所属行业定向补齐，使每个声明的题型都有真实题目可用。
    # ========================================================
    # --- 项目经历（字节跳动 8 个岗位，互联网）---
    {"id": "q79", "title": "（字节跳动）讲一个你主导的项目：目标、你的角色、关键决策与最终结果。", "type": "项目经历", "difficulty": "中等", "industry": "互联网", "company": "字节跳动",
     "reference_answer": "背景与目标(可量化) → 我的角色与边界 → 两三个关键决策及取舍理由 → 结果数据与复盘沉淀。", "template": "背景 → 角色 → 决策取舍 → 结果复盘"},
    {"id": "q80", "title": "（字节跳动）项目上线后未达预期指标，你如何定位原因并推动改进？", "type": "项目经历", "difficulty": "困难", "industry": "互联网", "company": "字节跳动",
     "reference_answer": "先确认指标口径与埋点 → 拆解漏斗定位流失环节 → 区分技术/产品/运营归因 → 制定实验方案 → 灰度验证与复盘。", "template": "口径 → 拆解 → 归因 → 实验 → 复盘"},
    {"id": "q81", "title": "（字节跳动）项目中你做过的最有技术含量的取舍是什么？为什么这么选？", "type": "项目经历", "difficulty": "中等", "industry": "互联网", "company": "字节跳动",
     "reference_answer": "明确约束(时间/人力/性能/成本) → 列候选方案 → 对比量化指标 → 说明最终取舍与遗留风险。", "template": "约束 → 备选 → 指标对比 → 取舍与风险"},
    {"id": "q82", "title": "（字节跳动）介绍一个你从 0 到 1 交付的项目，说明里程碑与风险控制。", "type": "项目经历", "difficulty": "简单", "industry": "互联网", "company": "字节跳动",
     "reference_answer": "目标与范围界定 → 里程碑拆分(可演示的最小闭环优先) → 关键风险与预案 → 联调验收 → 上线与观测。", "template": "范围 → 里程碑 → 风险预案 → 验收"},
    # --- 电商运营（阿里 5 + 拼多多 2，互联网）---
    {"id": "q83", "title": "（阿里巴巴）如何提升店铺的转化率？请给出可执行的优化路径。", "type": "电商运营", "difficulty": "中等", "industry": "互联网", "company": "阿里巴巴",
     "reference_answer": "拆曝光→点击→加购→支付漏斗 → 定位最大流失环节 → 优化主图/详情/评价/价格锚点 → A/B 验证 → 固化 SOP。", "template": "漏斗拆解 → 定位 → 页面优化 → A/B"},
    {"id": "q84", "title": "（拼多多）大促期间如何设计货品与价格策略？", "type": "电商运营", "difficulty": "中等", "industry": "互联网", "company": "拼多多",
     "reference_answer": "引流款/利润款/形象款分层 → 价格带卡位与竞品对标 → 库存与产能预锁 → 节奏(预热/爆发/返场) → 复盘。", "template": "货品分层 → 价格卡位 → 备货 → 节奏"},
    {"id": "q85", "title": "（阿里巴巴）如何诊断一个 GMV 下滑的店铺？", "type": "电商运营", "difficulty": "困难", "industry": "互联网", "company": "阿里巴巴",
     "reference_answer": "GMV=流量×转化×客单 三段拆解 → 对比环比/竞品/行业大盘 → 排查流量结构、活动节奏、评价与售后 → 给出优先级动作。", "template": "三段拆解 → 横向对比 → 逐项排查 → 动作排序"},
    # --- 市场分析（联合利华/欧莱雅 外企、伊利 快消、比亚迪 制造业）---
    {"id": "q86", "title": "（联合利华）如何评估一个新市场的进入机会？", "type": "市场分析", "difficulty": "中等", "industry": "外企", "company": "联合利华",
     "reference_answer": "市场规模与增速(TAM/SAM/SOM) → 竞争格局与替代品 → 目标人群与需求验证 → 渠道与进入成本 → 进入方式(自建/并购/代理)。", "template": "规模 → 竞争 → 人群 → 渠道 → 方式"},
    {"id": "q87", "title": "（伊利）如何用数据判断一款新品的市场潜力？", "type": "市场分析", "difficulty": "中等", "industry": "快消", "company": "伊利集团",
     "reference_answer": "品类增速与价格带空缺 → 试销数据(动销率/复购/铺货率) → 搜索与社媒声量 → 竞品价格弹性 → 放量决策门槛。", "template": "品类 → 试销 → 声量 → 弹性 → 门槛"},
    {"id": "q88", "title": "（比亚迪）如何分析新能源汽车细分市场的竞争格局？", "type": "市场分析", "difficulty": "困难", "industry": "制造业", "company": "比亚迪",
     "reference_answer": "按价格带与车型细分 → 份额与增速矩阵(明星/现金牛) → 技术与供应链壁垒 → 政策与补贴趋势 → 自身定位结论。", "template": "细分 → 份额矩阵 → 壁垒 → 政策 → 定位"},
    {"id": "q89", "title": "（欧莱雅）如何做竞品对标与定价区间分析？", "type": "市场分析", "difficulty": "中等", "industry": "外企", "company": "欧莱雅中国",
     "reference_answer": "选对标集(直接/间接/替代) → 拆产品力(成分/功效/包装) → 价格带分布与价格锚点 → 消费者感知价值调研 → 定价建议与弹性验证。", "template": "对标集 → 产品力 → 价格带 → 感知价值 → 定价"},
    # --- 硬件基础（小米 4 互联网、苹果 外企）---
    {"id": "q90", "title": "（小米）简述手机主板常见硬件模块与信号完整性要点。", "type": "硬件基础", "difficulty": "中等", "industry": "互联网", "company": "小米",
     "reference_answer": "SoC/PMIC/射频/存储/摄像头等模块 → 电源完整性与纹波 → 高速信号阻抗匹配与串扰 → EMC 与热设计约束。", "template": "模块 → 电源 → 高速信号 → EMC/热"},
    {"id": "q91", "title": "（小米）硬件产品做可靠性测试时，你会设计哪些测试项目？", "type": "硬件基础", "difficulty": "困难", "industry": "互联网", "company": "小米",
     "reference_answer": "环境(高低温/湿热/盐雾) → 机械(跌落/振动/插拔) → 电气(ESD/浪涌/老化) → 寿命与 MTBF → 失效判定标准与抽样方案。", "template": "环境 → 机械 → 电气 → 寿命 → 判定"},
    {"id": "q92", "title": "（苹果）如何定位一个偶发的硬件失效问题？", "type": "硬件基础", "difficulty": "中等", "industry": "外企", "company": "苹果中国",
     "reference_answer": "复现条件收敛(温度/电压/时序) → 失效样本切片与 X-Ray/显微分析 → 对比良品做差异定位 → 根因验证(改设计/改工艺) → 批次风险评估。", "template": "复现 → 失效分析 → 差异对比 → 根因 → 风险评估"},
    # --- 金融科技（工行 3 + 招行 2，国企）---
    {"id": "q93", "title": "（工商银行）银行核心系统做分布式改造，难点在哪里？", "type": "金融科技", "difficulty": "中等", "industry": "国企", "company": "工商银行",
     "reference_answer": "强一致账务与分布式事务 → 数据分片与热点账户 → 幂等与对账补偿 → 灰度迁移与双跑 → 监管合规与审计留痕。", "template": "一致性 → 分片 → 幂等对账 → 灰度 → 合规"},
    {"id": "q94", "title": "（招商银行）如何设计一个高可用的支付清算链路？", "type": "金融科技", "difficulty": "困难", "industry": "国企", "company": "招商银行",
     "reference_answer": "多活架构与单元化 → 幂等键与状态机 → 异步对账与差错处理 → 限流熔断与降级 → 全链路压测与演练。", "template": "多活 → 幂等状态机 → 对账 → 限流降级 → 演练"},
    {"id": "q95", "title": "（工商银行）谈谈你对金融数据安全与隐私保护的落地做法。", "type": "金融科技", "difficulty": "中等", "industry": "国企", "company": "工商银行",
     "reference_answer": "分类分级与最小权限 → 传输与存储加密、脱敏与去标识化 → 访问审计与堡垒机 → 数据出境与合规评估 → 应急与追责机制。", "template": "分级 → 加密脱敏 → 审计 → 合规 → 应急"},
    # --- 供应链（宝洁/特斯拉 外企、玛氏 快消）---
    {"id": "q96", "title": "（宝洁）如何设计一个端到端的供应链计划体系（S&OP）？", "type": "供应链", "difficulty": "中等", "industry": "外企", "company": "宝洁",
     "reference_answer": "需求预测(统计+共识) → 供应能力与产能规划 → 库存策略(安全库存/补货点) → 产销协同会议机制 → 指标(达成率/周转/缺货)。", "template": "预测 → 产能 → 库存 → 协同 → 指标"},
    {"id": "q97", "title": "（玛氏）如何应对旺季产能与库存的错配？", "type": "供应链", "difficulty": "中等", "industry": "快消", "company": "玛氏中国",
     "reference_answer": "旺季需求预测与提前备货 → 产线排产与柔性产能 → 分仓铺货与调拨规则 → 缺货优先级(高毛利/战略客户) → 复盘修正参数。", "template": "预测 → 产线 → 分仓 → 优先级 → 复盘"},
    {"id": "q98", "title": "（特斯拉）如何缩短零部件从下单到上线的周期？", "type": "供应链", "difficulty": "困难", "industry": "外企", "company": "特斯拉中国",
     "reference_answer": "拆解全链路周期(下单/生产/运输/入厂检验) → 找最长环节 → 供应商就近化与 VMI → 运输与关务优化 → 库存与齐套率平衡。", "template": "拆周期 → 找瓶颈 → 就近化 → 物流 → 齐套"},
    {"id": "q99", "title": "（玛氏）供应商交付不稳定，你如何建立预警与替代机制？", "type": "供应链", "difficulty": "中等", "industry": "快消", "company": "玛氏中国",
     "reference_answer": "交付绩效看板与红黄绿分级 → 提前期与在途监控预警 → 双源/备选供应商认证 → 安全库存与合同约束 → 季度评审与淘汰。", "template": "看板 → 预警 → 双源 → 库存合同 → 评审"},
    # --- 算法题（百度 3，互联网）---
    {"id": "q100", "title": "（百度）手写实现 LRU 缓存，并说明时间复杂度。", "type": "算法题", "difficulty": "中等", "industry": "互联网", "company": "百度",
     "reference_answer": "哈希表 + 双向链表；get/put 均为 O(1)；注意容量边界、节点移动与淘汰尾部；可提并发场景下的分段锁优化。", "template": "结构选择 → 核心操作 → 复杂度 → 边界"},
    {"id": "q101", "title": "（百度）给定海量日志，如何找出出现频率最高的 Top K？", "type": "算法题", "difficulty": "困难", "industry": "互联网", "company": "百度",
     "reference_answer": "哈希分桶拆分成小文件 → 各桶内哈希计数 → 每桶取 Top K(小顶堆) → 归并求全局 Top K；说明内存与 IO 权衡。", "template": "分桶 → 计数 → 堆 → 归并"},
    {"id": "q102", "title": "（百度）如何判断链表是否有环？给出证明与扩展。", "type": "算法题", "difficulty": "中等", "industry": "互联网", "company": "百度",
     "reference_answer": "快慢指针相遇即有环，O(n)/O(1)；证明给出相遇时距离关系；扩展求环入口(相遇后一指针回头同速走)。", "template": "快慢指针 → 证明 → 入口扩展"},
    # --- 物流运营（京东 3，互联网）---
    {"id": "q103", "title": "（京东）如何设计仓配一体的履约时效方案？", "type": "物流运营", "difficulty": "中等", "industry": "互联网", "company": "京东",
     "reference_answer": "按订单密度分仓与前置仓布局 → 库存下沉与品类匹配 → 波次拣选与分拣时效 → 末端配送路径 → 时效达成率与成本双指标。", "template": "布仓 → 库存下沉 → 仓内时效 → 末端 → 双指标"},
    {"id": "q104", "title": "（京东）大促期间如何做运力与仓容的弹性规划？", "type": "物流运营", "difficulty": "中等", "industry": "互联网", "company": "京东",
     "reference_answer": "历史单量预测与峰值系数 → 仓容与人力缺口测算 → 临时仓/外包运力储备 → 分时段限流与预约 → 实时监控与预案触发。", "template": "预测 → 缺口测算 → 储备 → 限流 → 预案"},
    {"id": "q105", "title": "（京东）如何降低末端配送的履约成本？", "type": "物流运营", "difficulty": "困难", "industry": "互联网", "company": "京东",
     "reference_answer": "单均成本拆解(人力/里程/失败重投) → 智能路径与集单 → 自提柜/驿站分流 → 时效分层定价 → 考核与激励机制。", "template": "拆成本 → 路径集单 → 分流 → 分层定价 → 激励"},
    # --- 金融风控（蚂蚁 3，互联网）---
    {"id": "q106", "title": "（蚂蚁集团）如何设计一套实时交易反欺诈规则与模型体系？", "type": "金融风控", "difficulty": "困难", "industry": "互联网", "company": "蚂蚁集团",
     "reference_answer": "设备/行为/关系特征 → 规则(强约束)+模型(评分)双通道 → 决策引擎与策略分层 → 处置动作(拦截/验证/放行) → 误杀监控与对抗迭代。", "template": "特征 → 规则+模型 → 决策引擎 → 处置 → 迭代"},
    {"id": "q107", "title": "（蚂蚁集团）风控模型误杀率高，你如何优化？", "type": "金融风控", "difficulty": "中等", "industry": "互联网", "company": "蚂蚁集团",
     "reference_answer": "核对误杀定义与样本标注 → 分析误杀集中的特征与阈值 → 调整阈值/引入白名单与人工复核 → 挑战者模型 A/B → 灰度放量与监控。", "template": "口径 → 归因 → 阈值白名单 → A/B → 灰度"},
    {"id": "q108", "title": "（蚂蚁集团）如何做贷前、贷中、贷后的全流程风险监控？", "type": "金融风控", "difficulty": "中等", "industry": "互联网", "company": "蚂蚁集团",
     "reference_answer": "贷前准入评分与反欺诈 → 贷中行为监控(额度/交易/多头) → 贷后催收与预警分层 → 风险指标(逾期率/迁徙率) → 策略闭环回写。", "template": "贷前准入 → 贷中监控 → 贷后预警 → 指标 → 闭环"},
    # --- 社区运营（小红书 2，互联网）---
    {"id": "q109", "title": "（小红书）如何提升社区创作者的持续产出意愿？", "type": "社区运营", "difficulty": "中等", "industry": "互联网", "company": "小红书",
     "reference_answer": "创作者分层(头部/腰部/新手) → 冷启动流量扶持与选题引导 → 成长激励(等级/权益/变现) → 反馈与陪伴机制 → 留存与产出率指标。", "template": "分层 → 扶持 → 激励 → 陪伴 → 指标"},
    {"id": "q110", "title": "（小红书）社区内容质量下滑，你如何建立治理机制？", "type": "社区运营", "difficulty": "中等", "industry": "互联网", "company": "小红书",
     "reference_answer": "定义质量维度与量化指标 → 机审+人审分级处置 → 优质内容加权分发 → 违规成本与公示 → 周期复盘与规则迭代。", "template": "标准 → 审核 → 加权 → 惩戒 → 迭代"},
    # --- 内容运营（哔哩哔哩 2，互联网）---
    {"id": "q111", "title": "（哔哩哔哩）如何规划一个垂类内容的年度选题矩阵？", "type": "内容运营", "difficulty": "中等", "industry": "互联网", "company": "哔哩哔哩",
     "reference_answer": "垂类用户画像与需求分层 → 选题池(常青/热点/系列) → 供给与创作者匹配 → 排期与资源位 → 数据回收调整配比。", "template": "画像 → 选题池 → 供给匹配 → 排期 → 调优"},
    {"id": "q112", "title": "（哔哩哔哩）如何用数据评估内容运营效果？", "type": "内容运营", "difficulty": "中等", "industry": "互联网", "company": "哔哩哔哩",
     "reference_answer": "北极星指标(播放/互动/关注转化) → 分渠道与内容类型归因 → 完播与互动率看质量 → 留存与回访看长期 → 实验对照定因果。", "template": "北极星 → 归因 → 质量指标 → 留存 → 实验"},
    {"id": "q113", "title": "（哔哩哔哩）UP 主投稿量下降，你会如何做运营干预？", "type": "内容运营", "difficulty": "简单", "industry": "互联网", "company": "哔哩哔哩",
     "reference_answer": "先分群定位(新手/腰部/头部) → 访谈找真实卡点(收益/流量/创作成本) → 针对性激励与工具支持 → 小范围试点验证 → 全量推广。", "template": "分群 → 访谈 → 激励工具 → 试点 → 推广"},
    # --- 工程管理（中国建筑 2，国企）---
    {"id": "q114", "title": "（中国建筑）如何编制一个项目的施工进度计划并控制偏差？", "type": "工程管理", "difficulty": "中等", "industry": "国企", "company": "中国建筑",
     "reference_answer": "WBS 分解与工程量 → 关键路径法排计划 → 资源与工序穿插 → 进度对比(计划 vs 实际) → 纠偏(赶工/调序/增资源)。", "template": "WBS → 关键路径 → 穿插 → 对比 → 纠偏"},
    {"id": "q115", "title": "（中国建筑）项目成本超支，你会如何做成本管控？", "type": "工程管理", "difficulty": "困难", "industry": "国企", "company": "中国建筑",
     "reference_answer": "成本科目拆解与责任归属 → 量价分离分析超支点 → 材料损耗与分包结算核查 → 变更签证管理 → 月度成本例会与预警线。", "template": "拆解 → 量价分析 → 核查 → 变更管理 → 预警"},
    {"id": "q116", "title": "（中国建筑）如何处理施工中的设计变更与签证？", "type": "工程管理", "difficulty": "中等", "industry": "国企", "company": "中国建筑",
     "reference_answer": "变更发起与必要性论证 → 技术与成本影响评估 → 图纸与交底同步 → 签证资料留痕(影像/量单) → 结算主张与审计配合。", "template": "论证 → 影响评估 → 交底 → 留痕 → 结算"},
    # --- 系统设计（微软中国 2，外企）---
    {"id": "q117", "title": "（微软）设计一个支持千万级并发的短链服务，说明关键取舍。", "type": "系统设计", "difficulty": "困难", "industry": "外企", "company": "微软中国",
     "reference_answer": "发号器(雪花/号段)与 Base62 编码 → 读写分离与多级缓存 → 分库分表与热点 key → 301/302 取舍与统计异步化 → 容量与降级方案。", "template": "编码 → 缓存 → 分片 → 跳转取舍 → 容量"},
    {"id": "q118", "title": "（微软）如何设计一个多租户 SaaS 的权限与数据隔离方案？", "type": "系统设计", "difficulty": "困难", "industry": "外企", "company": "微软中国",
     "reference_answer": "隔离级别选择(库/表/行，按成本与合规) → RBAC/ABAC 模型 → 租户上下文透传与拦截 → 密钥与加密隔离 → 越权测试与审计。", "template": "隔离级别 → 权限模型 → 上下文 → 加密 → 审计"},
    {"id": "q119", "title": "（微软）设计一个分布式定时任务调度系统。", "type": "系统设计", "difficulty": "中等", "industry": "外企", "company": "微软中国",
     "reference_answer": "任务注册与 Cron 解析 → 调度中心选主与分片 → 触发与执行解耦(消息队列) → 幂等与失败重试 → 执行日志、告警与可视化。", "template": "注册 → 选主分片 → 解耦触发 → 幂等重试 → 监控"},
    # --- 算法基础（海康威视 2，制造业）---
    {"id": "q120", "title": "（海康威视）简述卷积神经网络的基本组成与感受野概念。", "type": "算法基础", "difficulty": "中等", "industry": "制造业", "company": "海康威视",
     "reference_answer": "卷积/激活/池化/全连接的作用 → 权值共享与局部连接 → 感受野逐层累积公式 → 对检测任务尺度设计的影响。", "template": "组件作用 → 共享与局部 → 感受野 → 尺度设计"},
    {"id": "q121", "title": "（海康威视）目标检测中如何平衡精度与推理速度？", "type": "算法基础", "difficulty": "困难", "industry": "制造业", "company": "海康威视",
     "reference_answer": "骨干网络轻量化(深度可分离/MobileNet) → 输入分辨率与多尺度取舍 → 剪枝/量化/蒸馏 → 算子融合与硬件适配 → 端侧实测 mAP 与 FPS 曲线。", "template": "轻量骨干 → 分辨率 → 压缩 → 硬件适配 → 实测"},
    {"id": "q122", "title": "（海康威视）如何处理训练数据的类别不平衡问题？", "type": "算法基础", "difficulty": "中等", "industry": "制造业", "company": "海康威视",
     "reference_answer": "重采样(过采样/欠采样) → 损失加权(Focal Loss/Class Weight) → 数据增强与合成 → 分类型评估(P/R 与混淆矩阵) → 阈值调优。", "template": "重采样 → 损失加权 → 增强 → 分类评估 → 阈值"},
    # --- 行为面试 STAR 补充（补足市场/供应链管培生 8 题缺口）---
    {"id": "q123", "title": "（联合利华）讲一次你在压力下同时推进多个任务的经历。", "type": "行为面试 STAR", "difficulty": "中等", "industry": "外企", "company": "联合利华",
     "reference_answer": "情境与冲突(多任务/时间紧) → 我的优先级判断依据 → 具体协调与取舍动作 → 结果与他人的评价。", "template": "情境 → 判断 → 行动 → 结果"},
    {"id": "q124", "title": "（玛氏）举一个你说服他人接受你方案的例子。", "type": "行为面试 STAR", "difficulty": "中等", "industry": "快消", "company": "玛氏中国",
     "reference_answer": "对方立场与分歧点 → 我用数据/试点降低对方顾虑 → 沟通与让步策略 → 达成结果与长期影响。", "template": "分歧 → 证据 → 沟通 → 结果"},
]


def build_questions():
    return EXTRA_QUESTIONS


def slug(name):
    return re.sub(r"\s+", "-", name.strip())


def main():
    jobs = build_jobs()
    questions = build_questions()

    seed_dir = os.path.join(ROOT, "app", "seed_data")
    os.makedirs(seed_dir, exist_ok=True)

    # 幂等合并：保留既有数据（如历史导入、CSV 导入的岗位/题目），按 id 去重
    # prefer_fresh=True 时同一 id 以生成器配置为准（用于岗位配置：代码是唯一事实源，
    # 否则旧库里的 question_types 会反向覆盖本次调整）
    def merge_write(name, fresh, prefer_fresh=False):
        path = os.path.join(seed_dir, name)
        existing = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
        order = [it["id"] for it in existing]
        table = {it["id"]: it for it in existing}
        for item in fresh:
            is_new = item["id"] not in table
            if is_new:
                order.append(item["id"])
            if is_new or prefer_fresh:
                table[item["id"]] = item
        merged = [table[i] for i in order]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=1)
        return len(merged)

    n_jobs = merge_write("jobs.json", jobs, prefer_fresh=True)
    n_qs = merge_write("questions.json", questions)

    # 前端 TS（mock 数据：jobConfigs + questions 驼峰，全部来自合并后的 JSON）
    with open(os.path.join(seed_dir, "jobs.json"), encoding="utf-8") as f:
        all_jobs = json.load(f)
    with open(os.path.join(seed_dir, "questions.json"), encoding="utf-8") as f:
        all_qs = json.load(f)

    js_jobs = [{
        "id": j["id"], "name": j["name"], "company": j["company"], "industry": j["industry"],
        "duration": j["duration"], "questionTypes": j["question_types"],
        "answerMode": j["answer_mode"], "mode": j["mode"], "totalQuestions": j["total_questions"],
    } for j in all_jobs]
    js_questions = [{
        "id": q["id"], "title": q["title"], "type": q["type"], "difficulty": q["difficulty"],
        "industry": q["industry"], "company": q.get("company", ""),
        "referenceAnswer": q["reference_answer"], "template": q["template"],
    } for q in all_qs]

    def to_ts(objs):
        lines = []
        for o in objs:
            items = ",\n    ".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in o.items())
            lines.append("  {\n    " + items + "\n  }")
        return "[\n" + ",\n".join(lines) + "\n]"

    ts = (
        "// 本文件由 backend/tools/generate_seed.py 自动生成，请勿手改；修改数据后重新运行生成器。\n"
        "import type { JobConfig, QuestionItem } from '@/types'\n\n"
        f"export const seedJobs: JobConfig[] = {to_ts(js_jobs)}\n\n"
        f"export const seedQuestions: QuestionItem[] = {to_ts(js_questions)}\n"
    )
    ts_path = os.path.abspath(os.path.join(ROOT, "..", "frontend", "src", "mock", "seed_data.ts"))
    os.makedirs(os.path.dirname(ts_path), exist_ok=True)
    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(ts)

    print(f"JOBS={n_jobs}  QUESTIONS={n_qs}")
    print("OK ->", os.path.join(seed_dir, "jobs.json"))
    print("OK ->", os.path.join(seed_dir, "questions.json"))
    print("OK ->", ts_path)


if __name__ == "__main__":
    main()
