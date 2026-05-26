"""
供应计划模块 —— ROD（再订货日期）策略

业务背景：
  中小企业跨境电商通常不是"随时下单"，而是每月集中采购 2 次，
  固定日期统一向供应商下单，降低沟通成本和运费。

ROD 策略：
  每月 1 号和 15 号是固定的"集中采购日"
  当天检查每个 SKU：库存还够不够？不够就下单补货
  采购提前期 = 30 天（下单 → 货物到达国内仓）

采购量公式：
  采购量 = 目标库存 − (当前库存 + 在途库存 − 提前期内消耗)
         = 目标库存 − 预计到货时的库存

  如果算出来是负数 → 库存还够，不补货
  如果算出来是正数 → 按需补到目标库存水平
"""
import pandas as pd                                     # 数据分析
import numpy as np                                      # 数值计算
from datetime import datetime, timedelta                 # 日期处理（datetime 表示时刻、timedelta 表示时间差）
from data.schemas import ProcurementPlanResult, InventoryPlanResult  # 列名常量
import config                                           # 全局配置


def get_upcoming_rod_dates(current_date: datetime, months_ahead: int = 3) -> list:
    """
    计算未来 N 个月的所有 ROD 日期（含对应的预计到货日期）

    为什么需要这个函数？
      ROD 日期不是"今天+15天"，而是"每月1号和15号"。
      需要根据当前日期，算出接下来哪些 1 号和 15 号还没过。

    Args:
        current_date: 当前日期（作为"现在"的参考点）
        months_ahead: 向前看几个月，默认 3 个月（= 6 次 ROD）

    Returns:
        list of tuples: [(ROD日期, 预计到货日期), ...]
          例: [(datetime(2026,1,1), datetime(2026,1,31)), (datetime(2026,1,15), datetime(2026,2,14)), ...]

    算法：
      从当前月开始，逐月遍历 1 号和 15 号，
      如果该日期 ≥ 当前日期 → 加入列表，
      直到收集了 months_ahead × 2 条记录。
    """
    dates = []                                           # 结果列表
    year = current_date.year                             # 当前年份
    month = current_date.month                           # 当前月份

    for _ in range(months_ahead + 2):                    # 多算 2 个月确保不会不够取
        for day in config.ROD_DAYS:                      # 遍历 [1, 15]
            rod = datetime(year, month, day)             # 构造这个月的这个日期的 datetime 对象
            if rod >= current_date:                      # 这个 ROD 日期还没过（在本月或未来）
                arrival = rod + timedelta(days=config.PROCUREMENT_LEAD_TIME)  # 到货日 = ROD + 30天
                dates.append((rod, arrival))             # 加入结果列表
        month += 1                                       # 下一个月
        if month > 12:                                   # 跨年处理
            month = 1                                    # 月份归 1
            year += 1                                    # 年份 +1

    return dates[:months_ahead * 2]                      # 只返回前 N 个月的（每月 2 次）


def calculate_procurement(
    inventory_row: pd.Series,          # 当前库存信息（一行 Series）
    forecast_row: pd.Series,           # 预测信息（库存计划输出的一行）
    next_rod: datetime,                # 下一个 ROD 日期
    next_arrival: datetime,            # 预计到货日期（ROD + 30天）
    days_to_next_rod: int,             # 距离下次补货窗口还有多少天（当前未使用，预留参数）
) -> dict:
    """
    计算单个 SKU 在某个 ROD 日期的采购量和补货建议

    核心逻辑（逐步推导）：
      1. 预计到货时库存 = 现在库存 + 在途 − Lead Time 期间消耗
      2. 缺口 = 目标库存 − 预计到货时库存
      3. 缺口 > 0 → 需要补货，缺口 = 建议采购量
      4. 考虑 MOQ 约束：如果 0 < 缺口 < MOQ，按 MOQ 下单

    为什么只用"最近一次 ROD"？
      当前版本的 ROD 策略是"每次只规划最近一次采购"，
      不需要同时规划未来多次的采购量（可以根据最新库存重新算）。

    Args:
        inventory_row: 当前库存信息（含 SKU, 当前库存, 在途库存）
        forecast_row: 预测信息（含 日均需求, 安全库存, 目标库存）
        next_rod: 下一个 ROD 日期
        next_arrival: 预计到货日期
        days_to_next_rod: 预留参数（未使用）

    Returns:
        dict: 采购建议单行数据（最终会转成 DataFrame 的一行）
    """
    # 从输入行中提取关键参数
    current_stock = inventory_row["当前库存"]            # 现在仓库里的量
    in_transit = inventory_row["在途库存"]               # 已下单还没到的量
    daily_demand = forecast_row["日均需求"]              # 日均销量（从库存计划拿来的）
    safety_stock = forecast_row["安全库存"]              # 安全库存基线
    target_inventory = forecast_row["目标库存"]          # 目标库存基线

    # 提前期内的总消耗 = 每天卖这么多 × 30天
    demand_until_next = daily_demand * config.PROCUREMENT_LEAD_TIME

    # 预计到货时的库存 = 现在有 + 路上有 − 30天内卖掉的
    projected_stock = current_stock + in_transit - demand_until_next

    # 缺口 = 目标库存 − 预计到时库存（正数 = 缺货，负数 = 够用）
    suggested_qty = target_inventory - projected_stock

    # MOQ（最小起订量）约束处理
    moq = inventory_row.get("最小起订量", config.DEFAULT_MOQ)  # 取产品的 MOQ，没配就 0（不限制）
    if suggested_qty > 0 and suggested_qty < moq:         # 需要补货但量不够 MOQ
        final_qty = moq                                   #   按 MOQ 下单（宁可多订一点）
    elif suggested_qty > 0:                               # 需要补货且 ≥ MOQ
        final_qty = int(np.ceil(suggested_qty))            #   向上取整（不能订 0.3 件）
    else:                                                 # 不需要补货
        final_qty = 0                                     #   下单量为 0

    need_replenish = final_qty > 0                         # 最终采购量 > 0 才算需要补货

    return {                                               # 返回一个字典，对应采购计划表的一行
        "SKU": inventory_row["SKU"],                       # SKU 编码
        "再订货日期": next_rod.strftime("%Y-%m-%d"),        # ROD 日期（如"2026-01-01"）
        "当前库存": current_stock,                          # 当前库存
        "在途库存": in_transit,                             # 在途库存
        "安全库存": safety_stock,                           # 安全库存基线
        "目标库存": target_inventory,                       # 目标库存基线
        "建议采购量": max(0, int(np.ceil(suggested_qty))),  # 建议量（暴露原始计算值，可能被 MOQ 调整）
        "最终采购量": final_qty,                             # 实际下单量（已含 MOQ 约束）
        "预计到货日": next_arrival.strftime("%Y-%m-%d"),    # ROD + 30天
        "是否需要补货": "是" if need_replenish else "否",     # 人类可读的布尔值
    }


def run_supply_plan(
    df_inventory: pd.DataFrame,            # 当前库存数据（含 SKU, 当前库存, 在途库存）
    df_forecast: pd.DataFrame,             # 库存计划输出（含 日均需求, 安全库存, 目标库存）
    current_date: datetime = None,         # 当前日期（None = 用系统当前时间）
    months_ahead: int = 3,                 # 往前规划几个月
) -> pd.DataFrame:
    """
    供应计划主函数 —— "一键生成采购建议"

    流程：
      1. 计算未来的 ROD 日期列表
      2. 合并库存数据和预测数据（按 SKU 对齐）
      3. 对每个 SKU，计算最近一次 ROD 的采购建议

    Args:
        df_inventory: 当前库存 DataFrame（来自 sample_data/current_inventory.csv）
        df_forecast: 库存计划输出 DataFrame（来自 inventory_plan.run_inventory_plan()）
        current_date: 以哪个日期为"现在"（用于计算后续 ROD 日期）
        months_ahead: 向前看几个月

    Returns:
        标准 ProcurementPlanResult DataFrame
    """
    if current_date is None:                             # 如果没传日期
        current_date = datetime.now()                    #   用系统当前时间

    pp = ProcurementPlanResult()                         # 获取采购计划列名常量

    # 计算未来 ROD 日期列表
    rod_dates = get_upcoming_rod_dates(current_date, months_ahead)

    # 按 SKU 合并库存数据和预测数据（inner join：只保留两边都有的 SKU）
    merged = df_inventory.merge(df_forecast, on="SKU", how="inner")

    results = []                                         # 收集结果行
    for sku in merged["SKU"].unique():                    # 遍历每个 SKU
        sku_data = merged[merged["SKU"] == sku].iloc[0]  # 取该 SKU 的第一行（主数据 + 预测合并后）

        for next_rod, next_arrival in rod_dates[:1]:     # 只看最近一次 ROD（[:1] 取第一个）
            result = calculate_procurement(               # 调用计算函数
                sku_data, sku_data,                      # 库存行和预测行（当前合并后是同一行）
                next_rod, next_arrival, 0                # ROD日期、到货日期、间隔天数（暂未使用）
            )
            results.append(result)                       # 加入结果列表

    return pd.DataFrame(results)[pp.columns[:len(results[0])]]  # 列表 → DataFrame，按 Schema 选列
