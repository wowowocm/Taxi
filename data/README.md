# 数据备份目录

## 目录结构

```
data/
├── raw/                    # 原始数据备份
│   └── 乘车出行数据源.csv   # 原始GPS数据 (1,601,307条)
├── processed/              # 清洗后数据备份
│   └── taxi_sz_cleaned.csv # 清洗后OD行程数据 (8,517条)
└── README.md               # 本文件
```

## 数据说明

### cleaned taxi_sz.csv 字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| VehicleNum | int | 车辆编号 |
| Stime | str | 行程开始时间 (HH:MM:SS) |
| SLng | float | 起点经度 |
| SLat | float | 起点纬度 |
| ELng | float | 终点经度 |
| ELat | float | 终点纬度 |
| Etime | str | 行程结束时间 (HH:MM:SS) |
| duration_min | float | 行程时长 (分钟) |
| distance_km | float | 行程距离 (公里) |
| avg_speed | float | 平均速度 (km/h) |

## 数据来源

- 原始GPS轨迹数据：500辆深圳出租车全天候定位记录
- 时间范围：00:00:00 ~ 23:59:59
- 空间范围：深圳市 (Lng: 113.5-114.5, Lat: 22.4-22.9)

## 更新日志

- 2026-06-27: 初始数据备份，清洗流水线首次运行
