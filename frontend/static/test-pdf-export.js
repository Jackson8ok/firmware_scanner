/**
 * PDF 导出功能测试脚本
 * 
 * 使用方法:
 * 1. 打开浏览器开发者工具 (F12)
 * 2. 切换到 Console 标签
 * 3. 粘贴以下代码并运行
 * 4. 检查生成的 PDF
 */

// 测试函数 1: 检查 jsPDF 和 html2canvas 是否加载
function testLibrariesLoaded() {
    console.log('🔍 测试 1: 检查 PDF 库是否加载...');
    
    if (window.jspdf && window.jspdf.jsPDF) {
        console.log('✅ jsPDF 已加载');
    } else {
        console.error('❌ jsPDF 未加载，请检查 CDN 链接');
        return false;
    }
    
    if (window.html2canvas) {
        console.log('✅ html2canvas 已加载');
    } else {
        console.error('❌ html2canvas 未加载，请检查 CDN 链接');
        return false;
    }
    
    console.log('✅ 所有库加载成功!');
    return true;
}

// 测试函数 2: 检查按钮是否存在
function testButtonExists() {
    console.log('\n🔍 测试 2: 检查 PDF 导出按钮...');
    
    const btn = document.getElementById('exportPdfBtn');
    
    if (btn) {
        console.log('✅ PDF 导出按钮存在');
        console.log(`   按钮文本: ${btn.textContent}`);
        console.log(`   按钮类名: ${btn.className}`);
        return true;
    } else {
        console.error('❌ PDF 导出按钮不存在');
        return false;
    }
}

// 测试函数 3: 模拟生成 PDF（需要已经有扫描数据）
async function testGeneratePDF() {
    console.log('\n🔍 测试 3: 测试 PDF 生成功能...');
    
    // 检查是否有当前扫描 ID
    if (typeof currentScanId === 'undefined' || !currentScanId) {
        console.warn('⚠️ 没有当前扫描 ID，请先进行固件扫描');
        console.log('提示：你可以手动设置 currentScanId 进行测试');
        console.log('示例：currentScanId = "test_scan_001"');
        return false;
    }
    
    console.log(`✓ 使用扫描 ID: ${currentScanId}`);
    
    try {
        // 检查 generateClientSidePDF 函数是否存在
        if (typeof generateClientSidePDF !== 'function') {
            console.error('❌ generateClientSidePDF 函数不存在');
            return false;
        }
        
        console.log('✅ PDF 生成函数存在，开始测试...');
        console.log('📄 正在生成 PDF...');
        
        // 调用客户端 PDF 生成函数
        await generateClientSidePDF(currentScanId);
        
        console.log('✅ PDF 生成成功！请检查下载的文件');
        return true;
        
    } catch (error) {
        console.error('❌ PDF 生成失败:', error.message);
        return false;
    }
}

// 测试函数 4: 完整测试流程
async function runAllTests() {
    console.log('═══════════════════════════════════');
    console.log('🧪 开始 PDF 导出功能测试');
    console.log('═══════════════════════════════════\n');
    
    let passed = 0;
    let total = 4;
    
    // 测试 1: 库加载
    if (testLibrariesLoaded()) {
        passed++;
    }
    
    // 测试 2: 按钮存在
    if (testButtonExists()) {
        passed++;
    }
    
    // 测试 3: 函数存在性
    console.log('\n🔍 测试 3: 检查 PDF 生成函数...');
    if (typeof generateClientSidePDF === 'function') {
        console.log('✅ generateClientSidePDF 函数存在');
        passed++;
    } else {
        console.error('❌ generateClientSidePDF 函数不存在');
    }
    
    // 测试 4: 实际生成（如果 possible）
    if (testLibrariesLoaded() && testButtonExists()) {
        const result = await testGeneratePDF();
        if (result) {
            passed++;
        }
    } else {
        console.log('\n⏭️ 跳过实际生成测试（前置条件不满足）');
    }
    
    // 总结
    console.log('\n═══════════════════════════════════');
    console.log(`📊 测试结果: ${passed}/${total} 通过`);
    
    if (passed === total) {
        console.log('✅ 所有测试通过！PDF 导出功能正常工作！');
    } else {
        console.log(`⚠️ 有 ${total - passed} 个测试失败，请检查错误信息`);
    }
    console.log('═══════════════════════════════════');
}

// 添加快捷命令到控制台
window.testPDFExport = runAllTests;

console.log('💡 提示：输入 testPDFExport() 来运行完整测试');
console.log('或者逐个运行：');
console.log('  - testLibrariesLoaded()');
console.log('  - testButtonExists()');
console.log('  - testGeneratePDF()');
