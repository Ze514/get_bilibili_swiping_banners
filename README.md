# B站首页轮换广告收集

## 参数与用法

1. **--beacon_rate -> 控制每轮收集间隔（单位为分钟）**

2. **--test -> 决定是否以调试模式（ONE SHOT）运行：1代表使用，0代表不使用，默认值为0**

3. **--file -> 是否传入自定义的UA配置文件**

4. **--type -> 选择使用Chrome或Firefox**

## --file 模式下文件标准

```json
{
    "part": "path1";
    "all": "path2";
}
```


