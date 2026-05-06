#!/usr/bin/env python3
"""
从 EIA psw09.xls (Table 9) 提取历史周度数据，补充到 eia_weekly.csv 中。
覆盖 2018 年至今所有指标，填补缺失的 2024/2025 数据。

XLS 中:
- 产量/进口/出口/需求 单位 = 千桶/天 (Thousand Barrels per Day) → 直接用
- 库存 单位 = 千桶 (Thousand Barrels) → 需除以 1000 转为百万桶
- 产能利用率 单位 = % → 直接用

用法: python3 fetch_eia_history.py
"""
import polars as pl
import datetime
import os
import sys

XLS_URL = "https://ir.eia.gov/wpsr/psw09.xls"
XLS_PATH = "/tmp/psw09.xls"
CSV_PATH = "./data/eia_weekly.csv"
START_DATE = "2018-01-01"


def download_xls():
    import urllib.request
    print(f"正在下载 EIA Table 9: {XLS_URL}")
    urllib.request.urlretrieve(XLS_URL, XLS_PATH)
    size = os.path.getsize(XLS_PATH)
    print(f"下载完成，文件大小: {size / 1024 / 1024:.1f} MB")


def extract_series(sheet_name, col_idx, stub_1, stub_2, name, unit_divisor=1.0):
    """
    从 XLS 指定 sheet 提取时间序列
    unit_divisor: 值需要除以的系数（库存千桶→百万桶 = 1000）
    """
    df = pl.read_excel(XLS_PATH, engine='calamine', sheet_name=sheet_name)
    col_name = df.columns[col_idx]

    result_rows = []
    for row in df.iter_rows(named=True):
        date_val = row[df.columns[0]]
        val = row[col_name]

        if date_val is None or str(date_val).strip() in ('', 'Date', 'Sourcekey', 'Back to Contents'):
            continue

        if isinstance(date_val, datetime.datetime):
            date_str = date_val.strftime("%Y-%m-%d")
        elif isinstance(date_val, datetime.date):
            date_str = date_val.strftime("%Y-%m-%d")
        else:
            try:
                date_str = str(date_val).split(" ")[0]
                datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except:
                continue

        if date_str < START_DATE:
            continue

        if val is None or str(val).strip() in ('', 'None', 'nan'):
            continue

        try:
            float_val = float(val) / unit_divisor
        except (ValueError, TypeError):
            continue

        result_rows.append({
            "STUB_1": stub_1,
            "STUB_2": stub_2,
            "variable": date_str,
            "value": float_val,
            "name": name,
        })

    return pl.DataFrame(result_rows)


def get_sub_title(name):
    if "汽油" in name:
        return "汽油"
    elif "柴油" in name:
        return "柴油"
    elif "航煤" in name:
        return "航煤"
    elif "燃料油" in name:
        return "燃料油"
    else:
        return "原油"


def main():
    if not os.path.exists(XLS_PATH) or os.path.getsize(XLS_PATH) < 1000:
        download_xls()

    print("正在提取历史数据...")

    # 映射表: (sheet, col_idx, STUB_1, STUB_2, name, unit_divisor)
    # unit_divisor=1.0: 产量/进口/出口/需求/利用率（千桶/天 或 %）
    # unit_divisor=1000.0: 库存（千桶→百万桶）
    #
    # 所有列索引已通过最新日期数值与 table9.csv 验证匹配
    series_map = [
        # ===== Data 1: Crude Oil Production =====
        ("Data 1", 1, "Crude Oil Production ", "Domestic Production",
         "美国原油产量（千桶/天）", 1.0),

        # ===== Data 2: Inputs and Utilization =====
        ("Data 2", 13, "Refiner Inputs and Utilization ", "Operable Capacity",
         "美国炼厂运营炼能（千桶/天）", 1.0),
        ("Data 2", 19, "Refiner Inputs and Utilization ", "Percent Utilization",
         "美国炼厂产能利用率（%）", 1.0),

        # ===== Data 3: Refiner and Blender Net Production =====
        # 注意: col[1]=WGFRPUS2 = Adjusted Net Production (总量, 包含调整项)
        # table9.csv 中 "Finished Motor Gasoline" 列实际显示的是 WGFRPUS2
        # 如果后续 table9.csv 更新后匹配到其他列，需要调整此处
        ("Data 3", 1, "Refiner and Blender Net Production ", "Finished Motor Gasoline",
         "美国汽油产量（千桶/天）", 1.0),    # WGFRPUS2
        ("Data 3", 57, "Refiner and Blender Net Production ", "Kerosene-Type Jet Fuel",
         "美国航煤产量（千桶/天）", 1.0),
        ("Data 3", 75, "Refiner and Blender Net Production ", "Distillate Fuel Oil",
         "美国柴油产量（千桶/天）", 1.0),
        ("Data 3", 99, "Refiner and Blender Net Production ", "Residual Fuel Oil",
         "美国燃料油产量（千桶/天）", 1.0),

        # ===== Data 6: Stocks (千桶 → 百万桶, /1000) =====
        ("Data 6", 2, "Stocks (Million Barrels) ", "Commercial",
         "美国商业原油库存（百万桶）", 1000.0),
        ("Data 6", 5, "Stocks (Million Barrels) ", "Cushing, Oklahoma",
         "美国库欣原油库存（百万桶）", 1000.0),
        ("Data 6", 10, "Stocks (Million Barrels) ", "SPR",
         "美国战略原油储备（百万桶）", 1000.0),     # WCSSTUS1
        ("Data 6", 11, "Stocks (Million Barrels) ", "Total Motor Gasoline",
         "美国汽油库存（百万桶）", 1000.0),
        ("Data 6", 102, "Stocks (Million Barrels) ", "Kerosene-Type Jet Fuel",
         "美国航煤库存（百万桶）", 1000.0),
        ("Data 6", 108, "Stocks (Million Barrels) ", "Distillate Fuel Oil",
         "美国柴油库存（百万桶）", 1000.0),
        ("Data 6", 144, "Stocks (Million Barrels) ", "Residual Fuel Oil",
         "美国燃料油库存（百万桶）", 1000.0),
        ("Data 6", 168, "Stocks (Million Barrels) ", "Total Stocks (Excluding SPR)",
         "美国原油成品油总库存去除战略储备（百万桶）", 1000.0),  # WTESTUS1
        ("Data 6", 169, "Stocks (Million Barrels) ", "Total Stocks (Including SPR)",
         "美国原油成品油总库存包含战略储备（百万桶）", 1000.0),  # WTTSTUS1

        # ===== Data 7: Imports =====
        ("Data 7", 1, "Imports ", "Total Crude Oil Incl SPR",
         "美国原油进口（千桶/天）", 1.0),
        ("Data 7", 10, "Imports ", "Total Motor Gasoline",
         "美国汽油进口（千桶/天）", 1.0),        # WGTIMUS2
        ("Data 7", 106, "Imports ", "Kerosene-Type Jet Fuel",
         "美国航煤进口（千桶/天）", 1.0),
        ("Data 7", 112, "Imports ", "Distillate Fuel Oil",
         "美国柴油进口（千桶/天）", 1.0),
        ("Data 7", 142, "Imports ", "Residual Fuel Oil",
         "美国燃料油进口（千桶/天）", 1.0),

        # ===== Data 8: Exports =====
        ("Data 8", 2, "Exports ", "Crude Oil",
         "美国原油出口（千桶/天）", 1.0),          # WCREXUS2
        ("Data 8", 4, "Exports ", "Total Motor Gasoline",
         "美国汽油出口（千桶/天）", 1.0),          # W_EPM0F_EEX
        ("Data 8", 6, "Exports ", "Kerosene-Type Jet Fuel",
         "美国航煤出口（千桶/天）", 1.0),
        ("Data 8", 7, "Exports ", "Distillate Fuel Oil",
         "美国柴油出口（千桶/天）", 1.0),
        ("Data 8", 8, "Exports ", "Residual Fuel Oil",
         "美国燃料油出口（千桶/天）", 1.0),

        # ===== Data 10: Product Supplied =====
        ("Data 10", 2, "Product Supplied ", "Finished Motor Gasoline",
         "美国汽油需求（千桶/天）", 1.0),         # WGFUPUS2
        ("Data 10", 3, "Product Supplied ", "Kerosene-Type Jet Fuel",
         "美国航煤需求（千桶/天）", 1.0),
        ("Data 10", 4, "Product Supplied ", "Distillate Fuel Oil",
         "美国柴油需求（千桶/天）", 1.0),
        ("Data 10", 5, "Product Supplied ", "Residual Fuel Oil",
         "美国燃料油需求（千桶/天）", 1.0),
    ]

    all_dfs = []
    for sheet_name, col_idx, stub_1, stub_2, name, divisor in series_map:
        try:
            df = extract_series(sheet_name, col_idx, stub_1, stub_2, name, divisor)
            if len(df) > 0:
                df = df.with_columns(pl.lit(get_sub_title(name)).alias("sub_title"))
                all_dfs.append(df)
                print(f"  OK: {name} ({stub_2}) - {len(df)} rows")
            else:
                print(f"  WARN: {name} - 0 rows from {sheet_name} col[{col_idx}]")
        except Exception as e:
            print(f"  ERROR: {name} - {e}")

    if not all_dfs:
        print("未提取到任何数据，退出")
        sys.exit(1)

    history = pl.concat(all_dfs, rechunk=True)
    print(f"\n历史数据总计: {len(history)} 行")

    # 读取现有 CSV
    existing = pl.read_csv(CSV_PATH, encoding="utf-8")
    print(f"现有 CSV 数据: {len(existing)} 行")

    # 合并：用 STUB_1 + STUB_2 + variable 作为唯一键去重
    # keep="last" 确保新数据覆盖旧数据
    combined = pl.concat([existing, history], rechunk=True)
    combined = combined.unique(subset=["STUB_1", "STUB_2", "variable"], keep="last")
    combined = combined.sort(by=["sub_title", "name", "variable"])

    combined.write_csv(CSV_PATH)
    print(f"\n合并完成，最终数据: {len(combined)} 行")

    # 验证
    print("\n=== 数据验证 ===")
    year_counts = combined.select(
        pl.col("variable").str.slice(0, 4).alias("year")
    ).group_by("year").len().sort("year")
    print(year_counts)

    for yr in ["2024", "2025", "2026"]:
        dy = combined.filter(pl.col("variable").str.slice(0, 4) == yr)
        if len(dy) > 0:
            print(f"{yr} 数据: {len(dy)} 行, 范围: {dy['variable'].min()} ~ {dy['variable'].max()}")
        else:
            print(f"{yr} 数据: 无")

    # 验证最新日期的值是否与 table9.csv 一致
    print("\n=== 2026-04-24 数据抽样验证 ===")
    sample = combined.filter(pl.col("variable") == "2026-04-26")
    # 如果 04-26 没数据就取 04-24
    if len(sample) == 0:
        sample = combined.filter(pl.col("variable") == "2026-04-24")
    for row in sample.head(5).iter_rows(named=True):
        print(f"  {row['STUB_2']:40s} | {row['value']}")


if __name__ == "__main__":
    main()
