# 🦞 固件漏洞扫描平台 - 快速参考

## 命令速查

### 启动服务
```bash
./scripts/startup.sh
```

### 检查状态
```bash
./scripts/status.sh
```

### 下载 Grype 数据库
```bash
./scripts/download_grype_db.sh /path/to/store
```

### 手动停止
```bash
pkill -f "uvicorn.*8765"     # 停止 FastAPI
pkill -f "node.*report"      # 停止 Node.js 报告服务
```

## API 端点

| 方法 | 端点 | 说明 |
|-----|------|------|
| GET | `/` | 主页面 |
| POST | `/api/upload` | 上传固件 |
| POST | `/api/scan` | 执行扫描 |
| GET | `/api/results/{id}` | 获取结果 |
| GET | `/api/scans` | 列出扫描历史 |
| POST | `/api/report/excel` | 导出 Excel |
| POST | `/api/report/word` | 导出 Word |
| POST | `/api/report/ppt` | 导出 PPT |

## 配置参数

### config.yaml 关键参数

```yaml
server:
  host: "127.0.0.1"    # 监听地址
  port: 8765           # 监听端口

paths:
  grype_db: "/path/grype.db"  # ⚠️ 必须设置

scoring:
  cvss_weight: 0.35
  epss_weight: 0.45
  component_weight: 0.20

compliance:
  cvss_threshold: 7.0
  days_threshold: 180
```

## 支持的固件格式

| 类型 | 扩展名 | 处理方法 |
|-----|-------|---------|
| SquashFS | .squashfs, .img | 7-Zip 解包 + Syft SBOM |
| HEX | .hex | objcopy/Python 转换 + 字符串提取 |
| SREC | .srec, .s19 | objcopy/Python 转换 + 字符串提取 |
| Binary | .bin | 直接字符串提取 |

## 已识别组件

| 组件 | 特征字符串 | 类型 |
|-----|-----------|-----|
| FreeRTOS | xTaskCreate, pvPortMalloc | RTOS |
| lwIP | tcp_connect, udp_sendto | Network |
| wolfSSL | wolfSSL_, WOLFSSL_ | Crypto |
| mbedTLS | mbedtls_, MBEDTLS_ | Crypto |
| BusyBox | BusyBox | Utilities |

## 优先级计算

```
priority_score = 0.35 × (CVSS/10) + 0.45 × EPSS + 0.20 × Component_Factor
```

**Component_Factor:**
- openssl, libssl, linux-kernel, freertos = 1.0
- 其他组件 = 0.5

## R155 合规规则

```python
如果 (CVSS >= 7.0) AND (未修复天数 > 180) AND (无修复版本):
    标记为 ❌ 不合规
否则:
    标记为 ✅ 合规
```

## 故障排查清单

### 问题：服务无法启动
```bash
# 检查端口占用
netstat -tlnp | grep 8765

# 查看日志
tail -f logs/server.log
```

### 问题：Syft 扫描失败
```bash
# 安装 Syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# 或接受降级到字符串提取模式
```

### 问题：数据库查询为空
```bash
# 验证数据库路径
grep grype_db config.yaml

# 测试数据库连接
sqlite3 /path/to/grype.db ".tables"
```

### 问题：Node.js 报告生成失败
```bash
cd services/node-report
npm install
node report-service.js
```

## 性能优化

### 提高扫描速度
1. 启用 Syft (比字符串提取更快更准确)
2. 本地缓存 EPSS 数据
3. 并行处理多个固件

### 减少误报
1. 添加供应商白名单
2. 过滤 OpenSSL 兼容层
3. 版本模糊匹配增强

## 数据安全

- ✅ 所有数据本地存储
- ✅ 无需网络连接
- ✅ 数据库离线可用
- ✅ 自动清理临时文件

## 后续扩展

### 添加新组件识别
编辑 `scanner/engine.py`:
```python
patterns['NewLib'] = (
    re.compile(r'newlib_func1|newlib_func2'),
    'library_type'
)
```

### 自定义报告模板
编辑 `services/node-report/report-service.js`

### 集成 CI/CD
```bash
# GitHub Actions 示例
- name: Scan Firmware
  run: |
    ./scripts/startup.sh
    curl -X POST http://localhost:8765/api/scan \
      -F "firmware_id=${{ github.sha }}" \
      -F "firmware_type=squashfs"
```

---

**提示**: 遇到问题时，先运行 `./scripts/status.sh` 检查系统状态
