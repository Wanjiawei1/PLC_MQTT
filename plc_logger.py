#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLC数据记录器
读取DB9000数据并写入日志文件，供MQTTX等工具使用
"""

import snap7
import struct
import time
import json
import logging
from datetime import datetime
import os

# 配置日志
log_filename = f"plc_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PLCLogger:
    """PLC数据记录器"""
    
    def __init__(self, plc_ip="172.16.10.66"):
        self.plc_ip = plc_ip
        self.plc_client = snap7.client.Client()
        self.plc_connected = False
        self.running = False
        
    def connect_plc(self):
        """连接到PLC"""
        try:
            logger.info(f"正在连接到PLC: {self.plc_ip}")
            self.plc_client.connect(self.plc_ip, 0, 1)
            
            if self.plc_client.get_connected():
                self.plc_connected = True
                logger.info("✓ PLC连接成功")
                return True
            else:
                logger.error("✗ PLC连接失败")
                return False
                
        except Exception as e:
            logger.error(f"PLC连接错误: {e}")
            return False
    
    def disconnect_plc(self):
        """断开PLC连接"""
        if self.plc_connected:
            self.plc_client.disconnect()
            self.plc_connected = False
            logger.info("已断开PLC连接")
    
    def read_bool_at_address(self, db_number=9000, byte_address=0, bit_position=0):
        """读取指定地址的布尔值"""
        if not self.plc_connected:
            return None
            
        try:
            data = self.plc_client.db_read(db_number, byte_address, 1)
            if data:
                byte_value = data[0]
                return bool(byte_value & (1 << bit_position))
            return None
        except Exception as e:
            logger.error(f"读取布尔值错误 (DB{db_number}.DBX{byte_address}.{bit_position}): {e}")
            return None
    
    def read_string(self, db_number=9000, start_address=4, max_length=20):
        """读取字符串"""
        if not self.plc_connected:
            return None
            
        try:
            data = self.plc_client.db_read(db_number, start_address, max_length + 2)
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
        if not self.plc_connected:
            return None
            
        try:
            data = self.plc_client.db_read(db_number, start_address, 4)
            if data:
                return struct.unpack('>i', data)[0]  # 大端序
            return None
        except Exception as e:
            logger.error(f"读取DInt错误 (DB{db_number}.DBD{start_address}): {e}")
            return None
    
    def read_int(self, db_number=9000, start_address=34):
        """读取16位整数 (Int)"""
        if not self.plc_connected:
            return None
            
        try:
            data = self.plc_client.db_read(db_number, start_address, 2)
            if data:
                return struct.unpack('>h', data)[0]  # 大端序
            return None
        except Exception as e:
            logger.error(f"读取Int错误 (DB{db_number}.DBW{start_address}): {e}")
            return None
    
    def read_all_data(self, db_number=9000):
        """读取所有数据"""
        if not self.plc_connected:
            logger.error("PLC未连接")
            return None
        
        timestamp = datetime.now()
        results = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'device_id': 'PLC_DB9000',
            'data': {}
        }
        
        try:
            # 1. 读取32个布尔值
            bool_values = {}
            for byte_addr in range(4):  # 0, 1, 2, 3
                for bit_pos in range(8):  # 0-7
                    bool_index = byte_addr * 8 + bit_pos + 1
                    bool_name = f"B{bool_index}"
                    bool_value = self.read_bool_at_address(db_number, byte_addr, bit_pos)
                    bool_values[bool_name] = bool_value
            
            results['data']['booleans'] = bool_values
            
            # 2. 读取字符串
            string_value = self.read_string(db_number, 4, 20)
            results['data']['string'] = string_value
            
            # 3. 读取32位整数1 (地址 26.0)
            dint1_value = self.read_dint(db_number, 26)
            results['data']['dint1'] = dint1_value
            
            # 4. 读取32位整数2 (地址 30.0)
            dint2_value = self.read_dint(db_number, 30)
            results['data']['dint2'] = dint2_value
            
            # 5. 读取16位整数1 (地址 34.0)
            int1_value = self.read_int(db_number, 34)
            results['data']['int1'] = int1_value
            
            # 6. 读取16位整数2 (地址 36.0)
            int2_value = self.read_int(db_number, 36)
            results['data']['int2'] = int2_value
            
            # 记录到日志
            logger.info(f"数据读取完成 - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"布尔值真值数量: {sum(1 for v in bool_values.values() if v)}/32")
            logger.info(f"字符串: '{string_value}'")
            logger.info(f"DInt1: {dint1_value}, DInt2: {dint2_value}")
            logger.info(f"Int1: {int1_value}, Int2: {int2_value}")
            
            # 输出JSON格式数据（供MQTTX使用）
            json_data = json.dumps(results, ensure_ascii=False, indent=2)
            logger.info(f"JSON数据: {json_data}")
            
            return results
            
        except Exception as e:
            logger.error(f"读取数据时发生错误: {e}")
            return None
    
    def continuous_logging(self, interval_seconds=2):
        """连续记录数据"""
        logger.info(f"开始连续数据记录，间隔: {interval_seconds}秒")
        logger.info(f"日志文件: {log_filename}")
        logger.info("按 Ctrl+C 停止")
        
        self.running = True
        collect_count = 0
        
        try:
            while self.running:
                # 读取数据
                data = self.read_all_data()
                
                if data:
                    collect_count += 1
                    logger.info(f"成功记录第 {collect_count} 条数据")
                else:
                    logger.error("数据读取失败")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("用户中断数据记录")
        except Exception as e:
            logger.error(f"数据记录过程中发生错误: {e}")
        finally:
            self.running = False
    
    def stop_logging(self):
        """停止数据记录"""
        self.running = False
        logger.info("正在停止数据记录...")

def main():
    """主函数"""
    print("=" * 80)
    print("PLC数据记录器")
    print("=" * 80)
    
    # 创建记录器
    logger_instance = PLCLogger("172.16.10.66")
    
    try:
        # 连接到PLC
        if not logger_instance.connect_plc():
            print("无法连接到PLC，程序退出")
            return
        
        # 询问记录参数
        interval = int(input("请输入记录间隔（秒，默认2）: ").strip() or "2")
        
        print(f"\n开始数据记录...")
        print(f"PLC IP: 172.16.10.66")
        print(f"记录间隔: {interval}秒")
        print(f"日志文件: {log_filename}")
        print("按 Ctrl+C 停止")
        print("\n数据将以JSON格式记录，可直接用于MQTTX等工具")
        
        # 开始连续记录
        logger_instance.continuous_logging(interval)
        
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        logger.error(f"程序执行时发生错误: {e}")
    finally:
        logger_instance.stop_logging()
        logger_instance.disconnect_plc()

if __name__ == "__main__":
    main() 