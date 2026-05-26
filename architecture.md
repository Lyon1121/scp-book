# SCP-Book 供应链计划模型

## 🏗 入口 & 编排
### app.py — Streamlit 四页 Dashboard
### pipeline.py — run_pipeline() 一键串联
### config.py — 全局参数中心

## 📊 Module 1: 需求预测
### 输入
#### historical_sales.csv（24月日销量，含渠道列）
#### manual_forecast.csv（月度人工预测，含历史+未来）
### 数据处理
#### aggregate_to_monthly() — 日→月聚合
### 双轨预测
#### 轨道1: 销售人员月度人工预测
#### 轨道2: 统计预测
##### MovingAverageForecaster（移动平均）
##### SimpleExponentialSmoothing（指数平滑）
##### get_forecaster() — 工厂函数插拔
### 双轨对比
#### compare_historical() — 历史：实际 vs 人工 → 达成率
#### compare_future() — 未来：统计 vs 人工 → 偏差
#### run_dual_forecast() — 主入口
### 输出
#### 历史达成率（平均/最高/最低）
#### 历史 MAPE
#### 未来偏差（统计 vs 人工）

## 📦 Module 2: 库存计划
### calculate_safety_stock() — MAD × Z因子 × √补货周期
### calculate_cycle_stock() — 日均需求 × 补货周期 ÷ 2
### classify_abc() — ABC分类（累计销量占比）
### classify_xyz() — XYZ分类（需求波动 CV）
### run_inventory_plan() — 主入口
### 输出
#### 日均需求 / 安全库存 / 周转库存 / 目标库存
#### ABC分类 + XYZ分类

## 🚚 Module 3: 供应计划
### 策略
#### ROD 再订货日期（每月1号&15号）
#### 采购提前期 30天
### 核心函数
#### get_upcoming_rod_dates() — 未来ROD日期列表
#### calculate_procurement() — 单SKU采购量计算
### 采购量公式
#### 采购量 = 目标库存 − （当前库存 + 在途 − 提前期消耗）
#### MOQ 最小起订量约束
### run_supply_plan() — 主入口

## 📬 Module 4: 发货计划
### 策略
#### 默认海运 60天
#### 库存 < 安全库存 → 自动切换空运 14天
#### 单仓 → 亚马逊主仓
### 核心函数
#### determine_freight_mode() — 运输方式决策
#### run_shipment_plan() — 主入口
### 输出
#### 运输方式（海运/空运）
#### 安排发货日 / 预计上架日

## 🛠 数据层
### data/schemas.py
#### ForecastCompareResult（双轨对比列名）
#### InventoryPlanResult（库存计划列名）
#### ProcurementPlanResult（采购计划列名）
#### ShipmentPlanResult（发货计划列名）
#### SalesInput / ManualForecastInput / InventoryInput / ProductInput
### data/loader.py
#### load_csv() — CSV 读取
#### validate_columns() — 列名校验
#### load_and_validate() — 一步到位

## 🔧 工具层
### utils/metrics.py
#### mape() — 平均绝对百分比误差
#### mad() — 平均绝对偏差
#### rmse() — 均方根误差
#### bias() — 系统性偏差方向
#### calculate_all_metrics() — 一键出报表
### utils/viz.py
#### plot_historical_compare() — 实际 vs 人工折线图
#### plot_achievement_rate() — 达成率趋势图
#### plot_future_compare() — 未来对比柱状图
#### plot_inventory_structure() — 库存结构堆叠图

## 📁 示例数据
### sample_data/historical_sales.csv（24月 × 3SKU × 2渠道）
### sample_data/manual_forecast.csv（24月历史 + 6月未来）
### sample_data/current_inventory.csv（当前库存 + 在途）
### sample_data/product_master.csv（品类/提前期/MOQ/成本）

## 🧪 测试
### tests/test_demand_forecast.py
### tests/test_inventory_plan.py
### tests/test_supply_ship.py

## 📋 维护文档
### CHANGELOG.md（更新日志，日期版本）
### PROGRESS.md（进度快照，上下文恢复）
### README.md（项目说明 + 快速开始）
### architecture.md（思维导图源文件）
### architecture.html（交互式思维导图）
