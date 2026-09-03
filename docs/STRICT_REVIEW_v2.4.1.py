import ast, os, re
from collections import defaultdict

REPORT = []
BASE = "."

def add(section, item, severity="MEDIUM"):
    REPORT.append((section, item, severity))

def scan_security():
    add("SECURITY", "开始安全扫描...", "INFO")
    for root, dirs, files in os.walk(BASE):
        if any(s in root for s in ['venv','__pycache__','.git','.ipynb']):
            continue
        for f in files:
            if f.endswith(('.py','.js','.yaml','.yml','.json')):
                path = os.path.join(root, f)
                try:
                    content = open(path, encoding='utf-8', errors='ignore').read()
                except Exception:
                    continue
                if re.search(r'(?i)(password|secret|token|api_key|private_key)\s*[:=]\s*["\'][^"\']+["\']', content):
                    add("SECURITY", f"发现硬编码凭证: {path}", "HIGH")
                if 'f"' in content and 'execute(' in content and 'SELECT' in content:
                    add("SECURITY", f"疑似 SQL 注入: {path}", "HIGH")
                if 'cors_allowed_origins="*"' in content:
                    add("SECURITY", f"CORS 全放开: {path}", "MEDIUM")

def scan_api_contract():
    add("API", "开始 API 契约扫描...", "INFO")
    frontend_calls = set()
    for f in ['frontend/static/app.js','frontend/static/r155-ui.js','frontend/static/dashboard-enhanced.js']:
        if os.path.exists(f):
            content = open(f).read()
            for m in re.finditer(r'fetch\(["\']([^"\']+)["\']\)', content):
                frontend_calls.add(m.group(1).split('?')[0])
    
    backend_routes = set()
    for root, dirs, files in os.walk(BASE):
        if any(s in root for s in ['venv','__pycache__','.git','.ipynb']):
            continue
        for f in files:
            if f.endswith('.py') and root.startswith('./api'):
                path = os.path.join(root, f)
                try:
                    tree = ast.parse(open(path).read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if getattr(node.func, 'attr', None) in ('get','post','put','delete'):
                                if node.args and isinstance(node.args[0], ast.Constant):
                                    backend_routes.add(node.args[0].value.split('?')[0])
                except Exception:
                    pass
    
    missing = frontend_calls - backend_routes
    for m in missing:
        add("API", f"前端调用无对应后端: {m}", "HIGH")

def scan_code_quality():
    add("QUALITY", "开始代码质量扫描...", "INFO")
    func_locations = defaultdict(list)
    for root, dirs, files in os.walk(BASE):
        if any(s in root for s in ['venv','__pycache__','.git','.ipynb']):
            continue
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                try:
                    tree = ast.parse(open(path).read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            func_locations[node.name].append(path)
                except Exception:
                    pass
    for name, paths in func_locations.items():
        if len(paths) > 1 and not name.startswith('_') and name not in ('__init__', 'main', 'test', 'to_dict', 'close'):
            add("QUALITY", f"函数重复定义: {name} 在 {set(paths)}", "MEDIUM")

def scan_docs():
    add("DOCS", "开始文档扫描...", "INFO")
    required = ['README.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md','DEPLOYMENT.md','TESTING_GUIDE.md']
    for r in required:
        if not os.path.exists(r):
            add("DOCS", f"缺少必需文档: {r}", "MEDIUM")

def scan_perf():
    add("PERF", "开始性能扫描...", "INFO")
    for root, dirs, files in os.walk(BASE):
        if any(s in root for s in ['venv','__pycache__','.git','.ipynb']):
            continue
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                try:
                    content = open(path).read()
                    lines = content.splitlines()
                    for i, line in enumerate(lines, 1):
                        if 'time.sleep(' in line and 'test' not in path.lower():
                            add("PERF", f"{path}:{i} 发现 time.sleep，可能阻塞", "MEDIUM")
                except Exception:
                    pass

scan_security()
scan_api_contract()
scan_code_quality()
scan_docs()
scan_perf()

print("=" * 60)
print("🔍 玄武 v2.4.1-hotfix 严格自评审结果")
print("=" * 60)
sections = defaultdict(list)
for sec, item, sev in REPORT:
    sections[sec].append((item, sev))

for sec in ["SECURITY","API","QUALITY","DOCS","PERF"]:
    items = sections.get(sec, [])
    print(f"\n【{sec}】({len(items)} 条)")
    for item, sev in items:
        if sev == "HIGH":
            print(f"  ❌ {item}")
        elif sev == "MEDIUM":
            print(f"  ⚠️  {item}")
        else:
            print(f"  ℹ️  {item}")

high = sum(1 for _,_,s in REPORT if s=="HIGH")
med = sum(1 for _,_,s in REPORT if s=="MEDIUM")
print(f"\n总计: {high} 个 HIGH, {med} 个 MEDIUM")
print("=" * 60)
