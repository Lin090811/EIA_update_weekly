#!/bin/bash
# EIA Weekly Auto Update + DingTalk Push
# 由 macOS launchd 调度，每周自动执行
#
# 流程:
# 1. 更新 EIA 数据 (spider_clean)
# 2. 生成图表 (pic_update + tab_pic_combine)
# 3. 推送到钉钉 (push_notify)

set -e

SCRIPT_DIR="/Users/lin/WorkBuddy/2026-05-06-task-4/EIA_update_weekly/Py_Version"
PYTHON="/Users/lin/anaconda3/bin/python3"
LOG_FILE="/Users/lin/WorkBuddy/2026-05-06-task-4/EIA_update_weekly/Py_Version/logs/eia_auto_$(date +%Y%m%d_%H%M%S).log"

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

echo "============================================="
echo "EIA 自动更新开始: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================="

cd "$SCRIPT_DIR"

# 执行 EIA 自动更新脚本 (任务 456 = 表格图+季节图+合并图+钉钉推送)
"$PYTHON" eia_auto_update.py 456 >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

echo ""
echo "============================================="
echo "EIA 自动更新结束: $(date '+%Y-%m-%d %H:%M:%S')"
echo "退出码: $EXIT_CODE"
echo "日志文件: $LOG_FILE"
echo "============================================="

exit $EXIT_CODE
