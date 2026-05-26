# PROGRESS — 项目进度快照

> **用途**：聊天上下文崩溃后，新会话读取此文件即可恢复当前进度。
> **最后更新**：2026-05-26

---

## 项目定位

**SCP-Book**：中小企业跨境电商供应链计划模型（Python + Streamlit）

**模拟背景**：
- 企业：中小跨境电商，SKU 1000~5000（模拟用 3 个代表 SKU）
- 渠道：亚马逊（欧美站）+ 独立站
- 采购：Lead Time 30天，ROD（再订货日期）每月1号、15号集中采购
- 发货：单仓→亚马逊，默认海运60天，库存<安全库存触发空运14天

**GitHub**：https://github.com/Lyon1121/scp-book（Lyon1121）

---

## 当前进度

### ✅ 已完成

| 模块 | 文件 | 状态 |
|------|------|:--:|
| 需求预测（双轨） | `models/demand_forecast.py` | ✅ |
| 库存计划（ABC-XYZ） | `models/inventory_plan.py` | ✅ |
| 供应计划（ROD） | `models/supply_plan.py` | ✅ |
| 发货计划（海运/空运） | `models/shipment_plan.py` | ✅ |
| Pipeline 串联 | `pipeline.py` | ✅ |
| Streamlit 界面 | `app.py` | ✅ |
| 数据层（Schema+Loader） | `data/schemas.py` `data/loader.py` | ✅ |
| 工具层（Metrics+Viz） | `utils/metrics.py` `utils/viz.py` | ✅ |
| 示例数据 | `sample_data/`（4个CSV） | ✅ |
| 测试 | `tests/`（3个测试文件） | ✅ |
| 思维导图 | `architecture.md` `architecture.html` | ✅ |
| 行内注释 | 所有 `.py` 文件 | ✅ |
| 更新日志 | `CHANGELOG.md` | ✅ |

### 📋 待优化（优先级排序）

1. **采购量公式调优** — 当前偏激进，需加平滑系数或上限封顶
2. **统计预测扩展** — 添加 Holt-Winters、ARIMA 等
3. **独立站发货** — 目前独立站数据仅标记，未参与发货计划
4. **多仓分配** — 亚马逊欧美站分仓逻辑
5. **参数实时调节** — Streamlit 侧边栏加更多滑块（安全因子、Lead Time）

---

## 核心架构

```
historical_sales.csv ──→ [Module 1: 需求预测] ──→ forecast_df
manual_forecast.csv ──┘         │
                                ↓
                         [Module 2: 库存计划] ──→ inventory_df
current_inventory.csv ─────────────┤
                                   ↓
                            [Module 3: 供应计划] ──→ procurement_df
                                   │
                                   ↓
                            [Module 4: 发货计划] ──→ shipment_df
                                   │
                            ┌──────┴──────┐
                            │  Streamlit  │
                            │  4-Tab UI   │
                            └─────────────┘
```

---

## 技术栈

| 项 | 内容 |
|----|------|
| 语言 | Python 3.12 |
| 数据 | pandas + numpy |
| 界面 | Streamlit 1.28+ |
| 图表 | Plotly 5.17+ |
| 测试 | pytest |
| 版本管理 | Git → GitHub（main 分支） |

---

## 运行方式

```bash
cd C:\Users\Lyon\Desktop\scp_models
pip install -r requirements.txt
streamlit run app.py          # Dashboard（端口 8501）
python -m http.server 8765    # 思维导图（architecture.html）
```

---

## 关键参数（config.py）

| 参数 | 值 | 说明 |
|------|-----|------|
| PROCUREMENT_LEAD_TIME | 30天 | 采购提前期 |
| ROD_DAYS | [1, 15] | 每月集中采购日 |
| SEA_FREIGHT_DAYS | 60天 | 海运时效 |
| AIR_FREIGHT_DAYS | 14天 | 空运时效 |
| Z_FACTOR | 1.65 | 安全因子（95%服务水平） |
| REPLENISHMENT_CYCLE | 15天 | 补货周期 |

---

## 用户偏好速查

- 回复语言：中文
- 界面风格：黑白灰，不要润色
- CSV 列名：中文（SKU/日期/销量/渠道）
- 修改确认：阶段性确认后推 GitHub
- 注释要求：每行代码后面加 # 注释

## 维护规则（AI 自检清单）

每次功能迭代后，需自查是否更新以下文件：
- [ ] `CHANGELOG.md` — 新条目，日期精确到分钟
- [ ] `PROGRESS.md` — 进度、已知问题、待优化清单
- [ ] `architecture.md` — 新增/改名模块同步到思维导图
- [ ] `git commit + push` — 阶段性确认后推送
