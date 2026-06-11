import json
import os
from pathlib import Path
import yaml

ONTOLOGY_DIR = Path("ontology")
TAGS_PATH = ONTOLOGY_DIR / "tags.yaml"
STYLES_PATH = ONTOLOGY_DIR / "styles.yaml"
PARSED_JSON_PATH = Path("/root/.gemini/antigravity-cli/brain/4c476c26-7094-4a21-a988-2871e514f073/scratch/parsed_tags.json")

# Mapping of English term to common Japanese aliases for precise matching
TRANSLATIONS = {
    # Outfit Types
    "Short Pants": ["ショートパンツ", "短パン", "ショーツ"],
    "One-Piece Dress": ["ワンピース", "ワンピ"],
    "Jacket": ["ジャケット"],
    "Dress": ["ドレス"],
    "Boots": ["ブーツ"],
    "Shirt": ["シャツ"],
    "Hoodie": ["パーカー", "フーディ"],
    "Skirt": ["スカート"],
    "Knit": ["ニット"],
    "Crop Top": ["クロップド", "クロップト"],
    "Swimsuit": ["水着", "スイムウェア"],
    "Pants": ["パンツ", "ズボン"],
    "Bikini": ["ビキニ"],
    "School Uniform": ["制服", "学生服"],
    "Knee-High": ["ニーハイ"],
    "Bodysuit": ["ボディスーツ"],
    "Coat": ["コート"],
    "Underwear": ["下着", "アンダーウェア"],
    "Sweater": ["セーター"],
    "Maid Outfit": ["メイド服", "メイド"],
    "T-Shirt": ["tシャツ", "Tシャツ"],
    "Miniskirt": ["ミニスカート", "ミニスカ"],
    "Loungewear": ["ルームウェア", "部屋着"],
    "Pleated Skirt": ["プリーツスカート"],
    "Outerwear": ["アウター"],
    "Sailor Uniform": ["セーラー服", "セーラー"],
    "Kimono": ["着物", "きもの"],
    "Cardigan": ["カーディガン"],
    "Sneakers": ["スニーカー"],
    "Lingerie": ["ランジェリー"],
    "Blouse": ["ブラウス"],
    "Denim": ["デニム"],
    "Off-Shoulder": ["オフショル", "オフショルダー"],
    "Frill": ["フリル"],
    "Vest": ["ベスト"],
    "China Dress": ["チャイナドレス", "チャイナ服"],
    "Stockings": ["ストッキング"],
    "Tights": ["タイツ"],
    "Oversized": ["オーバーサイズ"],
    "Apron": ["エプロン"],
    "Harness": ["ハーネス"],
    "Sandals": ["サンダル"],
    "Suit": ["スーツ"],
    "Bunny Suit": ["バニースーツ", "バニーガール"],
    "Jersey": ["ジャージ"],
    "High Heels": ["ハイヒール"],
    "Pajamas": ["パジャマ"],
    "Corset": ["コルセット"],
    "Tank Top": ["タンクトップ"],
    "Leotard": ["レオタード"],
    "Necktie": ["ネクタイ"],
    "Garter Belt": ["ガーターベルト"],
    "Yukata": ["浴衣"],
    "Hat": ["帽子", "ハット"],
    "Loafers": ["ローファー"],
    "Overalls": ["オーバーオール"],
    "Cargo Pants": ["カーゴパンツ"],
    "Camisole": ["キャミソール", "キャミ"],
    "Jeans": ["ジーンズ"],
    "Leg Warmers": ["レッグウォーマー"],
    "Turtleneck": ["タートルネック"],
    "Cloak": ["マント", "クローク"],
    "Blazer": ["ブレザー"],
    "Beret": ["ベレー帽", "ベレー"],
    "Robe": ["ローブ"],
    "Gothic Dress": ["ゴシックドレス"],
    "Tight Skirt": ["タイトスカート"],
    "Nun Outfit": ["シスター", "修道女"],
    "Suspenders": ["サスペンダー"],
    "Babydoll": ["ベビードール"],
    "Military Uniform": ["軍服", "ミリタリー制服"],
    "Leather Jacket": ["レザージャケット", "革ジャン"],
    "Haori": ["羽織"],
    "Shorts": ["ショーツ"],
    "Tops": ["トップス"],
    "Scarf": ["マフラー", "スカーフ"],
    "Slacks": ["スラックス"],
    "Sportswear": ["スポーツウェア"],
    "Innerwear": ["インナー"],
    "Belt": ["ベルト"],
    "Furisode": ["振袖"],
    "Hakama": ["袴"],
    "Loose Socks": ["ルーズソックス"],
    "Bra Top": ["ブラトップ"],
    "Bustier": ["ビスチェ"],
    "Leggings": ["レギンス"],
    "Santa Outfit": ["サンタ服", "サンタ衣装"],
    "School Swimsuit": ["スクール水着", "スク水"],
    "Lace": ["レース"],
    "Down Jacket": ["ダウンジャケット", "ダウン"],
    "Pumps": ["パンプス"],
    "Micro Bikini": ["マイクロビキニ"],
    "Miko Outfit": ["巫女服", "巫女"],
    "Headdress": ["ヘッドドレス"],
    "Bloomers": ["ブルマ"],
    "Nurse Outfit": ["ナース服", "ナース"],
    "Armor": ["鎧", "アーマー"],
    "Uniform": ["制服", "ユニフォーム"],
    "Techwear": ["テックウェア"],
    "Spats": ["スパッツ"],
    "Veil": ["ベール", "ヴェール"],
    "Lab Coat": ["白衣"],
    "Idol Outfit": ["アイドル衣装"],
    "Raincoat": ["レインコート", "カッパ"],
    "Wedding Dress": ["ウェディングドレス"],
    "Witch Outfit": ["魔女服", "魔女"],
    
    # Styles
    "Cute": ["キュート", "かわいい", "可愛い"],
    "Cool": ["クール", "かっこいい", "格好いい"],
    "Girly": ["ガーリー"],
    "Sexy": ["セクシー", "えち"],
    "Dark": ["ダーク", "闇"],
    "Casual": ["カジュアル"],
    "Street": ["ストリート"],
    "Natural": ["ナチュラル"],
    "Fantasy": ["ファンタジー"],
    "Gothic": ["ゴシック", "ゴス"],
    "Elegant": ["エレガント"],
    "Yume Kawaii": ["ゆめかわいい", "ゆめかわ"],
    "Simple": ["シンプル"],
    "Japanese Style": ["和風", "和装"],
    "Classical": ["クラシック", "クラシカル"],
    "Refined": ["きれいめ"],
    "Mature": ["大人っぽい", "お姉さん"],
    "Cyberpunk": ["サイバーパンク"],
    "Near-Future": ["近未来"],
    "Yami Kawaii": ["病みかわいい", "病みかわ"],
    "Boyish": ["ボーイッシュ"],
    "Sci-Fi": ["sf", "サイファイ"],
    "Realistic": ["リアル"],
    "Military": ["ミリタリー"],
    "Cyber": ["サイバー"],
    "Jirai Kei": ["地雷系", "地雷"],
    "Pop": ["ポップ"],
    "Mecha": ["メカ", "ロボ"],
    "Animal Motif": ["アニマル", "動物"],
    "School": ["学生", "スクール"],
    "Sporty": ["スポーティー"],
    "Horror": ["ホラー"],
    "Feminine": ["フェミニン"],
    "Lolita": ["ロリータ"],
    "Tactical": ["タクティカル"],
    "Maid": ["メイド"],
    "Kemono": ["ケモノ"],
    "Subculture": ["サブカル"],
    "Y2K": ["y2k"],
    "Antique": ["アンティーク"],
    "Fancy": ["ファンシー"],
    "Formal": ["フォーマル"],
    "Idol": ["アイドル"],
    "Steampunk": ["スチームパンク"],
    "Space": ["宇宙", "スペース"],
    "Gyaru": ["ギャル"],
    "Ryousankata": ["量産型"],
    "Vampire": ["吸血鬼", "ヴァンパイア"],
    "Anime": ["アニメ"],
    "Vintage": ["ヴィンテージ"],
    "Princess": ["プリンセス"],
    "Neon": ["ネオン"],
    "Wedding": ["ウェディング", "ブライダル"],
    "Battle": ["バトル", "戦闘", "戦う"],
    "Chic": ["シック", "上品"],
    "Chinese Style": ["中華", "チャイナ", "チャイナ服", "中華風"],
    "Cosplay": ["コスプレ", "cosplay"],
    "Comical": ["コミカル"],
    "Funny": ["おもしろい", "面白い", "ウケる"],
    "Joke": ["ジョーク", "ネタ", "ネタ系"],
    "Mysterious": ["ミステリアス", "神秘的"],
    "Modest": ["控えめ", "地味"],
    "Horror": ["ホラー", "怖い", "怪談"],
    "Feminine": ["フェミニン"],
    "Heartwarming": ["ほっこり", "温かい"],
    "Sparkly": ["キラキラ", "きらきら"],
    "Fluffy": ["ふわふわ", "もこもこ", "モコモコ"],
    "For Men": ["男性向け", "メンズ向け", "男用"],
    "Relaxed": ["リラックス", "部屋着"],
    "Real Clothes": ["リアルクローズ", "普段着", "私服"],
    "Fashionable": ["お洒落", "おしゃれ", "ファッショナブル"],
    "Unique": ["個性的", "ユニーク"],
    "Modern": ["モダン", "現代的"],
    "Ethereal": ["幻想的", "幽玄"],
    "Clean Style": ["きれいめ", "上品", "清楚"],
    "Maid": ["メイド", "メイド服"],
    "Kemono": ["ケモノ", "けもの", "獣"],
    "Mystical": ["神秘的", "ミスティカル"],
    "Mode": ["モード", "モード系"],
    "Chuunibyou": ["中二病", "ちゅうにびょう"],
    "Fancy": ["ファンシー"],
    "Marine": ["マリン", "海", "水兵"],
    "Bondage": ["ボンデージ", "拘束"],
    "Everyday": ["日常", "デイリー"],
    "Unisex": ["ユニセックス", "男女兼用"],
    "Gothic Lolita": ["ゴスロリ", "ゴシックロリータ"],
    "Resort": ["リゾート"],
    "Sweets": ["スイーツ", "お菓子"],
    "Game": ["ゲーム", "ゲーマー"],
    "Mechanical": ["メカニカル", "機械的"],
    "Grunge": ["グランジ"],
    "Stylish": ["スタイリッシュ"],
    "Glamorous": ["グラマラス"],
    "Cafe": ["カフェ"],
    "Little Devil": ["小悪魔", "こあくま"],
    "Wild": ["ワイルド"],
    "Fetish": ["フェティッシュ", "フェチ"],
    "Magic": ["魔法", "マジック"],
    "Magical Girl": ["魔法少女"],
    "Rock": ["ロック"],
    "Religious": ["宗教的", "シスター", "神父"],
    "Gorgeous": ["ゴージャス", "豪華"],
    "Onee-san Style": ["お姉さん", "お姉さん系"],
    "Humor": ["ユーモア", "おもしろ"],
    "Fairytale": ["メルヘン", "おとぎ話"],
    "Colorful": ["カラフル"],
    "Nostalgic": ["ノスタルジック", "懐かしい"],
    "Exotic": ["エキゾチック", "異国情緒"],
    "Minimal": ["ミニマル", "最小限"],
    "Medieval": ["中世", "中世風"],
    "Soft & Relaxed": ["やわらかい", "ふんわり"],
    "Pastel": ["パステル", "パステルカラー"],
    "Refreshing": ["さわやか", "爽やか"],
    "Princess": ["プリンセス", "お姫様"],
    "Intellectual": ["インテリ", "知的", "メガネ"],
    "Doll": ["ドール", "人形"],
    "Korean Style": ["韓国風", "オルチャン"],
    "Ojou-sama": ["お嬢様", "お嬢さま"],
    "Surreal": ["シュール"],
    "Calm": ["落ち着いた", "静か"],
    "Ethnic": ["エスニック", "民族調"],
    "Emo": ["エモ", "エモい"],
    "Luxury": ["ラグジュアリー", "高級"],
    "Energetic": ["エネルギッシュ", "活発"],
    "Lovely": ["ラブリー"],
    "Industrial": ["インダストリアル", "工業的"],
    "Mori Girl": ["森ガール"],
    "Taisho Roman": ["大正ロマン", "大正浪漫"],
    "Post-Apocalyptic": ["終末もの", "ポストアポカリプス"],
    "Androgynous": ["アンドロジナス", "中性的"],
    "Western": ["ウェスタン", "西部劇"],
    "Ninja": ["忍者", "ニンジャ"],
    "Harajuku Style": ["原宿系"],
    "American Casual": ["アメカジ", "アメリカンカジュアル"],
    "Fairy": ["フェアリー", "妖精"],
    "Decora": ["デコラ"],
    "Practical": ["実用的"],
    "Bewitching": ["妖艶な", "あでやか"],
    "Retro-Futuristic": ["レトロフューチャー"],
    "Cartoon": ["カートゥーン", "アニメ調"],
    "Premium Feel": ["高級感"],
    "Daily": ["デイリー", "普段着"],
    "Valentine": ["バレンタイン"],
    "Preppy": ["プレッピー"],

    # Body Type
    "Female": ["女性", "レディース", "女の子", "female", "feminine"],
    "Male": ["男性", "メンズ", "男の子", "male", "masculine"],
    "Chibi": ["ちび", "デフォルメ", "sd", "chibi"],

    # Color
    "Black": ["黒", "black", "ブラック"],
    "White": ["白", "white", "ホワイト"],
    "Pink": ["ピンク", "pink"],
    "Red": ["赤", "red", "レッド"],
    "Blue": ["青", "blue", "ブルー"],
    "Brown": ["茶", "brown", "ブラウン"],
    "Light Blue": ["水色", "light blue", "ライトブルー"],
    "Purple": ["紫", "purple", "パープル"],
    "Silver": ["銀", "silver", "シルバー"],
    "Gray": ["灰", "gray", "grey", "グレー"],
    "Gold": ["金", "gold", "ゴールド"],
    "Green": ["緑", "green", "グリーン"],
    "Beige": ["ベージュ", "beige"],
    "Pastel": ["パステル", "pastel"],
    "Navy": ["紺", "navy", "ネイビー"],
    "Orange": ["橙", "orange", "オレンジ"],
    "Yellow": ["黄", "yellow", "イエロー"],
    "Neon": ["ネオン", "neon"],
    "Khaki": ["カーキ", "khaki"],
    "Lavender": ["ラベンダー", "lavender"],
    "Bordeaux": ["ボルドー", "bordeaux"],
    "Cream": ["クリーム", "cream"],
    "Turquoise": ["ターコイズ", "turquoise"],
    "Mint": ["ミント", "mint"],
    "Cyan": ["シアン", "cyan"],
    "Ivory": ["アイボリー", "ivory"],

    # Platform
    "VRChat": ["vrchat", "vrc"],
    "Unity": ["unity"],
    "Cluster": ["cluster"],

    # Season
    "Winter": ["冬", "winter", "ウィンター", "雪"],
    "Summer": ["夏", "summer", "サマー", "水着"],
    "Halloween": ["ハロウィン", "halloween"],
    "Spring": ["春", "spring", "スプリング", "桜"],
    "Autumn": ["秋", "autumn", "fall", "オータム", "紅葉"],
    "Christmas": ["クリスマス", "christmas"],
    "New Year": ["正月", "新年", "new year"],
}

def load_parsed_tags() -> dict[str, list[str]]:
    with open(PARSED_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def run_evolution():
    parsed = load_parsed_tags()
    
    # 1. Update tags.yaml
    with open(TAGS_PATH, "r", encoding="utf-8") as f:
        tags_data = yaml.safe_load(f)
        
    # Initialize sections if not present
    for key in ["outfit_types", "accessories", "appearances", "colors", "body_types", "platforms", "seasons"]:
        if key not in tags_data:
            tags_data[key] = {}
            
    # Map Outfit Type to outfit_types
    for t in parsed.get("Outfit Type", []):
        aliases = list(set([t, t.lower()] + TRANSLATIONS.get(t, [])))
        tags_data["outfit_types"][t] = {"aliases": aliases}
        
    # Map Accessory to accessories
    for t in parsed.get("Accessory", []):
        aliases = list(set([t, t.lower()] + TRANSLATIONS.get(t, [])))
        tags_data["accessories"][t] = {"aliases": aliases}

    # Map Appearance to appearances
    for t in parsed.get("Appearance", []):
        aliases = list(set([t, t.lower()] + TRANSLATIONS.get(t, [])))
        tags_data["appearances"][t] = {"aliases": aliases}

    # Map Color to colors
    for t in parsed.get("Color", []):
        aliases = list(set([t, t.lower()] + TRANSLATIONS.get(t, [])))
        tags_data["colors"][t] = {"aliases": aliases}

    # Map Body Type to body_types
    body_types_list = list(parsed.get("Body Type", []))
    for bt in ["Female", "Male"]:
        if bt not in body_types_list:
            body_types_list.append(bt)
    for t in body_types_list:
        aliases = list(set([t, t.lower()] + TRANSLATIONS.get(t, [])))
        tags_data["body_types"][t] = {"aliases": aliases}

    # Map Platform to platforms
    for t in parsed.get("Platform", []):
        aliases = list(set([t, t.lower()] + TRANSLATIONS.get(t, [])))
        tags_data["platforms"][t] = {"aliases": aliases}

    # Map Season to seasons
    for t in parsed.get("Season", []):
        aliases = list(set([t, t.lower()] + TRANSLATIONS.get(t, [])))
        tags_data["seasons"][t] = {"aliases": aliases}

    # Update features (if any new feature parsed)
    for t in parsed.get("Feature", []):
        if t not in tags_data["features"]:
            aliases = list(set([t, t.lower()] + TRANSLATIONS.get(t, [])))
            tags_data["features"][t] = {"aliases": aliases}

    with open(TAGS_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(tags_data, f, allow_unicode=True, default_flow_style=False)
        
    # 2. Update styles.yaml
    with open(STYLES_PATH, "r", encoding="utf-8") as f:
        styles_data = yaml.safe_load(f)
        
    if "styles" not in styles_data:
        styles_data["styles"] = {}
        
    for t in parsed.get("Style", []):
        # Merge existing if present
        existing = styles_data["styles"].get(t, [])
        aliases = list(set([t, t.lower()] + existing + TRANSLATIONS.get(t, [])))
        styles_data["styles"][t] = aliases
        
    with open(STYLES_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(styles_data, f, allow_unicode=True, default_flow_style=False)

    print("Ontology YAML files successfully evolved with VRCFinder tags!")

if __name__ == "__main__":
    run_evolution()
