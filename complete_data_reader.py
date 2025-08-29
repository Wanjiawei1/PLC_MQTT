#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB9000完整数据读取脚本
读取所有类型的数据：布尔值、字符串、整数等
"""

import snap7
import struct
import time
from datetime import datetime
import logging
import csv
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('complete_data_reader.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompleteDataReader:
    """完整数据读取器"""
    
    def __init__(self, ip_address="172.16.10.66", rack=0, slot=1):
        self.ip_address = ip_address
        self.rack = rack
        self.slot = slot
        self.client = snap7.client.Client()
        self.connected = False
        
    def connect(self):
        """连接到PLC"""
        try:
            logger.info(f"正在连接到PLC: {self.ip_address}")
            self.client.connect(self.ip_address, self.rack, self.slot)
            
            if self.client.get_connected():
                self.connected = True
                logger.info("成功连接到PLC")
                return True
            else:
                logger.error("连接PLC失败")
                return False
                
        except Exception as e:
            logger.error(f"连接PLC时发生错误: {e}")
            return False
    
    def disconnect(self):
        """断开PLC连接"""
        if self.connected:
            self.client.disconnect()
            self.connected = False
            logger.info("已断开PLC连接")
    
    def read_bool_at_address(self, db_number=9000, byte_address=0, bit_position=0):
        """读取指定地址的布尔值"""
        if not self.connected:
            return None
            
        try:
            data = self.client.db_read(db_number, byte_address, 1)
            if data:
                byte_value = data[0]
                return bool(byte_value & (1 << bit_position))
            return None
        except Exception as e:
            logger.error(f"读取布尔值错误 (DB{db_number}.DBX{byte_address}.{bit_position}): {e}")
            return None
    
    def read_string(self, db_number=9000, start_address=4, max_length=20):
        """读取字符串"""
        if not self.connected:
            return None
            
        try:
            # 西门子字符串格式：第一个字节是最大长度，第二个字节是实际长度
            data = self.client.db_read(db_number, start_address, max_length + 2)
            if data and len(data) >= 2:
                actual_length = data[1]
                if actual_length > 0 and len(data) >= 2 + actual_length:
                    string_data = data[2:2+actual_length]
                    return string_data.decode('utf-8', errors='ignore')
            return ""
        except Exception as e:
            logger.error(f"读取字符串错误 (DB{db_number}.DBString{start_address}): {e}")
            return None
    
    def read_dint(self, db_number=9000, start_address=26):
        """读取32位整数 (DInt)"""
        if not self.connected:
            return None
            
        try:
            data = self.client.db_read(db_number, start_address, 4)
            if data:
                return struct.unpack('>i', data)[0]  # 大端序
            return None
        except Exception as e:
            logger.error(f"读取DInt错误 (DB{db_number}.DBD{start_address}): {e}")
            return None
    
    def read_int(self, db_number=9000, start_address=30):
        """读取16位整数 (Int)"""
        if not self.connected:
            return None
            
        try:
            data = self.client.db_read(db_number, start_address, 2)
            if data:
                return struct.unpack('>h', data)[0]  # 大端序
            return None
        except Exception as e:
            logger.error(f"读取Int错误 (DB{db_number}.DBW{start_address}): {e}")
            return None
    
    def read_byte(self, db_number=9000, start_address=32):
        """读取8位数据 (Byte)"""
        if not self.connected:
            return None
            
        try:
            data = self.client.db_read(db_number, start_address, 1)
            if data:
                return data[0]
            return None
        except Exception as e:
            logger.error(f"读取Byte错误 (DB{db_number}.DBB{start_address}): {e}")
            return None
    
    def read_all_data(self, db_number=9000):
        """读取所有数据"""
        if not self.connected:
            logger.error("PLC未连接")
            return {}
        
        timestamp = datetime.now()
        results = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'data': {}
        }
        
        logger.info(f"开始读取所有数据 - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        # 1. 读取32个布尔值
        logger.info("1. 读取32个布尔值 (地址 0.0 - 3.7):")
        bool_values = {}
        for byte_addr in range(4):  # 0, 1, 2, 3
            for bit_pos in range(8):  # 0-7
                bool_index = byte_addr * 8 + bit_pos + 1
                bool_name = f"B{bool_index}"
                bool_value = self.read_bool_at_address(db_number, byte_addr, bit_pos)
                bool_values[bool_name] = bool_value
                
                if bool_value is not None:
                    status = "✓" if bool_value else "✗"
                    logger.info(f"  {status} {bool_name:>4}: DB{db_number}.DBX{byte_addr}.{bit_pos} = {bool_value}")
                else:
                    logger.warning(f"  ✗ {bool_name:>4}: DB{db_number}.DBX{byte_addr}.{bit_pos} = ERROR")
        
        results['data']['booleans'] = bool_values
        
        # 2. 读取字符串
        logger.info("\n2. 读取字符串 (地址 4.0):")
        string_value = self.read_string(db_number, 4, 20)
        if string_value is not None:
            logger.info(f"  ✓ String: DB{db_number}.DBString4 = '{string_value}'")
            results['data']['string'] = string_value
        else:
            logger.warning(f"  ✗ String: DB{db_number}.DBString4 = ERROR")
            results['data']['string'] = None
        
        # 3. 读取32位整数1 (地址 26.0)
        logger.info("\n3. 读取32位整数1 (地址 26.0):")
        dint1_value = self.read_dint(db_number, 26)
        if dint1_value is not None:
            logger.info(f"  ✓ DInt1: DB{db_number}.DBD26 = {dint1_value}")
            results['data']['dint1'] = dint1_value
        else:
            logger.warning(f"  ✗ DInt1: DB{db_number}.DBD26 = ERROR")
            results['data']['dint1'] = None
        
        # 4. 读取32位整数2 (地址 30.0)
        logger.info("\n4. 读取32位整数2 (地址 30.0):")
        dint2_value = self.read_dint(db_number, 30)
        if dint2_value is not None:
            logger.info(f"  ✓ DInt2: DB{db_number}.DBD30 = {dint2_value}")
            results['data']['dint2'] = dint2_value
        else:
            logger.warning(f"  ✗ DInt2: DB{db_number}.DBD30 = ERROR")
            results['data']['dint2'] = None
        

        
        # 5. 读取16位整数1 (地址 34.0)
        logger.info("\n5. 读取16位整数1 (地址 34.0):")
        int1_value = self.read_int(db_number, 34)
        if int1_value is not None:
            logger.info(f"  ✓ Int1: DB{db_number}.DBW34 = {int1_value}")
            results['data']['int1'] = int1_value
        else:
            logger.warning(f"  ✗ Int1: DB{db_number}.DBW34 = ERROR")
            results['data']['int1'] = None
        
        # 6. 读取16位整数2 (地址 36.0)
        logger.info("\n6. 读取16位整数2 (地址 36.0):")
        int2_value = self.read_int(db_number, 36)
        if int2_value is not None:
            logger.info(f"  ✓ Int2: DB{db_number}.DBW36 = {int2_value}")
            results['data']['int2'] = int2_value
        else:
            logger.warning(f"  ✗ Int2: DB{db_number}.DBW36 = ERROR")
            results['data']['int2'] = None
        
        logger.info("=" * 80)
        logger.info("数据读取完成")
        
        return results
    
    def continuous_read(self, interval_seconds=2, max_reads=0):
        """连续读取数据"""
        logger.info(f"开始连续读取，间隔: {interval_seconds}秒")
        logger.info("按 Ctrl+C 停止")
        
        read_count = 0
        all_results = []
        
        try:
            while True:
                if max_reads > 0 and read_count >= max_reads:
                    logger.info(f"达到最大读取次数: {max_reads}")
                    break
                
                results = self.read_all_data()
                if results:
                    all_results.append(results)
                    read_count += 1
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("用户中断连续读取")
        except Exception as e:
            logger.error(f"连续读取时发生错误: {e}")
        
        return all_results
    
    def save_results_to_file(self, results, filename_prefix="complete_data"):
        """保存结果到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存JSON文件
        json_filename = f"{filename_prefix}_{timestamp}.json"
        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"数据已保存到: {json_filename}")
        except Exception as e:
            logger.error(f"保存JSON文件时发生错误: {e}")
        
        # 保存CSV文件
        csv_filename = f"{filename_prefix}_{timestamp}.csv"
        try:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 写入表头
                header = ['timestamp']
                if 'data' in results:
                    if 'booleans' in results['data']:
                        header.extend([f'B{i}' for i in range(1, 33)])
                    header.extend(['string', 'dint1', 'dint2', 'int1', 'int2'])
                writer.writerow(header)
                
                # 写入数据
                row = [results.get('timestamp', '')]
                if 'data' in results:
                    data = results['data']
                    if 'booleans' in data:
                        row.extend([data['booleans'].get(f'B{i}', '') for i in range(1, 33)])
                    row.extend([
                        data.get('string', ''),
                        data.get('dint1', ''),
                        data.get('dint2', ''),
                        data.get('int1', ''),
                        data.get('int2', '')
                    ])
                writer.writerow(row)
            
            logger.info(f"数据已保存到: {csv_filename}")
        except Exception as e:
            logger.error(f"保存CSV文件时发生错误: {e}")

def main():
    """主函数"""
    print("=" * 80)
    print("DB9000 完整数据读取器")
    print("=" * 80)
    
    # 创建读取器
    reader = CompleteDataReader("172.16.10.66")
    
    try:
        # 连接到PLC
        if not reader.connect():
            print("无法连接到PLC，程序退出")
            return
        
        # 读取一次所有数据
        print("\n执行单次数据读取...")
        results = reader.read_all_data()
        
        # 保存结果
        if results:
            reader.save_results_to_file(results)
        
        # 询问是否进行连续读取
        print("\n" + "=" * 50)
        print("是否开始连续读取？")
        print("输入 'y' 开始连续读取，其他键退出: ", end="")
        
        try:
            user_input = input().strip().lower()
            if user_input == 'y':
                print("请输入连续读取参数:")
                interval = int(input("读取间隔（秒，默认2）: ") or "2")
                max_reads = int(input("最大读取次数（0表示无限，默认10）: ") or "10")
                
                all_results = reader.continuous_read(interval, max_reads)
                
                # 保存所有结果
                if all_results:
                    reader.save_results_to_file(all_results, "continuous_data")
                    
        except KeyboardInterrupt:
            print("\n用户中断程序")
        except ValueError:
            print("输入无效，退出程序")
        
    except Exception as e:
        logger.error(f"程序执行时发生错误: {e}")
    finally:
        reader.disconnect()

if __name__ == "__main__":
    main() 