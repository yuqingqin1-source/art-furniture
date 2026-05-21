#!/usr/bin/env python3
"""Build the data payload for the static VOC report site."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "voc_report_site" / "data.js"
DATA_ROOT = ROOT if (ROOT / "outputs").exists() else Path("/Users/qing/Documents/New project")


TAXONOMY = {
    "外观审美": {
        "desc": "造型、颜色、风格、空间装饰效果，以及商品图片带来的第一视觉判断。",
        "keywords": ["beautiful", "gorgeous", "cute", "stylish", "design", "modern", "sleek", "color"],
    },
    "艺术感/收藏感": {
        "desc": "是否具有雕塑感、作品感、话题感，能否成为空间中的视觉焦点。",
        "keywords": ["art", "work of art", "sculptural", "statement piece", "showstopper", "iconic", "classic", "replica"],
    },
    "材质质感": {
        "desc": "木纹、皮革、布料、金属、塑料、饰面等真实触感和视觉质感。",
        "keywords": ["wood", "grain", "leather", "boucle", "fabric", "plastic", "metal", "finish"],
    },
    "做工质量": {
        "desc": "稳固性、耐用性、瑕疵、破损、结构安全和整体制造质量。",
        "keywords": ["quality", "sturdy", "solid", "durable", "broken", "cracked", "wobbly", "fragile"],
    },
    "尺寸与空间适配": {
        "desc": "大小、高矮、宽窄、重量和与客厅、卧室、阳台等场景的匹配。",
        "keywords": ["size", "small", "large", "short", "height", "space", "room", "fit"],
    },
    "舒适度/实用性": {
        "desc": "坐感、软硬、功能性、旋转、叠放、日常使用效率和便利程度。",
        "keywords": ["comfortable", "comfy", "sit", "seat", "firm", "soft", "functional", "swivel"],
    },
    "物流包装": {
        "desc": "发货速度、包装保护、到货破损、退换货和开箱体验。",
        "keywords": ["shipping", "delivery", "arrived", "packaged", "box", "replacement", "carrier"],
    },
    "安装体验": {
        "desc": "是否免安装、安装步骤、配件、说明书和组装难度。",
        "keywords": ["assemble", "assembly", "install", "instructions", "screw", "hardware", "unbox"],
    },
    "价格价值感": {
        "desc": "价格是否匹配材质、设计、品牌、耐用性和整体获得感。",
        "keywords": ["price", "value", "worth", "overpriced", "great buy", "for the money", "investment", "quality-price"],
    },
    "情绪价值": {
        "desc": "喜欢、惊喜、推荐、满意、空间氛围提升等主观愉悦反馈。",
        "keywords": ["love", "happy", "amazing", "perfect", "recommend", "favorite", "stunning"],
    },
    "照片与实物差异": {
        "desc": "图片、颜色、比例、材质、描述与实物到手后的预期一致性，包括如图、如描述、符合或超出预期。",
        "keywords": ["picture", "photo", "as pictured", "as described", "expected", "different", "actual", "works perfectly"],
    },
    "未归类": {
        "desc": "现有词典未充分覆盖的评论，可作为下一轮标签扩展池。",
        "keywords": [],
    },
}

SCENE_PATTERNS = {
    "客厅/起居室": {
        "keywords": ["living room", "lounge", "family room"],
        "takeaway": "艺术家具在客厅中承担“空间焦点”和风格升级角色，消费者高频提到 stylish、unique、sophistication。",
        "strategy": "商品页应展示沙发旁、边几、单椅组合等完整客厅搭配，突出 statement piece 与装饰性。",
    },
    "餐厅/餐椅": {
        "keywords": ["dining", "kitchen", "table chair"],
        "takeaway": "餐厅场景同时关注造型和坐感，部分用户会把装饰椅作为餐桌补充座位。",
        "strategy": "补充餐桌高度、坐深、靠背角度和多人使用图，避免“好看但不适合餐桌”的落差。",
    },
    "民宿/商业空间": {
        "keywords": ["airbnb", "rental", "business", "studio", "photo studio", "shoots", "office", "lobby"],
        "takeaway": "商业场景评分最高，用户看重出片、吸睛和快速形成空间记忆点。",
        "strategy": "沉淀民宿、影棚、办公室前厅等商业模板，强调耐用、免安装、好拍照和社媒传播价值。",
    },
    "卧室/床头": {
        "keywords": ["bedroom", "bedside", "nightstand", "bed room", "guest bedroom"],
        "takeaway": "床头和客卧场景偏好小体量边几、舒适单椅和柔和材质，但对包装破损更敏感。",
        "strategy": "展示床边尺度参照、夜灯/书本摆放图和开箱保护说明，降低卧室场景的尺寸误判。",
    },
    "小空间/角落": {
        "keywords": ["small space", "corner", "apartment", "compact", "nook"],
        "takeaway": "小空间用户需要艺术感，但也担心过宽、过矮或无法靠墙摆放。",
        "strategy": "给出最小摆放面积、靠墙距离、转身空间和公寓场景图，帮助用户快速判断能否放下。",
    },
    "阳台/户外": {
        "keywords": ["balcony", "outdoor", "patio", "deck", "porch", "garden", "weather"],
        "takeaway": "户外/阳台评论强调轻便、叠放、耐候和颜色表现，也会质疑塑料感与承重安全。",
        "strategy": "把耐候、叠放、搬运重量和户外材质维护讲清楚，同时避免把轻便误读为廉价。",
    },
}

UNMET_NEED_PATTERNS = {
    "尺寸需要更直观": {
        "keywords": ["too small", "very small", "mini", "short", "shorter", "height", "measure", "smaller than expected", "larger than expected"],
        "root": "消费者在下单前难以把商品尺寸转化为空间里的真实比例。",
        "action": "标题区前置关键尺寸，增加真人/沙发/床边比例图和“适合/不适合”空间提示。",
    },
    "材质需要更有高级感": {
        "keywords": ["cheap", "plastic", "material", "not good material", "feels very cheap", "quality", "finish"],
        "root": "艺术造型拉高了用户对材质和工艺的预期，塑料感、掉漆、开裂会快速拉低价值判断。",
        "action": "补充材质微距、重量、表面工艺、耐磨测试和真实用户图，解释价格背后的设计与工艺价值。",
    },
    "包装与到货需要更可靠": {
        "keywords": ["damaged", "broken", "scratches", "scratch", "box", "packaging", "replacement", "arrived damaged"],
        "root": "大件/异形艺术家具在运输中容易破损，负面评论集中在开箱即损和二次补发失败。",
        "action": "升级边角保护、内衬固定和外箱强度；对高破损 SKU 建立极速补发和免回寄策略。",
    },
    "实物需要更接近图片": {
        "keywords": ["picture", "photo", "as pictured", "different", "not exactly as described", "color", "ivory", "orange"],
        "root": "颜色、材质光泽和比例在图片中被美化后，会造成到手落差。",
        "action": "提供自然光/室内光多光源图、用户实拍、色卡对比和“可能存在色差”的具体说明。",
    },
    "退换货需要更低摩擦": {
        "keywords": ["return", "refund", "replacement", "customer service", "exchange"],
        "root": "大件退货成本高，一旦尺寸或破损问题出现，用户会把售后难度纳入整体差评。",
        "action": "在购买前明确退换货费用和大件处理方式；对破损、错发、严重色差设置低门槛售后。",
    },
    "坐感与实用性需要更明确": {
        "keywords": ["uncomfortable", "firm", "hard", "sit", "seat", "comfortable", "back rest", "support"],
        "root": "用户既想要雕塑感，也需要知道它能不能久坐、靠背是否支撑、餐桌高度是否适配。",
        "action": "补充坐高、坐深、靠背角度、软硬等级、承重和典型使用时长建议。",
    },
}

PURCHASE_CONCERN_PATTERNS = {
    "外观设计": {
        "keywords": ["beautiful", "gorgeous", "stylish", "design", "modern", "sleek", "look", "looks", "color", "decor"],
        "description": "购买前最先判断是否好看、是否符合空间风格、颜色是否能成为视觉亮点。",
    },
    "尺寸与空间适配": {
        "keywords": ["size", "small", "large", "wide", "short", "height", "fit", "fits", "space", "room", "apartment"],
        "description": "关注尺寸、高度、宽度和摆放空间，担心到手后比例不对或放不下。",
    },
    "材质与质感": {
        "keywords": ["wood", "leather", "fabric", "boucle", "plastic", "metal", "material", "texture", "finish", "grain"],
        "description": "关注真实触感、表面工艺、材质高级感，以及是否有廉价感。",
    },
    "质量与稳固性": {
        "keywords": ["quality", "sturdy", "solid", "durable", "well made", "heavy", "wobbly", "fragile", "broken", "cracked"],
        "description": "关注结构是否稳、做工是否可靠、是否耐用，尤其是椅子和大件家具。",
    },
    "舒适度与实用性": {
        "keywords": ["comfortable", "comfy", "sit", "seat", "firm", "soft", "functional", "versatile", "swivel", "support"],
        "description": "既要艺术造型，也要能坐、能放、能日常使用。",
    },
    "价格与价值感": {
        "keywords": ["price", "value", "worth", "expensive", "overpriced", "cheap", "deal", "investment", "great buy", "for the money"],
        "description": "衡量价格是否匹配设计、材质、品牌和耐用性。",
    },
    "图片/描述一致性": {
        "keywords": ["picture", "photo", "as pictured", "as described", "expected", "different", "actual", "in person", "true to description"],
        "description": "关注商品图、颜色、比例和描述是否与实物一致。",
    },
    "物流包装与到货": {
        "keywords": ["shipping", "delivery", "arrived", "packaged", "packaging", "box", "damaged", "scratches", "replacement"],
        "description": "担心运输破损、包装保护不足、补发和售后处理。",
    },
    "安装与使用门槛": {
        "keywords": ["assemble", "assembly", "assembled", "install", "installation", "instructions", "hardware", "screw", "unbox"],
        "description": "关注是否免安装、安装难度、配件完整性和开箱便利性。",
    },
    "艺术感/独特性": {
        "keywords": ["art", "work of art", "sculptural", "statement", "unique", "showstopper", "iconic", "conversation", "classic"],
        "description": "关注是否足够独特、是否能作为空间中的设计焦点或收藏感单品。",
    },
}

PRODUCT_PRICES = {
    "Aaisha Faux Leather Armchair": 359.99,
    "Abdullahi Glass Top End Table": 740.04,
    "Desiree 22.5_ Wide Boucle Fabric Accent Chair": 449.99,
    "Elivra Iron Top End Table": 319.99,
    "FL_Y 1 - Light Single Pendant": 444.00,
    "Hot Mesh Lounge Chair": 395.00,
    "Kloud 1 - Light Single Globe Pendant": 618.44,
    "Lampert Sofa": 4100.00,
    "Lize Upholstered Swivel Barrel Chair": 1136.85,
    "Louis Ghost Premium All-Weather Wicker Outdoor Stacking Dining Armchair (Set of 2)": 1032.00,
    "Masters 18.11'' H Stacking Armchair (Set of 2)": 728.00,
    "Max Beam End Table": 412.00,
    "Meurice 42 - Light Dimmable Modern Linear Chandelier": 1650.00,
    "Modern Table": 926.28,
    "Modway Vivi 30.5 Wide": 419.25,
    "Raechell Solid Wood End Table": 266.99,
    "Randal Chenille Accent Chair": 519.99,
    "Rider Dining Chair": 995.00,
    "Rider Upholstered Side Chair": 1500.00,
    "Saralie Modern ABS Plastic Side Table – Curved Geometric Design End Table with Pedestal Base, Living Room Table or Bedroom Nightstand (Set of 2)": 137.99,
    "Serpent End Table": 429.44,
    "Upholstered Counter Stool with Metal Frame (Set of 2)": 1652.00,
    "Ventana 12 - Light Tiered Chandelier": 1495.00,
}

PRICE_BANDS = [
    ("<$300", 0, 300),
    ("$300-600", 300, 600),
    ("$600-1200", 600, 1200),
    ("$1200-2000", 1200, 2000),
    (">$2000", 2000, float("inf")),
]
PRICE_BAND_ORDER = [band[0] for band in PRICE_BANDS]


def price_to_band(price: float | int | None) -> str:
    if price is None or pd.isna(price):
        return "未定价"
    for label, low, high in PRICE_BANDS:
        if low <= float(price) < high:
            return label
    return "未定价"

PRICE_FUNCTION_PATTERNS = {
    "外观审美": ["外观审美"],
    "情绪价值": ["情绪价值"],
    "收藏感/独特性": ["艺术感/收藏感"],
    "实用性/舒适性": ["舒适度/实用性"],
    "价格价值感": ["价格价值感"],
    "可搭配性": ["match", "matches", "goes with", "blend", "blends", "pair", "pairs", "addition", "accent", "decor", "space", "room"],
    "尺寸与空间适配": ["尺寸与空间适配"],
    "材质": ["材质质感"],
    "做工质感": ["做工质量"],
}

BUYER_GROUP_PATTERNS = {
    "家居审美升级者": {
        "keywords": ["living room", "room", "decor", "stylish", "beautiful", "gorgeous", "elegant", "sophistication", "elevates", "statement piece"],
        "description": "把艺术家具作为空间风格升级工具，关注好看、独特、显高级和是否能成为视觉焦点。",
    },
    "设计收藏/艺术爱好者": {
        "keywords": ["art", "work of art", "sculptural", "unique", "unusual", "kartell", "ghost", "masters", "wassily", "replica", "authentic"],
        "description": "偏好经典设计、雕塑感和作品感，愿意为设计语言、品牌符号或复刻款买单。",
    },
    "民宿/影棚/商业经营者": {
        "keywords": ["airbnb", "studio", "photo studio", "shoots", "business", "office", "lobby", "rental", "trade program", "business program"],
        "description": "用于民宿、影棚、办公室或商业空间，重视出片、吸睛、免安装和空间记忆点。",
    },
    "小空间/公寓住户": {
        "keywords": ["apartment", "small space", "corner", "compact", "nook", "little", "small", "bedroom", "bedside", "nightstand"],
        "description": "需要小体量高颜值家具，但对过宽、过矮、无法靠墙或比例误判更敏感。",
    },
    "户外阳台生活者": {
        "keywords": ["balcony", "outdoor", "patio", "deck", "porch", "garden", "weather", "stacked", "carry outside"],
        "description": "围绕阳台、露台、户外聚会使用，关注轻便、叠放、耐候、颜色和安全感。",
    },
    "舒适实用导向者": {
        "keywords": ["comfortable", "comfy", "sit", "seat", "soft", "firm", "functional", "versatile", "swivel", "support"],
        "description": "在艺术造型之外更在乎坐感、功能性、支撑、日常使用和是否适合餐桌/会客。",
    },
    "价值/折扣敏感者": {
        "keywords": ["price", "value", "worth", "expensive", "cheap", "deal", "for the money", "overpriced", "great buy", "cost"],
        "description": "会把价格与材质、工艺、品牌、耐用性一起衡量，容易受廉价感和退货成本影响。",
    },
    "礼品/乔迁购买者": {
        "keywords": ["gift", "present", "housewarming", "friend", "daughter", "son", "mom", "wife", "husband"],
        "description": "把艺术家具当作礼物或家庭成员使用物，重视惊喜感、稳妥交付和通用审美。",
    },
}


def clean(value):
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def truncate(text: str, limit: int = 210) -> str:
    text = " ".join(clean(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def pattern_mask(series: pd.Series, keywords: list[str]) -> pd.Series:
    lowered = series.fillna("").astype(str).str.lower()
    return lowered.apply(lambda text: any(keyword in text for keyword in keywords))


def matched_pattern_names(text: str, patterns: dict[str, dict[str, object]]) -> list[str]:
    lowered = clean(text).lower()
    return [
        name
        for name, cfg in patterns.items()
        if any(keyword in lowered for keyword in cfg["keywords"])
    ]


def image_from_series(series: pd.Series) -> str:
    for value in series.dropna().astype(str):
        first = value.splitlines()[0].strip()
        if first.startswith("http"):
            return first
    return ""


def main() -> None:
    tagged = pd.read_csv(DATA_ROOT / "outputs" / "review_with_voc_tags.csv")
    tags = pd.read_csv(DATA_ROOT / "outputs" / "voc_tag_summary.csv")
    products = pd.read_csv(DATA_ROOT / "outputs" / "product_summary.csv")
    clean_reviews = pd.read_csv(DATA_ROOT / "data_clean" / "all_reviews_clean.csv")

    for frame in (tagged, clean_reviews):
        frame["rating"] = pd.to_numeric(frame["rating"], errors="coerce")

    total_reviews = int(len(tagged))
    avg_rating = round(float(tagged["rating"].mean()), 2)
    low_rating_count = int((tagged["rating"] <= 3).sum())
    sentiment_counts = tagged["sentiment"].value_counts().to_dict()

    top_images = {}
    if "Images URL" in clean_reviews.columns:
        source_images = clean_reviews
    else:
        source_images = pd.DataFrame()
    if not source_images.empty:
        top_images = {
            product: image_from_series(group.get("Images URL", pd.Series(dtype=str)))
            for product, group in source_images.groupby("product_name")
        }

    # The normalized output does not carry Images URL, so re-read raw files for product images.
    if not top_images:
        dataset = Path("/Users/qing/Desktop/数字艺术实践/dataset")
        for path in dataset.glob("*.xlsx"):
            try:
                raw = pd.read_excel(path)
            except Exception:
                continue
            name = path.stem
            if "_" in name:
                name = name.rsplit("_", 1)[0]
            if "Images URL" in raw:
                top_images[name] = image_from_series(raw["Images URL"])

    product_rows = []
    for _, row in products.iterrows():
        name = row["product_name"]
        subset = tagged[tagged["product_name"] == name]
        lows = int((subset["rating"] <= 3).sum())
        dominant_tags = Counter(
            tag
            for value in subset["voc_tags"].dropna()
            for tag in str(value).split("; ")
        ).most_common(3)
        product_rows.append(
            {
                "name": name,
                "reviewCount": int(row["review_count"]),
                "avgRating": round(float(row["avg_rating"]), 2),
                "lowCount": lows,
                "lowShare": round(lows / max(1, len(subset)), 4),
                "dominantTags": [tag for tag, _ in dominant_tags],
                "image": top_images.get(name, ""),
            }
        )

    tag_rows = []
    max_count = max(tags["review_count"])
    for _, row in tags.iterrows():
        name = row["voc_tag"]
        tag_rows.append(
            {
                "name": name,
                "reviewCount": int(row["review_count"]),
                "share": round(float(row["review_count"]) / total_reviews, 4),
                "avgRating": round(float(row["avg_rating"]), 2),
                "negativeCount": int(row["negative_count"]),
                "positiveCount": int(row["positive_count"]),
                "neutralCount": int(row["neutral_count"]),
                "negativeShare": round(float(row["negative_share"]), 4),
                "index": round(float(row["review_count"]) / max_count, 4),
                "desc": TAXONOMY.get(name, {}).get("desc", ""),
                "keywords": TAXONOMY.get(name, {}).get("keywords", []),
            }
        )

    exploded = tagged.assign(voc_tag=tagged["voc_tags"].str.split("; ")).explode("voc_tag")
    heatmap = []
    for product in product_rows[:10]:
        subset = exploded[exploded["product_name"] == product["name"]]
        total = max(1, subset["source_review_id"].nunique())
        counts = subset["voc_tag"].value_counts().to_dict()
        heatmap.append(
            {
                "product": product["name"],
                "tags": {
                    tag["name"]: round(counts.get(tag["name"], 0) / total, 4)
                    for tag in tag_rows[:8]
                },
            }
        )

    def evidence(tag_name: str, sentiment: str, n: int = 6):
        subset = tagged[
            tagged["voc_tags"].fillna("").str.contains(tag_name, regex=False)
            & (tagged["sentiment"] == sentiment)
        ].copy()
        if sentiment == "负向":
            subset = subset.sort_values(["rating", "review_date"], ascending=[True, False])
        else:
            subset = subset.sort_values(["rating", "review_date"], ascending=[False, False])
        records = []
        for _, row in subset.head(n).iterrows():
            records.append(
                {
                    "tag": tag_name,
                    "product": row["product_name"],
                    "rating": clean(row["rating"]),
                    "date": clean(row["review_date"]),
                    "text": truncate(row["review_text"]),
                    "keywords": clean(row["matched_keywords"]),
                }
            )
        return records

    pain_tags = sorted(tag_rows, key=lambda x: (x["negativeCount"], x["negativeShare"]), reverse=True)[:6]
    delight_tags = sorted(tag_rows, key=lambda x: (x["positiveCount"], x["avgRating"]), reverse=True)[:6]

    scenes = []
    for name, cfg in SCENE_PATTERNS.items():
        subset = tagged[pattern_mask(tagged["review_text"], cfg["keywords"])].copy()
        if subset.empty:
            continue
        top_products = subset["product_name"].value_counts().head(3).index.tolist()
        top_tags = Counter(
            tag
            for value in subset["voc_tags"].dropna()
            for tag in str(value).split("; ")
        ).most_common(4)
        evidence_rows = subset.sort_values(["rating", "review_date"], ascending=[False, False]).head(2)
        scenes.append(
            {
                "name": name,
                "mentions": int(len(subset)),
                "avgRating": round(float(subset["rating"].mean()), 2),
                "positiveShare": round(float((subset["sentiment"] == "正向").sum()) / len(subset), 4),
                "topProducts": top_products,
                "topTags": [tag for tag, _ in top_tags],
                "takeaway": cfg["takeaway"],
                "strategy": cfg["strategy"],
                "evidence": [
                    {
                        "product": row["product_name"],
                        "rating": clean(row["rating"]),
                        "date": clean(row["review_date"]),
                        "text": truncate(row["review_text"]),
                    }
                    for _, row in evidence_rows.iterrows()
                ],
            }
        )
    scenes.sort(key=lambda item: item["mentions"], reverse=True)

    scene_assignments = []
    for idx, row in tagged.iterrows():
        for name in matched_pattern_names(row["review_text"], SCENE_PATTERNS):
            scene_assignments.append(
                {
                    "row_id": idx,
                    "scene": name,
                    "review_date": row["review_date"],
                }
            )
    scene_trend = []
    scene_df = pd.DataFrame(scene_assignments)
    if not scene_df.empty:
        scene_df["month"] = pd.to_datetime(scene_df["review_date"], errors="coerce").dt.strftime("%Y-%m")
        scene_df = scene_df.dropna(subset=["month"])
        months = sorted(scene_df["month"].unique())[-18:]
        scene_names = [item["name"] for item in scenes[:8]]
        for month in months:
            month_rows = {"month": month}
            month_subset = scene_df[scene_df["month"] == month]
            for name in scene_names:
                month_rows[name] = int((month_subset["scene"] == name).sum())
            scene_trend.append(month_rows)

    unmet_needs = []
    for name, cfg in UNMET_NEED_PATTERNS.items():
        subset = tagged[pattern_mask(tagged["review_text"], cfg["keywords"])].copy()
        if subset.empty:
            continue
        negative = subset[subset["sentiment"] == "负向"].copy()
        evidence_source = negative if not negative.empty else subset
        evidence_source = evidence_source.sort_values(["rating", "review_date"], ascending=[True, False]).head(2)
        affected_products = subset["product_name"].value_counts().head(3).index.tolist()
        unmet_needs.append(
            {
                "name": name,
                "mentions": int(len(subset)),
                "negativeCount": int((subset["sentiment"] == "负向").sum()),
                "avgRating": round(float(subset["rating"].mean()), 2),
                "severity": round(float((subset["sentiment"] == "负向").sum()) / len(subset), 4),
                "root": cfg["root"],
                "action": cfg["action"],
                "affectedProducts": affected_products,
                "evidence": [
                    {
                        "product": row["product_name"],
                        "rating": clean(row["rating"]),
                        "date": clean(row["review_date"]),
                        "text": truncate(row["review_text"]),
                    }
                    for _, row in evidence_source.iterrows()
                ],
            }
        )
    unmet_needs.sort(key=lambda item: (item["negativeCount"], item["severity"], item["mentions"]), reverse=True)

    purchase_concerns = []
    for name, cfg in PURCHASE_CONCERN_PATTERNS.items():
        subset = tagged[pattern_mask(tagged["review_text"], cfg["keywords"])].copy()
        if subset.empty:
            continue
        evidence_rows = subset.sort_values(["rating", "review_date"], ascending=[False, False]).head(2)
        negative_count = int((subset["sentiment"] == "负向").sum())
        purchase_concerns.append(
            {
                "name": name,
                "mentions": int(len(subset)),
                "share": round(float(len(subset)) / total_reviews, 4),
                "avgRating": round(float(subset["rating"].mean()), 2),
                "negativeCount": negative_count,
                "negativeShare": round(negative_count / len(subset), 4),
                "description": cfg["description"],
                "keywords": cfg["keywords"][:8],
                "evidence": [
                    {
                        "product": row["product_name"],
                        "rating": clean(row["rating"]),
                        "date": clean(row["review_date"]),
                        "text": truncate(row["review_text"]),
                    }
                    for _, row in evidence_rows.iterrows()
                ],
            }
        )
    purchase_concerns.sort(key=lambda item: (item["mentions"], item["negativeCount"]), reverse=True)
    max_concern_mentions = max([item["mentions"] for item in purchase_concerns] or [1])
    for item in purchase_concerns:
        item["weight"] = round(item["mentions"] / max_concern_mentions, 4)

    tagged["product_price"] = tagged["product_name"].map(PRODUCT_PRICES)
    tagged["price_band"] = tagged["product_price"].map(price_to_band)
    price_function_heatmap = []
    for band in PRICE_BAND_ORDER:
        band_subset = tagged[tagged["price_band"] == band].copy()
        denom = len(band_subset)
        cells = []
        for function_name, patterns in PRICE_FUNCTION_PATTERNS.items():
            if denom:
                matches = 0
                for _, row in band_subset.iterrows():
                    tag_text = clean(row["voc_tags"])
                    review_text = clean(row["review_text"]).lower()
                    if any(pattern in tag_text for pattern in patterns) or any(pattern in review_text for pattern in patterns):
                        matches += 1
                value = round(matches / denom, 4)
            else:
                matches = 0
                value = 0
            cells.append(
                {
                    "name": function_name,
                    "value": value,
                    "count": int(matches),
                }
            )
        price_function_heatmap.append(
            {
                "priceBand": band,
                "reviewCount": int(denom),
                "cells": cells,
            }
        )
    product_price_bands = [
        {"product": product, "price": price, "priceBand": price_to_band(price)}
        for product, price in sorted(PRODUCT_PRICES.items(), key=lambda item: (PRICE_BAND_ORDER.index(price_to_band(item[1])), item[1], item[0]))
    ]
    priced_review_count = int(tagged["product_price"].notna().sum())
    priced_product_count = int(len(PRODUCT_PRICES))

    buyer_assignments = []
    for idx, row in tagged.iterrows():
        for name in matched_pattern_names(row["review_text"], BUYER_GROUP_PATTERNS):
            buyer_assignments.append(
                {
                    "row_id": idx,
                    "group": name,
                    "rating": row["rating"],
                    "sentiment": row["sentiment"],
                    "review_date": row["review_date"],
                    "product_name": row["product_name"],
                    "review_text": row["review_text"],
                }
            )
    buyer_df = pd.DataFrame(buyer_assignments)

    buyer_groups = []
    if not buyer_df.empty:
        grouped = (
            buyer_df.groupby("group")
            .agg(
                mentions=("row_id", "count"),
                avg_rating=("rating", "mean"),
                positive_count=("sentiment", lambda s: (s == "正向").sum()),
                negative_count=("sentiment", lambda s: (s == "负向").sum()),
            )
            .reset_index()
        )
        grouped["share"] = grouped["mentions"] / total_reviews
        grouped = grouped.sort_values(["mentions", "avg_rating"], ascending=False)
        max_mentions = max(grouped["mentions"])
        for _, row in grouped.iterrows():
            name = row["group"]
            subset = buyer_df[buyer_df["group"] == name].copy()
            evidence_rows = subset.sort_values(["rating", "review_date"], ascending=[False, False]).head(2)
            buyer_groups.append(
                {
                    "name": name,
                    "mentions": int(row["mentions"]),
                    "share": round(float(row["share"]), 4),
                    "avgRating": round(float(row["avg_rating"]), 2),
                    "positiveShare": round(float(row["positive_count"]) / max(1, row["mentions"]), 4),
                    "negativeCount": int(row["negative_count"]),
                    "weight": round(float(row["mentions"]) / max_mentions, 4),
                    "description": BUYER_GROUP_PATTERNS[name]["description"],
                    "keywords": BUYER_GROUP_PATTERNS[name]["keywords"][:8],
                    "evidence": [
                        {
                            "product": item["product_name"],
                            "rating": clean(item["rating"]),
                            "date": clean(item["review_date"]),
                            "text": truncate(item["review_text"]),
                        }
                        for _, item in evidence_rows.iterrows()
                    ],
                }
            )

    buyer_trend = []
    if not buyer_df.empty:
        trend_df = buyer_df.copy()
        trend_df["month"] = pd.to_datetime(trend_df["review_date"], errors="coerce").dt.strftime("%Y-%m")
        trend_df = trend_df.dropna(subset=["month"])
        months = sorted(trend_df["month"].unique())[-18:]
        top_group_names = [item["name"] for item in buyer_groups[:8]]
        for month in months:
            month_rows = {"month": month}
            month_subset = trend_df[trend_df["month"] == month]
            for name in top_group_names:
                month_rows[name] = int((month_subset["group"] == name).sum())
            buyer_trend.append(month_rows)

    payload = {
        "meta": {
            "title": "艺术家具行业 VOC 用户洞察分析",
            "subtitle": "基于电商评论的标签体系、痛点、愉悦点与机会洞察",
            "source": "/Users/qing/Desktop/数字艺术实践/dataset",
            "totalReviews": total_reviews,
            "productCount": int(tagged["product_name"].nunique()),
            "avgRating": avg_rating,
            "lowRatingCount": low_rating_count,
            "lowRatingShare": round(low_rating_count / total_reviews, 4),
            "dateMin": clean(tagged["review_date"].min()),
            "dateMax": clean(tagged["review_date"].max()),
            "sentiment": {
                "positive": int(sentiment_counts.get("正向", 0)),
                "neutral": int(sentiment_counts.get("中性", 0)),
                "negative": int(sentiment_counts.get("负向", 0)),
            },
        },
        "tags": tag_rows,
        "products": product_rows,
        "heatmap": heatmap,
        "pain": [
            {
                "title": f"{item['name']}是当前首要体验阻力",
                "summary": f"负向评论 {item['negativeCount']} 条，负面占比 {item['negativeShare']:.1%}，平均评分 {item['avgRating']}。",
                "tag": item["name"],
                "evidence": evidence(item["name"], "负向", 2),
            }
            for item in pain_tags
            if item["negativeCount"] > 0
        ],
        "delight": [
            {
                "title": f"{item['name']}构成高分购买理由",
                "summary": f"正向评论 {item['positiveCount']} 条，平均评分 {item['avgRating']}，可沉淀为商品页卖点。",
                "tag": item["name"],
                "evidence": evidence(item["name"], "正向", 2),
            }
            for item in delight_tags
        ],
        "scenes": scenes,
        "sceneTrend": scene_trend,
        "unmetNeeds": unmet_needs,
        "purchaseConcerns": purchase_concerns,
        "priceFunction": {
            "note": f"价格基于用户提供的真实商品价格；当前覆盖 {priced_product_count} 个产品、{priced_review_count} 条评论，未提供价格的产品暂不纳入本热力图。",
            "columns": list(PRICE_FUNCTION_PATTERNS.keys()),
            "rows": price_function_heatmap,
            "productBands": product_price_bands,
        },
        "buyerGroups": buyer_groups,
        "buyerTrend": buyer_trend,
        "opportunities": [
            {
                "tag": "物流包装",
                "priority": "P0",
                "action": "升级内外双层防护、角位保护和大件搬运提示，建立破损极速补发机制。",
                "metric": "到货破损/退换货相关低分评论占比",
            },
            {
                "tag": "材质质感",
                "priority": "P0",
                "action": "补充材质微距图、触感描述、重量参数和保养说明，降低“看起来廉价”的预期落差。",
                "metric": "材质质感负向评论数",
            },
            {
                "tag": "尺寸与空间适配",
                "priority": "P1",
                "action": "增加真人、沙发、床边、阳台尺度参照，并在标题区突出关键尺寸与高度。",
                "metric": "尺寸相关退货/低分评论占比",
            },
            {
                "tag": "艺术感/收藏感",
                "priority": "P1",
                "action": "把“sculptural / work of art / statement”转译为设计故事和空间搭配模板。",
                "metric": "艺术感标签转化率与收藏/加购率",
            },
            {
                "tag": "情绪价值",
                "priority": "P2",
                "action": "提炼高频情绪词，形成标题、A+ 页面、短视频脚本和社媒种草素材库。",
                "metric": "高情绪价值评论占比",
            },
        ],
    }

    OUT.write_text(
        "window.VOC_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
