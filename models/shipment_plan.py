"""
发货计划模块 —— 亚马逊单仓发货安排

业务背景：
  跨境电商的物流是核心瓶颈。货物从国内仓发出 → 海运/空运 → 亚马逊仓库上架，
  这个过程的时间差直接影响缺货风险和资金占用。

当前策略（单仓 + 智能切换）：
  - 默认走海运（60天）：成本低，适合常规补货
  - 库存跌到安全库存以下 → 自动切空运（14天）：贵但快，救急用

  发货日 = 采购到货日（货物到达国内仓当天即安排发出）

未来扩展方向：
  - 亚马逊欧美站分仓
  - 独立站发货
  - 海运/空运成本优化
"""
import pandas as pd                                     # 数据分析
import numpy as np                                      # 数值计算
from datetime import datetime, timedelta                 # 日期处理
from data.schemas import ShipmentPlanResult, ProcurementPlanResult  # 列名常量
import config                                           # 全局配置（海运60天、空运14天）


def determine_freight_mode(current_stock: int, safety_stock: int) -> tuple:
    """
    根据当前库存水位判断运输方式

    决策规则：
      if 当前库存 < 安全库存:
        → 库存告急！必须走空运（14天到）
      else:
        → 库存正常，走海运（60天到，成本低）

    这是跨境电商最常用的"双模物流"策略：
      正常补货 → 海运（成本 $1-2/kg）
      紧急补货 → 空运（成本 $5-8/kg，但用不起的时候更亏）

    Args:
        current_stock: 当前仓库库存（件）
        safety_stock: 安全库存基线（件）

    Returns:
        tuple: (运输方式字符串, 运输天数)
          例: ("海运", 60) 或 ("空运", 14)
    """
    if current_stock < safety_stock:                     # 库存跌破安全线
        return "空运", config.AIR_FREIGHT_DAYS           #   紧急补货，空运 14 天
    return "海运", config.SEA_FREIGHT_DAYS               # 库存正常，海运 60 天


def run_shipment_plan(
    df_procurement: pd.DataFrame,                        # 供应计划的输出（含采购量 + 到货日）
    df_inventory: pd.DataFrame,                          # 当前库存 + 安全库存信息
) -> pd.DataFrame:
    """
    发货计划主函数 —— "货到了，安排发出去"

    只处理"需要补货"的 SKU（供应计划中"是否需要补货"="是"的记录）。
    不需要补货的 SKU 不发任何货，不生成发货计划。

    流程：
      1. 从供应计划中筛选需要补货的 SKU
      2. 获取该 SKU 的当前库存和安全库存
      3. 判断运输方式（海运 or 空运）
      4. 计算发货日（= 到货日）和预计上架日（= 发货日 + 运输天数）

    Args:
        df_procurement: 供应计划输出 DataFrame（含: SKU, 最终采购量, 预计到货日, 是否需要补货）
        df_inventory: 库存信息 DataFrame（含: SKU, 当前库存, 安全库存）

    Returns:
        标准 ShipmentPlanResult DataFrame:
          SKU, 目标仓库, 发货量, 运输方式, 安排发货日, 预计上架日, 运输天数
    """
    sp = ShipmentPlanResult()                            # 获取发货计划列名常量
    pp = ProcurementPlanResult()                         # 获取采购计划列名常量

    # 步骤1: 只处理"需要补货"的 SKU（不需要补的货不发）
    need_ship = df_procurement[df_procurement[pp.NEED_REPLENISH] == "是"].copy()  # 布尔过滤 + copy 防止警告

    if need_ship.empty:                                  # 如果所有 SKU 都不需要补货
        return pd.DataFrame(columns=sp.columns)          #   返回空 DataFrame（列名齐全但无数据）

    results = []                                         # 收集结果行
    for _, row in need_ship.iterrows():                  # iterrows() 逐行遍历，_ 表示不用的行索引
        sku = row[pp.SKU]                               # 从采购计划行中取 SKU
        final_qty = row[pp.FINAL_QTY]                    # 最终采购量（已含 MOQ 约束）
        expected_arrival = row[pp.EXPECTED_ARRIVAL]      # 预计到货日（字符串，如 "2026-01-31"）

        # 查找该 SKU 的库存信息
        inv_row = df_inventory[df_inventory["SKU"] == sku]  # 按 SKU 过滤
        if inv_row.empty:                                # 库存表里没有这个 SKU？跳过
            continue
        current_stock = inv_row.iloc[0].get("国内库存", 0)  # 国内库存
        fba_stock = inv_row.iloc[0].get("FBA库存", 0)       # FBA库存（新增）
        total_stock = current_stock + fba_stock              # 总可用库存 = 国内 + FBA
        safety_stock = inv_row.iloc[0].get("安全库存", 0)   # 取安全库存

        # 步骤3: 判断运输方式（核心决策），用总库存比较
        freight_mode, freight_days = determine_freight_mode(total_stock, safety_stock)

        # 步骤4: 计算日期
        arrival_date = datetime.strptime(expected_arrival, "%Y-%m-%d")  # 字符串 → datetime 对象
        dispatch_date = arrival_date                     # 发货日 = 到货日（当天安排发出）
        est_listing = dispatch_date + timedelta(days=freight_days)  # 上架日 = 发货日 + 运输天数

        # 构建结果行
        results.append({
            sp.SKU: sku,                                 # SKU 编码
            sp.WAREHOUSE: "亚马逊主仓",                   # 当前只发亚马逊
            sp.SHIP_QTY: final_qty,                      # 发货数量 = 最终采购量
            sp.FREIGHT_MODE: freight_mode,               # "海运" 或 "空运"
            sp.DISPATCH_DATE: dispatch_date.strftime("%Y-%m-%d"),  # 安排发货日
            sp.EST_ARRIVAL: est_listing.strftime("%Y-%m-%d"),      # 预计上架日（亚马逊可售）
            sp.FREIGHT_DAYS: freight_days,               # 运输天数（60 或 14）
        })

    return pd.DataFrame(results)[sp.columns]             # 列表 → DataFrame，按 Schema 选列
