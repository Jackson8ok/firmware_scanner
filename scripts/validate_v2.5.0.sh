#!/bin/bash
# 玄武 v2.5.0 实际环境验证脚本

set -e

echo "========================================="
echo "  🐢 玄武 v2.5.0 实际环境验证"
echo "========================================="
echo ""

cd /mnt/workspace/firmware_scanner

# 1. 检查服务状态
echo "[1/6] 检查服务状态..."
if pgrep -f "uvicorn api.main:app" > /dev/null; then
    echo "  ✅ 服务正在运行"
    PID=$(pgrep -f "uvicorn api.main:app")
    echo "  PID: $PID"
else
    echo "  ⚠️  服务未运行，启动中..."
    nohup python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > logs/app.log 2>&1 &
    sleep 5
fi

# 2. 健康检查
echo ""
echo "[2/6] 健康检查..."
HEALTH=$(curl -s http://localhost:8000/api/health)
echo "  响应：$HEALTH"

# 3. 上传测试样本
echo ""
echo "[3/6] 上传测试样本 (owrt_15.05.1.squashfs)..."
UPLOAD_RESULT=$(curl -s -X POST http://localhost:8000/api/upload \
  -F "file=@uploads/owrt_15.05.1.squashfs" \
  -F "firmware_type=squashfs")
echo "  上传结果：$UPLOAD_RESULT"

# 4. 启动扫描
echo ""
echo "[4/6] 启动扫描..."
SCAN_RESULT=$(curl -s -X POST "http://localhost:8000/api/scan" \
  -F "firmware_id=owrt_15.05.1.squashfs" \
  -F "firmware_type=squashfs")
TASK_ID=$(echo "$SCAN_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
echo "  任务 ID: $TASK_ID"

# 5. 等待完成
echo ""
echo "[5/6] 等待扫描完成..."
for i in {1..30}; do
    STATUS=$(curl -s "http://localhost:8000/api/task/$TASK_ID/status")
    STATE=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    if [ "$STATE" = "completed" ]; then
        echo "  ✅ 扫描完成 (耗时: $i 秒)"
        break
    elif [ "$STATE" = "failed" ]; then
        echo "  ❌ 扫描失败"
        exit 1
    fi
    sleep 1
done

# 6. 获取结果
echo ""
echo "[6/6] 获取扫描结果..."
RESULT=$(curl -s "http://localhost:8000/api/task/$TASK_ID/result")
echo "$RESULT" | python3 -m json.tool > /tmp/v2.5.0_validation_result.json

# 提取关键指标
COMPONENTS=$(echo "$RESULT" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('components', [])))")
TOTAL_CVES=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_cves', 0))")
CRITICAL=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('critical_count', 0))")
HIGH=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('high_count', 0))")

echo ""
echo "========================================="
echo "  📊 验证结果汇总"
echo "========================================="
echo ""
echo "  组件数：$COMPONENTS (目标：≥7)"
echo "  CVE 总数：$TOTAL_CVES"
echo "  Critical: $CRITICAL"
echo "  High: $HIGH"
echo ""

# 验证通过判断
if [ "$COMPONENTS" -ge 7 ]; then
    echo "  ✅ 组件数达标"
else
    echo "  ⚠️  组件数未达标 (当前：$COMPONENTS, 目标：≥7)"
fi

echo ""
echo "详细结果：/tmp/v2.5.0_validation_result.json"
echo ""
echo "========================================="
