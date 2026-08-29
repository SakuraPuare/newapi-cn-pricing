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

### 生成链(顺序固定)

```bash
python3 generate.py > pricing.json   # 1. 官网价 → ratio
python3 expand_aliases.py            # 2. 聚合平台别名(siliconflow/*、Pro/*)继承官方价
python3 snapshot_aliases.py          # 3. 日期快照(qwen-plus-2025-09-11)继承主版本价
```

第 3 步依赖 `models_live.txt`(线上模型名快照)。刷新它:

```bash
python3 snapshot_aliases.py --url https://<你的站>/api/pricing
```

⚠️ **第 3 步不是锦上添花,是防漏网**:new-api 查不到倍率会**静默**回落到内置兜底
`37.5`(≈ ¥75/1M),厂商每发一个日期快照就会多一个天价模型且无人察觉。
映射只在「剥掉日期后缀得到的 base 名已有价」时生成,误剥的名字自然被丢弃。

### 方式一:作为自定义上游预设 URL

1. 按上面的链生成 `pricing.json`
2. 将 `pricing.json` 部署到任意可访问的 HTTP 地址(GitHub Pages / Nginx / 对象存储)
3. new-api 后台 → 设置 → 模型定价 → 上游价格同步 → 添加自定义上游 → 填入 URL

### 方式二:直接 copy 到 new-api

1. 运行 `python3 generate.py`
2. 将输出的 `model_ratio` 和 `completion_ratio` 字段贴到 new-api 的模型倍率设置中

## 定价口径决定(2026-08-29 用户口径)

- **限时折扣一律填原价。** `qwen3.7-plus`(限时8折)、`qwen3.7-max`(限时5折)、
  `Minimax-M3`(永久5折)都按官网**原价**入库。理由:活动结束不会突然变成亏本卖。
- **思考模式输出价不单独处理。** `qwen-plus` 非思考输出 2 / 思考输出 8(差 4 倍),
  new-api 只有一个 `completion_ratio`,统一填**非思考价**。已知开思考模式会少收,
  用户明确表示不管这个。
- **老旧开源模型直接从渠道下架**,不猜价。2026-08-29 已下架 21 个
  (qwen1.5-*/qwen2-*/qwen-{1.8b,7b,14b,72b}-chat/codeqwen1.5-7b-chat/
  qwen-max-longcontext 等),这些在百炼官网已无定价页,历史调用数为 0。

## 已知缺口(会落到 new-api 内置兜底 37.5 ≈ ¥75/1M)

| 类别 | 数量 | 原因 |
|---|---|---|
| omni / realtime | 15 | 按模态分别计价,音频价是文本价数十倍,本文件只能表达单一 token 价 |
| TTS | ~12 | 按输入**字符**计价(0.8~1 元/万字符),非 token |
| ASR | ~4 | 按音频**秒**计价(0.00022~0.00033 元/秒),非 token |
| GLM-4.6 / 4.6v / 4.7 | 3 | 智谱定价页后端接口里查无此型号,需登控制台或问官方 |
| livetranslate | 5 | 官网只给 Token 换算率不给元单价 |

⚠️ **omni 是刻意留在兜底价的,不是遗漏**:`qwen-omni-turbo` 文本输入 0.4 而音频输入 25
(62 倍),按文本价上线 = 用户一传音频就真亏;兜底价只是"贵到没人用"。
**失败方向不对称,故选贵不选亏。** 正解是用 new-api 的 `audio_ratio` /
`audio_completion_ratio` 字段(上游同步已支持),待考证这两个字段的基准语义后再补。

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
