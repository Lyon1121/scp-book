# 更新日志

所有值得记录的项目变更，按日期倒序。

格式说明：
- 标题用 `YYYY-MM-DD HH:MM` 精确到分钟
- **Added** — 新增功能
- **Changed** — 功能修改
- **Fixed** — Bug 修复
- **Removed** — 移除功能

---

---

## 2026-05-26 22:25

### Changed
- **数据源迁移**：从 `sample_data/` 迁移到 `data_input/`
  - historical_sales.csv → Sales_data.csv（日期格式 `2024/1/1`）
  - manual_forecast.csv → Sales_forecasting.csv（月份格式 `Jan-24`，预测值已填充）
  - current_inventory.csv → SKU_Stock.csv（新增 FBA库存列）
  - product_master.csv → SKU_data.csv（新增 销售负责人/产品负责人）
- **库存模型升级**：供应计划和发货计划支持三级库存（国内库存 + 在途库存 + FBA库存）
- **loader.py**：支持 GBK 编码自动回退

### Fixed
- `aggregate_to_monthly()` 日期格式兼容：`2024/1/1` → `Jan-24` 匹配 Sales_forecasting.csv
- 管道验证：达成率 100.4%，MAPE 2.67%，四模块全部正常输出

### Added
- `fill_forecast.py`：预测值填充工具脚本

## 2026-05-26 20:51

### Added
- **CHANGELOG.md**：更新日志，每次功能迭代后追加一条
- **PROGRESS.md**：进度快照（上下文恢复文档），含项目定位、架构、参数、用户偏好

### Changed
- CHANGELOG 日期格式改为精确到分钟（YYYY-MM-DD HH:MM）

---

## 2026-05-26 20:30

### Added
- **交互式思维导图**：architecture.md + architecture.html（Markmap），展示完整架构
- **行内注释**：12个核心 Python 文件全部添加详细 # 注释

---

## 2026-05-26 20:05

### Added
- **四模块供应链计划模型**：需求预测、库存计划、供应计划、发货计划全部实现
- **需求预测**：双轨制（销售人员月度人工预测 vs 移动平均/指数平滑），历史达成率 + 未来偏差分析
- **库存计划**：安全库存（MAD×Z因子）、周转库存、ABC-XYZ 分类、目标库存计算
- **供应计划**：ROD 再订货日期策略（每月1号&15号），采购量 = 目标库存 − 预计库存，含 MOQ 约束
- **发货计划**：单仓→亚马逊，默认海运60天，库存<安全库存自动切换空运14天
- **Pipeline 串联**：一键 run_pipeline() 跑通四个模块
- **Streamlit Dashboard**：四页黑白灰界面（需求预测→库存计划→供应计划→发货计划）
- **示例数据**：24个月×3 SKU 日销量（含渠道列），24月历史+6月未来人工预测 CSV
- **Git 版本管理**：连接 GitHub 仓库 Lyon1121/scp-book

### Changed
- CSV 列名采用中文（SKU/日期/销量/渠道）
- 发货计划先做单仓（亚马逊），独立站渠道数据已标记但暂未参与计划
- 统计预测方法支持插拔（工厂函数 get_forecaster）

### Known Issues
- 采购量公式偏激进（当前库存 − Lead Time消耗 + 补到目标库存），后续需加平滑系数
- 仅支持移动平均和指数平滑，待扩展 Holt-Winters、ARIMA
- 独立站发货逻辑未实现
