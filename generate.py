#!/usr/bin/env python3
"""
Generate new-api compatible pricing JSON for Chinese domestic model APIs.

All prices are based on DOMESTIC (China mainland) pricing in CNY.
本站计价单位 1 "$" = 1 CNY,故直接使用人民币原价,不做汇率换算;
利润由 new-api 的分组倍率承担(default 组 1.1 = 原价 +10%)。

Output format: new-api "type1" ratio_config (same as basellm/llm-metadata).

Usage:
    python3 generate.py > pricing.json
    # Or serve as static file at /api/pricing for new-api upstream sync
"""

import json
import sys
from dataclasses import dataclass, field

# ─── Configuration ───────────────────────────────────────────────────────────
# 站内货币口径:本站 1 "$" = 1 CNY(用户充值 10 元 → 账户记 10 $)。
# 所以模型价直接使用厂商官网的人民币原价,不做汇率换算。
# 若将来改成真美元计价,把此值改为汇率(如 7.3)即可,两处公式都会跟随。
CNY_PER_SITE_UNIT = 1.0
RATIO_BASE = 2.0     # new-api: model_ratio=1.0 corresponds to 2 站内单位/1M tokens

# ─── Data structures ─────────────────────────────────────────────────────────
@dataclass
class Tier:
    """一个阶梯档位。up_to=None 表示最高档(无上限)。价格单位:元/百万 Token。"""
    up_to: int | None
    input_cny: float
    output_cny: float
    cache_read_cny: float = 0


@dataclass
class ModelPricing:
    input_cny: float          # CNY per 1M input tokens
    output_cny: float         # CNY per 1M output tokens
    cache_read_cny: float = 0 # CNY per 1M cache-hit input tokens (0 = not applicable)
    tiers: list[Tier] = field(default_factory=list)  # 阶梯计价;填了就自动生成 billing_expr
    price_per_call_cny: float = 0  # 按次计费(图像生成等,元/张),走 model_price 而非 ratio
    billing_expr: str = ""    # DEPRECATED: 手写表达式,迁移期兼容,新条目一律用 tiers


def _tier_label(prev: int | None, up_to: int | None) -> str:
    fmt = lambda n: f"{n // 1000}k" if n % 1_000_000 else f"{n // 1_000_000}m"
    lo = fmt(prev) if prev else "0"
    return f"{lo}_{fmt(up_to)}" if up_to else f"{lo}_plus"


def build_tiered_expr(tiers: list[Tier]) -> str:
    """把结构化档位编译成 new-api 的 billing_expr。

    系数单位是「站内$/1M tokens」(见 new-api pkg/billingexpr/expr.md),
    在本站 1$=1CNY 的口径下就是官网人民币原价。
    手写这串表达式极易把档位阈值或价格抄错,所以一律由本函数生成。
    """
    parts, prev = [], None
    for t in tiers:
        terms = f"p * {t.input_cny / CNY_PER_SITE_UNIT:.6g} + c * {t.output_cny / CNY_PER_SITE_UNIT:.6g}"
        if t.cache_read_cny:
            terms += f" + cr * {t.cache_read_cny / CNY_PER_SITE_UNIT:.6g}"
        call = f'tier("{_tier_label(prev, t.up_to)}", {terms})'
        parts.append(call if t.up_to is None else f"len <= {t.up_to} ? {call} : ")
        prev = t.up_to
    return "".join(parts)


def cny_to_ratio(cny_per_1m: float) -> float:
    """Convert CNY/1M tokens to new-api model_ratio."""
    site_unit_per_1m = cny_per_1m / CNY_PER_SITE_UNIT
    return site_unit_per_1m / RATIO_BASE


def completion_ratio(input_cny: float, output_cny: float) -> float:
    """Calculate completion_ratio = output_price / input_price."""
    if input_cny == 0:
        return 1.0
    return output_cny / input_cny


def cache_ratio(input_cny: float, cache_cny: float) -> float:
    """Calculate cache_ratio = cache_hit_price / input_price."""
    if input_cny == 0 or cache_cny == 0:
        return 0
    return cache_cny / input_cny


# ─── Domestic CNY Pricing Database ───────────────────────────────────────────
# Official pricing page URLs (for verification):
#   DeepSeek:    https://api-docs.deepseek.com/zh-cn/quick_start/pricing
#   Qwen/百炼:   https://help.aliyun.com/zh/model-studio/billing-for-model-studio
#   GLM/智谱:    https://open.bigmodel.cn/pricing (JS渲染,需浏览器打开)
#   Doubao/方舟:  https://www.volcengine.com/docs/82379/1099320
#   Kimi/月之暗面: https://platform.kimi.com/docs/pricing
#   MiniMax:     https://platform.minimaxi.com/docs/guides/pricing-paygo
#   Hunyuan/腾讯: https://cloud.tencent.com/document/product/1729/97731
#   SiliconFlow:  https://siliconflow.cn/pricing
#
# ⚠️ Yi/零一万物: 平台已于 2025 年停服,模型仅通过百炼/SiliconFlow 等第三方可用
# ⚠️ Baichuan/百川: 定价页已 404,价格基于最后已知公开信息
#
# Last updated: 2026-08-27
# ⚠️ DeepSeek 自 2026-08-16 起分时计费,本文件使用高峰价(非高峰=50%)

MODELS: dict[str, ModelPricing] = {
    # ━━━ DeepSeek ━━━
    'deepseek-chat':                                ModelPricing(3.0, 9.0, 0.1),
    'deepseek-r1':                                  ModelPricing(4.0, 16.0, 1.0),
    'deepseek-r1-lite':                             ModelPricing(1.0, 4.0, 0.1),
    'deepseek-reasoner':                            ModelPricing(4.0, 16.0, 1.0),
    'deepseek-v4-flash':                            ModelPricing(3.0, 9.0, 0.1),
    'deepseek-v4-flash-vision-exp':                 ModelPricing(3.0, 9.0, 0.1),
    'deepseek-v4-pro':                              ModelPricing(9.0, 27.0, 0.3),

    # ━━━ DeepSeek 蒸馏版 (百炼托管) ━━━
    'deepseek-r1-distill-qwen-1.5b':                ModelPricing(0.0, 0.0),

    # ━━━ Qwen / 阿里云百炼 (北京站) ━━━
    'qwen-coder-turbo':                             ModelPricing(2.0, 6.0),
    'qwen-deep-research':                           ModelPricing(5.0, 15.0),
    'qwen-deep-research-2025-12-15':                ModelPricing(79.0, 236.0),
    'qwen-doc-turbo':                               ModelPricing(0.3, 0.5),
    'qwen-flash':                                   ModelPricing(0.15, 1.5, 0.03, tiers=[Tier(128000, 0.15, 1.5, 0.03), Tier(256000, 0.6, 6, 0.12), Tier(None, 1.2, 12, 0.24)]),
    'qwen-flash-character':                         ModelPricing(0.25, 1.5, 0.05),
    'qwen-flash-character-2026-02-26':              ModelPricing(0.18, 1.5, 0.036),
    'qwen-image-2.0':                               ModelPricing(0, 0, price_per_call_cny=0.2),
    'qwen-image-2.0-2026-03-03':                    ModelPricing(0, 0, price_per_call_cny=0.2),
    'qwen-image-2.0-pro':                           ModelPricing(0, 0, price_per_call_cny=0.5),
    'qwen-image-2.0-pro-2026-03-03':                ModelPricing(0, 0, price_per_call_cny=0.5),
    'qwen-image-2.0-pro-2026-04-22':                ModelPricing(0, 0, price_per_call_cny=0.5),
    'qwen-image-edit-max-2026-01-16':               ModelPricing(0, 0, price_per_call_cny=0.5),
    'qwen-image-edit-plus-2025-10-30':              ModelPricing(0, 0, price_per_call_cny=0.2),
    'qwen-image-edit-plus-2025-12-15':              ModelPricing(0, 0, price_per_call_cny=0.2),
    'qwen-image-plus-2026-01-09':                   ModelPricing(0, 0, price_per_call_cny=0.2),
    'qwen-long':                                    ModelPricing(0.5, 2.0),
    'qwen-math-plus':                               ModelPricing(4.0, 12.0),
    'qwen-math-turbo':                              ModelPricing(2.0, 6.0),
    'qwen-max':                                     ModelPricing(2.4, 9.6, 0.48),
    'qwen-max-latest':                              ModelPricing(2.0, 6.0, 0.4),
    'qwen-mt-flash':                                ModelPricing(0.7, 1.95),
    'qwen-mt-lite':                                 ModelPricing(0.6, 1.6),
    'qwen-mt-plus':                                 ModelPricing(1.8, 5.4),
    'qwen-mt-turbo':                                ModelPricing(0.7, 1.95),
    'qwen-omni-turbo-realtime':                     ModelPricing(4.0, 8.0),
    'qwen-plus':                                    ModelPricing(0.8, 2.0, 0.16, tiers=[Tier(128000, 0.8, 2, 0.16), Tier(256000, 2.4, 20, 0.48), Tier(None, 4.8, 48, 0.96)]),
    'qwen-plus-2025-01-25':                         ModelPricing(0.8, 2.0),
    'qwen-plus-2025-04-28':                         ModelPricing(0.8, 2.0),
    'qwen-plus-2025-07-14':                         ModelPricing(0.8, 2.0),
    'qwen-plus-2025-09-11':                         ModelPricing(0.8, 2.0),
    'qwen-plus-2025-12-01':                         ModelPricing(0.8, 2.0),
    'qwen-plus-character':                          ModelPricing(0.8, 2.0),
    'qwen-plus-character-ja':                       ModelPricing(0.8, 2.0),
    'qwen-plus-latest':                             ModelPricing(0.8, 2.0),
    'qwen-turbo':                                   ModelPricing(0.3, 0.6, 0.06),
    'qwen-turbo-latest':                            ModelPricing(0.3, 0.6, 0.06),
    'qwen-vl-max':                                  ModelPricing(1.6, 4.0),
    'qwen-vl-ocr':                                  ModelPricing(0.3, 0.5),
    'qwen-vl-ocr-2025-11-20':                       ModelPricing(0.3, 0.5),
    'qwen-vl-ocr-latest':                           ModelPricing(0.3, 0.5),
    'qwen-vl-plus':                                 ModelPricing(0.8, 2.0),
    'qwen2-5-14b-instruct':                         ModelPricing(0.5, 2.0),
    'qwen2-5-32b-instruct':                         ModelPricing(1.0, 4.0),
    'qwen2-5-72b-instruct':                         ModelPricing(2.0, 8.0),
    'qwen2-5-7b-instruct':                          ModelPricing(0.3, 1.2),
    'qwen2-5-coder-32b-instruct':                   ModelPricing(0.6, 1.8),
    'qwen2-5-coder-7b-instruct':                    ModelPricing(0.3, 0.6),
    'qwen2-5-math-72b-instruct':                    ModelPricing(1.0, 3.0),
    'qwen2-5-math-7b-instruct':                     ModelPricing(0.3, 0.6),
    'qwen2-5-omni-7b':                              ModelPricing(4.0, 4.0),
    'qwen2-5-vl-72b-instruct':                      ModelPricing(4.0, 12.0),
    'qwen2-5-vl-7b-instruct':                       ModelPricing(0.5, 1.5),
    'qwen3-14b':                                    ModelPricing(1.0, 4.0),
    'qwen3-235b-a22b':                              ModelPricing(2.0, 8.0),
    'qwen3-32b':                                    ModelPricing(2.0, 8.0),
    'qwen3-8b':                                     ModelPricing(0.5, 2.0),
    'qwen3-asr-flash':                              ModelPricing(0.12, 0.12),
    'qwen3-coder-30b-a3b-instruct':                 ModelPricing(0.5, 2.5, tiers=[Tier(32000, 0.3, 1.5), Tier(128000, 0.5, 2.5), Tier(None, 0.8, 4.0)]),
    'qwen3-coder-480b-a35b-instruct':               ModelPricing(6.0, 24.0, tiers=[Tier(32000, 6, 24), Tier(128000, 9, 36), Tier(None, 15, 60)]),
    'qwen3-coder-flash':                            ModelPricing(1.0, 4.0, tiers=[Tier(32000, 1, 4), Tier(128000, 1.5, 6), Tier(256000, 2.5, 10), Tier(None, 5, 25)]),
    'qwen3-coder-plus':                             ModelPricing(4.0, 16.0, tiers=[Tier(32000, 4, 16), Tier(128000, 6, 24), Tier(256000, 10, 40), Tier(None, 20, 200)]),
    'qwen3-livetranslate-flash-realtime':           ModelPricing(10.0, 38.0),
    'qwen3-max':                                    ModelPricing(2.5, 10.0, tiers=[Tier(32000, 2.5, 10), Tier(128000, 4, 16), Tier(None, 7, 28)]),
    'qwen3-max-latest':                             ModelPricing(2.0, 10.0, 0.4),
    'qwen3-next-80b-a3b-instruct':                  ModelPricing(1.0, 4.0),
    'qwen3-next-80b-a3b-thinking':                  ModelPricing(1.0, 10.0),
    'qwen3-vl-235b-a22b':                           ModelPricing(1.0, 4.0),
    'qwen3-vl-30b-a3b':                             ModelPricing(0.3, 1.2),
    'qwen3-vl-flash-2025-10-15':                    ModelPricing(0.15, 1.5),
    'qwen3-vl-flash-2026-01-22':                    ModelPricing(0.15, 1.5),
    'qwen3-vl-plus':                                ModelPricing(1.0, 10.0, tiers=[Tier(32000, 1, 10), Tier(128000, 1.5, 15), Tier(None, 3, 30)]),
    'qwen3-vl-plus-2025-12-19':                     ModelPricing(1.0, 10.0),
    'qwen3.5-122b-a10b':                            ModelPricing(0.8, 6.4, tiers=[Tier(128000, 0.8, 6.4), Tier(None, 2, 16)]),
    'qwen3.5-27b':                                  ModelPricing(0.6, 4.8, tiers=[Tier(128000, 0.6, 4.8), Tier(None, 1.8, 14.4)]),
    'qwen3.5-35b-a3b':                              ModelPricing(0.4, 3.2, tiers=[Tier(128000, 0.4, 3.2), Tier(None, 1.6, 12.8)]),
    'qwen3.5-397b-a17b':                            ModelPricing(1.2, 7.2, tiers=[Tier(128000, 1.2, 7.2), Tier(None, 3, 18)]),
    'qwen3.5-flash':                                ModelPricing(0.2, 2.0, tiers=[Tier(128000, 0.2, 2), Tier(256000, 0.8, 8), Tier(None, 1.2, 12)]),
    'qwen3.5-flash-2026-02-23':                     ModelPricing(0.2, 2.0),
    'qwen3.5-ocr':                                  ModelPricing(0.5, 2.0),
    'qwen3.5-plus':                                 ModelPricing(0.8, 4.8, tiers=[Tier(128000, 0.8, 4.8), Tier(256000, 2, 12), Tier(None, 4, 24)]),
    'qwen3.5-plus-2026-02-15':                      ModelPricing(0.8, 4.8),
    'qwen3.5-plus-2026-04-20':                      ModelPricing(0.8, 4.8),
    'qwen3.6-27b':                                  ModelPricing(3.0, 18.0),
    'qwen3.6-35b-a3b':                              ModelPricing(1.8, 10.8),
    'qwen3.6-flash':                                ModelPricing(1.2, 7.2, tiers=[Tier(256000, 1.2, 7.2), Tier(None, 4.8, 28.8)]),
    'qwen3.6-flash-2026-04-16':                     ModelPricing(1.2, 7.2),
    'qwen3.6-max-preview':                          ModelPricing(9.0, 54.0, tiers=[Tier(128000, 9, 54), Tier(None, 15, 90)]),
    'qwen3.6-plus':                                 ModelPricing(2.0, 12.0, tiers=[Tier(256000, 2, 12), Tier(None, 8, 48)]),
    'qwen3.6-plus-2026-04-02':                      ModelPricing(2.0, 12.0),
    'qwen3.7-flash':                                ModelPricing(0.06, 0.24, tiers=[Tier(32000, 0.06, 0.24, 0.006), Tier(256000, 0.18, 0.72, 0.018), Tier(None, 0.36, 1.44, 0.036)]),
    'qwen3.7-max':                                  ModelPricing(2.4, 9.6, 0.48),
    'qwen3.7-max-2026-05-17':                       ModelPricing(12.0, 36.0),
    'qwen3.7-max-2026-05-20':                       ModelPricing(12.0, 36.0),
    'qwen3.7-max-2026-06-08':                       ModelPricing(12.0, 36.0),
    'qwen3.7-max-preview':                          ModelPricing(12.0, 36.0),
    'qwen3.7-plus':                                 ModelPricing(2.0, 8.0, tiers=[Tier(256000, 2, 8), Tier(None, 6, 24)]),
    'qwen3.7-plus-2026-05-26':                      ModelPricing(2.0, 8.0),
    'qwen3.8-max':                                  ModelPricing(4.0, 12.0, 0.8),
    'qwq-plus':                                     ModelPricing(1.6, 4.0, 0.32),
    'qwq-plus-latest':                              ModelPricing(1.6, 4.0, 0.32),
    'tongyi-intent-detect-v3':                      ModelPricing(0.3, 0.6),

    # ⚠️ omni / realtime 系列**刻意不在此定价**,会落到 new-api 内置兜底 37.5。
    # 原因:这些模型按模态分别计价,音频价远高于文本价(qwen-omni-turbo 文本输入 0.4
    # 但音频输入 25 = 62 倍;qwen3-omni-flash 输出 纯文本 6.9 / 文本+音频 62.6),
    # 而本文件目前只能表达单一 token 价。按文本价上线 = 用户一传音频就亏几十倍。
    # 兜底价只是"贵到没人用",按文本价上线才是真亏 —— 失败方向不对称,故选择前者。
    # 正解:改用 new-api 的 audio_ratio / audio_completion_ratio 字段(上游同步已支持),
    # 待确认这两个字段的基准语义后再补。见 README「已知缺口」。

    # ━━━ GLM / 智谱 ━━━
    'glm-4.5':                                      ModelPricing(5.0, 10.0, 1.0),
    'glm-4.5-air':                                  ModelPricing(1.0, 5.0, 0.2),
    'glm-4.5-flash':                                ModelPricing(0.0, 0.0),
    'glm-4.5v':                                     ModelPricing(5.0, 10.0),
    'glm-4.6':                                      ModelPricing(5.0, 10.0, 1.0),
    'glm-4.6v':                                     ModelPricing(2.5, 5.0, 0.5),
    'glm-4.7':                                      ModelPricing(5.0, 10.0, 1.0),
    'glm-4.7-flash':                                ModelPricing(0.0, 0.0),
    'glm-4.7-flashx':                               ModelPricing(0.5, 2.0, 0.1),
    'glm-5':                                        ModelPricing(7.0, 14.0, 1.4),
    'glm-5-turbo':                                  ModelPricing(8.0, 16.0, 1.6),
    'glm-5.1':                                      ModelPricing(10.0, 20.0, 2.0),
    'glm-5.2':                                      ModelPricing(10.0, 20.0, 2.0),
    'glm-5.3':                                      ModelPricing(10.0, 20.0, 2.0),
    'glm-5.3-flash':                                ModelPricing(0.5, 1.0, 0.1),
    'glm-5v-turbo':                                 ModelPricing(8.0, 16.0, 1.6),
    'zai-glm-5-2':                                  ModelPricing(10.0, 20.0, 1.0),

    # ━━━ Doubao / 火山引擎 ━━━
    'doubao-1.5-pro-128k':                          ModelPricing(5.0, 9.0),
    'doubao-1.5-pro-256k':                          ModelPricing(5.0, 9.0),
    'doubao-1.5-pro-32k':                           ModelPricing(0.8, 2.0, 0.16),
    'doubao-1.5-thinking-pro':                      ModelPricing(4.0, 16.0, 1.0),
    'doubao-seed-1.6-lite':                         ModelPricing(0.3, 0.6),
    'doubao-seed-2.0-lite':                         ModelPricing(0.1, 0.5),
    'doubao-seed-2.0-mini':                         ModelPricing(0.2, 2.0),
    'doubao-seed-2.0-pro':                          ModelPricing(0.5, 2.5),
    'doubao-seed-2.1-pro':                          ModelPricing(2.5, 10.0, 0.5),
    'doubao-seed-code':                             ModelPricing(0.5, 2.0),

    # ━━━ Kimi / 月之暗面 ━━━
    'kimi-k2-0711-preview':                         ModelPricing(4.0, 16.0, 1.0),
    'kimi-k2-0905-preview':                         ModelPricing(4.0, 16.0, 1.0),
    'kimi-k2-thinking':                             ModelPricing(4.0, 20.0, 0.8),
    'kimi-k2-thinking-turbo':                       ModelPricing(8.0, 56.0, 1.0),
    'kimi-k2-turbo-preview':                        ModelPricing(16.0, 64.0, 4.0),
    'kimi-k2.5':                                    ModelPricing(4.0, 21.0, 0.7),
    'kimi-k2.6':                                    ModelPricing(7.0, 28.0, 1.4),
    'kimi-k2.7-code':                               ModelPricing(7.0, 28.0, 1.4),
    'kimi-k2.7-code-highspeed':                     ModelPricing(14.0, 56.0, 2.8),
    'kimi-k3':                                      ModelPricing(20.0, 100.0, 2.0),
    'moonshot-v1-128k':                             ModelPricing(6.0, 12.0),
    'moonshot-v1-32k':                              ModelPricing(2.0, 12.0),
    'moonshot-v1-8k':                               ModelPricing(1.0, 12.0),

    # ━━━ MiniMax ━━━
    'MiniMax-M2':                                   ModelPricing(2.1, 8.4, 0.21),
    'MiniMax-M2.1':                                 ModelPricing(2.1, 8.4, 0.21),
    'MiniMax-M2.1-highspeed':                       ModelPricing(4.2, 16.8, 0.21),
    'MiniMax-M2.5':                                 ModelPricing(2.1, 8.4, 0.21),
    'MiniMax-M2.5-highspeed':                       ModelPricing(4.2, 16.8, 0.21),
    'MiniMax-M2.7':                                 ModelPricing(2.1, 8.4, 0.42),
    'MiniMax-M2.7-highspeed':                       ModelPricing(4.2, 16.8, 0.42),
    'MiniMax-M3':                                   ModelPricing(2.0, 8.0, tiers=[Tier(512000, 2.1, 8.4, 0.42), Tier(None, 4.2, 16.8, 0.84)]),
    # ⚠️ 线上模型名是 'Minimax-M3'(小写 n),与其余 MiniMax-* 拼写不一致。
    # Go map 查找大小写敏感,只写一个拼写会让另一个静默落到 37.5 兜底价 → 两个都定价。
    # 价格填**原价**(官网标"永久五折",与其他限时折扣同样按原价口径,见 README)。
    'Minimax-M3':                                   ModelPricing(4.2, 16.8, 0.84, tiers=[Tier(512000, 4.2, 16.8, 0.84), Tier(None, 8.4, 33.6, 0.84)]),
    'MiniMax-M3':                                   ModelPricing(4.2, 16.8, 0.84, tiers=[Tier(512000, 4.2, 16.8, 0.84), Tier(None, 8.4, 33.6, 0.84)]),

    # ━━━ Baichuan ━━━
    'baichuan3-turbo':                              ModelPricing(1.0, 1.0),
    'baichuan3-turbo-128k':                         ModelPricing(5.0, 5.0),
    'baichuan4':                                    ModelPricing(10.0, 10.0),

    # ━━━ Yi / 01.AI ━━━
    'yi-large':                                     ModelPricing(3.0, 3.0),
    'yi-medium':                                    ModelPricing(0.5, 0.5),
    'yi-spark':                                     ModelPricing(0.0, 0.0),

    # ━━━ Hunyuan / 腾讯 ━━━
    'hunyuan-lite':                                 ModelPricing(0.0, 0.0),
    'hunyuan-pro':                                  ModelPricing(3.0, 10.0),
    'hunyuan-standard':                             ModelPricing(0.8, 2.0),
    'hunyuan-turbo':                                ModelPricing(1.5, 5.0),

    # ━━━ SiliconFlow 托管 ━━━
    'siliconflow/deepseek-r1-0528':                 ModelPricing(2.0, 8.72),
    'siliconflow/deepseek-v3-0324':                 ModelPricing(1.0, 4.0),
    'siliconflow/deepseek-v3.1-terminus':           ModelPricing(1.0, 3.7),
    'siliconflow/deepseek-v3.2':                    ModelPricing(1.0, 1.56),
}


# ─── Generate output ─────────────────────────────────────────────────────────
def generate() -> dict:
    model_ratio = {}
    completion_ratios = {}
    cache_ratios = {}
    billing_mode = {}
    billing_expr = {}
    model_price = {}

    for name, p in MODELS.items():
        # 按次计费(图像生成等):走 model_price,不参与 ratio 体系
        if p.price_per_call_cny:
            model_price[name] = round(p.price_per_call_cny / CNY_PER_SITE_UNIT, 6)
            continue

        # Skip free models
        if p.input_cny == 0 and p.output_cny == 0:
            model_ratio[name] = 0
            completion_ratios[name] = 1
            continue

        # 阶梯计价:表达式由档位结构自动生成,ratio 仅作预扣费估算的兜底
        if p.tiers:
            billing_mode[name] = "tiered_expr"
            billing_expr[name] = build_tiered_expr(p.tiers)

        model_ratio[name] = round(cny_to_ratio(p.input_cny), 6)
        completion_ratios[name] = round(completion_ratio(p.input_cny, p.output_cny), 6)

        if p.cache_read_cny > 0:
            cache_ratios[name] = round(cache_ratio(p.input_cny, p.cache_read_cny), 6)

    output = {
        "success": True,
        "message": "",
        "data": {
            "model_ratio": model_ratio,
            "completion_ratio": completion_ratios,
            "cache_ratio": cache_ratios,
            "billing_mode": billing_mode,
            "billing_expr": billing_expr,
            "model_price": model_price,
        }
    }
    return output


if __name__ == "__main__":
    result = generate()
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
