import React, { useEffect, useRef } from 'react';

// 默认参数
const DEFAULT_ORIGIN = { keyword: '南开大学津南校区', city: '天津' };
const DEFAULT_DESTINATION = { keyword: '金逸影城（大港IMAX店）', city: '天津' };
const DEFAULT_CITY = '天津';
const DEFAULT_MODE = 'Driving';

// 动态加载JS
function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.head.appendChild(script);
  });
}

// 动态加载CSS
function loadCss(href) {
  return new Promise((resolve) => {
    if (document.querySelector(`link[href="${href}"]`)) {
      resolve();
      return;
    }
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.onload = () => resolve();
    document.head.appendChild(link);
  });
}

export default function AmapRouteBox({
  origin,
  destination = DEFAULT_DESTINATION,
  city = DEFAULT_CITY,
  mode = DEFAULT_MODE,
  amapjs_key = 'a64c3600e44f633e2af4fd8b0c8bb5eb',
  security_key = '57a82ef7ebde5553411673bc0ae7c6b2',
  style = { width: '100%', height: '500px' }
}) {
  const mapRef = useRef();
  const panelRef = useRef();
  const timerRef = useRef(null); // 防抖定时器

  // 标准化 origin，确保只有合法对象才认为有效，否则为 null，触发自动定位
  const safeOrigin =
    origin && typeof origin === 'object' && origin.keyword ? origin : null;

  useEffect(() => {
    // 防抖：等300ms后执行，避免依赖频繁变化导致重复执行
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (!destination || !amapjs_key || !security_key) {
        console.warn('必要参数缺失，停止渲染地图');
        return;
      }

      console.log('AmapRouteBox useEffect 触发，safeOrigin:', safeOrigin);
      console.log('mapRef.current 初始状态:', mapRef.current);
      // 配置安全密钥
      window._AMapSecurityConfig = { securityJsCode: security_key };

      // 等待 window.AMap 初始化完成的辅助函数
      async function waitForAMapReady(timeout = 5000) {
        const start = Date.now();
        return new Promise((resolve, reject) => {
          (function check() {
            if (window.AMap && typeof window.AMap.Map === 'function') {
              resolve();
            } else if (Date.now() - start > timeout) {
              reject(new Error('等待AMap初始化超时'));
            } else {
              setTimeout(check, 50);
            }
          })();
        });
      }

      // 动态加载高德主SDK、UI插件脚本和样式
      async function loadAmapResources() {
        try {
          // 主SDK
          await loadScript(`https://webapi.amap.com/maps?v=2.0&key=${amapjs_key}`);
          await waitForAMapReady();

          // UI插件和样式
          await Promise.all([
            loadScript('https://webapi.amap.com/ui/1.1/main.js'),
            loadCss('https://a.amap.com/jsapi_demos/static/demo-center/css/demo-center.css')
          ]);
          console.log('高德地图主SDK及UI插件加载完成');

          initMapWithLocation();
        } catch (e) {
          console.error('加载高德地图资源失败', e);
        }
      }

      function doRoute(realOrigin) {
        console.log('doRoute 被调用，realOrigin:', realOrigin);
        if (!mapRef.current) {
          console.error('地图容器未挂载，无法规划路线');
          return;
        }

        const rect = mapRef.current.getBoundingClientRect();
        console.log('rect的尺寸为:',rect)
        console.log('地图容器尺寸:', rect.width, rect.height);
        if (rect.width === 0 || rect.height === 0) {
          console.warn('地图容器尺寸为0，地图无法渲染');
        }

        // 清空地图和面板容器，防止多次渲染叠加
        mapRef.current.innerHTML = '';
        if (panelRef.current) panelRef.current.innerHTML = '';

        const map = new window.AMap.Map(mapRef.current, {
          resizeEnable: true,
          zoom: 13
        });
        console.log('地图实例创建:', map);
        window._debugMap = map; // 方便浏览器控制台调试

        map.on('complete', () => {
          console.log('地图加载完成事件触发');
        });
        map.on('error', (e) => {
          console.error('地图加载错误事件:', e);
        });

        const safeRealOrigin =
          realOrigin && typeof realOrigin === 'object' && realOrigin.keyword
            ? {
                keyword: realOrigin.keyword,
                city: String(realOrigin.city || DEFAULT_CITY)
              }
            : { ...DEFAULT_ORIGIN, city: String(DEFAULT_ORIGIN.city) };

        const safeDestination =
          destination && destination.keyword
            ? { keyword: destination.keyword, city: String(destination.city || DEFAULT_CITY) }
            : { ...DEFAULT_DESTINATION, city: String(DEFAULT_DESTINATION.city) };

        console.log('路线规划起点:', safeRealOrigin);
        console.log('路线规划终点:', safeDestination);
        console.log('路线规划模式:', mode);

        const pluginName =
          {
            Driving: 'AMap.Driving',
            Walking: 'AMap.Walking',
            Riding: 'AMap.Riding',
            TruckDriving: 'AMap.TruckDriving',
            Transfer: 'AMap.Transfer'
          }[mode] || 'AMap.Driving';

        window.AMap.plugin(pluginName, function () {
          console.log(`${pluginName} 插件加载完成，开始路线规划`);
          let planner;

          const panelOption = panelRef.current ? { panel: panelRef.current } : {};

          if (mode === 'Driving') planner = new window.AMap.Driving({ map, ...panelOption });
          else if (mode === 'Walking') planner = new window.AMap.Walking({ map, ...panelOption });
          else if (mode === 'Riding') planner = new window.AMap.Riding({ map, ...panelOption });
          else if (mode === 'TruckDriving') planner = new window.AMap.TruckDriving({ map, ...panelOption });
          else if (mode === 'Transfer') planner = new window.AMap.Transfer({ map, ...panelOption });

          if (planner) {
            console.log('开始调用 planner.search');
            planner.search([safeRealOrigin, safeDestination], function(status, result) {
              console.log('planner.search 回调，status=', status, 'result=', result);
              try {
                if (status === 'complete') {
                  console.log('路线规划成功', result);
                  // 地图和面板已由插件自动渲染
                } else {
                  console.error('路线规划失败', result);
                }
              } catch (e) {
                console.error('回调异常', e);
              }
            });
            console.log('planner.search 调用结束');
          } else {
            console.error('路线规划插件实例化失败');
          }
        });
      }

      function initMapWithLocation() {
        if (!mapRef.current) {
          console.error('地图容器未挂载，无法初始化地图');
          return;
        }
        mapRef.current.innerHTML = '';

        if (!safeOrigin) {
          console.log('无有效起点，执行自动定位流程');
          const map = new window.AMap.Map(mapRef.current, {
            resizeEnable: true,
            zoom: 13
          });

          map.plugin('AMap.Geolocation', function () {
            const geolocation = new window.AMap.Geolocation({
              enableHighAccuracy: true,
              timeout: 10000,
              zoomToAccuracy: true,
              needAddress: true
            });

            if (mapRef.current && geolocation) {
              map.addControl(geolocation);
            } else {
              console.error('地图容器或 geolocation 控件无效');
            }

            geolocation.getCurrentPosition(function (status, result) {
              if (status === 'complete') {
                // 优先用 building 字段作为 keyword
                const ac = result.addressComponent || {};
                const keyword = ac.building
                  || ac.street
                  || ac.district
                  || ac.township
                  || ac.city
                  || '南开大学津南校区';
                console.log('定位成功，地址信息:', ac);
                const cityName = ac.city || ac.province || DEFAULT_CITY;
                console.log('调用 doRoute，使用定位信息作为起点:', { keyword, city: cityName });
                doRoute({ keyword, city: String(cityName) });
              } else {
                console.warn('定位失败，使用默认起点');
                doRoute({ ...DEFAULT_ORIGIN, city: String(DEFAULT_ORIGIN.city) });
              }
            });
          });
        } else {
          console.log('有传 origin，直接规划路线:', safeOrigin);
          doRoute(safeOrigin);
        }
      }

      loadAmapResources();

      return () => {
        if (window.AMap && mapRef.current) {
          console.log('组件卸载，清空地图容器');
          mapRef.current.innerHTML = '';
        }
        if (panelRef.current) {
          panelRef.current.innerHTML = '';
        }
      };
    }, 300);

    // 清理定时器，防止内存泄漏
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [safeOrigin, destination, city, mode, amapjs_key, security_key]);

  return (
    <div style={{ display: 'flex', flexDirection: 'row', width: '100%' }}>
    <div
      ref={mapRef}
      style={{
        width: '70%',
        height: '500px',
        border: '1px solid #ccc',
        backgroundColor: '#f0f0f0',
      }}
    />
    <div
      ref={panelRef}
      style={{
        width: '30%',
        height: '500px',
        overflow: 'auto',
        border: '1px solid #eee',
      }}
    />
    </div>

  );
}
