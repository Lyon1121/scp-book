"""
共享数据结构定义 —— 整个项目的"列名词典"

为什么需要这个文件？
  四个模块（需求预测、库存计划、供应计划、发货计划）之间
  通过 pandas DataFrame 传递数据。如果每个模块自己硬编码列名字符串，
  一旦改列名就要改 N 个地方。所以把列名集中定义在这里，
  所有模块 import 使用，改一处 = 全局生效。

设计原则：
  - 每个 DataClass 对应一个 DataFrame 的列名模板
  - 属性名用英文（代码可读），默认值用中文（CSV 列名直观）
  - columns() 方法返回完整的列名列表，方便校验和初始化空 DataFrame
"""
from dataclasses import dataclass, field  # dataclass 自动生成 __init__/__repr__，省代码
from typing import List                    # List 类型注解


# ============================================================
# Module 1 输出: 统计预测中间结果
# ============================================================
@dataclass  # @dataclass 装饰器让这个类自动获得 __init__、__repr__ 等方法
class ForecastResult:
    """
    统计模型预测后产出的中间结果
    目前主要用于未来预测值的存储
    """
    SKU: str = "SKU"                       # 产品唯一标识
    PERIOD: str = "月份"                    # 月度粒度，如 "2026-03"
    METHOD: str = "预测方法"                 # 用了哪种统计方法，如 "移动平均(窗口=3)"
    STAT_FORECAST: str = "统计预测量"        # 统计模型输出的预测值（月度）

# ============================================================
# Module 1 核心输出: 双轨对比结果（月度）
# ============================================================
@dataclass
class ForecastCompareResult:
    """
    需求预测的最终输出 —— 双轨对比表

    轨道1（人工）: 销售人员每月填的预测
    轨道2（统计）: 移动平均 / 指数平滑等统计模型跑出来的预测

    这张表同时包含"历史对比"和"未来对比"：
    - 历史行：有实际销量 + 人工预测 → 计算达成率
    - 未来行：只有人工预测 + 统计预测 → 计算偏差
    """
    SKU: str = "SKU"                        # 产品唯一标识
    PERIOD: str = "月份"                     # 月份，如 "2025-03"
    ACTUAL: str = "实际销量"                 # 该月实际销售总量（历史行有值，未来行为 NaN）
    MANUAL_FORECAST: str = "人工预测量"      # 销售人员填的月度预测
    STAT_FORECAST: str = "统计预测量"        # 统计模型跑出的月度预测（历史行为 NaN）
    ACHIEVEMENT_RATE: str = "达成率_人工"     # 历史行：实际销量 / 人工预测量 × 100%
    STAT_DEVIATION: str = "偏差_统计vs人工"   # 未来行：(统计预测 - 人工预测) / 人工预测 × 100%

    @property  # @property 让 columns 像属性一样调用，不用加 ()
    def columns(self) -> List[str]:
        """返回完整的列名列表，供创建空 DataFrame 或校验列名时使用"""
        return [self.SKU, self.PERIOD, self.ACTUAL, self.MANUAL_FORECAST,
                self.STAT_FORECAST, self.ACHIEVEMENT_RATE, self.STAT_DEVIATION]


# ============================================================
# Module 2 输出: 库存计划结果
# ============================================================
@dataclass
class InventoryPlanResult:
    """
    库存计划的最终输出

    告诉计划员每个 SKU：
    - 应该持有多少库存（目标库存 = 安全库存 + 周转库存）
    - 属于什么分类（ABC 按金额贡献，XYZ 按需求波动）
    """
    SKU: str = "SKU"                        # 产品唯一标识
    AVG_DAILY_DEMAND: str = "日均需求"       # 日均销量 = 月均销量 / 30
    SAFETY_STOCK: str = "安全库存"           # 应对需求波动的缓冲库存（MAD × Z因子）
    CYCLE_STOCK: str = "周转库存"            # 补货周期内正常消耗的量
    TARGET_INVENTORY: str = "目标库存"       # 安全库存 + 周转库存，即"该备多少货"
    ABC_CLASS: str = "ABC分类"               # A类（金额贡献70%）/ B类（70~90%）/ C类（90~100%）
    XYZ_CLASS: str = "XYZ分类"               # X类（CV≤0.2稳定）/ Y类（0.2~0.5）/ Z类（>0.5波动大）

    @property
    def columns(self) -> List[str]:
        """返回库存计划表的列名"""
        return [self.SKU, self.AVG_DAILY_DEMAND, self.SAFETY_STOCK,
                self.CYCLE_STOCK, self.TARGET_INVENTORY,
                self.ABC_CLASS, self.XYZ_CLASS]


# ============================================================
# Module 3 输出: 供应计划（采购计划）结果
# ============================================================
@dataclass
class ProcurementPlanResult:
    """
    供应计划（采购计划）的最终输出

    基于 ROD 再订货日期策略：
    - 每月 1 号和 15 号是固定的集中采购日
    - 在这两天计算每个 SKU 是否需要补货、补多少
    - 采购量 = 目标库存 − 预计到货时的库存（考虑在途 + 消耗）
    """
    SKU: str = "SKU"                         # 产品唯一标识
    ROD_DATE: str = "再订货日期"              # ROD = Re-Order Date，固定为每月1号或15号
    CURRENT_STOCK: str = "当前库存"           # 此刻仓库里的实际库存量
    IN_TRANSIT: str = "在途库存"              # 已下单但还没到仓库的数量
    SAFETY_STOCK: str = "安全库存"            # 从库存计划拿来的安全库存基线
    TARGET_INVENTORY: str = "目标库存"        # 从库存计划拿来的目标库存基线
    SUGGESTED_QTY: str = "建议采购量"         # 公式算出的建议采购量（未取整、未考虑 MOQ）
    FINAL_QTY: str = "最终采购量"             # 经 MOQ 约束取整后的实际下单量
    EXPECTED_ARRIVAL: str = "预计到货日"       # ROD 日 + Lead Time(30天)，预计货物到达日期
    NEED_REPLENISH: str = "是否需要补货"       # "是" 或 "否"，方便过滤

    @property
    def columns(self) -> List[str]:
        """返回采购计划表的列名"""
        return [self.SKU, self.ROD_DATE, self.CURRENT_STOCK, self.IN_TRANSIT,
                self.SAFETY_STOCK, self.TARGET_INVENTORY,
                self.SUGGESTED_QTY, self.FINAL_QTY,
                self.EXPECTED_ARRIVAL, self.NEED_REPLENISH]


# ============================================================
# Module 4 输出: 发货计划结果
# ============================================================
@dataclass
class ShipmentPlanResult:
    """
    发货计划的最终输出

    策略：
    - 默认走海运（60天）
    - 如果当前库存 < 安全库存，自动切换空运（14天）
    - 当前只发亚马逊单仓
    """
    SKU: str = "SKU"                         # 产品唯一标识
    WAREHOUSE: str = "目标仓库"              # 发货目的地仓库
    SHIP_QTY: str = "发货量"                 # 本次发出的数量
    FREIGHT_MODE: str = "运输方式"            # "海运" 或 "空运"，由库存水位自动决定
    DISPATCH_DATE: str = "安排发货日"         # 安排发货的日期（采购到货当日）
    EST_ARRIVAL: str = "预计上架日"           # 货物到达亚马逊仓库并可售的日期
    FREIGHT_DAYS: str = "运输天数"            # 海运 60 天 / 空运 14 天

    @property
    def columns(self) -> List[str]:
        """返回发货计划表的列名"""
        return [self.SKU, self.WAREHOUSE, self.SHIP_QTY, self.FREIGHT_MODE,
                self.DISPATCH_DATE, self.EST_ARRIVAL, self.FREIGHT_DAYS]


# ============================================================
# 输入数据 Schema —— CSV 模板的列名定义
# 这些类对应 sample_data/ 下的 CSV 文件结构
# ============================================================
@dataclass
class SalesInput:
    """
    历史销量 CSV 列名（sample_data/historical_sales.csv）

    每天每个 SKU 每个渠道一条记录
    """
    SKU: str = "SKU"            # 产品编码
    DATE: str = "日期"           # 销售日期，格式 YYYY-MM-DD
    SALES: str = "销量"          # 当日销量（件）
    CHANNEL: str = "渠道"        # 销售渠道："亚马逊" 或 "独立站"


@dataclass
class ManualForecastInput:
    """
    销售人员月度人工预测 CSV 列名（sample_data/manual_forecast.csv）

    每月每个 SKU 一条记录
    类型区分"历史"（用于计算达成率）和"未来"（用于与统计预测对比）
    """
    SKU: str = "SKU"               # 产品编码
    PERIOD: str = "月份"            # 月份，格式 YYYY-MM，如 "2025-03"
    FORECAST: str = "人工预测量"     # 销售人员预测该月销量
    FORECAST_TYPE: str = "类型"     # "历史"（已发生，可对比实际）或 "未来"（未发生）


@dataclass
class InventoryInput:
    """
    当前库存 CSV 列名（sample_data/current_inventory.csv）

    记录此刻每个 SKU 各仓库的库存状态
    """
    SKU: str = "SKU"               # 产品编码
    STOCK: str = "当前库存"         # 仓库现有库存（可售 + 不可售）
    IN_TRANSIT: str = "在途库存"    # 已下单采购但尚未入仓的数量
    WAREHOUSE: str = "仓库"         # 仓库名称，如 "亚马逊主仓"


@dataclass
class ProductInput:
    """
    产品主数据 CSV 列名（sample_data/product_master.csv）

    每个 SKU 一条记录，包含产品属性和采购参数
    """
    SKU: str = "SKU"               # 产品编码（主键，关联所有表）
    NAME: str = "产品名称"          # 中文产品名
    CATEGORY: str = "品类"          # 产品品类，用于分组分析
    LEAD_TIME: str = "提前期_天"    # 该 SKU 的采购提前期（天），可覆盖全局配置
    MOQ: str = "最小起订量"         # 供应商要求的最小起订量（件）
    COST: str = "成本单价"          # 采购成本单价（元/件）
