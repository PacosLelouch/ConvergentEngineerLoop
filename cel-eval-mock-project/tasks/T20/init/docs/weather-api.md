# 天气 API 文档

## 接口说明

GET /weather?city={city}

## 响应格式

```json
{
    "temp": 22.5,
    "humidity": 65
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| temp | float | 当前温度（摄氏度） |
| humidity | int | 湿度百分比 (0-100) |

## 错误处理

如果城市不存在，API 返回标准 HTTP 404 状态码。
