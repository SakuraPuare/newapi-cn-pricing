#!/usr/bin/env python3
"""
Generate new-api compatible pricing JSON for Chinese domestic model APIs.

All prices are based on DOMESTIC (China mainland) pricing in CNY,
then converted to USD using the configured exchange rate.

Output format: new-api "type1" ratio_config (same as basellm/llm-metadata).

Usage:
    python3 generate.py > pricing.json
    # Or serve as static file at /api/pricing for new-api upstream sync
"""

import json
import sys
from dataclasses import dataclass, field

# ─── Configuration ───────────────────────────────────────────────────────────
EXCHANGE_RATE = 7.3  # CNY per USD
RATIO_BASE = 2.0     # new-api: model_ratio=1.0 corresponds to $2/1M tokens

# ─── Data structures ─────────────────────────────────────────────────────────
@dataclass
class ModelPricing:
    input_cny: float          # CNY per 1M input tokens
    output_cny: float         # CNY per 1M output tokens
    cache_read_cny: float = 0 # CNY per 1M cache-hit input tokens (0 = not applicable)
    billing_expr: str = ""    # tiered billing expression (overrides ratio if set)


def cny_to_ratio(cny_per_1m: float) -> float:
    """Convert CNY/1M tokens to new-api model_ratio."""
    usd_per_1m = cny_per_1m / EXCHANGE_RATE
    return usd_per_1m / RATIO_BASE


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
    # https://api-docs.deepseek.com/zh-cn/quick_start/pricing
    # 2026-08-16 起分时计费: 高峰=下表, 非高峰=50%
    # 高峰: 周一至周五 9:00-12:00, 14:00-18:00 (北京时间)
    "deepseek-v4-flash":            ModelPricing(3.0,  9.0,  0.1),
    "deepseek-v4-flash-vision-exp": ModelPricing(3.0,  9.0,  0.1),
    "deepseek-v4-pro":              ModelPricing(9.0,  27.0, 0.3),
    "deepseek-r1":                  ModelPricing(4.0,  16.0, 1.0),
    "deepseek-r1-lite":             ModelPricing(1.0,  4.0,  0.1),
    "deepseek-chat":                ModelPricing(3.0,  9.0,  0.1),   # alias → v4-flash
    "deepseek-reasoner":            ModelPricing(4.0,  16.0, 1.0),   # alias → r1
    # SiliconFlow hosted DeepSeek
    # https://siliconflow.cn/pricing
    "siliconflow/deepseek-r1-0528":       ModelPricing(2.0, 8.72),
    "siliconflow/deepseek-v3-0324":       ModelPricing(1.0, 4.0),
    "siliconflow/deepseek-v3.1-terminus": ModelPricing(1.0, 3.7),
    "siliconflow/deepseek-v3.2":          ModelPricing(1.0, 1.56),

    # ━━━ Qwen / Alibaba Cloud (Beijing endpoint) ━━━
    # https://help.aliyun.com/zh/model-studio/billing-for-model-studio
    "qwen-turbo":                   ModelPricing(0.3,  0.6,  0.06),
    "qwen-turbo-latest":            ModelPricing(0.3,  0.6,  0.06),
    "qwen-plus":                    ModelPricing(0.8,  2.0,  0.16),
    "qwen-plus-latest":             ModelPricing(0.8,  2.0,  0.16),
    "qwen-plus-character":          ModelPricing(0.8,  2.0),
    "qwen-plus-character-ja":       ModelPricing(0.8,  2.0),
    "qwen-max":                     ModelPricing(2.0,  6.0,  0.4),
    "qwen-max-latest":              ModelPricing(2.0,  6.0,  0.4),
    "qwen-flash":                   ModelPricing(0.0,  0.0),  # free
    "qwen-long":                    ModelPricing(0.5,  2.0),
    "qwen-vl-plus":                 ModelPricing(0.8,  2.0),
    "qwen-vl-max":                  ModelPricing(2.0,  6.0),
    "qwen-vl-ocr":                  ModelPricing(0.5,  0.5),
    "qwen-math-plus":               ModelPricing(2.0,  6.0),
    "qwen-math-turbo":              ModelPricing(0.6,  1.2),
    "qwen-mt-plus":                 ModelPricing(2.0,  6.0),
    "qwen-mt-turbo":                ModelPricing(0.3,  0.6),
    "qwen-doc-turbo":               ModelPricing(0.3,  0.5),
    "qwen-deep-research":           ModelPricing(5.0,  15.0),
    "qwen-omni-turbo":              ModelPricing(4.0,  8.0),
    "qwen-omni-turbo-realtime":     ModelPricing(4.0,  8.0),
    "tongyi-intent-detect-v3":      ModelPricing(0.3,  0.6),
    "qwq-plus":                     ModelPricing(1.6,  4.0,  0.32),
    "qwq-plus-latest":              ModelPricing(1.6,  4.0,  0.32),
    # Qwen3 series (Beijing)
    "qwen3-235b-a22b":              ModelPricing(1.0,  4.0,  0.2),
    "qwen3-32b":                    ModelPricing(1.0,  4.0,  0.2),
    "qwen3-14b":                    ModelPricing(0.5,  2.0,  0.1),
    "qwen3-8b":                     ModelPricing(0.3,  1.2,  0.06),
    "qwen3-max":                    ModelPricing(2.0,  10.0, 0.4),
    "qwen3-max-latest":             ModelPricing(2.0,  10.0, 0.4),
    "qwen3-asr-flash":              ModelPricing(0.12, 0.12),
    "qwen3-next-80b-a3b-instruct":  ModelPricing(0.5,  2.0),
    "qwen3-next-80b-a3b-thinking":  ModelPricing(0.5,  6.0),
    "qwen3-omni-flash":             ModelPricing(3.0,  12.0),
    "qwen3-omni-flash-realtime":    ModelPricing(3.6,  14.0),
    "qwen3-livetranslate-flash-realtime": ModelPricing(10.0, 38.0),
    # Qwen3 VL (Beijing)
    "qwen3-vl-235b-a22b":           ModelPricing(1.0,  4.0),
    "qwen3-vl-30b-a3b":             ModelPricing(0.3,  1.2),
    "qwen3-vl-plus":                ModelPricing(0.8,  2.0),
    # Qwen3 Coder (Beijing, tiered pricing)
    "qwen3-coder-plus": ModelPricing(4.0, 16.0, billing_expr=(
        'len <= 32000 ? tier("0_32k", p * %.4f + c * %.4f) '
        ': len <= 128000 ? tier("32k_128k", p * %.4f + c * %.4f) '
        ': tier("128k_plus", p * %.4f + c * %.4f)' % (
            2.0/EXCHANGE_RATE, 10.0/EXCHANGE_RATE,
            4.0/EXCHANGE_RATE, 20.0/EXCHANGE_RATE,
            8.0/EXCHANGE_RATE, 40.0/EXCHANGE_RATE,
        )
    )),
    "qwen3-coder-flash": ModelPricing(1.0, 4.0, billing_expr=(
        'len <= 32000 ? tier("0_32k", p * %.4f + c * %.4f) '
        ': len <= 128000 ? tier("32k_128k", p * %.4f + c * %.4f) '
        ': tier("128k_plus", p * %.4f + c * %.4f)' % (
            0.5/EXCHANGE_RATE, 2.0/EXCHANGE_RATE,
            1.0/EXCHANGE_RATE, 4.0/EXCHANGE_RATE,
            2.0/EXCHANGE_RATE, 8.0/EXCHANGE_RATE,
        )
    )),
    "qwen3-coder-30b-a3b-instruct": ModelPricing(0.5, 2.5, billing_expr=(
        'len <= 32000 ? tier("0_32k", p * %.4f + c * %.4f) '
        ': len <= 128000 ? tier("32k_128k", p * %.4f + c * %.4f) '
        ': tier("128k_plus", p * %.4f + c * %.4f)' % (
            0.3/EXCHANGE_RATE, 1.5/EXCHANGE_RATE,
            0.5/EXCHANGE_RATE, 2.5/EXCHANGE_RATE,
            0.8/EXCHANGE_RATE, 4.0/EXCHANGE_RATE,
        )
    )),
    "qwen3-coder-480b-a35b-instruct": ModelPricing(1.5, 7.5, billing_expr=(
        'len <= 32000 ? tier("0_32k", p * %.4f + c * %.4f) '
        ': len <= 128000 ? tier("32k_128k", p * %.4f + c * %.4f) '
        ': tier("128k_plus", p * %.4f + c * %.4f)' % (
            1.5/EXCHANGE_RATE, 7.5/EXCHANGE_RATE,
            2.7/EXCHANGE_RATE, 13.5/EXCHANGE_RATE,
            4.5/EXCHANGE_RATE, 22.5/EXCHANGE_RATE,
        )
    )),
    # Qwen3.5 series (Beijing)
    "qwen3.5-27b":                  ModelPricing(0.5,  4.0),
    "qwen3.5-35b-a3b":             ModelPricing(0.3,  2.4),
    "qwen3.5-122b-a10b":           ModelPricing(0.5,  4.0),
    "qwen3.5-397b-a17b":           ModelPricing(0.8,  4.8),
    "qwen3.5-flash":               ModelPricing(0.15, 1.5),
    "qwen3.5-plus":                ModelPricing(0.5,  3.0),
    # Qwen3.6/3.7/3.8 series (Beijing, tiered)
    "qwen3.6-27b":                  ModelPricing(0.8,  4.8),
    "qwen3.6-35b-a3b":             ModelPricing(0.3,  1.8),
    "qwen3.6-flash":               ModelPricing(0.2,  1.2),
    "qwen3.6-max-preview":         ModelPricing(2.0,  12.0, 0.2),
    "qwen3.6-plus": ModelPricing(1.0, 6.0, billing_expr=(
        'len <= 256000 ? tier("0_256k", p * %.4f + c * %.4f + cr * %.4f) '
        ': tier("256k_plus", p * %.4f + c * %.4f + cr * %.4f)' % (
            1.0/EXCHANGE_RATE, 6.0/EXCHANGE_RATE, 0.2/EXCHANGE_RATE,
            4.0/EXCHANGE_RATE, 12.0/EXCHANGE_RATE, 0.8/EXCHANGE_RATE,
        )
    )),
    "qwen3.7-flash": ModelPricing(0.06, 0.24, billing_expr=(
        'len <= 32000 ? tier("0_32k", p * %.5f + c * %.5f + cr * %.6f) '
        ': len <= 256000 ? tier("32k_256k", p * %.5f + c * %.5f + cr * %.6f) '
        ': tier("256k_plus", p * %.5f + c * %.5f + cr * %.6f)' % (
            0.06/EXCHANGE_RATE, 0.24/EXCHANGE_RATE, 0.006/EXCHANGE_RATE,
            0.18/EXCHANGE_RATE, 0.72/EXCHANGE_RATE, 0.018/EXCHANGE_RATE,
            0.36/EXCHANGE_RATE, 1.44/EXCHANGE_RATE, 0.036/EXCHANGE_RATE,
        )
    )),
    "qwen3.7-plus": ModelPricing(1.0, 6.0, billing_expr=(
        'len <= 256000 ? tier("0_256k", p * %.4f + c * %.4f + cr * %.4f) '
        ': tier("256k_plus", p * %.4f + c * %.4f + cr * %.4f)' % (
            1.0/EXCHANGE_RATE, 6.0/EXCHANGE_RATE, 0.2/EXCHANGE_RATE,
            4.0/EXCHANGE_RATE, 12.0/EXCHANGE_RATE, 0.8/EXCHANGE_RATE,
        )
    )),
    "qwen3.7-max":                  ModelPricing(2.4,  9.6,  0.48),
    "qwen3.8-max":                  ModelPricing(4.0,  12.0, 0.8),
    # Qwen 2.5 open-weight hosted (Beijing)
    "qwen2-5-7b-instruct":          ModelPricing(0.3,  1.2),
    "qwen2-5-14b-instruct":         ModelPricing(0.5,  2.0),
    "qwen2-5-32b-instruct":         ModelPricing(1.0,  4.0),
    "qwen2-5-72b-instruct":         ModelPricing(2.0,  8.0),
    "qwen2-5-coder-7b-instruct":    ModelPricing(0.3,  0.6),
    "qwen2-5-coder-32b-instruct":   ModelPricing(0.6,  1.8),
    "qwen2-5-math-7b-instruct":     ModelPricing(0.3,  0.6),
    "qwen2-5-math-72b-instruct":    ModelPricing(1.0,  3.0),
    "qwen2-5-vl-7b-instruct":       ModelPricing(0.5,  1.5),
    "qwen2-5-vl-72b-instruct":      ModelPricing(4.0,  12.0),
    "qwen2-5-omni-7b":              ModelPricing(4.0,  4.0),

    # ━━━ GLM / Zhipu AI (domestic) ━━━
    # https://open.bigmodel.cn/pricing
    # https://bigmodel.cn/pricing (新域名)
    "glm-4.5-flash":                ModelPricing(0.0,  0.0),  # free
    "glm-4.7-flash":                ModelPricing(0.0,  0.0),  # free
    "glm-4.7-flashx":              ModelPricing(0.5,  2.0,   0.1),
    "glm-4.5-air":                  ModelPricing(1.0,  5.0,   0.2),
    "glm-4.5":                      ModelPricing(5.0, 10.0,   1.0),
    "glm-4.5v":                     ModelPricing(5.0, 10.0),
    "glm-4.6":                      ModelPricing(5.0, 10.0,   1.0),
    "glm-4.6v":                     ModelPricing(2.5, 5.0,    0.5),
    "glm-4.7":                      ModelPricing(5.0, 10.0,   1.0),
    "glm-5":                        ModelPricing(7.0, 14.0,   1.4),
    "glm-5-turbo":                  ModelPricing(8.0, 16.0,   1.6),
    "glm-5.1":                      ModelPricing(10.0, 20.0,  2.0),
    "glm-5.2":                      ModelPricing(10.0, 20.0,  2.0),
    "glm-5.3":                      ModelPricing(10.0, 20.0,  2.0),
    "glm-5.3-flash":                ModelPricing(0.5, 1.0,    0.1),
    "glm-5v-turbo":                 ModelPricing(8.0, 16.0,   1.6),
    "zai-glm-5-2":                  ModelPricing(10.0, 20.0,  1.0),  # Z.AI alias

    # ━━━ Doubao / Volcano Engine (domestic) ━━━
    # https://www.volcengine.com/docs/82379/1099320 (方舟按量计费)
    "doubao-seed-1.6-lite":         ModelPricing(0.3,  0.6),
    "doubao-1.5-pro-32k":           ModelPricing(0.8,  2.0,   0.16),
    "doubao-1.5-pro-128k":          ModelPricing(5.0,  9.0),
    "doubao-1.5-pro-256k":          ModelPricing(5.0,  9.0),
    "doubao-seed-2.0-lite":         ModelPricing(0.1,  0.5),
    "doubao-seed-2.0-mini":         ModelPricing(0.2,  2.0),
    "doubao-seed-2.0-pro":          ModelPricing(0.5,  2.5),
    "doubao-seed-2.1-pro":          ModelPricing(2.5, 10.0,   0.5),
    "doubao-seed-code":             ModelPricing(0.5,  2.0),
    "doubao-1.5-thinking-pro":      ModelPricing(4.0, 16.0,   1.0),

    # ━━━ Kimi / Moonshot (domestic, CNY) ━━━
    # https://platform.kimi.com/docs/pricing
    "moonshot-v1-8k":               ModelPricing(1.0, 12.0),
    "moonshot-v1-32k":              ModelPricing(2.0, 12.0),
    "moonshot-v1-128k":             ModelPricing(6.0, 12.0),
    "kimi-k2.5":                    ModelPricing(4.0, 20.0,   0.8),
    "kimi-k2.6":                    ModelPricing(7.0, 28.0,   1.4),
    "kimi-k2.7-code":               ModelPricing(7.0, 28.0,   1.4),
    "kimi-k2.7-code-highspeed":     ModelPricing(14.0, 56.0,  2.8),
    "kimi-k3":                      ModelPricing(20.0, 100.0, 2.0),
    "kimi-k2-thinking":             ModelPricing(4.0, 20.0,   0.8),
    "kimi-k2-thinking-turbo":       ModelPricing(8.0, 56.0,   1.0),
    "kimi-k2-turbo-preview":        ModelPricing(16.0, 64.0,  4.0),
    "kimi-k2-0711-preview":         ModelPricing(4.0, 16.0,   1.0),
    "kimi-k2-0905-preview":         ModelPricing(4.0, 16.0,   1.0),

    # ━━━ MiniMax (domestic, CNY) ━━━
    # https://platform.minimaxi.com/docs/guides/pricing-paygo
    "MiniMax-M2":                   ModelPricing(2.0,  8.0),
    "MiniMax-M2.1":                 ModelPricing(2.0,  8.0,   0.2),
    "MiniMax-M2.5":                 ModelPricing(2.0,  8.0,   0.2),
    "MiniMax-M2.5-highspeed":       ModelPricing(4.0,  16.0,  0.4),
    "MiniMax-M2.7":                 ModelPricing(2.0,  8.0,   0.4),
    "MiniMax-M2.7-highspeed":       ModelPricing(4.0,  16.0,  0.4),
    "MiniMax-M3": ModelPricing(2.0, 8.0, billing_expr=(
        'len <= 512000 ? tier("0_512k", p * %.4f + c * %.4f + cr * %.4f) '
        ': tier("512k_plus", p * %.4f + c * %.4f + cr * %.4f)' % (
            2.0/EXCHANGE_RATE, 8.0/EXCHANGE_RATE, 0.4/EXCHANGE_RATE,
            4.0/EXCHANGE_RATE, 16.0/EXCHANGE_RATE, 0.8/EXCHANGE_RATE,
        )
    )),

    # ━━━ Baichuan (domestic) ━━━
    # ⚠️ platform.baichuan-ai.com/price 已 404,价格基于最后已知公开信息
    "baichuan4":                    ModelPricing(10.0, 10.0),
    "baichuan3-turbo":              ModelPricing(1.0,  1.0),
    "baichuan3-turbo-128k":         ModelPricing(5.0,  5.0),

    # ━━━ Yi / 01.AI ━━━
    # ⚠️ 平台已于 2025 年停服,模型仅通过百炼/SiliconFlow 等第三方可用
    # 以下为最后已知价格,仅供参考
    "yi-large":                     ModelPricing(3.0,  3.0),
    "yi-medium":                    ModelPricing(0.5,  0.5),
    "yi-spark":                     ModelPricing(0.0,  0.0),  # free tier

    # ━━━ Hunyuan / Tencent (domestic) ━━━
    # https://cloud.tencent.com/document/product/1729/97731
    "hunyuan-lite":                 ModelPricing(0.0,  0.0),  # free
    "hunyuan-standard":             ModelPricing(0.8,  2.0),
    "hunyuan-pro":                  ModelPricing(3.0,  10.0),
    "hunyuan-turbo":                ModelPricing(1.5,  5.0),
}


# ─── Generate output ─────────────────────────────────────────────────────────
def generate() -> dict:
    model_ratio = {}
    completion_ratios = {}
    cache_ratios = {}
    billing_mode = {}
    billing_expr = {}

    for name, p in MODELS.items():
        # Skip free models
        if p.input_cny == 0 and p.output_cny == 0:
            model_ratio[name] = 0
            completion_ratios[name] = 1
            continue

        # If has tiered billing expression, use that instead of simple ratio
        if p.billing_expr:
            billing_mode[name] = "tiered_expr"
            billing_expr[name] = p.billing_expr
            # Still set fallback ratio for pre-consume estimation
            model_ratio[name] = round(cny_to_ratio(p.input_cny), 6)
            completion_ratios[name] = round(completion_ratio(p.input_cny, p.output_cny), 6)
        else:
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
        }
    }
    return output


if __name__ == "__main__":
    result = generate()
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
