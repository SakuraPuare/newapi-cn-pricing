#!/usr/bin/env python3
"""
Expand aggregator model aliases into pricing.json.

Reads pricing.json (official models only), applies MAPPINGS to generate
siliconflow/* and Pro/* entries that inherit from official model prices,
then writes back to pricing.json.

Usage: python3 expand_aliases.py
"""

import json

# ─── Aggregator → Official model mapping ─────────────────────────────────────
# Key = aggregator model name (as seen in new-api channel)
# Value = official model name (must exist in pricing.json)
#
# Rule: regardless of which platform you route through, the cost to YOU
# is the official provider's price. The aggregator is just a relay.

MAPPINGS = {
    # DeepSeek via SiliconFlow
    "siliconflow/deepseek-ai/DeepSeek-V4-Flash": "deepseek-v4-flash",
    "siliconflow/deepseek-ai/DeepSeek-V4-Pro": "deepseek-v4-pro",
    "siliconflow/deepseek-ai/DeepSeek-R1": "deepseek-reasoner",
    "siliconflow/deepseek-ai/DeepSeek-V3": "deepseek-v4-flash",
    "siliconflow/deepseek-ai/DeepSeek-V3.2": "deepseek-v4-flash",
    "siliconflow/deepseek-ai/DeepSeek-V3.1-Terminus": "deepseek-v4-flash",
    # GLM via SiliconFlow
    "siliconflow/zai-org/GLM-5.2": "glm-5.2",
    "siliconflow/zai-org/GLM-5": "glm-5",
    "siliconflow/zai-org/GLM-5V-Turbo": "glm-5v-turbo",
    "siliconflow/zai-org/GLM-4.5V": "glm-4.5v",
    "siliconflow/zai-org/GLM-4.5-Air": "glm-4.5-air",
    "siliconflow/THUDM/GLM-4-32B-0414": "glm-4.7-flash",
    "siliconflow/THUDM/GLM-Z1-32B-0414": "glm-4.7-flash",
    "siliconflow/THUDM/GLM-Z1-9B-0414": "glm-4.7-flash",
    # Kimi via SiliconFlow
    "siliconflow/moonshotai/Kimi-K3": "kimi-k3",
    "siliconflow/moonshotai/Kimi-K2.7-Code": "kimi-k2.7-code",
    "siliconflow/moonshotai/Kimi-K2.5": "kimi-k2.6",
    # MiniMax via SiliconFlow
    "siliconflow/MiniMaxAI/MiniMax-M3": "MiniMax-M3",
    "siliconflow/MiniMaxAI/MiniMax-M2.5": "MiniMax-M2.5",
    # Qwen via SiliconFlow
    "siliconflow/Qwen/Qwen3.6-35B-A3B": "qwen3.6-35b-a3b",
    "siliconflow/Qwen/Qwen3.6-27B": "qwen3.6-27b",
    "siliconflow/Qwen/Qwen3.5-397B-A17B": "qwen3.5-397b-a17b",
    "siliconflow/Qwen/Qwen3.5-122B-A10B": "qwen3.5-122b-a10b",
    "siliconflow/Qwen/Qwen3.5-35B-A3B": "qwen3.5-35b-a3b",
    "siliconflow/Qwen/Qwen3.5-27B": "qwen3.5-27b",
    "siliconflow/Qwen/Qwen3-Coder-480B-A35B-Instruct": "qwen3-coder-plus",
    "siliconflow/Qwen/Qwen3-235B-A22B": "qwen3-235b-a22b",
    "siliconflow/Qwen/Qwen3-32B": "qwen3-32b",
    "siliconflow/Qwen/Qwen3-30B-A3B": "qwen3-30b-a3b",
    "siliconflow/Qwen/Qwen3-14B": "qwen3-14b",
    "siliconflow/Qwen/Qwen3-8B": "qwen3-8b",
    "siliconflow/Qwen/QwQ-32B": "qwq-plus",
    "siliconflow/Qwen/Qwen2.5-72B-Instruct": "qwen-plus",
    "siliconflow/Qwen/Qwen2.5-7B-Instruct": "qwen-turbo",
    # Hunyuan via SiliconFlow
    "siliconflow/tencent/Hunyuan-A13B-Instruct": "hunyuan-a13b",
    # Pro/ = same mapping, high-speed channel
    "Pro/deepseek-ai/DeepSeek-V4-Flash": "deepseek-v4-flash",
    "Pro/deepseek-ai/DeepSeek-V4-Pro": "deepseek-v4-pro",
    "Pro/deepseek-ai/DeepSeek-R1": "deepseek-reasoner",
    "Pro/deepseek-ai/DeepSeek-V3": "deepseek-v4-flash",
    "Pro/deepseek-ai/DeepSeek-V3.2": "deepseek-v4-flash",
    "Pro/deepseek-ai/DeepSeek-V3.1-Terminus": "deepseek-v4-flash",
    "Pro/zai-org/GLM-5.1": "glm-5.1",
    "Pro/moonshotai/Kimi-K2.6": "kimi-k2.6",
    "Pro/MiniMaxAI/MiniMax-M2.5": "MiniMax-M2.5",
    "Pro/Qwen/Qwen3-235B-A22B": "qwen3-235b-a22b",
}


def main():
    with open("pricing.json") as f:
        data = json.load(f)

    mr = data["data"]["model_ratio"]
    cr = data["data"]["completion_ratio"]
    ca = data["data"]["cache_ratio"]

    # Remove existing aggregator entries (will regenerate)
    for section in (mr, cr, ca):
        to_del = [k for k in section if k.startswith("siliconflow/") or k.startswith("Pro/")]
        for k in to_del:
            del section[k]

    # Generate from mappings
    added = 0
    missing = []
    for alias, official in MAPPINGS.items():
        if official not in mr:
            missing.append(f"{alias} → {official}")
            continue
        mr[alias] = mr[official]
        if official in cr:
            cr[alias] = cr[official]
        if official in ca:
            ca[alias] = ca[official]
        added += 1

    with open("pricing.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Added {added} aggregator aliases")
    if missing:
        print(f"WARNING: {len(missing)} mappings point to missing official models:")
        for m in missing:
            print(f"  {m}")


if __name__ == "__main__":
    main()
