#!/bin/bash
# EPSS 数据更新脚本

echo "========================================="
echo "  📊 EPSS 漏洞利用概率数据管理器"
echo "========================================="

cd "$(dirname "$0")/.."

python3 << 'EOF'
import sys
from scanner.epss_cache import EPSSCacheManager

def main():
    manager = EPSSCacheManager('./cache/epss/epss_cache.db')
    
    print("\n📈 当前状态:")
    if manager.is_data_available():
        stats = manager.get_statistics()
        print(f"   ✅ 可用 ({stats['total_records']:,} 条记录)")
        print(f"   📅 最后更新：{stats['last_update']}")
        print(f"   📊 平均 EPSS: {stats['avg_epss']:.4f}")
        print(f"   🔥 最高 EPSS: {stats['max_epss']:.4f}")
    else:
        print("   ❌ 未初始化")
    
    print("\n⚙️  操作选项:")
    print("1) 下载最新数据")
    print("2) 检查并更新（超过 7 天）")
    print("3) 查看 Top 10 高风险 CVE")
    print("4) 查询特定 CVE")
    print("5) 清理旧数据（保留 90 天）")
    print("0) 退出")
    
    while True:
        try:
            choice = input("\n请选择 [0-5]: ").strip()
            
            if choice == '1':
                print("\n正在下载最新 EPSS 数据...")
                if manager.download_latest_epss():
                    print("✅ 下载成功！")
                    stats = manager.get_statistics()
                    print(f"   总记录：{stats['total_records']:,}")
                    print(f"   最后更新：{stats['last_update']}")
                else:
                    print("❌ 下载失败，请检查网络连接")
            
            elif choice == '2':
                print("\n检查是否需要更新...")
                if manager.update_data_if_needed(auto_download=True):
                    print("✅ 数据已更新或已是最新")
                else:
                    print("⚠️  无法更新，请手动下载")
            
            elif choice == '3':
                print("\n🔥 Top 10 最高 EPSS 风险:")
                top_vulns = manager.get_top_vulnerabilities(limit=10, min_score=0.5)
                
                if not top_vulns:
                    print("   未找到高分漏洞，请先下载数据")
                else:
                    for i, (cve, epss) in enumerate(top_vulns, 1):
                        risk_level = "🔴 极高" if epss > 0.8 else ("🟠 高" if epss > 0.6 else "🟡 中高")
                        print(f"   {i}. {cve}: {epss:.4f} ({epss*100:.2f}%) - {risk_level}")
            
            elif choice == '4':
                cve = input("请输入 CVE ID (如 CVE-2024-1234): ").strip().upper()
                if not cve.startswith("CVE-"):
                    cve = f"CVE-{cve}"
                
                score = manager.get_epss_score(cve)
                
                if score:
                    risk = "🔴 极高" if score > 0.8 else ("🟠 高" if score > 0.6 else ("🟡 中" if score > 0.3 else "🟢 低"))
                    print(f"\n   {cve}: EPSS = {score:.4f} ({score*100:.2f}%)\n   风险等级：{risk}")
                else:
                    print(f"\n   ❌ 未找到 {cve} 的 EPSS 数据")
            
            elif choice == '5':
                confirm = input("确定要清理 90 天前的数据吗？(y/n): ")
                if confirm.lower() == 'y':
                    manager.clear_old_data(keep_days=90)
                    print("✅ 清理完成")
                else:
                    print("已取消")
            
            elif choice == '0':
                print("\n再见！")
                break
            
            else:
                print("无效选择，请重新输入")
        
        except KeyboardInterrupt:
            print("\n\n已取消")
            break
        except Exception as e:
            print(f"❌ 错误：{e}")
    
    manager.close()

if __name__ == "__main__":
    main()
EOF
