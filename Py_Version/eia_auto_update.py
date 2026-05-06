#!/usr/bin/env python3
"""
EIA 油品数据自动更新+推送脚本 (macOS 自动化版)
- 从 EIA 官网获取最新周度油品数据
- 生成表格图 + 季节图 + 合并图
- 推送图片到指定渠道

用法:
  python eia_auto_update.py          # 自动执行任务 456（表格+季节图+合并）
  python eia_auto_update.py 123      # 全量更新 + 增量更新 + 清洗
  python eia_auto_update.py 1234567  # 全部任务（含微信发送，仅 Windows）
"""
import os
import sys
import json
import datetime

# 确保工作目录为脚本所在目录（Py_Version）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from spider_clean import all_update, one_year_update, data_clean
from tab_update import tab_update
from pic_update import pic_update, tab_pic_combine
from wechat_send import sending_pics

# 推送模块（macOS 可选，Windows 使用微信发送）
try:
    from push_notify import push_results
except ImportError:
    push_results = None

TASKS = {
    1: ("全量更新（5年数据）", all_update),
    2: ("1年增量更新", one_year_update),
    3: ("数据清洗", data_clean),
    4: ("表格图更新", tab_update),
    5: ("季节图更新", pic_update),
    6: ("表格图+季节图合并", tab_pic_combine),
    7: ("微信发送图片", sending_pics),
}

def run_tasks(task_ids):
    """执行指定的任务列表"""
    results = []
    for tid in sorted(task_ids):
        if tid not in TASKS:
            print(f"[跳过] 未知任务号: {tid}")
            continue
        name, func = TASKS[tid]
        print(f"\n{'='*60}")
        print(f"[任务 {tid}] {name}")
        print(f"{'='*60}")
        try:
            start = datetime.datetime.now()
            func()
            elapsed = (datetime.datetime.now() - start).total_seconds()
            print(f"[完成] 任务 {tid} ({name}) - 耗时 {elapsed:.1f}s")
            results.append({"task": tid, "name": name, "status": "success", "elapsed": f"{elapsed:.1f}s"})
        except Exception as e:
            print(f"[失败] 任务 {tid} ({name}): {e}")
            import traceback
            traceback.print_exc()
            results.append({"task": tid, "name": name, "status": "failed", "error": str(e)})
    return results

def main():
    # 确定要执行的任务
    if len(sys.argv) > 1:
        task_str = sys.argv[1]
    else:
        # 从 config.ini 读取默认配置
        import configparser
        config = configparser.ConfigParser()
        config.read("config.ini", encoding="utf-8")
        if config.has_option("Task", "default"):
            task_str = config.get("Task", "default").strip()
        else:
            task_str = "456"  # 默认执行数据更新+图表生成

    task_ids = sorted(set(int(c) for c in task_str.replace(" ", "") if c.isdigit()))
    print(f"EIA 油品数据自动更新系统")
    print(f"执行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"任务列表: {task_ids}")

    results = run_tasks(task_ids)

    # 输出汇总
    print(f"\n{'='*60}")
    print("执行汇总:")
    print(f"{'='*60}")
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"成功: {success}  失败: {failed}")
    for r in results:
        icon = "✅" if r["status"] == "success" else "❌"
        print(f"  {icon} 任务{r['task']} {r['name']} ({r.get('elapsed', r.get('error', ''))})")

    # 输出生成的文件
    pic_dir = os.path.join(SCRIPT_DIR, "pic")
    if os.path.isdir(pic_dir):
        print(f"\n生成文件:")
        for f in os.listdir(pic_dir):
            if f.endswith(('.png', '.jpg')):
                fpath = os.path.join(pic_dir, f)
                size = os.path.getsize(fpath)
                print(f"  📊 {f} ({size/1024:.0f} KB)")

    # 推送结果
    if push_results:
        print(f"\n{'='*60}")
        print("开始推送结果...")
        print(f"{'='*60}")
        try:
            push_results()
        except Exception as e:
            print(f"[推送] 失败: {e}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
