/**
 * 华恒物流站台名称映射配置
 * 站台索引从0开始，对应40个站台的中文名称
 */

const STATION_NAMES = {
  0: "1号膜式璧焊接单站",
  1: "2号缓存台", 
  2: "3号自动烟管焊01",
  3: "4号自动烟管焊02",
  4: "5号自动烟管焊03", 
  5: "6号自动烟管焊04",
  6: "7号自动烟管焊05",
  7: "8号自动烟管焊06", 
  8: "9号自动烟管焊07",
  9: "10号自动烟管焊08",
  10: "11号缓存台",
  11: "12号缓存台",
  12: "13号缓存台", 
  13: "14号缓存台",
  14: "15号缓存台",
  15: "16号缓存台",
  16: "17号对接站台",
  17: "18号备用",
  18: "19号备用", 
  19: "20号备用",
  20: "21号上料台",
  21: "22号穿管1",
  22: "23号穿管2",
  23: "24号视觉检测",
  24: "25号缓存台",
  25: "26号缓存台",
  26: "27号缓存台",
  27: "28号缓存台", 
  28: "29号缓存台",
  29: "30号缓存台",
  30: "31号缓存台",
  31: "32号缓存台",
  32: "33号查漏1",
  33: "34号查漏2",
  34: "35号备用",
  35: "36号备用",
  36: "37号备用", 
  37: "38号备用",
  38: "39号备用",
  39: "40号备用"
};

/**
 * 获取站台名称
 * @param {number} index - 站台索引 (0-39)
 * @returns {string} 站台名称
 */
function getStationName(index) {
  return STATION_NAMES[index] || `${index + 1}号未命名站台`;
}

/**
 * 获取所有站台名称映射
 * @returns {Object} 完整的站台名称映射对象
 */
function getAllStationNames() {
  return { ...STATION_NAMES };
}

/**
 * 检查索引是否有效
 * @param {number} index - 站台索引
 * @returns {boolean} 是否为有效索引
 */
function isValidStationIndex(index) {
  return Number.isInteger(index) && index >= 0 && index < 40;
}

module.exports = {
  STATION_NAMES,
  getStationName,
  getAllStationNames,
  isValidStationIndex
};
