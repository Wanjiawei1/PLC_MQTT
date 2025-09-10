const mysql = require('mysql2/promise');

// 数据库配置
const dbConfig = {
  host: process.env.DB_HOST || 'localhost',
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'huaheng_wuliu',
  port: process.env.DB_PORT || 3306,
  charset: 'utf8mb4',
  timezone: '+08:00',
  connectionLimit: 10,
  acquireTimeout: 60000,
  timeout: 60000
};

// 创建连接池
const pool = mysql.createPool(dbConfig);

// 初始化数据库和表
async function initDatabase() {
  try {
    console.log('🔄 正在初始化数据库...');
    
    // 创建数据库（如果不存在）
    const connection = await mysql.createConnection({
      host: dbConfig.host,
      user: dbConfig.user,
      password: dbConfig.password,
      port: dbConfig.port
    });
    
    await connection.execute(`CREATE DATABASE IF NOT EXISTS \`${dbConfig.database}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`);
    await connection.end();
    
    // 创建表结构
    await pool.execute(`
      CREATE TABLE IF NOT EXISTS station_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        station_index INT NOT NULL,
        occupied BOOLEAN NOT NULL,
        call_station BOOLEAN NOT NULL,
        type INT NOT NULL,
        old_station INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_station_index (station_index),
        INDEX idx_created_at (created_at)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    `);
    
    // 创建历史数据表（可选，用于数据分析）
    await pool.execute(`
      CREATE TABLE IF NOT EXISTS station_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        station_index INT NOT NULL,
        occupied BOOLEAN NOT NULL,
        call_station BOOLEAN NOT NULL,
        type INT NOT NULL,
        old_station INT NOT NULL,
        data_snapshot JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_station_index (station_index),
        INDEX idx_created_at (created_at)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    `);
    
    console.log('✅ 数据库初始化完成');
  } catch (error) {
    console.error('❌ 数据库初始化失败:', error);
    throw error;
  }
}

// 保存站台数据
async function saveStationData(stationData) {
  try {
    const query = `
      INSERT INTO station_data (station_index, occupied, call_station, type, old_station)
      VALUES (?, ?, ?, ?, ?)
      ON DUPLICATE KEY UPDATE
        occupied = VALUES(occupied),
        call_station = VALUES(call_station),
        type = VALUES(type),
        old_station = VALUES(old_station),
        updated_at = CURRENT_TIMESTAMP
    `;
    
    await pool.execute(query, [
      stationData.index,
      stationData.Occupied,
      stationData.CallStation,
      stationData.Type,
      stationData.OldStation
    ]);
    
    // 同时保存到历史记录表
    await pool.execute(
      `INSERT INTO station_history (station_index, occupied, call_station, type, old_station, data_snapshot) VALUES (?, ?, ?, ?, ?, ?)`,
      [
        stationData.index,
        stationData.Occupied,
        stationData.CallStation,
        stationData.Type,
        stationData.OldStation,
        JSON.stringify(stationData)
      ]
    );
    
  } catch (error) {
    console.error('保存站台数据失败:', error);
    throw error;
  }
}

// 批量保存站台数据
async function saveMultipleStationData(stationList) {
  const connection = await pool.getConnection();
  try {
    await connection.beginTransaction();
    
    for (const station of stationList) {
      await saveStationData(station);
    }
    
    await connection.commit();
    console.log(`✅ 批量保存 ${stationList.length} 条站台数据`);
  } catch (error) {
    await connection.rollback();
    console.error('批量保存站台数据失败:', error);
    throw error;
  } finally {
    connection.release();
  }
}

// 获取最新站台数据
async function getLatestStationData() {
  try {
    const [rows] = await pool.execute(`
      SELECT station_index as 'index', occupied as 'Occupied', call_station as 'CallStation', 
             type as 'Type', old_station as 'OldStation', updated_at
      FROM station_data 
      ORDER BY station_index ASC
    `);
    return rows;
  } catch (error) {
    console.error('获取站台数据失败:', error);
    throw error;
  }
}

// 获取站台历史数据
async function getStationHistory(stationIndex, limit = 100) {
  try {
    const [rows] = await pool.execute(`
      SELECT * FROM station_history 
      WHERE station_index = ? 
      ORDER BY created_at DESC 
      LIMIT ?
    `, [stationIndex, limit]);
    return rows;
  } catch (error) {
    console.error('获取站台历史数据失败:', error);
    throw error;
  }
}

// 关闭数据库连接
async function closeDatabase() {
  await pool.end();
  console.log('📴 数据库连接已关闭');
}

module.exports = {
  pool,
  initDatabase,
  saveStationData,
  saveMultipleStationData,
  getLatestStationData,
  getStationHistory,
  closeDatabase
};
