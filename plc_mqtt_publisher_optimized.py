#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLC数据采集器 - MQTT发布优化版本
只在数据发生变化时才上传到MQTT服务器
"""

import snap7
import struct
import time
import json
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
import threading
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('plc_mqtt_publisher_optimized.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PLCMQTTPublisherOptimized:
    """PLC数据采集器 - MQTT发布优化版本"""
    
    def __init__(self, plc_ip="172.16.10.66"):
        self.plc_ip = plc_ip
        self.plc_client = snap7.client.Client()
        self.plc_connected = False
        
        # MQTT配置
        self.mqtt_broker = "Mqtt.dxiot.liju.cc"
        self.mqtt_port = 1883
        self.mqtt_topic_pub = "/dxiot/4q/pub/huaheng/zudui"
        self.mqtt_topic_sub = "/dxiot/4q/get/huaheng/zudui"
        
        # MQTT客户端
        self.mqtt_client = mqtt.Client()
        self.mqtt_connected = False
        self.running = False
        
        # 数据变化检测
        self.last_data_hash = None
        self.last_data = None
        self.data_change_count = 0
        self.total_read_count = 0
        
        # 设置MQTT回调
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_publish = self.on_mqtt_publish
        self.mqtt_client.on_message = self.on_mqtt_message
        
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
    
    def connect_mqtt(self):
        """连接到MQTT服务器"""
        try:
            import os, socket
            broker = os.getenv('MQTT_BROKER', self.mqtt_broker)
            port = int(os.getenv('MQTT_PORT', str(self.mqtt_port)))
            broker_ip = os.getenv('MQTT_BROKER_IP', '').strip()

            # 解析域名
            resolved_ip = None
            try:
                resolved_ip = socket.gethostbyname(broker)
                logger.info(f"MQTT域名解析成功: {broker} -> {resolved_ip}")
            except Exception as re:
                logger.warning(f"MQTT域名解析失败: {broker} ({re})")

            target_host = broker
            if not resolved_ip and broker_ip:
                target_host = broker_ip
                logger.info(f"使用备用直连IP连接MQTT: {target_host}:{port}")

            logger.info(f"正在连接到MQTT服务器: {target_host}:{port}")

            # 设置认证（如后续需要可通过环境变量传入）
            user = os.getenv('MQTT_USERNAME', '').strip()
            pwd = os.getenv('MQTT_PASSWORD', '').strip()
            if user and pwd:
                self.mqtt_client.username_pw_set(user, pwd)
                logger.info("已启用MQTT用户名密码认证")

            self.mqtt_client.connect(target_host, port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"MQTT连接错误: {e}")
            return False
    
    def disconnect_mqtt(self):
        """断开MQTT连接"""
        if self.mqtt_connected:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_connected = False
            logger.info("已断开MQTT连接")
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            self.mqtt_connected = True
            logger.info("✓ MQTT连接成功")
            # 订阅主题
            client.subscribe(self.mqtt_topic_sub)
            logger.info(f"已订阅主题: {self.mqtt_topic_sub}")
        else:
            logger.error(f"MQTT连接失败，错误码: {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        self.mqtt_connected = False
        logger.warning("MQTT连接断开")
    
    def on_mqtt_publish(self, client, userdata, mid):
        """MQTT发布回调"""
        logger.debug(f"MQTT消息已发布，消息ID: {mid}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            payload = msg.payload.decode('utf-8')
            logger.info(f"收到MQTT消息: {msg.topic} -> {payload}")
        except Exception as e:
            logger.error(f"处理MQTT消息时发生错误: {e}")
    
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
    
    def calculate_data_hash(self, data):
        """计算数据的哈希值用于变化检测"""
        if not data:
            return None
        
        # 创建数据摘要（排除timestamp，只比较实际数据）
        data_summary = {
            'booleans': data.get('data', {}).get('booleans', {}),
            'string': data.get('data', {}).get('string', ''),
            'dint1': data.get('data', {}).get('dint1'),
            'dint2': data.get('data', {}).get('dint2'),
            'int1': data.get('data', {}).get('int1'),
            'int2': data.get('data', {}).get('int2')
        }
        
        # 转换为JSON字符串并计算MD5哈希
        json_str = json.dumps(data_summary, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(json_str.encode('utf-8')).hexdigest()
    
    def has_data_changed(self, current_data):
        """检查数据是否发生变化"""
        if not current_data:
            return False
        
        current_hash = self.calculate_data_hash(current_data)
        
        if self.last_data_hash is None:
            # 第一次读取，记录哈希值但不认为有变化
            self.last_data_hash = current_hash
            self.last_data = current_data
            return False
        
        if current_hash != self.last_data_hash:
            # 数据发生变化
            self.last_data_hash = current_hash
            self.last_data = current_data
            return True
        
        return False
    
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
            
            return results
            
        except Exception as e:
            logger.error(f"读取数据时发生错误: {e}")
            return None
    
    def publish_data(self, data):
        """发布数据到MQTT"""
        if not self.mqtt_connected or not data:
            return False
        
        try:
            # 转换为JSON格式
            json_data = json.dumps(data, ensure_ascii=False)
            
            # 发布到MQTT
            result = self.mqtt_client.publish(self.mqtt_topic_pub, json_data, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"数据已发布到MQTT主题: {self.mqtt_topic_pub}")
                return True
            else:
                logger.error(f"MQTT发布失败，错误码: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"发布MQTT数据时发生错误: {e}")
            return False
    
    def collect_and_publish_optimized(self, interval_seconds=2):
        """优化版本：只在数据变化时发布"""
        logger.info(f"开始优化数据采集和发布，间隔: {interval_seconds}秒")
        logger.info(f"MQTT服务器: {self.mqtt_broker}")
        logger.info(f"发布主题: {self.mqtt_topic_pub}")
        logger.info(f"订阅主题: {self.mqtt_topic_sub}")
        logger.info("只在数据发生变化时才发布到MQTT")
        logger.info("按 Ctrl+C 停止")
        
        self.running = True
        collect_count = 0
        
        try:
            while self.running:
                # 读取数据
                data = self.read_all_data()
                self.total_read_count += 1
                
                if data:
                    # 检查数据是否发生变化
                    if self.has_data_changed(data):
                        # 数据发生变化，发布到MQTT
                        if self.publish_data(data):
                            self.data_change_count += 1
                            collect_count += 1
                            
                            # 记录变化详情
                            bool_true_count = sum(1 for v in data['data']['booleans'].values() if v)
                            logger.info(f"数据变化 #{self.data_change_count} - 发布成功")
                            logger.info(f"  布尔值真值数量: {bool_true_count}/32")
                            logger.info(f"  字符串: '{data['data']['string']}'")
                            logger.info(f"  DInt1: {data['data']['dint1']}, DInt2: {data['data']['dint2']}")
                            logger.info(f"  Int1: {data['data']['int1']}, Int2: {data['data']['int2']}")
                        else:
                            logger.warning("数据变化但发布失败")
                    else:
                        # 数据未变化，只记录读取状态
                        if self.total_read_count % 10 == 0:  # 每10次读取显示一次状态
                            logger.info(f"数据未变化 - 总读取: {self.total_read_count}, 变化发布: {self.data_change_count}")
                else:
                    logger.error("数据读取失败")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("用户中断数据采集")
        except Exception as e:
            logger.error(f"数据采集过程中发生错误: {e}")
        finally:
            self.running = False
            # 显示统计信息
            logger.info(f"采集结束统计:")
            logger.info(f"  总读取次数: {self.total_read_count}")
            logger.info(f"  数据变化次数: {self.data_change_count}")
            logger.info(f"  发布成功次数: {collect_count}")
            if self.total_read_count > 0:
                change_rate = (self.data_change_count / self.total_read_count) * 100
                logger.info(f"  变化率: {change_rate:.2f}%")
    
    def stop_collection(self):
        """停止数据采集"""
        self.running = False
        logger.info("正在停止数据采集...")

def main():
    """主函数"""
    print("=" * 80)
    print("PLC数据采集器 - MQTT发布优化版本")
    print("=" * 80)
    print("特点：只在数据发生变化时才上传到MQTT服务器")
    print("=" * 80)
    
    # 创建发布器
    publisher = PLCMQTTPublisherOptimized("172.16.10.66")
    
    try:
        # 连接到PLC
        if not publisher.connect_plc():
            print("无法连接到PLC，程序退出")
            return
        
        # 连接到MQTT
        if not publisher.connect_mqtt():
            print("无法连接到MQTT服务器，程序退出")
            return
        
        # 询问采集参数
        interval = int(input("请输入采集间隔（秒，默认2）: ").strip() or "2")
        
        print(f"\n开始优化数据采集和发布...")
        print(f"PLC IP: 172.16.10.66")
        print(f"MQTT服务器: {publisher.mqtt_broker}")
        print(f"发布主题: {publisher.mqtt_topic_pub}")
        print(f"订阅主题: {publisher.mqtt_topic_sub}")
        print(f"采集间隔: {interval}秒")
        print("只在数据发生变化时才发布到MQTT")
        print("按 Ctrl+C 停止")
        
        # 开始采集和发布
        publisher.collect_and_publish_optimized(interval)
        
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        logger.error(f"程序执行时发生错误: {e}")
    finally:
        publisher.stop_collection()
        publisher.disconnect_mqtt()
        publisher.disconnect_plc()

if __name__ == "__main__":
    main() 