# scp-book

中小企业跨境电商供应链计划模型，基于 Streamlit 构建的交互式 Dashboard。

## 核心链路

需求预测 → 库存计划 → 供应计划 → 发货计划

## 项目结构

```
scp_models/
├── app.py                  # Streamlit 入口
├── pipeline.py             # 端到端 Pipeline
├── config.py               # 全局配置
├── requirements.txt        # Python 依赖
├── models/
│   ├── demand_forecast.py  # 需求预测（双轨：统计+人工）
│   ├── inventory_plan.py   # 库存计划（安全库存计算）
│   ├── supply_plan.py      # 供应计划（ROD 补货逻辑）
│   └── shipment_plan.py    # 发货计划（海运/空运分流）
├── data/
│   ├── loader.py           # CSV 加载
│   └── schemas.py          # 数据 Schema
├── utils/
│   ├── metrics.py          # 指标计算（MAPE、达成率等）
│   └── viz.py              # Plotly 可视化
├── sample_data/            # 示例数据
└── tests/                  # 单元测试
```

## 快速开始

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 功能

- **需求预测**：移动平均 / 指数平滑双轨对比，历史 MAPE & 达成率评估
- **库存计划**：ABC 安全库存自动计算
- **供应计划**：ROD（常规订货日）采购建议，导出采购计划 CSV
- **发货计划**：海运/空运自动分流，运输时效匹配
