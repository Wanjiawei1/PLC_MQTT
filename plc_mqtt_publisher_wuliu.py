#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华恒物流产线 PLC 数据采集器 - MQTT 发布版本
仅采集前 4 个信号量并发布至指定主题
"""

import snap7
import struct
import time
import json
import logging
from datetime import datetime   
import paho.mqtt.client as mqtt
import os
import socket

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('plc_mqtt_publisher_wuliu.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LogisticsPLCMQTTPublisher:
    """华恒物流产线 PLC 数据采集器 - 仅采集 Occupied、CallStation、Type、OldStation"""

    # DB 号与信号偏移量常量（基于真实10字节结构修正）
    DB_NUMBER = 3003  # 站台信息 DB3003
    OFFSET_OCCUPIED_BYTE = 0  # Bool 0.0
    OFFSET_CALLSTATION_BYTE = 0  # Bool 0.1
    OFFSET_FIELD3_BYTE = 2  # Int 2.0 (第3个数据字段，备用)
    OFFSET_TYPE_BYTE = 4  # Int 4.0 (修正：从2改为4)
    OFFSET_OLDSTATION_BYTE = 6  # Int 6.0 (修正：从4改为6)
    OFFSET_RESERVE2_BYTE = 8  # Int 8.0 (备用字段2)

    STATION_COUNT = int(os.getenv("STATION_COUNT", "40"))  # 站台数量，根据用户例子修正为40
    CHUNK_SIZE = int(os.getenv("MQTT_CHUNK", "10"))  # 每条 MQTT 消息包含的最大站台数量

    def __init__(self, plc_ip: str | None = None):
        self.plc_ip = plc_ip or os.getenv("PLC_IP", "172.16.10.201")
        self.plc_client = snap7.client.Client()
        self.plc_connected = False

        # MQTT 配置
        self.mqtt_broker = os.getenv("MQTT_BROKER", "Mqtt.dxiot.liju.cc")
        self.mqtt_port = 1883
        self.mqtt_topic_pub = "/dxiot/4q/pub/huaheng/wuliu"
        self.mqtt_topic_sub = "/dxiot/4q/get/huaheng/wuliu"  # 按需求订阅 wuliu

        # MQTT 客户端
        self.mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
        self.mqtt_connected = False
        self.running = False

        # 设置 MQTT 回调
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.on_publish = self._on_mqtt_publish
        self.mqtt_client.on_message = self._on_mqtt_message

        # 上次采集的快照
        self._last_batch: list[dict] | None = None
        self._last_single: dict | None = None
        # 心跳机制：连续无变化计数器
        self._unchanged_count = 0
        self.HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "5"))  # 连续N次无变化后强制发送

    # ------------------------- MQTT 相关 -------------------------
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        mqtt_errors = {
            0: "连接成功",
            1: "协议版本不正确",
            2: "客户端标识符无效",
            3: "服务器不可用",
            4: "用户名或密码错误",
            5: "未授权"
        }
        error_msg = mqtt_errors.get(rc, f"未知错误 ({rc})")
        
        if rc == 0:
            self.mqtt_connected = True
            logger.info(f"✓ MQTT 连接成功: {error_msg}")
            client.subscribe(self.mqtt_topic_sub)
            logger.info(f"已订阅主题: {self.mqtt_topic_sub}")
        else:
            self.mqtt_connected = False
            logger.error(f"MQTT 连接失败: {error_msg}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        self.mqtt_connected = False
        if rc != 0:
            logger.warning(f"MQTT 意外断开连接 (错误码: {rc})")
        else:
            logger.info("MQTT 正常断开连接")

    def _on_mqtt_publish(self, client, userdata, mid):
        logger.debug(f"MQTT 消息已发布，消息 ID: {mid}")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            logger.info(f"收到 MQTT 消息: {msg.topic} -> {payload}")
        except Exception as e:
            logger.error(f"处理 MQTT 消息时发生错误: {e}")

    def connect_mqtt(self) -> bool:
        """连接到 MQTT 服务器"""
        try:
            broker = os.getenv("MQTT_BROKER", self.mqtt_broker)
            port = int(os.getenv("MQTT_PORT", str(self.mqtt_port)))
            broker_ip = os.getenv("MQTT_BROKER_IP", "").strip()
            connect_timeout = int(os.getenv("MQTT_CONNECT_TIMEOUT", "30"))  # 连接超时30秒
            keepalive = int(os.getenv("MQTT_KEEPALIVE", "120"))  # 保活时间120秒

            logger.info(f"正在连接 MQTT 服务器: {broker}:{port}")
            logger.info(f"连接超时: {connect_timeout}秒, 保活时间: {keepalive}秒")

            # 域名解析
            try:
                resolved_ip = socket.gethostbyname(broker)
                logger.info(f"MQTT 域名解析成功: {broker} -> {resolved_ip}")
                target_host = resolved_ip
            except Exception as re:
                logger.warning(f"MQTT 域名解析失败: {broker} ({re})")
                target_host = broker_ip or broker

            # 用户名/密码
            user = os.getenv("MQTT_USERNAME", "").strip()
            pwd = os.getenv("MQTT_PASSWORD", "").strip()
            if user and pwd:
                self.mqtt_client.username_pw_set(user, pwd)
                logger.info("已启用 MQTT 用户名密码认证")
            else:
                logger.info("未设置 MQTT 认证信息，使用匿名连接")

            # 设置连接超时和保活时间
            logger.info(f"尝试连接到: {target_host}:{port}")
            self.mqtt_client.connect(target_host, port, keepalive)
            
            # 等待连接结果，最多等待 connect_timeout 秒
            self.mqtt_client.loop_start()
            start_time = time.time()
            while not self.mqtt_connected and (time.time() - start_time) < connect_timeout:
                time.sleep(0.1)
            
            if self.mqtt_connected:
                logger.info("✓ MQTT 连接成功")
                return True
            else:
                logger.error(f"MQTT 连接超时 ({connect_timeout}秒)")
                self.mqtt_client.loop_stop()
                return False
                
        except Exception as e:
            logger.error(f"MQTT 连接错误: {e}")
            return False

    def disconnect_mqtt(self):
        if self.mqtt_connected:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_connected = False
            logger.info("已断开 MQTT 连接")

    # ------------------------- PLC 相关 -------------------------
    def connect_plc(self, retries: int = 3, delay: float = 2.0) -> bool:
        """连接到 PLC，支持重试"""
        for attempt in range(1, retries + 1):
            try:
                logger.info(f"正在连接到 PLC: {self.plc_ip} (第 {attempt}/{retries} 次)")
                self.plc_client.connect(self.plc_ip, 0, 1)
                if self.plc_client.get_connected():
                    self.plc_connected = True
                    logger.info("✓ PLC 连接成功")
                    return True
                logger.error("✗ PLC 连接失败")
            except Exception as e:
                logger.error(f"PLC 连接错误: {e}")
            time.sleep(delay)
        return False

    def disconnect_plc(self):
        if self.plc_connected:
            self.plc_client.disconnect()
            self.plc_connected = False
            logger.info("已断开 PLC 连接")

    # ------------------------- 数据读取 -------------------------
    def _read_bool(self, byte_address: int, bit_position: int = 0) -> bool | None:
        if not self.plc_connected:
            logger.warning("PLC 未连接，尝试重新连接...")
            if not self.connect_plc():
                logger.error("PLC 重新连接失败")
                return None
        try:
            data = self.plc_client.db_read(self.DB_NUMBER, byte_address, 1)
            if data:
                return bool(data[0] & (1 << bit_position))
            return None
        except Exception as e:
            logger.error(f"读取 Bool 错误 (DB{self.DB_NUMBER}.DBX{byte_address}.{bit_position}): {e}")
            return None

    def _read_int(self, start_address: int) -> int | None:
        if not self.plc_connected:
            logger.warning("PLC 未连接，尝试重新连接...")
            if not self.connect_plc():
                logger.error("PLC 重新连接失败")
                return None
        try:
            data = self.plc_client.db_read(self.DB_NUMBER, start_address, 2)
            if data:
                return struct.unpack('>h', data)[0]
            return None
        except Exception as e:
            logger.error(f"读取 Int 错误 (DB{self.DB_NUMBER}.DBW{start_address}): {e}")
            return None

    def read_single_station(self, station_index: int) -> dict | None:
        """读取指定站台的完整6个数据字段"""
        if not self.plc_connected:
            logger.error("PLC 未连接")
            return None
        
        if station_index < 0 or station_index >= self.STATION_COUNT:
            logger.error(f"站台索引 {station_index} 超出范围 (0-{self.STATION_COUNT-1})")
            return None
        
        station_size = 10
        base_offset = station_index * station_size
        
        try:
            raw = self.plc_client.db_read(self.DB_NUMBER, base_offset, station_size)
            if len(raw) != station_size:
                logger.error(f"读取站台 {station_index} 数据长度不正确")
                return None
            
            # 按10字节结构解析6个字段
            occupied = bool(raw[0] & 1)
            call_station = bool(raw[0] & 2)
            field3 = struct.unpack('>h', raw[2:4])[0]      # 第3个数据字段(备用)
            type_value = struct.unpack('>h', raw[4:6])[0]  # Type字段
            old_station = struct.unpack('>h', raw[6:8])[0] # OldStation字段
            reserve2 = struct.unpack('>h', raw[8:10])[0]   # 备用字段2
            
            timestamp = datetime.now()
            result = {
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "device_id": f"PLC_DB3003_Station{station_index}",
                "station_index": station_index,
                "base_offset": base_offset,
                "data": {
                    "Occupied": occupied,
                    "CallStation": call_station,
                    "Field3": field3,           # 备用字段1
                    "Type": type_value,
                    "OldStation": old_station,
                    "Reserve2": reserve2,       # 备用字段2
                }
            }
            
            logger.info(f"读取站台{station_index}数据: {json.dumps(result, ensure_ascii=False)}")
            return result
            
        except Exception as e:
            logger.error(f"读取站台 {station_index} 数据时发生错误: {e}")
            return None

    def read_signals(self, station_index: int = 0) -> dict | None:
        """读取指定站台的信号量（保持向后兼容，默认读取第0个站台）"""
        return self.read_single_station(station_index)

    def read_all_stations(self, max_stations: int | None = None) -> list[dict]:
        """批量读取所有站台信息，自动截断到 PLC 实际 DB 大小"""
        if not self.plc_connected:
            logger.error("PLC 未连接")
            return []

        station_size = 10  # 每站台结构长度（真实结构：2Bool + 4Int = 10字节）
        max_len = max_stations or self.STATION_COUNT
        results: list[dict] = []
        for idx in range(max_len):
            base = idx * station_size
            try:
                raw = self.plc_client.db_read(self.DB_NUMBER, base, station_size)
            except Exception as e:
                if "Address out of range" in str(e):
                    logger.info(f"已到达 DB 尾部，在第 {idx} 个站台处停止")
                    break
                logger.error(f"读取站台 {idx} 数据块错误: {e}")
                break
            if len(raw) != station_size:
                break
            # 按真实10字节结构解析
            occupied = bool(raw[0] & 1)
            call_station = bool(raw[0] & 2)
            field3 = struct.unpack('>h', raw[2:4])[0]      # 第3个数据字段
            type_value = struct.unpack('>h', raw[4:6])[0]  # Type字段
            old_station = struct.unpack('>h', raw[6:8])[0] # OldStation字段
            reserve2 = struct.unpack('>h', raw[8:10])[0]   # 备用字段2
            
            # 不过滤任何站台数据，包括全为0的备用站台
            results.append({
                "index": idx,
                "Occupied": occupied,
                "CallStation": call_station,
                "Field3": field3,           # 第3个数据字段
                "Type": type_value,
                "OldStation": old_station,
                "Reserve2": reserve2,       # 备用字段2
            })
        logger.info(f"批量读取站台完成，总计 {len(results)} 条有效数据")
        return results

    # ------------------------- 数据发布 -------------------------
    def publish_data(self, data: dict) -> bool:
        if not self.mqtt_connected or not data:
            return False
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            result = self.mqtt_client.publish(self.mqtt_topic_pub, json_data, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"数据已发布到 MQTT 主题: {self.mqtt_topic_pub}")
                return True
            logger.error(f"MQTT 发布失败，错误码: {result.rc}")
            return False
        except Exception as e:
            logger.error(f"发布 MQTT 数据时发生错误: {e}")
            return False

    # ------------------------- 主循环 -------------------------
    def collect_and_publish(self, interval_seconds: int = 2, batch: bool = False):
        logger.info(f"开始数据采集和发布，间隔: {interval_seconds} 秒")
        logger.info(f"MQTT 服务器: {self.mqtt_broker}")
        logger.info(f"发布主题: {self.mqtt_topic_pub}")
        logger.info(f"订阅主题: {self.mqtt_topic_sub}")
        logger.info("按 Ctrl+C 停止")

        self.running = True
        cnt = 0
        try:
            while self.running:
                # 检查并重试 MQTT 连接
                if not self.mqtt_connected:
                    logger.warning("MQTT 未连接，尝试重新连接...")
                    retry_count = int(os.getenv("MQTT_RETRY_COUNT", "3"))
                    retry_delay = int(os.getenv("MQTT_RETRY_DELAY", "5"))
                    
                    for attempt in range(1, retry_count + 1):
                        logger.info(f"MQTT 重连尝试 {attempt}/{retry_count}")
                        if self.connect_mqtt():
                            break
                        if attempt < retry_count:
                            logger.info(f"等待 {retry_delay} 秒后重试...")
                            time.sleep(retry_delay)
                if batch:
                    data_list = self.read_all_stations()
                    if not data_list:
                        time.sleep(interval_seconds)
                        continue
                    # 变更检测：仅发送与上次快照不同的站台
                    if self._last_batch is None:
                        changed = data_list  # 首次全部发送
                    else:
                        prev_map = {d["index"]: d for d in self._last_batch}
                        changed = [cur for cur in data_list if cur != prev_map.get(cur["index"])]

                    if not changed:
                        self._unchanged_count += 1
                        if self._unchanged_count >= self.HEARTBEAT_INTERVAL:
                            logger.info(f"连续 {self._unchanged_count} 次无变化，发送心跳数据证明程序运行正常")
                            changed = data_list  # 强制发送全部数据作为心跳
                            self._unchanged_count = 0  # 重置计数器
                        else:
                            logger.debug(f"所有站台无变化({self._unchanged_count}/{self.HEARTBEAT_INTERVAL})，跳过发布")
                            time.sleep(interval_seconds)
                            continue
                    else:
                        # 有变化时重置计数器
                        self._unchanged_count = 0

                    # 分包发送变更数据
                    for i in range(0, len(changed), self.CHUNK_SIZE):
                        chunk = changed[i:i + self.CHUNK_SIZE]
                        if self.publish_data(chunk):
                            cnt += len(chunk)
                            logger.info(f"已发布变更包 {i//self.CHUNK_SIZE+1} ，{len(chunk)} 条；累计 {cnt}")
                        else:
                            logger.error("MQTT 发布失败，停止后续包发送")
                            break

                    # 更新快照
                    self._last_batch = data_list
                else:
                    # 单站台模式：读取第0个站台的数据
                    data = self.read_single_station(0)
                    if data:
                        if data != self._last_single:
                            if self.publish_data(data):
                                cnt += 1
                                logger.info(f"成功发布单点数据（站台0），总计 {cnt}")
                                self._last_single = data
                                self._unchanged_count = 0  # 重置计数器
                        else:
                            self._unchanged_count += 1
                            if self._unchanged_count >= self.HEARTBEAT_INTERVAL:
                                logger.info(f"连续 {self._unchanged_count} 次单点数据无变化，发送心跳数据")
                                if self.publish_data(data):
                                    cnt += 1
                                    logger.info(f"成功发布单点心跳数据（站台0），总计 {cnt}")
                                self._unchanged_count = 0  # 重置计数器
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("用户中断采集")
        except Exception as e:
            logger.error(f"采集过程中发生错误: {e}")
        finally:
            self.running = False

    def stop(self):
        self.running = False
        logger.info("停止数据采集...")


# ------------------------- 入口 -------------------------

def main():
    print("=" * 80)
    print("华恒物流产线 PLC 数据采集器 - MQTT 发布版本 (仅 4 信号)")
    print("=" * 80)

    publisher = LogisticsPLCMQTTPublisher()
    try:
        if not publisher.connect_plc():
            print("无法连接到 PLC，程序退出")
            return
        if not publisher.connect_mqtt():
            print("⚠️  MQTT 连接失败，将在采集过程中持续重试...")

        interval = int(input("请输入采集间隔（秒，默认 2）: ").strip() or "2")
        batch_mode = input("是否批量发布所有站台数据？(y/n，默认 n): ").strip().lower() == 'y'
        publisher.collect_and_publish(interval, batch_mode)

    except KeyboardInterrupt:
        print("\n用户中断程序")
    finally:
        publisher.stop()
        publisher.disconnect_mqtt()
        publisher.disconnect_plc()


if __name__ == "__main__":
    main()
