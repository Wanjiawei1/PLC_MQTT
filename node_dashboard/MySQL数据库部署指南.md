# MySQL数据库部署指南 - 华恒物流监控系统

## 🗄️ 数据库架构

### 数据表结构

**主数据表 (`station_data`)**：
```sql
- id: 自增主键
- station_index: 站台序号
- occupied: 是否有货 (布尔值)
- call_station: 是否呼叫 (布尔值)  
- type: 类型
- old_station: 旧站台号
- created_at: 创建时间
- updated_at: 更新时间
```

**历史数据表 (`station_history`)**：
```sql
- id: 自增主键
- station_index: 站台序号
- occupied: 是否有货
- call_station: 是否呼叫
- type: 类型
- old_station: 旧站台号
- data_snapshot: 完整JSON数据快照
- created_at: 创建时间
```

## 📋 宝塔部署步骤

### 1. 安装MySQL数据库

1. **在宝塔面板 → 软件商店**
2. **搜索 "MySQL" → 安装 MySQL 5.7 或 8.0**
3. **设置root密码**（请记住此密码）
4. **启动MySQL服务**

### 2. 创建数据库和用户

登录宝塔MySQL管理界面：

```sql
-- 创建数据库
CREATE DATABASE huaheng_wuliu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建专用用户（推荐）
CREATE USER 'wuliu_user'@'localhost' IDENTIFIED BY '您的密码';
GRANT ALL PRIVILEGES ON huaheng_wuliu.* TO 'wuliu_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 配置环境变量

在宝塔 Node.js 项目设置中添加环境变量：

```bash
# 数据库配置
DB_HOST=localhost
DB_USER=wuliu_user
DB_PASSWORD=您设置的密码
DB_NAME=huaheng_wuliu
DB_PORT=3306

# 原有配置
PORT=5000
MQTT_BROKER=mqtt://Mqtt.dxiot.liju.cc
NODE_ENV=production
```

### 4. 安装新依赖

更新项目依赖：
```bash
cd /www/wwwroot/plc-dashboard
npm install
```

### 5. 重启服务

在宝塔 Node.js 项目管理中：
1. **停止** 当前服务
2. **启动** 服务
3. **查看日志** 确认数据库连接成功

### 成功日志示例：
```
🔄 正在初始化数据库...
✅ 数据库初始化完成
✓ MQTT connected
subscribed /dxiot/4q/pub/huaheng/wuliu
🚀 Dashboard listening on 5000
📊 MySQL数据库已连接，数据将持久化保存
```

## 🔍 数据验证

### 查看实时数据
```sql
-- 查看所有站台当前状态
SELECT * FROM station_data ORDER BY station_index;

-- 查看最近的历史记录
SELECT * FROM station_history ORDER BY created_at DESC LIMIT 10;
```

### 数据分析查询示例
```sql
-- 统计各站台有货情况
SELECT station_index, COUNT(*) as total_records,
       SUM(occupied) as occupied_count,
       SUM(call_station) as call_count
FROM station_history 
GROUP BY station_index;

-- 查看某站台24小时内的变化
SELECT * FROM station_history 
WHERE station_index = 1 
  AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY created_at DESC;
```

## 📊 新增功能特性

### ✅ **数据持久化**
- 所有MQTT数据自动保存到MySQL
- 服务器重启后数据不丢失
- 支持历史数据查询和分析

### ✅ **性能优化**  
- 使用连接池提高数据库性能
- 批量插入减少数据库压力
- 内存+数据库双重缓存

### ✅ **故障恢复**
- 服务重启时自动从数据库恢复最新状态
- 数据库连接失败不影响实时监控
- 优雅关闭保证数据完整性

## 🚨 注意事项

### 安全配置
1. **修改默认密码**：不要使用弱密码
2. **网络安全**：限制数据库访问权限
3. **备份策略**：定期备份数据库

### 性能监控
- 监控数据库连接数
- 检查磁盘空间使用
- 定期清理过期历史数据

### 清理历史数据示例
```sql
-- 删除30天前的历史记录
DELETE FROM station_history 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
```

## 🔧 故障排除

### Q: 数据库连接失败？
A: 检查环境变量配置，确认MySQL服务运行状态

### Q: 数据没有保存？
A: 查看服务器日志，检查数据库权限设置

### Q: 性能变慢？
A: 检查数据库索引，考虑清理历史数据

### Q: 内存使用过高？
A: 调整数据库连接池大小，优化查询语句

## 📈 扩展建议

1. **添加数据分析API**：提供RESTful接口查询历史数据
2. **数据可视化**：集成图表展示趋势分析
3. **报警功能**：基于历史数据设置异常报警
4. **数据导出**：支持CSV/Excel格式导出

现在您的华恒物流监控系统已经具备完整的数据持久化能力！
