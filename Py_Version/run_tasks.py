#!/usr/bin/env python3
"""
EIA 油品数据更新运行脚本 (macOS 适配版)
用法: python run_tasks.py [任务号组合]
例如: python run_tasks.py 4     # 仅更新表格图
      python run_tasks.py 456   # 表格图 + 季节图 + 合并
      python run_tasks.py       # 默认按 config.ini 配置运行
"""
import os
import sys

# 确保工作目录为 Py_Version
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spider_clean import all_update, one_year_update, data_clean
from tab_update import tab_update
from pic_update import pic_update, tab_pic_combine
from wechat_send import sending_pics

tasks = {
    1: ("全量更新（5年数据）", all_update),
    2: ("1年增量更新", one_year_update),
    3: ("数据清洗", data_clean),
    4: ("表格图更新", tab_update),
    5: ("季节图更新", pic_update),
    6: ("表格图+季节图合并", tab_pic_combine),
    7: ("微信发送图片", sending_pics),
}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_ids = list(set(map(int, list(sys.argv[1].replace(" ", "")))))
    else:
        # 从 config.ini 读取默认配置
        import configparser
        config = configparser.ConfigParser()
        config.read("config.ini", encoding="utf-8")
        if config.has_option("Task", "default"):
            task_ids = list(set(map(int, list(config.get("Task", "default").replace(" ", "")))))
        else:
            print("请指定任务号，例如: python run_tasks.py 456")
            sys.exit(1)

    for tid in sorted(task_ids):
        if tid not in tasks:
            print(f"未知任务号: {tid}")
            continue
        name, func = tasks[tid]
        print(f"\n{'='*50}")
        print(f"正在执行任务 {tid}: {name}")
        print(f"{'='*50}")
        try:
            func()
            print(f"任务 {tid} ({name}) 完成!")
        except Exception as e:
            print(f"任务 {tid} ({name}) 失败: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*50}")
    print("所有指定任务执行完毕！")
    print(f"{'='*50}")
