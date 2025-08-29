# DB9000_PA_PLC_DATA 数据读取脚本

这是一个用于从西门子PLC的DB9000数据块读取数据的Python脚本。

## 功能特性

- 连接到指定IP地址的西门子PLC
- 读取DB9000数据块中的各种数据类型
- 支持的数据类型：
  - 16位整数 (INT)
  - 32位整数 (DINT)
  - 浮点数 (REAL)
  - 字符串 (STRING)
  - 布尔值 (BOOL)
- 完整的日志记录
- 错误处理和连接管理

## 安装依赖

1. 确保已安装Python 3.6+
2. 安装依赖包：

```bash
pip install -r requirements.txt
```

### Windows用户注意事项

在Windows系统上，您可能需要安装snap7库的二进制文件：

1. 下载snap7库：https://sourceforge.net/projects/snap7/
2. 将snap7.dll文件复制到Python安装目录或系统PATH中

## 使用方法

### 基本使用

直接运行脚本：

```bash
python db9000_reader.py
```

### 自定义配置

修改脚本中的配置参数：

```python
# PLC配置
PLC_IP = "172.16.10.66"  # 修改为您的PLC IP地址
DB_NUMBER = 9000         # 修改为您的DB块号
```

### 在代码中使用

```python
from db9000_reader import DB9000Reader

# 创建读取器实例
reader = DB9000Reader("172.16.10.66")

# 连接到PLC
if reader.connect():
    # 读取数据
    data = reader.read_db_data(9000, 0, 100)
    
    # 读取特定数据类型
    int_value = reader.read_int16(9000, 0)
    real_value = reader.read_real(9000, 20)
    string_value = reader.read_string(9000, 30, 20)
    
    # 断开连接
    reader.disconnect()
```

## 数据读取方法

### 读取原始数据
```python
data = reader.read_db_data(db_number=9000, start=0, size=100)
```

### 读取特定数据类型
```python
# 16位整数
int16_value = reader.read_int16(9000, 0)

# 32位整数
int32_value = reader.read_int32(9000, 4)

# 浮点数
real_value = reader.read_real(9000, 8)

# 字符串
string_value = reader.read_string(9000, 30, 20)

# 布尔值
bool_value = reader.read_bool(9000, 0, 0)  # 读取第0字节的第0位
```

### 查看数据结构
```python
reader.print_data_structure(9000, 0, 100)  # 以十六进制格式显示数据
```

## 配置说明

### PLC连接参数
- `ip_address`: PLC的IP地址
- `rack`: 机架号（通常为0）
- `slot`: 插槽号（通常为1）

### 数据读取参数
- `db_number`: DB块号（默认9000）
- `start`: 起始字节地址
- `size`: 读取字节数

## 日志文件

脚本运行时会生成 `db9000_reader.log` 日志文件，记录：
- 连接状态
- 数据读取操作
- 错误信息
- 调试信息

## 故障排除

### 连接问题
1. 检查PLC IP地址是否正确
2. 确保网络连接正常
3. 检查防火墙设置
4. 验证PLC是否支持S7协议

### 数据读取问题
1. 确认DB块号正确
2. 检查起始地址和大小
3. 验证数据类型匹配

### Windows特定问题
1. 确保snap7.dll在系统PATH中
2. 以管理员权限运行
3. 检查防病毒软件是否阻止连接

## 示例输出

```
2024-01-01 10:00:00 - INFO - 正在连接到PLC: 172.16.10.66
2024-01-01 10:00:01 - INFO - 成功连接到PLC
2024-01-01 10:00:01 - INFO - 开始读取DB9000数据...
2024-01-01 10:00:01 - INFO - DB9000 数据结构 (起始地址: 0):
2024-01-01 10:00:01 - INFO - ==================================================
2024-01-01 10:00:01 - INFO - 0000: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F |................|
2024-01-01 10:00:01 - INFO - 0010: 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F |................|
2024-01-01 10:00:01 - INFO - ==================================================
2024-01-01 10:00:01 - INFO - 已断开PLC连接
```

## 许可证

本项目采用MIT许可证。 