"""
共享数据结构定义

四个模块之间通过 pandas DataFrame 通信，此处定义各模块输入输出的列名常量。
"""
from dataclasses import dataclass, field
from typing import List


# ============================================================
# Module 1: 需求预测 → 产出 ForecastCompareResult
# ============================================================
@dataclass
class ForecastResult:
    """统计预测结果列名"""
    SKU: str = "SKU"
    PERIOD: str = "月份"          # 月度粒度
    METHOD: str = "预测方法"
    STAT_FORECAST: str = "统计预测量"


@dataclass
class ForecastCompareResult:
    """双轨对比结果列名（月度）"""
    SKU: str = "SKU"
    PERIOD: str = "月份"
    ACTUAL: str = "实际销量"
    MANUAL_FORECAST: str = "人工预测量"
    STAT_FORECAST: str = "统计预测量"
    ACHIEVEMENT_RATE: str = "达成率_人工"       # 实际/人工预测 × 100
    STAT_DEVIATION: str = "偏差_统计vs人工"     # (统计-人工)/人工 × 100

    @property
    def columns(self) -> List[str]:
        return [self.SKU, self.PERIOD, self.ACTUAL, self.MANUAL_FORECAST,
                self.STAT_FORECAST, self.ACHIEVEMENT_RATE, self.STAT_DEVIATION]


# ============================================================
# Module 2: 库存计划 → 产出 InventoryPlanResult
# ============================================================
@dataclass
class InventoryPlanResult:
    """库存计划结果列名"""
    SKU: str = "SKU"
    AVG_DAILY_DEMAND: str = "日均需求"
    SAFETY_STOCK: str = "安全库存"
    CYCLE_STOCK: str = "周转库存"
    TARGET_INVENTORY: str = "目标库存"
    ABC_CLASS: str = "ABC分类"
    XYZ_CLASS: str = "XYZ分类"

    @property
    def columns(self) -> List[str]:
        return [self.SKU, self.AVG_DAILY_DEMAND, self.SAFETY_STOCK,
                self.CYCLE_STOCK, self.TARGET_INVENTORY,
                self.ABC_CLASS, self.XYZ_CLASS]


# ============================================================
# Module 3: 供应计划 → 产出 ProcurementPlanResult
# ============================================================
@dataclass
class ProcurementPlanResult:
    """供应计划（采购计划）结果列名"""
    SKU: str = "SKU"
    ROD_DATE: str = "再订货日期"       # ROD: 每月1号或15号
    CURRENT_STOCK: str = "当前库存"
    IN_TRANSIT: str = "在途库存"
    SAFETY_STOCK: str = "安全库存"
    TARGET_INVENTORY: str = "目标库存"
    SUGGESTED_QTY: str = "建议采购量"
    FINAL_QTY: str = "最终采购量"       # 含MOQ调整
    EXPECTED_ARRIVAL: str = "预计到货日"  # ROD日期 + 30天
    NEED_REPLENISH: str = "是否需要补货"

    @property
    def columns(self) -> List[str]:
        return [self.SKU, self.ROD_DATE, self.CURRENT_STOCK, self.IN_TRANSIT,
                self.SAFETY_STOCK, self.TARGET_INVENTORY,
                self.SUGGESTED_QTY, self.FINAL_QTY,
                self.EXPECTED_ARRIVAL, self.NEED_REPLENISH]


# ============================================================
# Module 4: 发货计划 → 产出 ShipmentPlanResult
# ============================================================
@dataclass
class ShipmentPlanResult:
    """发货计划结果列名（亚马逊单仓）"""
    SKU: str = "SKU"
    WAREHOUSE: str = "目标仓库"
    SHIP_QTY: str = "发货量"
    FREIGHT_MODE: str = "运输方式"      # 海运 / 空运
    DISPATCH_DATE: str = "安排发货日"
    EST_ARRIVAL: str = "预计上架日"
    FREIGHT_DAYS: str = "运输天数"

    @property
    def columns(self) -> List[str]:
        return [self.SKU, self.WAREHOUSE, self.SHIP_QTY, self.FREIGHT_MODE,
                self.DISPATCH_DATE, self.EST_ARRIVAL, self.FREIGHT_DAYS]


# ============================================================
# 输入数据 Schema（CSV 模板列名）
# ============================================================
@dataclass
class SalesInput:
    """历史销量 CSV 列名"""
    SKU: str = "SKU"
    DATE: str = "日期"
    SALES: str = "销量"
    CHANNEL: str = "渠道"          # 亚马逊 / 独立站


@dataclass
class ManualForecastInput:
    """销售人员月度人工预测 CSV 列名"""
    SKU: str = "SKU"
    PERIOD: str = "月份"           # 如 2025-01
    FORECAST: str = "人工预测量"
    FORECAST_TYPE: str = "类型"    # "历史" or "未来"


@dataclass
class InventoryInput:
    """当前库存 CSV 列名"""
    SKU: str = "SKU"
    STOCK: str = "当前库存"
    IN_TRANSIT: str = "在途库存"
    WAREHOUSE: str = "仓库"


@dataclass
class ProductInput:
    """产品主数据 CSV 列名"""
    SKU: str = "SKU"
    NAME: str = "产品名称"
    CATEGORY: str = "品类"
    LEAD_TIME: str = "提前期_天"
    MOQ: str = "最小起订量"
    COST: str = "成本单价"
