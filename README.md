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

⚠️ **本站计价单位 1 "$" = 1 CNY**(用户充值 10 元 → 账户记 10 $),
所以**直接用人民币原价,不做汇率换算**。利润由 new-api 的**分组倍率**承担。

```
model_ratio      = 国内CNY价(元/百万token) ÷ 2      # RATIO_BASE=2
completion_ratio = 输出价 ÷ 输入价                  # 无量纲
cache_ratio      = 缓存命中价 ÷ 输入价              # 无量纲
billing_expr 系数 = 国内CNY价(元/百万token)         # 阶梯计费,单位是「站内$/1M」
```

new-api 侧的换算链(`pkg/billingexpr/settle.go`、`expr.md:244`):

```
显示价 = model_ratio × 2 × group_ratio
quota  = tokens × model_ratio × group_ratio          (输出再乘 completion_ratio)
阶梯   = exprOutput ÷ 1e6 × QuotaPerUnit × group_ratio
```

线上 `GroupRatio` 实测:`default=1.1`(原价 +10% 利润)、`official=7`、
`claude=0.2`、`codex=0.14`、`cc0=0.1`、`ccf=0.8`、`cckiro=0.06`、`ccmax=0.8`。

于是 default 组:`用户显示消耗 = CNY原价 × 1.1` ✓

⚠️ **别再除 7.3**。除了就变成只收原价的 15%(亏 6.6 倍)——
`CNY_PER_SITE_UNIT = 1.0` 这个常量就是唯一的口径开关,
若将来改成真美元计价,把它改成汇率即可,简单倍率与阶梯表达式两处都会跟随。

## 更新

价格变动时编辑 `generate.py` 中的 `MODELS` 字典,重新运行即可。

各厂商定价页:
- DeepSeek: https://api-docs.deepseek.com/zh-cn/quick_start/pricing
- Qwen: https://help.aliyun.com/zh/model-studio/billing
- GLM: https://open.bigmodel.cn/pricing
- Doubao: https://www.volcengine.com/docs/82379/1099320
- Kimi: https://platform.moonshot.cn/docs/pricing
- MiniMax: https://platform.minimaxi.com/document/Price
