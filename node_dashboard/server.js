// 加载环境变量
require('dotenv').config();

const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const mqtt = require('mqtt');
const { initDatabase, saveStationData, saveMultipleStationData, getLatestStationData, closeDatabase } = require('./config/database');
const { getStationName, getAllStationNames } = require('./config/station_names');

const MQTT_BROKER = process.env.MQTT_BROKER || 'mqtt://Mqtt.dxiot.liju.cc';
const MQTT_TOPIC = '/dxiot/4q/pub/huaheng/wuliu';

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.static('public'));

// API端点：获取所有站台名称
app.get('/api/stations', (req, res) => {
  res.json({
    success: true,
    data: getAllStationNames()
  });
});

io.on('connection', async (socket) => {
  console.log('client connected');
  try {
    // Send current snapshot if we already have data
    if (global.stationSnapshot && Object.keys(global.stationSnapshot).length > 0) {
      // 过滤只发送0-39范围内的站台数据
      const validStations = Object.values(global.stationSnapshot).filter(item => 
        Number.isInteger(item.index) && item.index >= 0 && item.index < 40
      );
      socket.emit('update', validStations);
    } else {
      // 如果内存中没有数据，从数据库加载最新数据
      const latestData = await getLatestStationData();
      if (latestData.length > 0) {
        // 重建内存快照，并添加站台名称（只处理0-39范围内的站台）
        const filteredData = latestData.filter(item => 
          Number.isInteger(item.index) && item.index >= 0 && item.index < 40
        );
        filteredData.forEach(item => {
          item.stationName = getStationName(item.index);
          global.stationSnapshot[item.index] = item;
        });
        socket.emit('update', filteredData);
        console.log(`📊 从数据库加载了 ${filteredData.length} 条有效站台数据`);
      }
    }
  } catch (error) {
    console.error('发送初始数据失败:', error);
  }
});

// MQTT client
const client = mqtt.connect(MQTT_BROKER);
global.stationSnapshot = {}; // {index: stationObj}
client.on('connect', () => {
  console.log('✓ MQTT connected');
  client.subscribe(MQTT_TOPIC);
  console.log('subscribed', MQTT_TOPIC);
});

client.on('message', async (topic, payload) => {
  try {
    console.log(`📨 收到MQTT消息 - 主题: ${topic}, 数据长度: ${payload.length}字节`);
    const data = JSON.parse(payload.toString());
    const list = Array.isArray(data) ? data : [data];
    console.log(`📥 解析MQTT数据: ${list.length}条记录`);
    
    let changed = false;
    const changedItems = [];
    
    list.forEach((item) => {
      const idx = item.index;
      console.log(`🔍 检查站台${idx}: 类型=${typeof idx}, 是整数=${Number.isInteger(idx)}`);
      
      // 只处理0-39范围内的站台
      if (!Number.isInteger(idx) || idx < 0 || idx >= 40) {
        console.log(`⚠️  跳过站台 ${idx}：超出范围0-39`);
        return;
      }
      
      // 添加站台名称
      item.stationName = getStationName(idx);
      
      // 调试信息：显示接收到的数据
      console.log(`📊 站台${idx}数据: Occupied=${item.Occupied}, CallStation=${item.CallStation}, Type=${item.Type}, OldStation=${item.OldStation}`);
      
      const prev = global.stationSnapshot[idx];
      if (JSON.stringify(prev) !== JSON.stringify(item)) {
        global.stationSnapshot[idx] = item;
        changedItems.push(item);
        changed = true;
      }
    });
    
    if (changed) {
      // 保存到数据库
      try {
        if (changedItems.length === 1) {
          await saveStationData(changedItems[0]);
        } else {
          await saveMultipleStationData(changedItems);
        }
        console.log(`💾 已保存 ${changedItems.length} 条数据到数据库`);
      } catch (dbError) {
        console.error('保存数据库失败:', dbError);
        // 即使数据库保存失败，仍然继续实时推送
      }
      
      // 推送到前端（只推送0-39范围内的站台）
      const validStations = Object.values(global.stationSnapshot).filter(item => 
        Number.isInteger(item.index) && item.index >= 0 && item.index < 40
      );
      io.emit('update', validStations);
    }
  } catch (e) {
    console.error('MQTT message error', e);
  }
});

// 初始化数据库
initDatabase().then(() => {
  const PORT = process.env.PORT || 5000;
  server.listen(PORT, () => {
    console.log(`🚀 Dashboard listening on ${PORT}`);
    console.log(`📊 MySQL数据库已连接，数据将持久化保存`);
  });
}).catch(error => {
  console.error('❌ 数据库初始化失败，无法启动服务:', error);
  process.exit(1);
});

// 优雅关闭
process.on('SIGINT', async () => {
  console.log('\n🔄 正在关闭服务...');
  try {
    await closeDatabase();
    process.exit(0);
  } catch (error) {
    console.error('关闭数据库连接失败:', error);
    process.exit(1);
  }
});

process.on('SIGTERM', async () => {
  console.log('\n🔄 正在关闭服务...');
  try {
    await closeDatabase();
    process.exit(0);
  } catch (error) {
    console.error('关闭数据库连接失败:', error);
    process.exit(1);
  }
});
