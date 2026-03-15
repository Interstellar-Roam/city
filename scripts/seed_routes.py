"""数据库种子脚本 - 添加咖啡和商场相关路线"""

import asyncio
from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# 咖啡和商场相关路线数据
ROUTES_DATA: list[dict[str, Any]] = [
    # === 咖啡主题路线 ===
    {
        "name": "静安咖啡馆漫步",
        "description": "探索上海静安区最受欢迎的特色咖啡馆，从网红打卡店到隐藏的精品咖啡小馆，品味不一样的咖啡文化。",
        "preview_image": "https://example.com/routes/jingan-coffee.jpg",
        "distance": 3500,
        "elevation_gain": 15,
        "estimated_duration": 180,
        "start_location": {"type": "Point", "coordinates": [121.4431, 31.2297]},
        "end_location": {"type": "Point", "coordinates": [121.4512, 31.2234]},
        "city": "上海",
        "district": "静安区",
        "difficulty": "easy",
        "tags": ["咖啡", "文艺", "网红打卡", "周末休闲"],
        "pois": [
            {"name": "%Arabica", "category": "咖啡", "location": {"type": "Point", "coordinates": [121.4431, 31.2297]}, "description": "网红咖啡打卡地", "rating": 4.8},
            {"name": "Manner Coffee", "category": "咖啡", "location": {"type": "Point", "coordinates": [121.4478, 31.2265]}, "description": "精品咖啡连锁", "rating": 4.5},
            {"name": "Seesaw Coffee", "category": "咖啡", "location": {"type": "Point", "coordinates": [121.4512, 31.2234]}, "description": "本土精品咖啡品牌", "rating": 4.7}
        ]
    },
    {
        "name": "徐汇精品咖啡之旅",
        "description": "漫步徐汇区梧桐树下，探访隐藏在老洋房里的精品咖啡馆，感受上海独特的咖啡氛围。",
        "distance": 4200,
        "elevation_gain": 20,
        "estimated_duration": 200,
        "start_location": {"type": "Point", "coordinates": [121.4367, 31.2032]},
        "end_location": {"type": "Point", "coordinates": [121.4423, 31.1987]},
        "city": "上海",
        "district": "徐汇区",
        "difficulty": "easy",
        "tags": ["咖啡", "老洋房", "精品咖啡", "文艺"],
        "pois": [
            {"name": "鲁马滋咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [121.4367, 31.2032]}, "description": "日式手冲咖啡", "rating": 4.9},
            {"name": "Gregorius Coffee", "category": "咖啡", "location": {"type": "Point", "coordinates": [121.4395, 31.2010]}, "description": "意大利风格咖啡馆", "rating": 4.6},
            {"name": "Coffee Spot", "category": "咖啡", "location": {"type": "Point", "coordinates": [121.4423, 31.1987]}, "description": "社区精品咖啡店", "rating": 4.7}
        ]
    },
    {
        "name": "成都太古里咖啡打卡",
        "description": "穿梭于成都太古里时尚街区，打卡最受欢迎的网红咖啡馆，感受成都的悠闲咖啡文化。",
        "distance": 2800,
        "elevation_gain": 10,
        "estimated_duration": 150,
        "start_location": {"type": "Point", "coordinates": [104.0804, 30.6571]},
        "end_location": {"type": "Point", "coordinates": [104.0852, 30.6534]},
        "city": "成都",
        "district": "锦江区",
        "difficulty": "easy",
        "tags": ["咖啡", "网红打卡", "太古里", "时尚"],
        "pois": [
            {"name": "Blue Bottle Coffee", "category": "咖啡", "location": {"type": "Point", "coordinates": [104.0804, 30.6571]}, "description": "美国精品咖啡品牌", "rating": 4.8},
            {"name": "星巴克臻选", "category": "咖啡", "location": {"type": "Point", "coordinates": [104.0828, 30.6552]}, "description": "臻选旗舰店", "rating": 4.5},
            {"name": "S.Engine Coffee", "category": "咖啡", "location": {"type": "Point", "coordinates": [104.0852, 30.6534]}, "description": "成都本土咖啡品牌", "rating": 4.6}
        ]
    },
    {
        "name": "杭州西湖咖啡慢行",
        "description": "沿着美丽的西湖漫步，探访湖边的特色咖啡馆，享受湖景与咖啡的双重美好。",
        "distance": 5500,
        "elevation_gain": 35,
        "estimated_duration": 240,
        "start_location": {"type": "Point", "coordinates": [120.1483, 30.2524]},
        "end_location": {"type": "Point", "coordinates": [120.1534, 30.2467]},
        "city": "杭州",
        "district": "西湖区",
        "difficulty": "easy",
        "tags": ["咖啡", "西湖", "湖景", "慢生活"],
        "pois": [
            {"name": "西湖国宾馆咖啡厅", "category": "咖啡", "location": {"type": "Point", "coordinates": [120.1483, 30.2524]}, "description": "湖景咖啡厅", "rating": 4.7},
            {"name": "茶人村咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [120.1509, 30.2495]}, "description": "茶园里的咖啡", "rating": 4.8},
            {"name": "西子湖畔咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [120.1534, 30.2467]}, "description": "最佳湖景观景点", "rating": 4.6}
        ]
    },
    {
        "name": "北京胡同咖啡探索",
        "description": "深入北京老胡同，发现那些隐藏在四合院里的特色咖啡馆，感受老北京的咖啡新生活。",
        "distance": 3800,
        "elevation_gain": 25,
        "estimated_duration": 190,
        "start_location": {"type": "Point", "coordinates": [116.4074, 39.9312]},
        "end_location": {"type": "Point", "coordinates": [116.4123, 39.9267]},
        "city": "北京",
        "district": "东城区",
        "difficulty": "easy",
        "tags": ["咖啡", "胡同", "四合院", "文艺"],
        "pois": [
            {"name": "Metal Hands铁手咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [116.4074, 39.9312]}, "description": "胡同里的网红咖啡", "rating": 4.8},
            {"name": "大小咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [116.4098, 39.9289]}, "description": "精品咖啡小馆", "rating": 4.7},
            {"name": "Soloist Coffee", "category": "咖啡", "location": {"type": "Point", "coordinates": [116.4123, 39.9267]}, "description": "复古风格咖啡馆", "rating": 4.6}
        ]
    },
    # === 商场主题路线 ===
    {
        "name": "上海南京路购物之旅",
        "description": "漫步中华商业第一街南京路，探访百年老店与现代购物中心，体验上海购物天堂的魅力。",
        "distance": 2500,
        "elevation_gain": 5,
        "estimated_duration": 180,
        "start_location": {"type": "Point", "coordinates": [121.4745, 31.2356]},
        "end_location": {"type": "Point", "coordinates": [121.4901, 31.2398]},
        "city": "上海",
        "district": "黄浦区",
        "difficulty": "easy",
        "tags": ["商场", "购物", "南京路", "地标"],
        "pois": [
            {"name": "新世界大丸百货", "category": "商场", "location": {"type": "Point", "coordinates": [121.4745, 31.2356]}, "description": "日系精品百货", "rating": 4.5},
            {"name": "上海第一百货", "category": "商场", "location": {"type": "Point", "coordinates": [121.4823, 31.2377]}, "description": "百年老店", "rating": 4.3},
            {"name": "新世界城", "category": "商场", "location": {"type": "Point", "coordinates": [121.4901, 31.2398]}, "description": "综合购物中心", "rating": 4.4}
        ]
    },
    {
        "name": "北京三里屯时尚购物",
        "description": "探索北京最时尚的三里屯商圈，从国际大牌到潮流买手店，感受首都的时尚脉搏。",
        "distance": 3200,
        "elevation_gain": 15,
        "estimated_duration": 200,
        "start_location": {"type": "Point", "coordinates": [116.4545, 39.9321]},
        "end_location": {"type": "Point", "coordinates": [116.4612, 39.9289]},
        "city": "北京",
        "district": "朝阳区",
        "difficulty": "easy",
        "tags": ["商场", "时尚", "三里屯", "潮流"],
        "pois": [
            {"name": "太古里北区", "category": "商场", "location": {"type": "Point", "coordinates": [116.4545, 39.9321]}, "description": "国际奢侈品聚集地", "rating": 4.7},
            {"name": "三里屯SOHO", "category": "商场", "location": {"type": "Point", "coordinates": [116.4578, 39.9305]}, "description": "时尚潮流中心", "rating": 4.5},
            {"name": "太古里南区", "category": "商场", "location": {"type": "Point", "coordinates": [116.4612, 39.9289]}, "description": "潮流品牌集合", "rating": 4.6}
        ]
    },
    {
        "name": "深圳万象城购物路线",
        "description": "探访深圳最大型购物中心万象城及周边商圈，享受一站式购物娱乐体验。",
        "distance": 2800,
        "elevation_gain": 10,
        "estimated_duration": 180,
        "start_location": {"type": "Point", "coordinates": [114.1089, 22.5478]},
        "end_location": {"type": "Point", "coordinates": [114.1156, 22.5445]},
        "city": "深圳",
        "district": "罗湖区",
        "difficulty": "easy",
        "tags": ["商场", "购物", "万象城", "一站式"],
        "pois": [
            {"name": "万象城", "category": "商场", "location": {"type": "Point", "coordinates": [114.1089, 22.5478]}, "description": "深圳最大购物中心", "rating": 4.7},
            {"name": "KK MALL", "category": "商场", "location": {"type": "Point", "coordinates": [114.1123, 22.5461]}, "description": "潮流购物中心", "rating": 4.5},
            {"name": "京基百纳空间", "category": "商场", "location": {"type": "Point", "coordinates": [114.1156, 22.5445]}, "description": "年轻时尚购物地", "rating": 4.4}
        ]
    },
    {
        "name": "广州天河商圈漫步",
        "description": "漫步广州最繁华的天河商圈，探访各大购物中心，体验华南购物之都的魅力。",
        "distance": 4000,
        "elevation_gain": 20,
        "estimated_duration": 220,
        "start_location": {"type": "Point", "coordinates": [113.3301, 23.1352]},
        "end_location": {"type": "Point", "coordinates": [113.3389, 23.1312]},
        "city": "广州",
        "district": "天河区",
        "difficulty": "easy",
        "tags": ["商场", "购物", "天河", "商圈"],
        "pois": [
            {"name": "正佳广场", "category": "商场", "location": {"type": "Point", "coordinates": [113.3301, 23.1352]}, "description": "亚洲第一购物中心", "rating": 4.6},
            {"name": "天河城", "category": "商场", "location": {"type": "Point", "coordinates": [113.3345, 23.1333]}, "description": "广州地标购物中心", "rating": 4.5},
            {"name": "太古汇", "category": "商场", "location": {"type": "Point", "coordinates": [113.3389, 23.1312]}, "description": "高端奢侈品中心", "rating": 4.8}
        ]
    },
    {
        "name": "成都IFS太古里购物",
        "description": "探索成都最时尚的春熙路商圈，从IFS国际金融中心到太古里开放式街区，感受成都的时尚脉搏。",
        "distance": 2600,
        "elevation_gain": 12,
        "estimated_duration": 180,
        "start_location": {"type": "Point", "coordinates": [104.0812, 30.6598]},
        "end_location": {"type": "Point", "coordinates": [104.0878, 30.6556]},
        "city": "成都",
        "district": "锦江区",
        "difficulty": "easy",
        "tags": ["商场", "购物", "春熙路", "时尚"],
        "pois": [
            {"name": "成都IFS", "category": "商场", "location": {"type": "Point", "coordinates": [104.0812, 30.6598]}, "description": "国际金融中心", "rating": 4.7},
            {"name": "远洋太古里", "category": "商场", "location": {"type": "Point", "coordinates": [104.0845, 30.6577]}, "description": "开放式购物街区", "rating": 4.8},
            {"name": "群光广场", "category": "商场", "location": {"type": "Point", "coordinates": [104.0878, 30.6556]}, "description": "年轻潮流购物中心", "rating": 4.4}
        ]
    },
    # === 咖啡+商场混合路线 ===
    {
        "name": "上海新天地咖啡购物之旅",
        "description": "漫步新天地石库门街区，品味特色咖啡馆，探索时尚精品店，感受上海中西合璧的独特魅力。",
        "distance": 3000,
        "elevation_gain": 18,
        "estimated_duration": 200,
        "start_location": {"type": "Point", "coordinates": [121.4789, 31.2212]},
        "end_location": {"type": "Point", "coordinates": [121.4856, 31.2178]},
        "city": "上海",
        "district": "黄浦区",
        "difficulty": "easy",
        "tags": ["咖啡", "商场", "新天地", "石库门"],
        "pois": [
            {"name": "新天地北里", "category": "商场", "location": {"type": "Point", "coordinates": [121.4789, 31.2212]}, "description": "石库门时尚街区", "rating": 4.7},
            {"name": "Alchemist Cafe", "category": "咖啡", "location": {"type": "Point", "coordinates": [121.4823, 31.2195]}, "description": "精品咖啡馆", "rating": 4.6},
            {"name": "新天地南里", "category": "商场", "location": {"type": "Point", "coordinates": [121.4856, 31.2178]}, "description": "国际品牌聚集地", "rating": 4.5}
        ]
    },
    {
        "name": "深圳华侨城咖啡文创之旅",
        "description": "探索华侨城创意文化园，探访文创咖啡馆和特色小店，感受深圳的文艺气息。",
        "distance": 3500,
        "elevation_gain": 25,
        "estimated_duration": 210,
        "start_location": {"type": "Point", "coordinates": [113.9823, 22.5334]},
        "end_location": {"type": "Point", "coordinates": [113.9889, 22.5289]},
        "city": "深圳",
        "district": "南山区",
        "difficulty": "easy",
        "tags": ["咖啡", "文创", "华侨城", "艺术"],
        "pois": [
            {"name": "华侨城创意文化园", "category": "文创", "location": {"type": "Point", "coordinates": [113.9823, 22.5334]}, "description": "深圳文青聚集地", "rating": 4.7},
            {"name": "旧天堂书店咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [113.9856, 22.5311]}, "description": "书店里的咖啡馆", "rating": 4.8},
            {"name": "华侨城购物公园", "category": "商场", "location": {"type": "Point", "coordinates": [113.9889, 22.5289]}, "description": "开放式购物街区", "rating": 4.5}
        ]
    },
    {
        "name": "北京侨福芳草地艺术购物",
        "description": "探访侨福芳草地艺术购物中心，欣赏艺术品收藏，品味特色咖啡，体验艺术与购物的完美结合。",
        "distance": 2200,
        "elevation_gain": 10,
        "estimated_duration": 150,
        "start_location": {"type": "Point", "coordinates": [116.4612, 39.9123]},
        "end_location": {"type": "Point", "coordinates": [116.4678, 39.9098]},
        "city": "北京",
        "district": "朝阳区",
        "difficulty": "easy",
        "tags": ["咖啡", "商场", "艺术", "CBD"],
        "pois": [
            {"name": "侨福芳草地", "category": "商场", "location": {"type": "Point", "coordinates": [116.4612, 39.9123]}, "description": "艺术购物中心", "rating": 4.8},
            {"name": "Gallery Café", "category": "咖啡", "location": {"type": "Point", "coordinates": [116.4645, 39.9110]}, "description": "画廊咖啡馆", "rating": 4.7},
            {"name": "世贸天阶", "category": "商场", "location": {"type": "Point", "coordinates": [116.4678, 39.9098]}, "description": "时尚购物中心", "rating": 4.4}
        ]
    },
    {
        "name": "杭州武林广场购物咖啡",
        "description": "漫步杭州武林商圈，探访老牌百货与新晋购物中心，在咖啡馆小憩，享受悠闲购物时光。",
        "distance": 3800,
        "elevation_gain": 20,
        "estimated_duration": 200,
        "start_location": {"type": "Point", "coordinates": [120.1634, 30.2812]},
        "end_location": {"type": "Point", "coordinates": [120.1712, 30.2778]},
        "city": "杭州",
        "district": "下城区",
        "difficulty": "easy",
        "tags": ["咖啡", "商场", "武林广场", "购物"],
        "pois": [
            {"name": "杭州大厦", "category": "商场", "location": {"type": "Point", "coordinates": [120.1634, 30.2812]}, "description": "杭州地标百货", "rating": 4.6},
            {"name": "星巴克臻选", "category": "咖啡", "location": {"type": "Point", "coordinates": [120.1673, 30.2795]}, "description": "臻选咖啡店", "rating": 4.5},
            {"name": "国大城市广场", "category": "商场", "location": {"type": "Point", "coordinates": [120.1712, 30.2778]}, "description": "综合性购物中心", "rating": 4.4}
        ]
    },
    {
        "name": "广州珠江新城商务休闲",
        "description": "穿梭于珠江新城CBD，探访高端购物中心与精品咖啡馆，体验广州现代都市生活。",
        "distance": 4500,
        "elevation_gain": 30,
        "estimated_duration": 230,
        "start_location": {"type": "Point", "coordinates": [113.3212, 23.1198]},
        "end_location": {"type": "Point", "coordinates": [113.3289, 23.1156]},
        "city": "广州",
        "district": "天河区",
        "difficulty": "easy",
        "tags": ["咖啡", "商场", "CBD", "珠江新城"],
        "pois": [
            {"name": "花城汇", "category": "商场", "location": {"type": "Point", "coordinates": [113.3212, 23.1198]}, "description": "CBD地下购物中心", "rating": 4.5},
            {"name": " cafe on air", "category": "咖啡", "location": {"type": "Point", "coordinates": [113.3251, 23.1177]}, "description": "精品咖啡馆", "rating": 4.6},
            {"name": "K11", "category": "商场", "location": {"type": "Point", "coordinates": [113.3289, 23.1156]}, "description": "艺术购物中心", "rating": 4.7}
        ]
    },
    {
        "name": "南京德基广场咖啡漫步",
        "description": "探访南京最繁华的新街口商圈，在德基广场购物，在特色咖啡馆小憩，感受古都的时尚一面。",
        "distance": 2800,
        "elevation_gain": 15,
        "estimated_duration": 180,
        "start_location": {"type": "Point", "coordinates": [118.7834, 32.0467]},
        "end_location": {"type": "Point", "coordinates": [118.7912, 32.0434]},
        "city": "南京",
        "district": "玄武区",
        "difficulty": "easy",
        "tags": ["咖啡", "商场", "新街口", "德基广场"],
        "pois": [
            {"name": "德基广场", "category": "商场", "location": {"type": "Point", "coordinates": [118.7834, 32.0467]}, "description": "南京顶级购物中心", "rating": 4.7},
            {"name": "鱼缸咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [118.7873, 32.0450]}, "description": "文艺咖啡馆", "rating": 4.6},
            {"name": "金鹰国际购物中心", "category": "商场", "location": {"type": "Point", "coordinates": [118.7912, 32.0434]}, "description": "综合购物中心", "rating": 4.5}
        ]
    },
    {
        "name": "武汉武广商圈购物咖啡",
        "description": "漫步武汉最繁华的武广商圈，探访各大购物中心，在网红咖啡馆打卡，体验江城时尚生活。",
        "distance": 3200,
        "elevation_gain": 18,
        "estimated_duration": 190,
        "start_location": {"type": "Point", "coordinates": [114.2689, 30.5823]},
        "end_location": {"type": "Point", "coordinates": [114.2756, 30.5789]},
        "city": "武汉",
        "district": "江汉区",
        "difficulty": "easy",
        "tags": ["咖啡", "商场", "武广商圈", "购物"],
        "pois": [
            {"name": "武汉国际广场", "category": "商场", "location": {"type": "Point", "coordinates": [114.2689, 30.5823]}, "description": "高端购物中心", "rating": 4.6},
            {"name": "老友记咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [114.2723, 30.5806]}, "description": "网红咖啡店", "rating": 4.5},
            {"name": "武汉广场", "category": "商场", "location": {"type": "Point", "coordinates": [114.2756, 30.5789]}, "description": "老牌购物中心", "rating": 4.3}
        ]
    },
    {
        "name": "重庆解放碑购物咖啡之旅",
        "description": "探访重庆地标解放碑商圈，穿梭于各大购物中心，品尝山城特色咖啡，感受8D魔幻都市魅力。",
        "distance": 3600,
        "elevation_gain": 45,
        "estimated_duration": 210,
        "start_location": {"type": "Point", "coordinates": [106.5778, 29.5534]},
        "end_location": {"type": "Point", "coordinates": [106.5845, 29.5501]},
        "city": "重庆",
        "district": "渝中区",
        "difficulty": "medium",
        "tags": ["咖啡", "商场", "解放碑", "山城"],
        "pois": [
            {"name": "解放碑步行街", "category": "商圈", "location": {"type": "Point", "coordinates": [106.5778, 29.5534]}, "description": "重庆地标", "rating": 4.6},
            {"name": "质馆咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [106.5812, 29.5517]}, "description": "精品咖啡馆", "rating": 4.5},
            {"name": "时代广场", "category": "商场", "location": {"type": "Point", "coordinates": [106.5845, 29.5501]}, "description": "高端购物中心", "rating": 4.4}
        ]
    },
    {
        "name": "西安小寨咖啡购物之旅",
        "description": "探索西安最年轻的小寨商圈，探访潮流购物中心与网红咖啡馆，感受古都的时尚脉动。",
        "distance": 3000,
        "elevation_gain": 22,
        "estimated_duration": 180,
        "start_location": {"type": "Point", "coordinates": [108.9478, 34.2289]},
        "end_location": {"type": "Point", "coordinates": [108.9545, 34.2256]},
        "city": "西安",
        "district": "雁塔区",
        "difficulty": "easy",
        "tags": ["咖啡", "商场", "小寨", "年轻"],
        "pois": [
            {"name": "赛格国际购物中心", "category": "商场", "location": {"type": "Point", "coordinates": [108.9478, 34.2289]}, "description": "西安最火购物中心", "rating": 4.6},
            {"name": "minder咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [108.9512, 34.2272]}, "description": "网红咖啡馆", "rating": 4.5},
            {"name": "银泰城", "category": "商场", "location": {"type": "Point", "coordinates": [108.9545, 34.2256]}, "description": "综合购物中心", "rating": 4.4}
        ]
    },
    {
        "name": "苏州金鸡湖咖啡商街漫步",
        "description": "漫步苏州金鸡湖畔，探访湖滨商业街的精品咖啡馆与时尚购物中心，享受水城慢生活。",
        "distance": 4000,
        "elevation_gain": 15,
        "estimated_duration": 210,
        "start_location": {"type": "Point", "coordinates": [120.7012, 31.3123]},
        "end_location": {"type": "Point", "coordinates": [120.7089, 31.3089]},
        "city": "苏州",
        "district": "工业园区",
        "difficulty": "easy",
        "tags": ["咖啡", "商场", "金鸡湖", "湖景"],
        "pois": [
            {"name": "苏州中心广场", "category": "商场", "location": {"type": "Point", "coordinates": [120.7012, 31.3123]}, "description": "大型综合购物中心", "rating": 4.6},
            {"name": "SeeSaw Coffee", "category": "咖啡", "location": {"type": "Point", "coordinates": [120.7051, 31.3106]}, "description": "精品咖啡馆", "rating": 4.7},
            {"name": "诚品书店咖啡", "category": "咖啡", "location": {"type": "Point", "coordinates": [120.7089, 31.3089]}, "description": "书店里的文艺咖啡", "rating": 4.8}
        ]
    }
]


async def seed_routes():
    """执行数据插入"""
    # 连接MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.citywalk
    collection = db.routes
    
    # 清除现有数据
    await collection.delete_many({})
    print("已清除现有路线数据")
    
    # 插入新数据
    routes_to_insert = []
    for route_data in ROUTES_DATA:
        route = {
            "_id": str(ObjectId()),
            **route_data,
            "favorites_count": 0,
            "views_count": 0,
            "completions_count": 0,
            "is_published": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        routes_to_insert.append(route)
    
    result = await collection.insert_many(routes_to_insert)
    print(f"成功插入 {len(result.inserted_ids)} 条路线")
    
    # 创建索引（忽略已存在的错误）
    try:
        await collection.create_index([
            ("name", "text"),
            ("description", "text"),
            ("tags", "text"),
            ("city", "text"),
            ("district", "text")
        ])
        print("已创建文本索引")
    except Exception as e:
        print(f"文本索引已存在，跳过: {e}")
    
    try:
        await collection.create_index([("start_location", "2dsphere")])
        print("已创建地理空间索引")
    except Exception as e:
        print(f"地理空间索引已存在，跳过: {e}")
    
    client.close()
    print("\n种子数据插入完成！")


if __name__ == "__main__":
    asyncio.run(seed_routes())
