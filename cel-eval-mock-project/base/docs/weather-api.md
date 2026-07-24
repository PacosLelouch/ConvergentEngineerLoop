# 天气 API 文档

## 接口说明

GET /weather?city={city}

## 响应格式

根据生产日志推断的真实响应格式：

### 正常响应

```json
{
    "main": {
        "temp": 22.5
    },
    "humidity": 65
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| main.temp | float | 当前温度（摄氏度） |
| humidity | int | 湿度百分比 (0-100) |

### 错误响应

```json
{
    "error": "city not found"
}
```

### 不完整响应（边界情况）

某些情况下响应可能缺少个别字段（如 humidity 缺失），此时对应字段使用默认值（温度 0.0，湿度 0）。
