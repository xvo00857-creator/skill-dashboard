/**
 * 数据层
 * 注意：以下全部为示例数据（非真实商品），仅用于演示响应式布局与交互状态。
 * 模拟 API 支持延迟、随机失败与超时，用于测试加载态、错误态和慢网络表现。
 */
(function (global) {
  "use strict";

  // 示例数据
  const PRODUCTS = [
    {
      id: "p001",
      name: "极光无线耳机",
      category: "音频",
      price: 899,
      stock: 42,
      status: "hot",
      icon: "🎧",
      desc: "主动降噪，40 小时续航，支持空间音频与多设备无缝切换。",
      specs: ["主动降噪 ANC", "40 小时续航", "蓝牙 5.3", "IPX5 防水"],
    },
    {
      id: "p002",
      name: "云感机械键盘",
      category: "外设",
      price: 659,
      stock: 18,
      status: "new",
      icon: "⌨️",
      desc: "Gasket 结构，热插拔轴座，三模连接，PBT 双色键帽。",
      specs: ["Gasket 结构", "热插拔", "三模连接", "RGB 背光"],
    },
    {
      id: "p003",
      name: "超轻便携笔记本",
      category: "电脑",
      price: 6999,
      stock: 7,
      status: "hot",
      icon: "💻",
      desc: "1.1kg 全金属机身，2.8K OLED 屏，全天候续航。",
      specs: ["1.1kg 重量", "2.8K OLED", "16GB 内存", "1TB 固态"],
    },
    {
      id: "p004",
      name: "智能运动手表",
      category: "穿戴",
      price: 1299,
      stock: 0,
      status: "normal",
      icon: "⌚",
      desc: "全天候健康监测，双频 GPS，14 天超长续航。",
      specs: ["双频 GPS", "心率血氧", "14 天续航", "5ATM 防水"],
    },
    {
      id: "p005",
      name: "4K 高清摄像头",
      category: "外设",
      price: 449,
      stock: 23,
      status: "normal",
      icon: "📷",
      desc: "4K 60fps 录制，自动对焦，内置降噪麦克风。",
      specs: ["4K 60fps", "自动对焦", "降噪麦克风", "隐私盖"],
    },
    {
      id: "p006",
      name: "降噪会议音箱",
      category: "音频",
      price: 1099,
      stock: 15,
      status: "new",
      icon: "🔊",
      desc: "360 度全向拾音，AI 降噪，适合 10 人会议室。",
      specs: ["360° 拾音", "AI 降噪", "USB-C 即插即用", "全双工通话"],
    },
    {
      id: "p007",
      name: "人体工学椅",
      category: "办公",
      price: 2399,
      stock: 9,
      status: "normal",
      icon: "🪑",
      desc: "自适应腰托，4D 扶手，全网布透气设计。",
      specs: ["自适应腰托", "4D 扶手", "全网布", "150kg 承重"],
    },
    {
      id: "p008",
      name: "27 英寸 4K 显示器",
      category: "电脑",
      price: 3299,
      stock: 12,
      status: "hot",
      icon: "🖥️",
      desc: "IPS 面板，99% sRGB，Type-C 90W 反向充电。",
      specs: ["4K IPS", "99% sRGB", "Type-C 90W", "HDR400"],
    },
    {
      id: "p009",
      name: "无线充电板",
      category: "配件",
      price: 199,
      stock: 0,
      status: "normal",
      icon: "🔋",
      desc: "15W 快充，兼容 Qi 协议，带异物检测。",
      specs: ["15W 快充", "Qi 协议", "异物检测", "超薄设计"],
    },
    {
      id: "p010",
      name: "便携投影仪",
      category: "影音",
      price: 4599,
      stock: 5,
      status: "new",
      icon: "📽️",
      desc: "1080P 物理分辨率，自动梯形校正，内置电池。",
      specs: ["1080P", "自动对焦", "自动梯形校正", "内置电池"],
    },
    {
      id: "p011",
      name: "蓝牙静音鼠标",
      category: "外设",
      price: 179,
      stock: 56,
      status: "normal",
      icon: "🖱️",
      desc: "静音按键，4000 DPI，多设备切换。",
      specs: ["静音按键", "4000 DPI", "三设备切换", "6 个月续航"],
    },
    {
      id: "p012",
      name: "USB-C 扩展坞",
      category: "配件",
      price: 349,
      stock: 31,
      status: "normal",
      icon: "🔌",
      desc: "11 合 1，双 4K 输出，千兆网口，100W PD。",
      specs: ["11 合 1", "双 4K", "千兆网口", "100W PD"],
    },
  ];

  const CATEGORIES = ["全部", "音频", "外设", "电脑", "穿戴", "办公", "配件", "影音"];

  // 网络模拟配置
  const networkConfig = {
    delay: 600,        // 基础延迟（毫秒）
    jitter: 400,       // 随机抖动
    failRate: 0,       // 失败概率 0-1
    timeout: 0,        // 超时阈值（0 表示不超时）
  };

  function setNetworkConfig(cfg) {
    Object.assign(networkConfig, cfg);
  }

  function getNetworkConfig() {
    return { ...networkConfig };
  }

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // 模拟 fetch：支持延迟、抖动、失败、超时
  function mockFetch(data, options) {
    const opts = options || {};
    const baseDelay = typeof opts.delay === "number" ? opts.delay : networkConfig.delay;
    const jitter = Math.random() * networkConfig.jitter;
    const wait = baseDelay + jitter;

    return new Promise((resolve, reject) => {
      let timer = null;
      let timedOut = false;

      if (networkConfig.timeout > 0 && wait > networkConfig.timeout) {
        timer = setTimeout(() => {
          timedOut = true;
          reject(new Error("请求超时，请检查网络后重试"));
        }, networkConfig.timeout);
      }

      setTimeout(() => {
        if (timedOut) return;
        if (timer) clearTimeout(timer);

        if (Math.random() < networkConfig.failRate) {
          reject(new Error("网络异常，数据加载失败"));
          return;
        }
        resolve(JSON.parse(JSON.stringify(data)));
      }, wait);
    });
  }

  const api = {
    async getProducts(params) {
      const p = params || {};
      let result = PRODUCTS.slice();

      if (p.keyword) {
        const kw = p.keyword.trim().toLowerCase();
        result = result.filter(
          (item) =>
            item.name.toLowerCase().includes(kw) ||
            item.desc.toLowerCase().includes(kw) ||
            item.category.toLowerCase().includes(kw)
        );
      }

      if (p.category && p.category !== "全部") {
        result = result.filter((item) => item.category === p.category);
      }

      if (p.sort === "price-asc") {
        result.sort((a, b) => a.price - b.price);
      } else if (p.sort === "price-desc") {
        result.sort((a, b) => b.price - a.price);
      } else if (p.sort === "stock") {
        result.sort((a, b) => b.stock - a.stock);
      }

      return mockFetch(result, { delay: p.delay });
    },

    async getProduct(id) {
      const product = PRODUCTS.find((item) => item.id === id);
      if (!product) {
        return mockFetch(null).then(() => {
          const err = new Error("未找到该产品");
          err.code = "NOT_FOUND";
          throw err;
        });
      }
      return mockFetch(product);
    },

    async getStats() {
      const stats = {
        total: PRODUCTS.length,
        inStock: PRODUCTS.filter((p) => p.stock > 0).length,
        categories: new Set(PRODUCTS.map((p) => p.category)).size,
        avgPrice: Math.round(
          PRODUCTS.reduce((sum, p) => sum + p.price, 0) / PRODUCTS.length
        ),
      };
      return mockFetch(stats);
    },

    getCategories() {
      return CATEGORIES.slice();
    },

    setNetworkConfig,
    getNetworkConfig,
  };

  global.DemoData = { PRODUCTS, CATEGORIES, api };
})(window);
