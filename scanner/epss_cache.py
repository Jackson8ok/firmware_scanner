#!/usr/bin/env python3
"""
EPSS 本地缓存管理器

功能:
1. 下载最新的 EPSS CSV 数据集
2. 构建本地 SQLite 缓存数据库
3. 提供快速查询接口
4. 定期自动更新（每周）

使用方法:
    from epss_cache import EPSSCacheManager
    
    # 初始化
    manager = EPSSCacheManager("./cache/epss.db")
    
    # 首次使用需要下载数据
    if not manager.is_data_available():
        manager.download_latest_epss()
    
    # 查询某个 CVE 的 EPSS 分数
    score = manager.get_epss_score("CVE-2024-1234")
    print(f"EPSS Score: {score}")
    
    # 批量查询
    scores = manager.batch_get_epss(["CVE-2024-1234", "CVE-2024-5678"])
"""

import os
import sqlite3
import requests
import csv
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EPSSCacheManager:
    """EPSS 缓存管理器"""
    
    def __init__(self, db_path: str = "./cache/epss_cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._connect()
        self._init_schema()
    
    def _connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"EPSS 缓存数据库已连接：{self.db_path}")
    
    def _init_schema(self):
        """初始化数据库 schema"""
        cursor = self.conn.cursor()
        
        # EPSS 分数表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS epss_scores (
                cve TEXT PRIMARY KEY,
                epss REAL NOT NULL,
                percentile REAL,
                date TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS epss_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # 索引优化
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_epss_date 
            ON epss_scores(date DESC)
        """)
        
        self.conn.commit()
        logger.info("EPSS 数据库 schema 初始化完成")
    
    def is_data_available(self) -> bool:
        """检查是否有可用的 EPSS 数据"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM epss_scores")
            count = cursor.fetchone()[0]
            
            # 检查是否是最新的数据（最近 7 天）
            cursor.execute("""
                SELECT MAX(date) FROM epss_scores
            """)
            max_date_str = cursor.fetchone()[0]
            
            if not max_date_str:
                return False
            
            max_date = datetime.strptime(max_date_str, "%Y-%m-%d")
            days_old = (datetime.now() - max_date).days
            
            has_recent_data = days_old <= 7
            has_sufficient_data = count > 10000  # 至少 1 万条记录
            
            logger.info(f"EPSS 数据：{count} 条记录，最后更新 {max_date.date()} ({days_old}天前)")
            
            return has_recent_data and has_sufficient_data
            
        except Exception as e:
            logger.error(f"检查 EPSS 数据失败：{e}")
            return False
    
    def download_latest_epss(self, force: bool = False) -> bool:
        """下载最新的 EPSS 数据集"""
        # FIRST.org EPSS 官方数据源（2025 年后 URL 已变更）
        urls = [
            "https://epss.first.org/epss_scores-current.csv.gz",
            "https://epss.cyentia.com/epss_scores-current.csv.gz",
        ]
        
        # 快速网络连通性检查（避免在无网络环境下长时间阻塞）
        try:
            import socket
            socket.gethostbyname("epss.first.org")
        except socket.gaierror:
            logger.warning("网络不可达（DNS 解析失败），跳过 EPSS 下载")
            return False
        except Exception:
            pass
        
        # 首选 JSON 格式
        for url in urls:
            try:
                logger.info(f"正在下载 EPSS 数据集：{url}")
                
                if 'json' in url:
                    response = requests.get(url, timeout=30)  # 减少超时时间
                    response.raise_for_status()
                    
                    import gzip
                    import io
                    
                    with gzip.open(io.BytesIO(response.content), 'rt', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    return self._import_json_data(data)
                
                elif 'csv' in url:
                    response = requests.get(url, timeout=30)  # 减少超时时间
                    response.raise_for_status()
                    
                    import gzip
                    import io
                    
                    with gzip.open(io.BytesIO(response.content), 'rt', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                    
                    return self._import_csv_data(rows)
                    
            except Exception as e:
                logger.warning(f"下载失败 ({url}): {e}")
                continue
        
        logger.error("所有数据源下载失败")
        return False
    
    def _import_json_data(self, data: dict) -> bool:
        """导入 JSON 格式的 EPSS 数据"""
        try:
            cursor = self.conn.cursor()
            
            total_count = 0
            inserted_count = 0
            
            for entry in data.get('scores', []):
                cve = entry.get('cve')
                epss = float(entry.get('epss', 0))
                percentile = float(entry.get('percentile', 0))
                date = entry.get('date', datetime.now().strftime("%Y-%m-%d"))
                
                if not cve:
                    continue
                
                total_count += 1
                
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO epss_scores (cve, epss, percentile, date)
                        VALUES (?, ?, ?, ?)
                    """, (cve, epss, percentile, date))
                    inserted_count += 1
                except Exception as e:
                    logger.debug(f"跳过无效记录 {cve}: {e}")
                    continue
            
            self.conn.commit()
            
            logger.info(f"✅ 成功导入 EPSS 数据: {inserted_count}/{total_count} 条记录")
            
            # 更新元数据
            cursor.execute("""
                INSERT OR REPLACE INTO epss_metadata (key, value)
                VALUES ('last_updated', ?)
            """, (datetime.now().isoformat(),))
            
            cursor.execute("""
                INSERT OR REPLACE INTO epss_metadata (key, value)
                VALUES ('total_records', ?)
            """, (str(inserted_count),))
            
            self.conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"导入 EPSS 数据失败：{e}")
            return False
    
    def _import_csv_data(self, rows: List[Dict]) -> bool:
        """导入 CSV 格式的 EPSS 数据"""
        try:
            cursor = self.conn.cursor()
            
            total_count = len(rows)
            inserted_count = 0
            
            for row in rows:
                cve = row.get('cve')
                epss = float(row.get('epss', 0))
                percentile = float(row.get('percentile', 0))
                date = row.get('date', datetime.now().strftime("%Y-%m-%d"))
                
                if not cve:
                    continue
                
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO epss_scores (cve, epss, percentile, date)
                        VALUES (?, ?, ?, ?)
                    """, (cve, epss, percentile, date))
                    inserted_count += 1
                except Exception as e:
                    logger.debug(f"跳过无效记录 {cve}: {e}")
                    continue
            
            self.conn.commit()
            
            logger.info(f"✅ 成功导入 EPSS 数据: {inserted_count}/{total_count} 条记录")
            
            # 更新元数据
            cursor.execute("""
                INSERT OR REPLACE INTO epss_metadata (key, value)
                VALUES ('last_updated', ?)
            """, (datetime.now().isoformat(),))
            
            cursor.execute("""
                INSERT OR REPLACE INTO epss_metadata (key, value)
                VALUES ('total_records', ?)
            """, (str(inserted_count),))
            
            self.conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"导入 EPSS 数据失败：{e}")
            return False
    
    def get_epss_score(self, cve_id: str) -> Optional[float]:
        """获取单个 CVE 的 EPSS 分数"""
        try:
            cursor = self.conn.cursor()
            
            # 查询最新的记录
            cursor.execute("""
                SELECT epss FROM epss_scores
                WHERE cve = ?
                ORDER BY date DESC
                LIMIT 1
            """, (cve_id,))
            
            result = cursor.fetchone()
            
            if result:
                return float(result['epss'])
            
            return None
            
        except Exception as e:
            logger.error(f"查询 EPSS 分数失败 ({cve_id}): {e}")
            return None
    
    def batch_get_epss_scores(self, cve_ids: List[str]) -> Dict[str, float]:
        """批量获取多个 CVE 的 EPSS 分数"""
        results = {}
        
        try:
            cursor = self.conn.cursor()
            
            placeholders = ','.join(['?' for _ in cve_ids])
            
            cursor.execute(f"""
                SELECT cve, epss, date FROM epss_scores
                WHERE cve IN ({placeholders})
                ORDER BY date DESC
            """, cve_ids)
            
            # 为每个 CVE 取最新的记录
            seen = set()
            for row in reversed(cursor.fetchall()):
                if row['cve'] not in seen:
                    results[row['cve']] = float(row['epss'])
                    seen.add(row['cve'])
            
            logger.debug(f"批量查询 EPSS: {len(results)}/{len(cve_ids)} 命中")
            
        except Exception as e:
            logger.error(f"批量查询 EPSS 失败：{e}")
        
        return results
    
    def get_top_vulnerabilities(self, limit: int = 100, min_score: float = 0.1) -> List[Tuple[str, float]]:
        """获取高风险漏洞列表（按 EPSS 排序）"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT cve, epss, date FROM epss_scores
                WHERE epss >= ?
                ORDER BY epss DESC
                LIMIT ?
            """, (min_score, limit))
            
            return [(row['cve'], float(row['epss'])) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"获取高 EPSS 漏洞列表失败：{e}")
            return []
    
    def clear_old_data(self, keep_days: int = 90):
        """清理旧数据，只保留指定天数内的记录"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
            
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM epss_scores
                WHERE date < ?
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            self.conn.commit()
            
            logger.info(f"清理了 {deleted_count} 条旧的 EPSS 记录")
            
        except Exception as e:
            logger.error(f"清理旧数据失败：{e}")
    
    def update_data_if_needed(self, auto_download: bool = True) -> bool:
        """如果数据过期则自动更新"""
        if not self.is_data_available():
            if auto_download:
                logger.info("EPSS 数据不可用或过期，开始下载...")
                return self.download_latest_epss()
            else:
                logger.warning("EPSS 数据不可用，请先调用 download_latest_epss()")
                return False
        
        # 检查是否需要更新（超过 7 天）
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT MAX(date) FROM epss_scores")
            max_date_str = cursor.fetchone()[0]
            
            if max_date_str:
                max_date = datetime.strptime(max_date_str, "%Y-%m-%d")
                days_old = (datetime.now() - max_date).days
                
                if days_old > 7:
                    logger.info(f"EPSS 数据已过 {days_old} 天，开始更新...")
                    return self.download_latest_epss()
                else:
                    logger.info(f"EPSS 数据是最新的 ({days_old} 天前)")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查更新失败：{e}")
            return False
    
    def get_statistics(self) -> dict:
        """获取 EPSS 数据统计信息"""
        try:
            cursor = self.conn.cursor()
            
            # 总记录数
            cursor.execute("SELECT COUNT(*) FROM epss_scores")
            total_records = cursor.fetchone()[0]
            
            # 平均 EPSS 分数
            cursor.execute("SELECT AVG(epss) FROM epss_scores")
            avg_epss = cursor.fetchone()[0] or 0
            
            # 最高 EPSS 分数
            cursor.execute("SELECT MAX(epss) FROM epss_scores")
            max_epss = cursor.fetchone()[0] or 0
            
            # 最低 EPSS 分数
            cursor.execute("SELECT MIN(epss) FROM epss_scores")
            min_epss = cursor.fetchone()[0] or 0
            
            # 最近更新日期
            cursor.execute("SELECT MAX(date) FROM epss_scores")
            last_update = cursor.fetchone()[0]
            
            return {
                'total_records': total_records,
                'avg_epss': round(avg_epss, 4),
                'max_epss': round(max_epss, 4),
                'min_epss': round(min_epss, 4),
                'last_update': last_update
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败：{e}")
            return {}
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("EPSS 缓存数据库连接已关闭")


# 快捷函数
def init_epss_cache(cache_dir: str = "./cache") -> EPSSCacheManager:
    """初始化 EPSS 缓存"""
    db_path = os.path.join(cache_dir, "epss_cache.db")
    manager = EPSSCacheManager(db_path)
    
    # 如果数据不可用，提示下载
    if not manager.is_data_available():
        logger.warning("EPSS 数据未初始化，请手动下载:")
        logger.warning("  from epss_cache import EPSSCacheManager")
        logger.warning("  manager = EPSSCacheManager()")
        logger.warning("  manager.download_latest_epss()")
    
    return manager


if __name__ == "__main__":
    # 测试运行
    print("=" * 60)
    print("EPSS 本地缓存管理器")
    print("=" * 60)
    
    manager = EPSSCacheManager()
    
    # 检查数据状态
    if not manager.is_data_available():
        print("\n⚠️  EPSS 数据不可用，开始下载最新数据...")
        success = manager.download_latest_epss()
        
        if success:
            print("✅ 数据下载成功！")
        else:
            print("❌ 数据下载失败，请检查网络连接")
            exit(1)
    
    # 显示统计信息
    stats = manager.get_statistics()
    print(f"\n📊 EPSS 数据统计:")
    print(f"   总记录数：{stats['total_records']:,}")
    print(f"   平均 EPSS: {stats['avg_epss']:.4f}")
    print(f"   最高 EPSS: {stats['max_epss']:.4f}")
    print(f"   最低 EPSS: {stats['min_epss']:.4f}")
    print(f"   最后更新：{stats['last_update']}")
    
    # 测试查询
    test_cves = ["CVE-2024-1234", "CVE-2023-44487", "CVE-2021-44228"]
    print(f"\n🔍 测试查询:")
    for cve in test_cves:
        score = manager.get_epss_score(cve)
        if score:
            print(f"   {cve}: EPSS = {score:.4f} ({score*100:.2f}%)")
        else:
            print(f"   {cve}: 未找到")
    
    # 获取 Top 10 高危漏洞
    print(f"\n🔥 Top 10 最高 EPSS 漏洞:")
    top_vulns = manager.get_top_vulnerabilities(limit=10, min_score=0.5)
    for i, (cve, epss) in enumerate(top_vulns, 1):
        print(f"   {i}. {cve}: EPSS = {epss:.4f} ({epss*100:.2f}%)")
    
    manager.close()
    print("\n✅ 操作完成")
