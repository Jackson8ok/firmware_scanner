#!/usr/bin/env python3
"""
演示固件生成器 - 创建各种类型的测试固件样本
用于功能验证和演示目的
"""

import os
from pathlib import Path
import struct
import zlib

def create_simulated_firmware(output_dir: str):
    """创建模拟的真实固件文件"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print(" 🔧 生成演示固件样本")
    print("=" * 60)
    
    # 1. MCU HEX 固件（FreeRTOS + lwIP）
    print("\n[1/4] 生成 MCU HEX 固件 (FreeRTOS + lwIP)...")
    hex_content = generate_mcu_hex()
    hex_file = output_path / "mcu_firmware.hex"
    hex_file.write_text(hex_content)
    print(f"   ✅ {hex_file.name} ({len(hex_content)} chars)")
    
    # 2. 模拟 ELF 二进制（包含库特征）
    print("\n[2/4] 生成模拟 ELF 二进制...")
    elf_content = generate_elf_with_libraries()
    elf_file = output_path / "embedded_app.bin"
    elf_file.write_bytes(elf_content)
    print(f"   ✅ {elf_file.name} ({len(elf_content)} bytes)")
    
    # 3. 简单 SREC 格式
    print("\n[3/4] 生成 SREC 固件...")
    srec_content = generate_srec_firmware()
    srec_file = output_path / "plc_firmware.s19"
    srec_file.write_text(srec_content)
    print(f"   ✅ {srec_file.name} ({len(srec_content)} chars)")
    
    # 4. 压缩的 tar.gz 模拟
    print("\n[4/4] 生成压缩固件镜像...")
    compressed = create_compressed_firmware()
    gz_file = output_path / "linux_firmware.img.gz"
    gz_file.write_bytes(compressed)
    print(f"   ✅ {gz_file.name} ({len(compressed)} bytes)")
    
    print("\n" + "=" * 60)
    print(" 📦 固件样本生成完成!")
    print("   目录:", output_path)
    print("   总数: 4 个")
    print("=" * 60)
    
    return list(output_path.glob("*"))


def generate_mcu_hex():
    """生成模拟的 Intel HEX 格式 MCU 固件"""
    lines = []
    
    # 扩展线性地址记录
    lines.append(":020000040800F2")
    
    # FreeRTOS 相关代码段
    freertos_data = b"xTaskCreate\x00pvPortMalloc\x00vListInitialise\x00"
    lines.append(create_hex_record(0x0000, freertos_data))
    
    # lwIP 相关代码段
    lwip_data = b"tcp_connect\x00udp_sendto\x00netif_add\x00pbuf_alloc\x00"
    lines.append(create_hex_record(0x0040, lwip_data))
    
    # wolfSSL 相关代码段
    wolfssl_data = b"wolfSSL_Init\x00SSL_connect\x00X509_verify_cert\x00"
    lines.append(create_hex_record(0x0080, wolfssl_data))
    
    # 填充一些随机数据
    padding = bytes([i % 256 for i in range(32)])
    lines.append(create_hex_record(0x00C0, padding))
    
    # 结束记录
    lines.append(":00000001FF")
    
    return '\n'.join(lines) + '\n'


def create_hex_record(addr: int, data: bytes) -> str:
    """创建单个 HEX 记录"""
    record_type = 0  # 数据记录
    
    # 计算校验和
    byte_count = len(data)
    checksum = byte_count + ((addr >> 8) & 0xFF) + (addr & 0xFF) + record_type
    
    for byte in data:
        checksum += byte
    
    checksum = (-checksum) & 0xFF
    
    hex_str = f":{byte_count:02X}{addr:04X}{record_type:02X}"
    hex_str += data.hex().upper()
    hex_str += f"{checksum:02X}"
    
    return hex_str


def generate_elf_with_libraries():
    """生成模拟的 ELF 二进制（带库特征字符串）"""
    # ELF 头（简化的，非真实可执行）
    elf_header = b'\x7fELF'  # Magic number
    elf_header += b'\x02\x01\x01\x00'  # 64-bit, little endian
    elf_header += b'\x00' * 40  # 剩余头信息
    
    # 添加各种库的特征字符串
    libraries = [
        b"\x00FreeRTOS V10.4.3\x00Copyright (C) 2020 Amazon.com Inc\x00",
        b"\x00lwIP 2.1.2\x00Copyright (c) 2001-2018 Swedish Institute of Computer Science\x00",
        b"\x00wolfSSL 4.6.0\x00TLS/SSL Library\x00",
        b"\x00zlib 1.2.11\x00Copyright (C) 1995-2017 Jean-loup Gailly\x00",
        b"\x00mbedtls 2.28.0\x00Mbed TLS is a C library that implements cryptographic primitives\x00",
    ]
    
    content = elf_header
    content += b"\x00" * 1024  # 填充
    
    for lib in libraries:
        content += lib
        content += b"\x00" * (256 - len(lib) % 256)  # 对齐
    
    # 添加更多模拟代码段
    content += bytes(range(256)) * 10
    
    return content


def generate_srec_firmware():
    """生成模拟的 Motorola SREC 格式固件"""
    lines = []
    
    # S0 记录（标题）
    lines.append("S00B00004D6F746F726F6C6120533139FF")
    
    # S3 记录（32 位地址数据）
    s3_addr = 0x08000000
    
    # FreeRTOS 区域
    freertos_data = b"xTaskCreate\x00vQueueCreate\x00xSemaphoreCreateMutex\x00"
    lines.append(create_s3_record(s3_addr, freertos_data))
    s3_addr += len(freertos_data)
    
    # lwIP 区域
    lwip_data = b"tcp_new\x00tcp_bind\x00tcp_listen\x00udp_new\x00"
    lines.append(create_s3_record(s3_addr, lwip_data))
    s3_addr += len(lwip_data)
    
    # 结束记录（S7）
    lines.append("S70500000000FA")
    
    return '\n'.join(lines) + '\n'


def create_s3_record(addr: int, data: bytes) -> str:
    """创建 S3 记录"""
    byte_count = len(data) + 5  # 字节数 + 地址 + 计数 + 校验和
    checksum = byte_count + ((addr >> 24) & 0xFF) + ((addr >> 16) & 0xFF) + \
               ((addr >> 8) & 0xFF) + (addr & 0xFF)
    
    for byte in data:
        checksum += byte
    
    checksum = (~checksum) & 0xFF
    
    s3_str = f"S3{byte_count:02X}{addr:08X}"
    s3_str += data.hex().upper()
    s3_str += f"{checksum:02X}"
    
    return s3_str


def create_compressed_firmware():
    """创建压缩的固件镜像（gzip）"""
    # 模拟的文件系统内容
    filesystem = b""
    
    # 模拟目录结构
    files = {
        "/etc/config.txt": b"debug_mode=true\nwifi_ssid=MyRouter\nwifi_key=secret123\n",
        "/usr/bin/httpd": b"#!/bin/sh\necho 'Welcome to MyRouter WebUI'\n",
        "/lib/libssl.so.1.1": b"fake_ssl_library_placeholder_" * 100,
        "/lib/libcrypto.so.1.1": b"fake_crypto_library_placeholder_" * 100,
        "/tmp/dhcp_leases": b"192.168.1.10 MAC:AA:BB:CC:DD:EE:FF lease_time=86400\n",
    }
    
    for path, content in files.items():
        filesystem += f"[FILE:{path}]".encode()
        filesystem += content
        filesystem += b"\n---END---\n"
    
    # 添加一些组件特征
    filesystem += b"\nFreeRTOS V10.3.0\n"
    filesystem += b"lwIP 2.0.3\n"
    filesystem += b"BusyBox v1.33.1\n"
    
    # gzip 压缩
    compressed = zlib.compress(filesystem, level=9)
    
    # 添加 gzip 头尾
    gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
    gzip_footer = struct.pack('<II', len(filesystem), zlib.crc32(filesystem) & 0xffffffff)
    
    return gzip_header + compressed[2:-4] + gzip_footer


def create_sample_for_quick_test():
    """创建最简单的快速测试样本"""
    import tempfile
    
    tmp_dir = Path(tempfile.mkdtemp(prefix="quick_test_"))
    
    # 创建一个简单的二进制文件
    simple_fw = tmp_dir / "simple.bin"
    simple_fw.write_bytes(b"FreeRTOS V10.4.3\x00lwIP 2.1.2\x00test firmware")
    
    print(f"\n✅ 快速测试样本：{simple_fw}")
    print(f"   大小：{simple_fw.stat().st_size} bytes")
    
    return simple_fw


if __name__ == "__main__":
    import sys
    
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "./demo_firmwares"
    
    files = create_simulated_firmware(output_dir)
    
    print("\n💡 提示:")
    print("   可以使用这些文件测试扫描功能:")
    for f in files:
        print(f"   • {f.name}")
    
    print("\n   在 Web UI 中上传或使用 API:")
    print(f"   curl -X POST http://localhost:8765/api/upload -F 'file=@{files[0]}'")
