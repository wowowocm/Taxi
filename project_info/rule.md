# 目的
## 该项目指在宿主机实现代码，然后再移动到虚拟机（centos7）上进行项目运行。

1. 软件版本
|组件|版本|
|JDK|1.8.0_261|
|Hadoop|3.3.1|
|Spark|3.5.2-bin-hadoop3|
|MySQL|8.0.13|
|Python|3.812|
|PySpark|3.5.2|

2. Python核心库
|pyspark|3.5.2|
|scikit-learn|1.3.2|
|pandas| 2.0.3|
|numpy|1.24.4|
|Flask|2.2.5|
|Pymysql|2.0.3|

# 代码风格
## 代码风格简洁，层次分明，注释清晰

## 折线图
option = {
  xAxis: {
    type: 'category',
    data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      data: [150, 230, 224, 218, 135, 147, 260],
      type: 'line'
    }
  ]
};

## 柱状图
option = {
  xAxis: {
    type: 'category',
    data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      data: [120, 200, 150, 80, 70, 110, 130],
      type: 'bar'
    }
  ]
};

## 饼图
option = {
  title: {
    text: 'Referer of a Website',
    subtext: 'Fake Data',
    left: 'center'
  },
  tooltip: {
    trigger: 'item'
  },
  legend: {
    orient: 'vertical',
    left: 'left'
  },
  series: [
    {
      name: 'Access From',
      type: 'pie',
      radius: '50%',
      data: [
        { value: 1048, name: 'Search Engine' },
        { value: 735, name: 'Direct' },
        { value: 580, name: 'Email' },
        { value: 484, name: 'Union Ads' },
        { value: 300, name: 'Video Ads' }
      ],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }
  ]
};

## 地理坐标图
function createChart() {
  var chRoughLatitude = 47;
  option = {
    title: {
      text: 'Travel Routes'
    },
    geo: {
      map: 'ch',
      roam: true,
      aspectScale: Math.cos((chRoughLatitude * Math.PI) / 180),
      // nameProperty: 'name_en', // If using en name.
      label: {
        show: true,
        textBorderColor: '#fff',
        textBorderWidth: 2
      }
    },
    tooltip: {},
    series: [
      {
        type: 'graph',
        coordinateSystem: 'geo',
        data: [
          { name: 'a', value: [7.667821250000001, 46.791734269956265] },
          { name: 'b', value: [7.404848750000001, 46.516308805996054] },
          { name: 'c', value: [7.376673125000001, 46.24728858538375] },
          { name: 'd', value: [8.015320625000001, 46.39460918238572] },
          { name: 'e', value: [8.616400625, 46.7020608630855] },
          { name: 'f', value: [8.869981250000002, 46.37539345234199] },
          { name: 'g', value: [9.546196250000001, 46.58676648282309] },
          { name: 'h', value: [9.311399375, 47.182454114178896] },
          { name: 'i', value: [9.085994375000002, 47.55395822835779] },
          { name: 'j', value: [8.653968125000002, 47.47709530818285] },
          { name: 'k', value: [8.203158125000002, 47.44506909144329] }
        ],
        edges: [
          {
            source: 'a',
            target: 'b'
          },
          {
            source: 'b',
            target: 'c'
          },
          {
            source: 'c',
            target: 'd'
          },
          {
            source: 'd',
            target: 'e'
          },
          {
            source: 'e',
            target: 'f'
          },
          {
            source: 'f',
            target: 'g'
          },
          {
            source: 'g',
            target: 'h'
          },
          {
            source: 'h',
            target: 'i'
          },
          {
            source: 'i',
            target: 'j'
          },
          {
            source: 'j',
            target: 'k'
          }
        ],
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 5,
        lineStyle: {
          color: '#718adbff',
          opacity: 1
        }
      }
    ]
  };
  myChart.setOption(option);
}
function fetchGeoJSON() {
  myChart.showLoading();
  $.get(ROOT_PATH + '/data/asset/geo/ch.geo.json', function (geoJSON) {
    echarts.registerMap('ch', geoJSON);
    createChart();
    myChart.hideLoading();
  });
}
fetchGeoJSON();

## 地理坐标图
function createChart() {
  var chRoughLatitude = 47;
  option = {
    title: {
      text: 'Travel Routes'
    },
    geo: {
      map: 'ch',
      roam: true,
      aspectScale: Math.cos((chRoughLatitude * Math.PI) / 180),
      // nameProperty: 'name_en', // If using en name.
      label: {
        show: true,
        textBorderColor: '#fff',
        textBorderWidth: 2
      }
    },
    tooltip: {},
    series: [
      {
        type: 'graph',
        coordinateSystem: 'geo',
        data: [
          { name: 'a', value: [7.667821250000001, 46.791734269956265] },
          { name: 'b', value: [7.404848750000001, 46.516308805996054] },
          { name: 'c', value: [7.376673125000001, 46.24728858538375] },
          { name: 'd', value: [8.015320625000001, 46.39460918238572] },
          { name: 'e', value: [8.616400625, 46.7020608630855] },
          { name: 'f', value: [8.869981250000002, 46.37539345234199] },
          { name: 'g', value: [9.546196250000001, 46.58676648282309] },
          { name: 'h', value: [9.311399375, 47.182454114178896] },
          { name: 'i', value: [9.085994375000002, 47.55395822835779] },
          { name: 'j', value: [8.653968125000002, 47.47709530818285] },
          { name: 'k', value: [8.203158125000002, 47.44506909144329] }
        ],
        edges: [
          {
            source: 'a',
            target: 'b'
          },
          {
            source: 'b',
            target: 'c'
          },
          {
            source: 'c',
            target: 'd'
          },
          {
            source: 'd',
            target: 'e'
          },
          {
            source: 'e',
            target: 'f'
          },
          {
            source: 'f',
            target: 'g'
          },
          {
            source: 'g',
            target: 'h'
          },
          {
            source: 'h',
            target: 'i'
          },
          {
            source: 'i',
            target: 'j'
          },
          {
            source: 'j',
            target: 'k'
          }
        ],
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 5,
        lineStyle: {
          color: '#718adbff',
          opacity: 1
        }
      }
    ]
  };
  myChart.setOption(option);
}
function fetchGeoJSON() {
  myChart.showLoading();
  $.get(ROOT_PATH + '/data/asset/geo/ch.geo.json', function (geoJSON) {
    echarts.registerMap('ch', geoJSON);
    createChart();
    myChart.hideLoading();
  });
}
fetchGeoJSON();

# 要求
1. 各功能模块进行分区（建立不同文件夹）利于维护
2. 每次进行修改和创建的文件再 /log 文件中保存（记录修改日志）
3. 每次bug修复也保存在 /log 中