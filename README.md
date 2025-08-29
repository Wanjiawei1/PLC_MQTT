# PLC MQTT 数据采集系统

这是一个用于从西门子PLC的DB9000数据块读取数据并通过MQTT发送的Python系统。

## 功能特性

- **PLC数据读取**：支持读取DB9000中的各种数据类型
- **MQTT集成**：直接发送数据到MQTT服务器
- **智能优化**：只在数据发生变化时才上传，减少网络流量
- **多平台支持**：Windows和Linux环境
- **完整日志**：详细的操作日志和错误处理

## 支持的数据类型

1. **布尔值** (B1-B32): 地址 0.0 - 3.7
2. **字符串** (String[20]): 地址 4.0
3. **32位整数1** (DInt): 地址 26.0
4. **32位整数2** (DInt): 地址 30.0
5. **16位整数1** (Int): 地址 34.0
6. **16位整数2** (Int): 地址 36.0

## 文件说明

### 核心脚本
- `plc_mqtt_publisher.py` - 基础MQTT发布版本
- `plc_mqtt_publisher_optimized.py` - **优化版本**（只在数据变化时上传）
- `plc_logger.py` - 纯日志记录版本
- `complete_data_reader.py` - 完整数据读取器
- `quick_all_data_test.py` - 快速测试脚本

### 配置文件
- `config.py` - PLC和MQTT配置
- `requirements.txt` - Python依赖包
- `README.md` - 使用说明

## 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖包
- `python-snap7>=2.0.0` - 西门子PLC通信
- `paho-mqtt>=1.6.0` - MQTT客户端

## 使用方法

### 1. 基础MQTT发布版本
```bash
python plc_mqtt_publisher.py
```

### 2. 优化版本（推荐）
```bash
python plc_mqtt_publisher_optimized.py
```
**特点**：只在数据发生变化时才上传到MQTT，大大减少网络流量

### 3. 纯日志记录版本
```bash
python plc_logger.py
```

### 4. 快速测试
```bash
python quick_all_data_test.py
```

## 配置说明

### PLC配置
默认配置在脚本中：
- **IP地址**: 172.16.10.66
- **机架号**: 0
- **插槽号**: 1
- **DB块号**: 9000

### MQTT配置
默认配置：
- **服务器**: Mqtt.dxiot.liju.cc
- **端口**: 1883
- **发布主题**: /dxiot/4q/pub/huaheng/zudui
- **订阅主题**: /dxiot/4q/get/huaheng/zudui

### 环境变量支持
可以通过环境变量覆盖默认配置：
```bash
# MQTT配置
export MQTT_BROKER="your-mqtt-server.com"
export MQTT_PORT=1883
export MQTT_BROKER_IP="120.26.64.215"  # 绕过DNS解析
export MQTT_USERNAME="your-username"
export MQTT_PASSWORD="your-password"

# 运行程序
python plc_mqtt_publisher_optimized.py
```

## 数据格式

程序发送JSON格式数据到MQTT：

```json
{
  "timestamp": "2025-08-28 15:30:00",
  "device_id": "PLC_DB9000",
  "data": {
    "booleans": {
      "B1": true,
      "B2": false,
      "B3": true,
      ...
    },
    "string": "",
    "dint1": -2147483648,
    "dint2": 2147483647,
    "int1": -32768,
    "int2": 32767
  }
}
```

## Linux部署指南

### 1. 安装依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip build-essential git

# 安装snap7库
cd /tmp
wget https://sourceforge.net/projects/snap7/files/1.4.2/snap7-full-1.4.2.7z/download -O snap7.7z
sudo apt install p7zip-full
7z x snap7.7z
cd snap7-full-1.4.2/build/unix
make -f x86_64_linux.mk
sudo cp ../bin/x86_64-linux/libsnap7.so /usr/lib/
sudo ln -s /usr/lib/libsnap7.so /usr/lib/libsnap7.so.1
sudo ldconfig

# 安装Python依赖
pip3 install python-snap7 paho-mqtt
```

### 2. DNS配置（如果遇到解析问题）
```bash
# 方法1：使用环境变量绕过DNS
export MQTT_BROKER_IP="120.26.64.215"
python3 plc_mqtt_publisher_optimized.py

# 方法2：修复DNS
sudo systemctl enable --now systemd-resolved
sudo rm -f /etc/resolv.conf
sudo ln -s /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
sudo resolvectl dns enp2s0 223.5.5.5 114.114.114.114 8.8.8.8
sudo resolvectl flush-caches
```

### 3. 网络配置（如果PLC连接不通）
```bash
# 给网卡添加PLC网段地址
sudo ip addr add 172.16.10.203/24 dev enp2s0
sudo ip route add 172.16.10.0/24 dev enp2s0

# 测试连接
ping 172.16.10.66
nc -vz 172.16.10.66 102
```

### 4. 后台运行
```bash
# 使用nohup
nohup python3 plc_mqtt_publisher_optimized.py > plc_mqtt.log 2>&1 &

# 使用screen
screen -S plc_mqtt
python3 plc_mqtt_publisher_optimized.py
# Ctrl+A+D 分离screen
```

### 5. 系统服务（可选）
创建 `/etc/systemd/system/plc-mqtt.service`：
```ini
[Unit]
Description=PLC MQTT Publisher
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/plc-mqtt
ExecStart=/usr/bin/python3 /path/to/plc-mqtt/plc_mqtt_publisher_optimized.py
Restart=always
RestartSec=10
Environment=MQTT_BROKER_IP=120.26.64.215

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable plc-mqtt
sudo systemctl start plc-mqtt
sudo systemctl status plc-mqtt
```

## 优化版本特性

### 智能变化检测
- 使用MD5哈希算法比较数据
- 只比较实际数据内容，忽略时间戳
- 只在数据真正发生变化时才上传

### 统计信息
- 总读取次数
- 数据变化次数
- 发布成功次数
- 变化率统计

### 日志示例
```
2025-08-28 15:30:00 - INFO - 数据变化 #1 - 发布成功
2025-08-28 15:30:00 - INFO -   布尔值真值数量: 7/32
2025-08-28 15:30:00 - INFO -   字符串: ''
2025-08-28 15:30:00 - INFO -   DInt1: -2147483648, DInt2: 2147483647
2025-08-28 15:30:00 - INFO -   Int1: -32768, Int2: 32767

2025-08-28 15:30:20 - INFO - 数据未变化 - 总读取: 10, 变化发布: 1

2025-08-28 15:35:00 - INFO - 采集结束统计:
2025-08-28 15:35:00 - INFO -   总读取次数: 150
2025-08-28 15:35:00 - INFO -   数据变化次数: 3
2025-08-28 15:35:00 - INFO -   发布成功次数: 3
2025-08-28 15:35:00 - INFO -   变化率: 2.00%
```

## 故障排除

### 常见问题

1. **PLC连接失败**
   - 检查PLC IP地址是否正确
   - 确认PLC是否开机并运行
   - 检查网络连接和防火墙设置

2. **MQTT连接失败**
   - 检查MQTT服务器地址和端口
   - 使用环境变量 `MQTT_BROKER_IP` 绕过DNS问题
   - 确认网络能访问MQTT服务器

3. **DNS解析失败**
   - 使用 `MQTT_BROKER_IP` 环境变量
   - 修复系统DNS配置
   - 在 `/etc/hosts` 中添加IP映射

4. **权限问题**
   - 确保有足够的权限运行程序
   - 检查文件权限设置

### 调试命令
```bash
# 测试PLC连接
ping 172.16.10.66
nc -vz 172.16.10.66 102

# 测试MQTT连接
nc -vz Mqtt.dxiot.liju.cc 1883
nslookup Mqtt.dxiot.liju.cc

# 查看日志
tail -f plc_mqtt_publisher_optimized.log
```

## 许可证

本项目采用MIT许可证。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。 