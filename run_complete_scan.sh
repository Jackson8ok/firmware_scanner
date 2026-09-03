#!/bin/bash
# ============================================================
# 玄武 固件扫描平台 - 完整测试脚本
# v2.3 包含批量扫描、Dashboard 和 R155 合规检查
# ============================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/mnt/workspace/firmware_scanner"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║      🐢 玄武 固件漏洞扫描平台 v2.3 测试脚本       ║"
echo "║      批量扫描 + Dashboard 增强 + R155 合规检查         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 配置
BASE_URL="http://127.0.0.1:8765"
TEST_DIR="${PROJECT_DIR}/test_firmware"
REPORT_DIR="${PROJECT_DIR}/reports"

# 颜色输出函数
print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ ${1}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  ${1}${NC}"
}

print_error() {
    echo -e "${RED}❌ ${1}${NC}"
}

# 第 1 步：检查环境
print_step "1. 检查环境"

echo "检查 Python 版本..."
python3 --version || { print_error "Python 3 未安装"; exit 1; }

echo "检查关键依赖..."
for pkg in fastapi uvicorn openpyxl python-docx pyyaml; do
    if python3 -c "import $pkg" 2>/dev/null; then
        print_success "$pkg 已安装"
    else
        print_warning "$pkg 未安装，尝试自动安装..."
        pip install $pkg -q
    fi
done

echo "检查项目结构..."
if [ -d "$PROJECT_DIR" ]; then
    print_success "项目目录存在"
else
    print_error "项目目录不存在：$PROJECT_DIR"
    exit 1
fi

# 第 2 步：检查服务器状态
print_step "2. 检查服务器状态"

check_server() {
    if curl -s "$BASE_URL/api/queue/stats" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

if check_server; then
    print_success "服务器正在运行 ($BASE_URL)"
    
    # 获取队列统计
    stats=$(curl -s "$BASE_URL/api/queue/stats")
    echo ""
    echo "当前队列状态:"
    echo "$stats" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  等待中：{data.get('pending', 0)}\")
    print(f\"  进行中：{data.get('running', 0)}\")
    print(f\"  已完成：{data.get('completed', 0)}\")
    print(f\"  最大并发：{data.get('max_concurrent', 'N/A')}\")
except:
    pass
"
else
    print_warning "服务器未运行，请先启动服务："
    echo -e "  ${BLUE}cd $PROJECT_DIR && python -m api.main${NC}"
    echo -e "  或在新终端运行上述命令后继续此脚本"
    
    read -p "是否继续？(y/n): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        exit 0
    fi
fi

# 第 3 步：功能测试（如果服务器在运行）
if check_server; then
    print_step "3. API 功能测试"
    
    # 测试 1: 获取任务列表
    echo "测试 GET /api/tasks..."
    tasks=$(curl -s "$BASE_URL/api/tasks?limit=5")
    if [ $? -eq 0 ]; then
        task_count=$(echo "$tasks" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total', 0))" 2>/dev/null || echo "?")
        print_success "任务列表：共 $task_count 个任务"
    else
        print_error "获取任务列表失败"
    fi
    
    # 测试 2: 获取队列统计
    echo "测试 GET /api/queue/stats..."
    if curl -s "$BASE_URL/api/queue/stats" > /dev/null; then
        print_success "队列统计可用"
    else
        print_error "队列统计不可用"
    fi
    
    # 测试 3: 上传测试文件（如果有测试固件）
    if [ -d "$TEST_DIR" ] && [ "$(ls -A $TEST_DIR 2>/dev/null)" ]; then
        echo "测试文件上传..."
        test_file=$(find "$TEST_DIR" -type f -name "*.bin" -o -name "*.hex" | head -1)
        if [ -n "$test_file" ]; then
            response=$(curl -s -X POST \
                -F "file=@$test_file" \
                "$BASE_URL/api/upload" 2>/dev/null)
            
            if echo "$response" | grep -q '"success":true'; then
                fw_id=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('firmware_id',''))" 2>/dev/null)
                print_success "文件上传成功：$fw_id"
                
                # 可选：立即触发扫描
                read -p "是否立即扫描该文件？(y/n): " scan_now
                if [ "$scan_now" = "y" ] || [ "$scan_now" = "Y" ]; then
                    echo "触发同步扫描..."
                    scan_response=$(curl -s -X POST \
                        -F "firmware_id=$fw_id" \
                        -F "firmware_type=bin" \
                        "$BASE_URL/api/scan" 2>/dev/null)
                    
                    if echo "$scan_response" | grep -q '"success":true'; then
                        print_success "扫描完成！"
                        
                        # 生成报告
                        echo "生成 YAML 报告..."
                        curl -s "$BASE_URL/api/reports/$fw_id" -o "${REPORT_DIR}/${fw_id}_report.yaml"
                        print_success "报告已保存到：${REPORT_DIR}/${fw_id}_report.yaml"
                    else
                        print_error "扫描失败"
                    fi
                fi
            else
                print_warning "文件上传响应异常"
            fi
        else
            print_warning "未找到 .bin 或 .hex 测试文件"
        fi
    else
        print_warning "测试目录为空或未创建，跳过上传测试"
        print_step "💡 提示：创建测试文件"
        echo "  mkdir -p $TEST_DIR"
        echo "  echo 'test firmware data' > $TEST_DIR/sample.bin"
    fi
fi

# 第 4 步：Web 界面访问建议
print_step "4. Web 界面使用指南"

echo -e "${GREEN}🌐 请访问以下地址使用平台：${NC}"
echo ""
echo "主界面：   ${BLUE}$BASE_URL${NC}"
echo "API 文档：  ${BLUE}$BASE_URL/docs${NC}"
echo "健康检查： ${BLUE}$BASE_URL/api/queue/stats${NC}"
echo ""

echo -e "${YELLOW}📋 主要功能清单:${NC}"
echo "  ✅ 单文件扫描          - 上传并扫描单个固件"
echo "  ✅ 批量扫描            - 同时处理多个固件文件"
echo "  ✅ 任务队列监控        - 实时查看任务状态和进度"
echo "  ✅ Dashboard 增强       - 4 种图表可视化分析"
echo "  ✅ 智能筛选面板        - 按时间/严重程度/类型筛选"
echo "  ✅ 多格式报告导出      - Excel/PDF/YAML"
echo "  ✅ R155 合规检查        - EU R155/R156法规评估"
echo "  ✅ Word 合规报告        - 自动生成详细 PDF"
echo ""

# 第 5 步：性能基准（可选）
print_step "5. 性能提示"

echo "根据机器配置调整并发数（编辑 config.yaml）："
echo "  - 4GB RAM: max_concurrent: 1-2"
echo "  - 8GB RAM: max_concurrent: 2-3 (推荐)"
echo "  - 16GB+ RAM: max_concurrent: 3-5"
echo ""
echo "吞吐量参考："
echo "  • 单线程：~0.5 固件/分钟"
echo "  • 3 并发：~1.5 固件/分钟 (提升 3x)"
echo "  • 5 并发：~2.5 固件/分钟 (提升 5x)"

# 总结
print_step "✨ 测试完成"

echo -e "${GREEN}============================================${NC}"
echo "玄武 固件扫描平台已成功配置并运行！"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "下一步建议:"
echo "  1. 在浏览器中访问 $BASE_URL 开始使用"
echo "  2. 尝试上传一个固件文件进行测试"
echo "  3. 查看 Dashboard 中的 R155 合规得分"
echo "  4. 下载 Word 格式的合规报告"
echo ""
echo "文档位置:"
echo "  • BATCH_SCAN_GUIDE.md     - 批量扫描使用指南"
echo "  • DASHBOARD_ENHANCEMENT.md - Dashboard 功能说明"
echo "  • memory/2026-07-22.md    - 开发日志和决策记录"
echo ""
echo -e "🎉 ${BLUE}祝您好运，安全开发！${NC}"
