# new-api 国内站价格预设

为 new-api 生成国产模型**国内站 CNY 定价**的 ratio 配置,用于替代 basellm 官方预设(国际站 USD 定价)。

## 为什么需要这个

basellm/llm-metadata 官方预设源使用的是各模型的**国际站 USD 价格**。对于 DeepSeek、GLM、Kimi、MiniMax 等模型,国际价 ≈ 国内价/7.3,差异不大。但 **Qwen (阿里云)** 的国际站(新加坡)价格是国内站(北京)的 3~7 倍,如果你用的是国内站 API,直接用官方预设会严重高估成本。

## 覆盖的模型

| 厂商 | 模型数 | 来源 |
|------|--------|------|
| DeepSeek | 7 | api-docs.deepseek.com (CN) |
| Qwen/阿里云 | 30+ | help.aliyun.com 百炼 (北京站) |
| GLM/智谱 | 15 | open.bigmodel.cn |
| Doubao/火山引擎 | 10 | volcengine.com |
| Kimi/月之暗面 | 9 | platform.moonshot.cn |
| MiniMax | 3 | platform.minimaxi.com |
| Baichuan | 3 | platform.baichuan-ai.com |
| Yi/零一万物 | 3 | platform.lingyiwanwu.com |
| Hunyuan/腾讯 | 4 | cloud.tencent.com |

## 使用方式

### 方式一:作为自定义上游预设 URL

1. 生成 JSON:`python3 generate.py > pricing.json`
2. 将 `pricing.json` 部署到任意可访问的 HTTP 地址(GitHub Pages / Nginx / 对象存储)
3. new-api 后台 → 设置 → 模型定价 → 上游价格同步 → 添加自定义上游 → 填入 URL

### 方式二:直接 copy 到 new-api

1. 运行 `python3 generate.py`
2. 将输出的 `model_ratio` 和 `completion_ratio` 字段贴到 new-api 的模型倍率设置中

## 定价公式

```
model_ratio = 国内CNY价(元/百万token) ÷ 7.3 ÷ 2
completion_ratio = 输出价 ÷ 输入价
cache_ratio = 缓存命中价 ÷ 输入价
```

配合分组倍率 `7.3` 使用时:
```
用户显示消耗 = model_ratio × 2 × 7.3 = 国内CNY原价 ✓
```

## 更新

价格变动时编辑 `generate.py` 中的 `MODELS` 字典,重新运行即可。

各厂商定价页:
- DeepSeek: https://api-docs.deepseek.com/zh-cn/quick_start/pricing
- Qwen: https://help.aliyun.com/zh/model-studio/billing
- GLM: https://open.bigmodel.cn/pricing
- Doubao: https://www.volcengine.com/docs/82379/1099320
- Kimi: https://platform.moonshot.cn/docs/pricing
- MiniMax: https://platform.minimaxi.com/document/Price
