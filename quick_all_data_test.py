#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速完整数据测试
简单快速地读取所有数据类型
"""

import snap7
import struct

def quick_all_data_test():
    """快速测试所有数据类型"""
    print("=" * 80)
    print("DB9000 完整数据快速测试")
    print("=" * 80)
    
    # 创建客户端
    client = snap7.client.Client()
    
    try:
        # 连接到PLC
        print(f"正在连接到PLC: 172.16.10.66")
        client.connect("172.16.10.66", 0, 1)
        
        if client.get_connected():
            print("✓ 连接成功！")
            
            # 读取所有需要的数据（总共38字节）
            print("\n正在读取所有数据...")
            data = client.db_read(9000, 0, 38)
            
            if data:
                print(f"✓ 成功读取数据: {data.hex()}")
                print("\n数据解析结果:")
                print("-" * 60)
                
                # 1. 解析32个布尔值（前4个字节）
                print("1. 布尔值 (B1-B32):")
                for byte_index in range(4):
                    byte_value = data[byte_index]
                    print(f"   字节 {byte_index} (0x{byte_value:02X}):")
                    for bit_index in range(8):
                        bool_index = byte_index * 8 + bit_index + 1
                        bool_value = bool(byte_value & (1 << bit_index))
                        status = "✓" if bool_value else "✗"
                        print(f"     B{bool_index:2d}: {status}")
                    if byte_index < 3:
                        print()
                
                # 2. 解析字符串（从地址4开始，最大20字符+2字节长度）
                print("\n2. 字符串 (地址4.0):")
                if len(data) >= 6:  # 至少需要6字节（2字节长度+最多4字节字符串）
                    max_length = data[4]
                    actual_length = data[5]
                    if actual_length > 0 and len(data) >= 6 + actual_length:
                        string_data = data[6:6+actual_length]
                        try:
                            string_value = string_data.decode('utf-8', errors='ignore')
                            print(f"   字符串: '{string_value}' (长度: {actual_length})")
                        except:
                            print(f"   字符串: 解码失败 (原始数据: {string_data.hex()})")
                    else:
                        print("   字符串: 空字符串")
                else:
                    print("   字符串: 数据不足")
                
                # 3. 解析32位整数1（地址26）
                print("\n3. 32位整数1 (地址26.0):")
                if len(data) >= 30:  # 需要4字节
                    dint1_bytes = data[26:30]
                    try:
                        dint1_value = struct.unpack('>i', dint1_bytes)[0]
                        print(f"   DInt1: {dint1_value}")
                    except:
                        print(f"   DInt1: 解析失败 (原始数据: {dint1_bytes.hex()})")
                else:
                    print("   DInt1: 数据不足")
                
                # 4. 解析32位整数2（地址30）
                print("\n4. 32位整数2 (地址30.0):")
                if len(data) >= 34:  # 需要4字节
                    dint2_bytes = data[30:34]
                    try:
                        dint2_value = struct.unpack('>i', dint2_bytes)[0]
                        print(f"   DInt2: {dint2_value}")
                    except:
                        print(f"   DInt2: 解析失败 (原始数据: {dint2_bytes.hex()})")
                else:
                    print("   DInt2: 数据不足")
                
                # 5. 解析16位整数1（地址34）
                print("\n5. 16位整数1 (地址34.0):")
                if len(data) >= 36:  # 需要2字节
                    int1_bytes = data[34:36]
                    try:
                        int1_value = struct.unpack('>h', int1_bytes)[0]
                        print(f"   Int1: {int1_value}")
                    except:
                        print(f"   Int1: 解析失败 (原始数据: {int1_bytes.hex()})")
                else:
                    print("   Int1: 数据不足")
                
                # 6. 解析16位整数2（地址36）
                print("\n6. 16位整数2 (地址36.0):")
                if len(data) >= 38:  # 需要2字节
                    int2_bytes = data[36:38]
                    try:
                        int2_value = struct.unpack('>h', int2_bytes)[0]
                        print(f"   Int2: {int2_value}")
                    except:
                        print(f"   Int2: 解析失败 (原始数据: {int2_bytes.hex()})")
                else:
                    print("   Int2: 数据不足")
                
                print("-" * 60)
                print("测试完成！")
                
            else:
                print("✗ 无法读取数据")
                
        else:
            print("✗ 连接失败")
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        
    finally:
        # 断开连接
        if client.get_connected():
            client.disconnect()
            print("已断开连接")

if __name__ == "__main__":
    quick_all_data_test() 