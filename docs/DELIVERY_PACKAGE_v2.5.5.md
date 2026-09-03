# v2.5.5 交付包生成指南

**日期**: 2026-08-25  
**版本**: v2.5.5  
**状态**: ⏳ 待生成

---

## 📦 交付包内容

```
firmware_scanner-2.5.5.zip (~34MB)
├── api/                    # FastAPI 后端
├── scanner/                # 扫描引擎
├── frontend/               # Web UI
├── scripts/                # 部署脚本
├── docs/                   # 文档
├── config.yaml             # 配置文件
├── requirements.txt        # Python 依赖
└── README.md               # 项目说明
```

---

## 🚀 生成步骤

### 方式一：手动打包（推荐）

```bash
cd /mnt/workspace/firmware_scanner

# 1. 清理缓存
rm -rf api/cache/* cache/* uploads/* __pycache__ */__pycache__ .git logs/*.log *.log

# 2. 创建交付目录
mkdir -p /mnt/workspace/delivery

# 3. 打包（排除不必要文件）
zip -r /mnt/workspace/delivery/firmware_scanner-2.5.5.zip \
  . \
  -x ".git/*" \
  -x "node_modules/*" \
  -x "*.log" \
  -x "logs/*" \
  -x "cache/*" \
  -x "__pycache__/*" \
  -x "uploads/*" \
  -x ".ipynb_checkpoints/*"

# 4. 验证
ls -lh /mnt/workspace/delivery/firmware_scanner-2.5.5.zip
```

### 方式二：使用打包脚本

```bash
cd /mnt/workspace/firmware_scanner
./scripts/package_release_v2.5.5.sh
```

---

## 📤 上传到 GitHub Release

### 方式一：网页上传

1. 访问：https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/tag/v2.5.5
2. 点击 "Attach binaries by dropping them here or selecting them"
3. 选择 `/mnt/workspace/delivery/firmware_scanner-2.5.5.zip`
4. 等待上传完成
5. 点击 "Update" 保存

### 方式二：GitHub CLI

```bash
cd /mnt/workspace/delivery
gh release upload v2.5.5 firmware_scanner-2.5.5.zip --repo Jackson8ok/afvs-auto-firmware-vulnerability-scanner --clobber
```

### 方式三：GitHub API

```bash
GITHUB_TOKEN=$(cat /mnt/workspace/.github_token)
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary @/mnt/workspace/delivery/firmware_scanner-2.5.5.zip \
  "https://uploads.github.com/repos/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/376201279/assets?name=firmware_scanner-2.5.5.zip"
```

---

## ✅ 验证清单

- [ ] 交付包大小：~34MB
- [ ] 包含 config.yaml
- [ ] 包含 frontend/ 目录
- [ ] 包含 api/ 目录
- [ ] 包含 scanner/ 目录
- [ ] 包含 scripts/ 目录
- [ ] 不包含 .git/ 目录
- [ ] 不包含 node_modules/
- [ ] 不包含 *.log 文件
- [ ] 已上传到 GitHub Release v2.5.5

---

**执行人**: 攻城狮阿信 [Jackson]  
**联系**: zhu80k@163.com
