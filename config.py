"""
全局配置参数

模拟背景：
- 中小企业跨境电商，SKU 1000~5000，渠道：亚马逊 + 独立站
- 采购 Lead Time 30天，ROD 每月1号&15号集中采购
- 发货：单仓→亚马逊；默认海运60天，低于安全库存自动空运14天
"""
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent

# 数据目录
DATA_DIR = ROOT_DIR / "sample_data"

# ---- 需求预测默认参数 ----
DEFAULT_FORECAST_METHOD = "moving_average"   # 默认统计预测方法
DEFAULT_WINDOW = 3                            # 移动平均窗口期（月）
DEFAULT_ALPHA = 0.3                           # 指数平滑系数

# ---- 库存计划默认参数 ----
SERVICE_LEVEL = 0.95                          # 服务水平 (Z=1.65)
Z_FACTOR = 1.65                               # 安全因子（对应95%服务水平）
REPLENISHMENT_CYCLE = 15                      # 补货周期（天）= 每月2次

# ---- 供应计划（采购）参数 ----
PROCUREMENT_LEAD_TIME = 30                    # 采购提前期（天）
DEFAULT_MOQ = 0                               # 最小起订量（0=不限制）
ROD_DAYS = [1, 15]                            # 每月集中采购日（再订货日期）

# ---- 发货计划参数 ----
SEA_FREIGHT_DAYS = 60                         # 海运：安排发货→上架（天）
AIR_FREIGHT_DAYS = 14                         # 空运：安排发货→上架（天）
DEFAULT_WAREHOUSES = ["亚马逊主仓"]             # 默认单仓（亚马逊）
AIR_FREIGHT_TRIGGER = "below_safety_stock"    # 空运触发条件：库存低于安全库存
