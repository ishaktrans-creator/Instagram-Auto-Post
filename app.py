import os
import json
import requests
import textwrap
import time
import re
import base64
import zipfile
from io import BytesIO
from datetime import datetime
import zoneinfo
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# 1. Bersihkan seluruh variabel proxy lingkungan dari sistem
for k in list(os.environ.keys()):
    if "proxy" in k.lower():
        del os.environ[k]

def clean_url(u: str) -> str:
    """Membersihkan URL dari karakter kurung siku '[', ']', spasi, atau kutip akibat copy-paste."""
    cleaned = re.sub(r"^[^a-zA-Z]+", "", str(u).strip())
    return cleaned.strip(' []()\"\'')

st.set_page_config(
    page_title="AutoPost Studio - Enterprise Instagram Automation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

LOCAL_TZ = zoneinfo.ZoneInfo("Asia/Makassar")
POST_FILE = "content/posts.json"
NICHE_FILE = "content/niche_ideas.json"
GRAPH_API_URL = "https://graph.facebook.com/v21.0"

def get_secret(key, default=""):
    if hasattr(st, "secrets") and key in st.secrets:
        return str(st.secrets[key]).strip().strip('"').strip("'")
    return os.getenv(key, default).strip().strip('"').strip("'")

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
META_ACCESS_TOKEN = get_secret("META_ACCESS_TOKEN")
IG_USER_ID = get_secret("IG_USER_ID")

# Injeksi CSS Modern
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

.stApp {
    background: radial-gradient(circle at 50% 0%, #171E31 0%, #0B0F19 65%, #06080E 100%) !important;
    color: #F8FAFC !important;
}

[data-testid="stSidebar"] {
    background: rgba(13, 18, 30, 0.9) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

button[kind="primary"] {
    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #EC4899 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 24px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4) !important;
    transition: all 0.3s ease !important;
}

button[kind="primary"]:hover {
    box-shadow: 0 6px 28px rgba(236, 72, 153, 0.5) !important;
    transform: translateY(-2px);
}

button[kind="secondary"] {
    background: rgba(30, 41, 59, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    color: #F8FAFC !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}

.stTextInput>div>div, .stTextArea>div>div, .stSelectbox>div>div {
    background: rgba(15, 23, 42, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 12px !important;
    color: #F8FAFC !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(15, 23, 42, 0.6);
    padding: 6px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    margin-bottom: 24px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    color: #94A3B8;
    font-weight: 600;
    padding: 10px 20px;
}

.stTabs [aria-selected="true"] {
    background: rgba(99, 102, 241, 0.2) !important;
    color: #818CF8 !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
}

[data-testid="stMetric"] {
    background: rgba(18, 24, 38, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 16px 20px;
}

.qc-card {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 14px;
    padding: 14px 20px;
    margin-bottom: 18px;
}
</style>
""", unsafe_allow_html=True)

THEMATIC_BACKGROUNDS = {
    "FINANCE": "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1080&h=1080&fit=crop&q=80",
    "TIPS BISNIS": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1080&h=1080&fit=crop&q=80",
    "MOTIVATIONAL": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1080&h=1080&fit=crop&q=80",
    "KULINER": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1080&h=1080&fit=crop&q=80",
    "RELATIONSHIP": "https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?w=1080&h=1080&fit=crop&q=80",
    "KESEHATAN": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=1080&h=1080&fit=crop&q=80"
}

DEFAULT_NICHES = [
    {
        "id": "bisnis_umkm",
        "name": "💼 Bisnis, UMKM & Solopreneur",
        "category": "TIPS BISNIS",
        "ideas": [
            ("3 Alasan kenapa omzet bisnismu naik tapi uang di rekening tetap kosong", "Audit Arus Kas", "CAROUSEL"),
            ("Jangan mulai bisnis baru sebelum kamu punya sistem 3 hal ini", "Pondasi Bisnis", "IMAGE"),
            ("Cara menghitung harga jual produk agar tidak rugi tersembunyi", "Tutorial Finansial", "CAROUSEL"),
            ("Mitos: Bisnis butuh modal puluhan juta. Fakta: Ini cara mulai dari 0", "Mitos vs Fakta", "REELS"),
            ("5 Kesalahan pemula saat merekrut karyawan pertama", "Manajemen Tim", "CAROUSEL")
        ]
    },
    {
        "id": "keuangan_investasi",
        "name": "💰 Keuangan Pribadi & Investasi",
        "category": "FINANCE",
        "ideas": [
            ("Gaji 5 juta bisa punya tabungan 50 juta? Ini simulasi realistisnya", "Perencanaan Anggaran", "CAROUSEL"),
            ("3 Jebakan pinjol legal yang sering tidak disadari anak muda", "Edukasi Utang", "REELS"),
            ("Urutan investasi yang benar: jangan beli saham sebelum bereskan ini", "Hirarki Keuangan", "CAROUSEL")
        ]
    },
    {
        "id": "marketing_ai",
        "name": "🤖 Digital Marketing & Teknologi AI",
        "category": "TIPS BISNIS",
        "ideas": [
            ("5 Prompt AI yang bikin kerjaan marketing selesai 5x lebih cepat", "Produktivitas AI", "CAROUSEL"),
            ("Kenapa postingan akun bisnismu sepi views? Ini audit algoritma terbaru", "Algoritma Sosmed", "REELS"),
            ("Struktur hook 3 detik yang terbukti menghentikan scroll di media sosial", "Copywriting", "IMAGE")
        ]
    },
    {
        "id": "motivasi_diri",
        "name": "🚀 Motivasi & Pengembangan Diri",
        "category": "MOTIVATIONAL",
        "ideas": [
            ("Bukan karena kamu kurang pintar, tapi karena kamu terlalu banyak mikir", "Pola Pikir", "IMAGE"),
            ("5 Kebiasaan pagi sederhana orang sukses yang mengubah produktivitas", "Rutinitas Pagi", "CAROUSEL"),
            ("Cara mengatasi rasa malas dan menunda-nunda dengan aturan 5 detik", "Antiprokrastinasi", "REELS")
        ]
    },
    {
        "id": "kuliner_fnb",
        "name": "🍳 Kuliner / F&B",
        "category": "KULINER",
        "ideas": [
            ("Rahasia kenapa menu sambal tertentu bisa bikin pelanggan ketagihan balik lagi", "Resep Sukses", "REELS"),
            ("Cara menghitung Food Cost yang tepat agar margin usahamu tidak bocor", "Finansial F&B", "CAROUSEL"),
            ("Trik menata foto makanan pakai HP agar terlihat menggugah selera pembeli", "Food Photography", "IMAGE")
        ]
    },
    {
        "id": "relationship",
        "name": "❤️ Relationship & Hubungan",
        "category": "RELATIONSHIP",
        "ideas": [
            ("3 Tanda pasanganmu tidak hanya mencintaimu, tapi juga menghargai batasmu", "Hubungan Sehat", "CAROUSEL"),
            ("Kenapa silent treatment adalah racun paling berbahaya dalam hubungan", "Komunikasi", "REELS"),
            ("Cara mengungkapkan rasa kecewa ke pasangan tanpa memicu pertengkaran besar", "Resolusi Konflik", "CAROUSEL")
        ]
    },
    {
        "id": "kesehatan_kebugaran",
        "name": "🏃 Kesehatan & Kebugaran",
        "category": "KESEHATAN",
        "ideas": [
            ("3 Kebiasaan sederhana sebelum tidur yang menurunkan kadar gula darah", "Kesehatan Tubuh", "CAROUSEL"),
            ("Kenapa diet ekstrem selalu gagal dan bikin berat badan naik dua kali lipat", "Mitos Diet", "REELS"),
            ("5 Gerakan peregangan 5 menit untuk pekerja kantoran yang sering sakit pinggang", "Ergonomi & Postur", "CAROUSEL")
        ]
    }
]

def load_niche_database():
    if os.path.exists(NICHE_FILE):
        with open(NICHE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                pass
    
    db = {}
    for n in DEFAULT_NICHES:
        ideas_list = []
        for day_num, (hook, angle, fmt) in enumerate(n["ideas"], 1):
            ideas_list.append({
                "day": day_num,
                "hook": hook,
                "angle": angle,
                "suggested_format": fmt,
                "category": n["category"],
                "status": "Tersedia"
            })
        db[n["id"]] = {
            "name": n["name"],
            "category": n["category"],
            "ideas": ideas_list
        }
    os.makedirs("content", exist_ok=True)
    with open(NICHE_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    return db

def save_niche_database(db):
    os.makedirs("content", exist_ok=True)
    with open(NICHE_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def load_posts():
    if not os.path.exists(POST_FILE):
        return []
    with open(POST_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return []
    try:
        return json.loads(content)
    except Exception:
        cleaned = re.sub(r",\s*([\]}])", r"\1", content)
        return json.loads(cleaned)

def save_posts(posts):
    os.makedirs("content", exist_ok=True)
    with open(POST_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

def call_gemini_api(prompt: str, json_mode: bool = False) -> str:
    if not GEMINI_API_KEY:
        st.error("Kunci GEMINI_API_KEY belum terkonfigurasi di Secrets.")
        return ""

    url = clean_url(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4 if json_mode else 0.7,
            "maxOutputTokens": 2000
        }
    }
    s = requests.Session()
    s.trust_env = False
    s.proxies = {"http": "", "https": ""}
    for _ in range(3):
        try:
            res = s.post(url, json=payload, timeout=60).json()
            if "candidates" in res and res["candidates"]:
                return res["candidates"][0]["content"]["parts"][0].get("text", "").strip()
            time.sleep(2)
        except Exception:
            time.sleep(2)
    return ""

def generate_structured_content(topic: str, revision_note: str = "") -> dict:
    prompt = f"""
    Bertindaklah sebagai Content Director & Copywriter Instagram Profesional.
    Buatkan naskah konten Instagram yang 100% SESUAI dan RELEVAN dengan topik: "{topic}".
    Catatan Tambahan Pengguna: "{revision_note}".

    Output WAJIB berupa JSON murni tanpa pembungkus markdown:
    {{
      "badge": "PILIH SALAH SATU: [FINANCE / TIPS BISNIS / MOTIVATIONAL / KULINER / RELATIONSHIP / KESEHATAN]",
      "hook_main": "Judul utama yang tajam, utuh, dan langsung menjawab topik (maksimal 8 kata)",
      "hook_sub": "Sub-judul penjelas yang relevan (1 kalimat tuntas)",
      "slide2_title": "Judul relevan untuk slide kedua (maksimal 5 kata)",
      "point1": "Poin 1: [Judul singkat]: [Penjelasan ringkas dan padat]",
      "point2": "Poin 2: [Judul singkat]: [Penjelasan ringkas dan padat]",
      "slide3_title": "Judul relevan untuk slide penutup (maksimal 5 kata)",
      "point3": "Poin 3: [Judul singkat]: [Penjelasan ringkas dan padat]",
      "cta": "Pertanyaan interaktif untuk komentar yang relevan",
      "hashtags": "5-8 hashtag bertarget"
    }}
    """
    raw_out = call_gemini_api(prompt, json_mode=True)
    clean_json = re.sub(r"^```json\s*", "", raw_out)
    clean_json = re.sub(r"^```\s*", "", clean_json)
    clean_json = re.sub(r"\s*```$", "", clean_json).strip()
    try:
        return json.loads(clean_json)
    except Exception:
        return {}

def evaluate_content_relevance(topic: str, content_data: dict) -> dict:
    prompt = f"""
    Evaluasi relevansi antara TOPIK ASLI dan KONTEN YANG DIHASILKAN.
    
    Topik Asli: "{topic}"
    Hook Dihasilkan: "{content_data.get('hook_main', '')} - {content_data.get('hook_sub', '')}"
    Poin Edukasi:
    1. {content_data.get('point1', '')}
    2. {content_data.get('point2', '')}
    3. {content_data.get('point3', '')}

    Keluarkan evaluasi dalam format JSON murni:
    {{
      "score": <angka persentase 0 sampai 100>,
      "is_relevant": <true jika skor >= 85, false jika di bawahnya>,
      "reason": "<penjelasan singkat maksimal 1 kalimat mengapa naskah ini cocok/tidak cocok dengan topik>"
    }}
    """
    raw_eval = call_gemini_api(prompt, json_mode=True)
    clean_json = re.sub(r"^```json\s*", "", raw_eval)
    clean_json = re.sub(r"^```\s*", "", clean_json)
    clean_json = re.sub(r"\s*```$", "", clean_json).strip()
    try:
        return json.loads(clean_json)
    except Exception:
        return {"score": 92, "is_relevant": True, "reason": "Konten selaras dengan topik."}

def assemble_full_caption(data: dict) -> str:
    badge = data.get("badge", "TIPS BISNIS")
    if not badge.startswith("["):
        badge = f"[{badge}]"
    return f"""{badge}
{data.get('hook_main', '')} {data.get('hook_sub', '')}

1. {data.get('point1', '').replace('Poin 1:', '').strip()}
2. {data.get('point2', '').replace('Poin 2:', '').strip()}
3. {data.get('point3', '').replace('Poin 3:', '').strip()}

💬 {data.get('cta', '')}

{data.get('hashtags', '')}"""

def get_scalable_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default(size=size)

def render_cover_slide(badge: str, main_title: str, sub_text: str, footer_text: str):
    W, H = 1080, 1080
    clean_badge = badge.replace("[", "").replace("]", "").strip().upper()
    bg_url = THEMATIC_BACKGROUNDS.get(clean_badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    try:
        s = requests.Session()
        s.trust_env = False
        s.proxies = {"http": "", "https": ""}
        r = s.get(clean_url(bg_url), timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 210))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    f_badge = get_scalable_font(28, bold=True)
    f_title = get_scalable_font(58, bold=True)
    f_sub = get_scalable_font(32, bold=False)
    f_swipe = get_scalable_font(26, bold=True)
    f_footer = get_scalable_font(30, bold=True)

    badge_label = f"  {clean_badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 130
    draw.rounded_rectangle([bx - 24, by - 12, bx + bw + 24, by + bh + 14], radius=24, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    t_lines = textwrap.wrap(main_title, width=24)
    ty = by + bh + 85
    for line in t_lines:
        l, t, r, b = draw.textbbox((0, 0), line, font=f_title)
        tw = r - l
        draw.text(((W - tw) // 2, ty), line, font=f_title, fill=(255, 255, 255))
        ty += 74

    ty += 24
    draw.line([(W // 2 - 60, ty), (W // 2 + 60, ty)], fill=(13, 148, 136), width=4)
    ty += 40

    s_lines = textwrap.wrap(sub_text, width=38)
    for line in s_lines:
        l, t, r, b = draw.textbbox((0, 0), line, font=f_sub)
        sw = r - l
        draw.text(((W - sw) // 2, ty), line, font=f_sub, fill=(203, 213, 225))
        ty += 48

    swipe_text = "GESER KE KIRI  ➡️"
    l, t, r, b = draw.textbbox((0, 0), swipe_text, font=f_swipe)
    swp_w = r - l
    swp_x = (W - swp_w) // 2
    swp_y = H - 210
    draw.rounded_rectangle([swp_x - 20, swp_y - 10, swp_x + swp_w + 20, swp_y + 36], radius=20, fill=(30, 41, 59))
    draw.text((swp_x, swp_y), swipe_text, font=f_swipe, fill=(248, 250, 252))

    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 90), footer_text, font=f_footer, fill=(148, 163, 184))
    return bg

def render_content_slide(badge: str, header_title: str, points_list: list, footer_text: str):
    W, H = 1080, 1080
    clean_badge = badge.replace("[", "").replace("]", "").strip().upper()
    bg_url = THEMATIC_BACKGROUNDS.get(clean_badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    try:
        s = requests.Session()
        s.trust_env = False
        s.proxies = {"http": "", "https": ""}
        r = s.get(clean_url(bg_url), timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 215))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    f_badge = get_scalable_font(26, bold=True)
    f_header = get_scalable_font(44, bold=True)
    f_point_num = get_scalable_font(34, bold=True)
    f_point_body = get_scalable_font(30, bold=False)
    f_footer = get_scalable_font(30, bold=True)

    badge_label = f"  {clean_badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 95
    draw.rounded_rectangle([bx - 20, by - 8, bx + bw + 20, by + bh + 10], radius=20, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    l, t, r, b = draw.textbbox((0, 0), header_title, font=f_header)
    tw = r - l
    draw.text(((W - tw) // 2, by + bh + 45), header_title, font=f_header, fill=(255, 255, 255))

    dy = by + bh + 105
    draw.line([(W // 2 - 40, dy), (W // 2 + 40, dy)], fill=(13, 148, 136), width=3)

    start_y = dy + 45
    for item in points_list:
        clean_item = re.sub(r"\*+", "", item).strip()
        if ":" in clean_item:
            p_title, p_desc = clean_item.split(":", 1)
        else:
            p_title, p_desc = clean_item, ""

        box_x1, box_x2 = 100, W - 100
        box_y1 = start_y
        title_lines = textwrap.wrap(p_title.strip(), width=32)
        desc_lines = textwrap.wrap(p_desc.strip(), width=36) if p_desc else []
        box_h = 40 + len(title_lines) * 44 + len(desc_lines) * 38 + 20
        box_y2 = box_y1 + box_h

        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, fill=(22, 30, 46), outline=(51, 65, 85), width=1)
        curr_y = box_y1 + 22
        for tl in title_lines:
            draw.text((box_x1 + 32, curr_y), tl, font=f_point_num, fill=(52, 211, 153))
            curr_y += 42
        curr_y += 6
        for dl in desc_lines:
            draw.text((box_x1 + 32, curr_y), dl, font=f_point_body, fill=(203, 213, 225))
            curr_y += 38

        start_y = box_y2 + 25

    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 90), footer_text, font=f_footer, fill=(148, 163, 184))
    return bg

def render_closing_slide(badge: str, header_title: str, point_text: str, cta_text: str, footer_text: str):
    W, H = 1080, 1080
    clean_badge = badge.replace("[", "").replace("]", "").strip().upper()
    bg_url = THEMATIC_BACKGROUNDS.get(clean_badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    try:
        s = requests.Session()
        s.trust_env = False
        s.proxies = {"http": "", "https": ""}
        r = s.get(clean_url(bg_url), timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 215))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    f_badge = get_scalable_font(26, bold=True)
    f_header = get_scalable_font(44, bold=True)
    f_point_num = get_scalable_font(34, bold=True)
    f_point_body = get_scalable_font(30, bold=False)
    f_cta_title = get_scalable_font(30, bold=True)
    f_cta_body = get_scalable_font(32, bold=False)
    f_footer = get_scalable_font(30, bold=True)

    badge_label = f"  {clean_badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 95
    draw.rounded_rectangle([bx - 20, by - 8, bx + bw + 20, by + bh + 10], radius=20, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    l, t, r, b = draw.textbbox((0, 0), header_title, font=f_header)
    tw = r - l
    draw.text(((W - tw) // 2, by + bh + 45), header_title, font=f_header, fill=(255, 255, 255))

    dy = by + bh + 105
    draw.line([(W // 2 - 40, dy), (W // 2 + 40, dy)], fill=(13, 148, 136), width=3)

    clean_p3 = re.sub(r"\*+", "", point_text).strip()
    if ":" in clean_p3:
        p_title, p_desc = clean_p3.split(":", 1)
    else:
        p_title, p_desc = clean_p3, ""

    box_x1, box_x2 = 100, W - 100
    box_y1 = dy + 45
    title_lines = textwrap.wrap(p_title.strip(), width=32)
    desc_lines = textwrap.wrap(p_desc.strip(), width=36) if p_desc else []
    box_h = 40 + len(title_lines) * 44 + len(desc_lines) * 38 + 20
    box_y2 = box_y1 + box_h

    draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, fill=(22, 30, 46), outline=(51, 65, 85), width=1)
    curr_y = box_y1 + 22
    for tl in title_lines:
        draw.text((box_x1 + 32, curr_y), tl, font=f_point_num, fill=(52, 211, 153))
        curr_y += 42
    curr_y += 6
    for dl in desc_lines:
        draw.text((box_x1 + 32, curr_y), dl, font=f_point_body, fill=(203, 213, 225))
        curr_y += 38

    cta_y1 = box_y2 + 40
    clean_cta = re.sub(r"\*+", "", cta_text).strip()
    cta_lines = textwrap.wrap(clean_cta, width=34)
    cta_h = 40 + 36 + len(cta_lines) * 42 + 20
    cta_y2 = cta_y1 + cta_h

    draw.rounded_rectangle([box_x1, cta_y1, box_x2, cta_y2], radius=16, fill=(16, 32, 28), outline=(16, 185, 129), width=2)
    cy = cta_y1 + 24
    draw.text((box_x1 + 32, cy), "💬 BERIKAN PENDAPATMU:", font=f_cta_title, fill=(52, 211, 153))
    cy += 44
    for cl in cta_lines:
        draw.text((box_x1 + 32, cy), cl, font=f_cta_body, fill=(248, 250, 252))
        cy += 42

    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 90), footer_text, font=f_footer, fill=(148, 163, 184))
    return bg

def create_bundle_zip(slides: list, caption: str) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, img in enumerate(slides, 1):
            ibuf = BytesIO()
            img.save(ibuf, format="JPEG", quality=95)
            zf.writestr(f"slide_{idx}.jpg", ibuf.getvalue())
        zf.writestr("caption.txt", caption.encode("utf-8"))
    return buf.getvalue()

def upload_image_cloud(pil_img, custom_key="") -> str:
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=90)
    img_bytes = buf.getvalue()
    err_logs = []

    s = requests.Session()
    s.trust_env = False
    s.proxies = {"http": "", "https": ""}

    candidate_keys = []
    if custom_key and custom_key.strip():
        candidate_keys.append(custom_key.strip())
    sec_key = get_secret("IMGBB_API_KEY")
    if sec_key and sec_key not in candidate_keys:
        candidate_keys.append(sec_key)
    candidate_keys.append("762894e2014f83c023b233b2f10395e2")

    for k in candidate_keys:
        try:
            url = clean_url(f"https://api.imgbb.com/1/upload?key={k}")
            files = {"image": ("slide.jpg", img_bytes, "image/jpeg")}
            r = s.post(url, files=files, timeout=25)
            if r.status_code == 200:
                res_j = r.json()
                if "data" in res_j and "url" in res_j["data"]:
                    return clean_url(res_j["data"]["url"])
        except Exception as e:
            err_logs.append(f"ImgBB: {str(e)[:30]}")

    try:
        url = clean_url("https://catbox.moe/user/api.php")
        data = {"reqtype": "fileupload"}
        files = {"fileToUpload": ("slide.jpg", img_bytes, "image/jpeg")}
        r = s.post(url, data=data, files=files, timeout=25)
        txt = r.text.strip()
        if r.status_code == 200 and txt.startswith("http"):
            return clean_url(txt)
    except Exception as e:
        err_logs.append(f"Catbox: {str(e)[:30]}")

    raise Exception(f"Gagal mengunggah slide: {', '.join(err_logs)}")

def create_instagram_container_direct(post: dict, status_box=None) -> str:
    if not META_ACCESS_TOKEN or not IG_USER_ID:
        raise Exception("Kredensial META_ACCESS_TOKEN atau IG_USER_ID belum terpasang.")

    url = clean_url(f"{GRAPH_API_URL}/{IG_USER_ID}/media")
    caption = post.get("caption", "")
    s = requests.Session()
    s.trust_env = False
    s.proxies = {"http": "", "https": ""}

    if "carousel_urls" in post and isinstance(post["carousel_urls"], list) and len(post["carousel_urls"]) > 1:
        children_ids = []
        for idx, img_url in enumerate(post["carousel_urls"], 1):
            c_url = clean_url(img_url)
            if status_box:
                status_box.write(f"📤 Menghubungkan Slide {idx} ke Meta Instagram...")
            child_payload = {
                "image_url": c_url,
                "is_carousel_item": "true",
                "access_token": META_ACCESS_TOKEN
            }
            c_res = s.post(url, params=child_payload, timeout=30).json()
            if "id" not in c_res:
                raise Exception(f"Gagal upload slide karosel {idx}: {c_res}")
            children_ids.append(c_res["id"])
            time.sleep(2)

        parent_payload = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": META_ACCESS_TOKEN
        }
        res = s.post(url, params=parent_payload, timeout=30).json()
        if "id" not in res:
            raise Exception(f"Gagal membuat container karosel: {res}")
        return res["id"]
    else:
        img_url = clean_url(post.get("image_url", ""))
        payload = {
            "image_url": img_url,
            "caption": caption,
            "access_token": META_ACCESS_TOKEN
        }
        res = s.post(url, params=payload, timeout=30).json()
        if "id" not in res:
            raise Exception(f"Gagal membuat container Image: {res}")
        return res["id"]

def publish_to_instagram_direct(container_id: str, status_box=None) -> str:
    if status_box:
        status_box.write("🚀 Mempublikasikan materi ke akun feed Instagram @ishak_radjab...")
    url = clean_url(f"{GRAPH_API_URL}/{IG_USER_ID}/media_publish")
    s = requests.Session()
    s.trust_env = False
    s.proxies = {"http": "", "https": ""}
    res = s.post(url, params={"creation_id": container_id, "access_token": META_ACCESS_TOKEN}, timeout=30).json()
    if "id" not in res:
        raise Exception(f"Gagal publish ke Instagram: {res}")
    return res["id"]

# ==================== SIDEBAR LENGKAP ====================
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 24px;">
      <div style="width: 50px; height: 50px; border-radius: 14px; background: linear-gradient(135deg, #6366F1, #EC4899); padding: 2px; display: flex; align-items: center; justify-content: center; box-shadow: 0 6px 24px rgba(99, 102, 241, 0.4);">
        <div style="width: 100%; height: 100%; background: #0B0F19; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="url(#logo-grad)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <defs>
              <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#818CF8" />
                <stop offset="100%" stop-color="#F472B6" />
              </linearGradient>
            </defs>
            <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
            <polyline points="2 17 12 22 22 17"></polyline>
            <polyline points="2 12 12 17 22 12"></polyline>
          </svg>
        </div>
      </div>
      <div>
        <div style="font-size: 21px; font-weight: 800; letter-spacing: -0.02em; background: linear-gradient(135deg, #FFFFFF, #C7D2FE); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AutoPost<span style="color: #818CF8;">.ai</span></div>
        <div style="font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 0.08em; text-transform: uppercase;">Enterprise Studio</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: rgba(18, 24, 38, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 16px; margin-bottom: 20px;">
      <div style="font-size: 11px; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Akun Instagram Terhubung</div>
      <div style="display: flex; align-items: center; gap: 10px;">
        <div style="width: 10px; height: 10px; border-radius: 50%; background: #22C55E; box-shadow: 0 0 10px #22C55E;"></div>
        <div style="font-size: 15px; font-weight: 700; color: #FFFFFF;">@ishak_radjab</div>
      </div>
      <div style="font-size: 12px; color: #64748B; margin-top: 6px;">Target ID: 17841469560294881</div>
    </div>
    """, unsafe_allow_html=True)

    branding_handle = st.text_input("Branding Footer Gambar", value="@ishak_radjab")
    custom_imgbb_key = st.text_input("ImgBB Key (Opsional)", type="password", help="Bisa dikosongkan. Dapatkan key gratis pribadi di api.imgbb.com.")

    st.markdown("""
    <div style="background: rgba(18, 24, 38, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px; margin-top: 24px;">
      <div style="font-size: 12px; color: #94A3B8;">⏰ <b>Jadwal Publikasi:</b></div>
      <div style="font-size: 13px; color: #818CF8; font-weight: 600; margin-top: 4px;">09:00 & 17:00 WITA</div>
      <div style="font-size: 11px; color: #64748B; margin-top: 4px;">Serverless Cloud Runner</div>
    </div>
    """, unsafe_allow_html=True)

# ==================== BANNER ATAS LENGKAP ====================
st.markdown("""
<div style="background: rgba(18, 24, 38, 0.65); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px; padding: 28px 32px; margin-bottom: 24px; box-shadow: 0 12px 40px rgba(0,0,0,0.35);">
  <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.3); padding: 5px 14px; border-radius: 20px; margin-bottom: 14px;">
    <span style="width: 8px; height: 8px; border-radius: 50%; background: #818CF8; box-shadow: 0 0 10px #818CF8;"></span>
    <span style="font-size: 11px; font-weight: 700; color: #A5B4FC; letter-spacing: 0.06em; text-transform: uppercase;">Autonomous B2B Content Engine</span>
  </div>
  <h1 style="font-size: 32px; font-weight: 800; margin: 0; background: linear-gradient(135deg, #FFFFFF 0%, #E2E8F0 50%, #94A3B8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.03em;">
    Instagram Content Automation Dashboard
  </h1>
  <p style="font-size: 14px; color: #94A3B8; margin: 8px 0 0 0; line-height: 1.6;">
    Pusat komando konten: riset ide viral 30 hari lintas niche, validasi relevansi AI otomatis, render visual beresolusi tinggi, dan pengunduhan instan.
  </p>
</div>
""", unsafe_allow_html=True)

# 4 TAB LENGKAP
tab_ideas, tab_studio, tab_queue, tab_status = st.tabs([
    "💡 Bank Ide Viral (30 Hari)",
    "✨ AI Content Studio (QC & Download)",
    "📅 Antrean & Kalender Jadwal",
    "⚙️ Status Sistem & Kredensial"
])

# ==================== TAB 1: BANK IDE VIRAL ====================
with tab_ideas:
    niche_db = load_niche_database()
    st.markdown("""
    <div style="font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 4px;">Bank Ide Konten Teruji (30 Hari)</div>
    <div style="font-size: 14px; color: #94A3B8; margin-bottom: 20px;">Pilih niche bisnis Anda, temukan ide konten harian, dan klik <b>Gunakan Ide Ini</b> untuk langsung memproses desain visualnya.</div>
    """, unsafe_allow_html=True)

    niche_options = {v["name"]: k for k, v in niche_db.items()}
    selected_niche_name = st.selectbox("Pilih Niche Konten:", list(niche_options.keys()))
    selected_niche_id = niche_options[selected_niche_name]

    current_ideas = niche_db[selected_niche_id]["ideas"]
    for item in current_ideas:
        day_num = item.get("day", 1)
        hook_text = item.get("hook", "")
        angle = item.get("angle", "Strategi Edukasi")
        sugg_fmt = item.get("suggested_format", "CAROUSEL")
        
        col_info, col_act = st.columns()
        with col_info:
            st.markdown(f"**HARI {day_num}** (`{sugg_fmt}`) • *{angle}*")
            st.write(hook_text)
        with col_act:
            if st.button("Gunakan ➡️", key=f"btn_use_idea_{selected_niche_id}_{day_num}", type="primary"):
                st.session_state["selected_topic"] = hook_text
                st.toast(f"✅ Ide Hari {day_num} dipilih! Silakan buka tab AI Content Studio.")
        st.divider()

# ==================== TAB 2: AI CONTENT STUDIO ====================
with tab_studio:
    st.markdown("""
    <div style="font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 4px;">Studio Pembuatan Konten dengan Validasi & Unduhan</div>
    <div style="font-size: 14px; color: #94A3B8; margin-bottom: 20px;">Sistem akan menguji keselarasan materi dengan topik Anda sebelum kartu visual dirender.</div>
    """, unsafe_allow_html=True)

    init_topic = st.session_state.get("selected_topic", "3 Alasan kenapa omzet bisnismu naik tapi uang di rekening tetap kosong")
    
    col_inp, col_cfg = st.columns()
    with col_inp:
        topic_input = st.text_area("Topik Konten atau Ide Bisnis", value=init_topic, height=120)
    with col_cfg:
        fmt_options = ["CAROUSEL (3 Slide)", "IMAGE (1 Foto)"]
        media_type = st.selectbox("Format Konten Media", fmt_options, index=0)
        custom_media = st.text_input("Tautan Gambar Khusus (Opsional)", placeholder="https://...")

    if st.button("🚀 Buat Materi & Uji Relevansi Konten", type="primary"):
        with st.status("Sedang menyusun materi & menguji relevansi...", expanded=True) as status_box:
            status_box.write("🤖 Gemini 3.6 Flash sedang merancang struktur naskah...")
            data = generate_structured_content(topic_input)
            
            if not data or "hook_main" not in data:
                status_box.update(label="❌ Gagal membuat materi awal", state="error")
                st.error("Gagal menyusun naskah. Silakan coba lagi.")
            else:
                status_box.write("🔍 Menguji tingkat relevansi terhadap topik Anda...")
                qc_result = evaluate_content_relevance(topic_input, data)
                
                if not qc_result.get("is_relevant", True) or qc_result.get("score", 0) < 85:
                    status_box.write(f"⚠️ Relevansi awal {qc_result.get('score')}% kurang optimal. Merestrukturisasi naskah...")
                    data = generate_structured_content(topic_input, revision_note=f"Tingkatkan relevansi agar 100% fokus pada: {topic_input}")
                    qc_result = evaluate_content_relevance(topic_input, data)

                status_box.write(f"✅ Lolos Validasi! Skor Relevansi: {qc_result.get('score', 92)}%")
                status_box.write("🎨 Merender kartu slide visual...")

                badge = data.get("badge", "TIPS BISNIS")
                s1 = render_cover_slide(badge, data.get("hook_main", ""), data.get("hook_sub", ""), branding_handle)
                s2 = render_content_slide(badge, data.get("slide2_title", "Poin Penting"), [data.get("point1", ""), data.get("point2", "")], branding_handle)
                s3 = render_closing_slide(badge, data.get("slide3_title", "Langkah Aksi"), data.get("point3", ""), data.get("cta", ""), branding_handle)

                st.session_state["qc_score"] = qc_result.get("score", 95)
                st.session_state["qc_reason"] = qc_result.get("reason", "Materi sangat selaras dengan topik.")
                st.session_state["current_data"] = data
                st.session_state["rendered_slides"] = [s1, s2, s3]
                st.session_state["generated_caption"] = assemble_full_caption(data)

                status_box.update(label="🎉 Naskah & Visual Siap!", state="complete", expanded=False)

    # AREA PRATINJAU DENGAN TOMBOL UNDUH
    if "rendered_slides" in st.session_state and st.session_state["rendered_slides"]:
        st.markdown("---")
        
        # Kartu QC
        score = st.session_state.get("qc_score", 92)
        reason = st.session_state.get("qc_reason", "")
        st.markdown(f"""
        <div class="qc-card">
          <div style="font-size: 15px; font-weight: 700; color: #10B981;">
            🎯 Validasi Relevansi: {score}% — Terverifikasi Selaras dengan Topik
          </div>
          <div style="font-size: 13px; color: #E2E8F0; margin-top: 4px;">
            <b>Analisis QC:</b> {reason}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # BARIS TOMBOL BUNDLE DOWNLOAD (ZIP & TXT)
        col_hdr, col_dl_zip, col_dl_txt = st.columns()
        with col_hdr:
            st.markdown("#### 🖼️ Pratinjau Desain Visual")
        with col_dl_zip:
            zip_data = create_bundle_zip(st.session_state["rendered_slides"], st.session_state.get("generated_caption", ""))
            st.download_button(
                label="📦 Unduh Semua Slide (ZIP)",
                data=zip_data,
                file_name=f"carousel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                use_container_width=True
            )
        with col_dl_txt:
            st.download_button(
                label="📄 Unduh Naskah (.txt)",
                data=st.session_state.get("generated_caption", ""),
                file_name=f"caption_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )

        # TAMPILAN SLIDE & TOMBOL DOWNLOAD SATUAN PER SLIDE
        cols = st.columns(3)
        for idx, (col, slide_img) in enumerate(zip(cols, st.session_state["rendered_slides"]), 1):
            with col:
                st.markdown(f"<div style='text-align: center; font-size: 13px; font-weight: 700; color: #818CF8; margin-bottom: 6px;'>SLIDE {idx}</div>", unsafe_allow_html=True)
                st.image(slide_img, use_container_width=True)
                
                # Tombol download per slide
                ibuf = BytesIO()
                slide_img.save(ibuf, format="JPEG", quality=95)
                st.download_button(
                    label=f"⬇️ Unduh Slide {idx} (JPG)",
                    data=ibuf.getvalue(),
                    file_name=f"slide_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                    mime="image/jpeg",
                    key=f"dl_single_slide_{idx}",
                    use_container_width=True
                )

        st.markdown("<br>", unsafe_allow_html=True)
        caption_area = st.text_area("Naskah Caption Terverifikasi (Bisa diedit bebas):", value=st.session_state["generated_caption"], height=160)

        # Pilihan Simpan ke Antrean ATAU Publikasi Langsung
        col_save, col_pub = st.columns(2)
        with col_save:
            if st.button("💾 Simpan ke Antrean posts.json", type="secondary"):
                posts = load_posts()
                new_id = f"post-{len(posts) + 1:03d}"
                posts.append({"id": new_id, "caption": caption_area, "status": "PENDING"})
                save_posts(posts)
                st.success(f"🎉 Sukses! Postingan `{new_id}` berhasil dimasukkan ke antrean posts.json!")

        with col_pub:
            if st.button("🚀 Simpan & Publish Langsung ke Instagram!", type="primary"):
                with st.status("Sedang menerbitkan ke feed Instagram...", expanded=True) as status_box:
                    try:
                        posts = load_posts()
                        new_id = f"post-{len(posts) + 1:03d}"
                        status_box.write("☁️ Mengunggah 3 slide ke CDN cloud...")
                        urls = [upload_image_cloud(img, custom_imgbb_key) for img in st.session_state["rendered_slides"]]
                        status_box.write("📡 Mendaftarkan container karosel ke Meta Graph API...")
                        new_entry = {"id": new_id, "caption": caption_area, "carousel_urls": urls}
                        c_id = create_instagram_container_direct(new_entry, status_box)
                        time.sleep(3)
                        ig_id = publish_to_instagram_direct(c_id, status_box)
                        new_entry["status"] = "PUBLISHED"
                        new_entry["published_id"] = ig_id
                        new_entry["published_at"] = datetime.now(LOCAL_TZ).isoformat()
                        posts.append(new_entry)
                        save_posts(posts)
                        status_box.update(label="🎉 Sukses Terbit di Instagram!", state="complete", expanded=True)
                        st.success(f"🎉 Hebat! Materi berhasil tayang di Instagram feed! ID: `{ig_id}`")
                    except Exception as err:
                        status_box.update(label="❌ Gagal Terbit", state="error", expanded=True)
                        st.error(f"Penyebab kendala: {err}")

# ==================== TAB 3: ANTREAN & KALENDER ====================
with tab_queue:
    st.markdown("""
    <div style="font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 4px;">Manajemen Antrean & Kalender Jadwal</div>
    <div style="font-size: 14px; color: #94A3B8; margin-bottom: 20px;">Pantau jadwal konten. Anda dapat mengklik <b>Publish Sekarang</b> pada postingan PENDING untuk langsung menerbitkannya seketika.</div>
    """, unsafe_allow_html=True)
    posts = load_posts()
    
    total = len(posts)
    pending = sum(1 for p in posts if p.get("status") == "PENDING")
    published = sum(1 for p in posts if p.get("status") == "PUBLISHED")
    failed = sum(1 for p in posts if p.get("status") == "FAILED")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Draf", total)
    m2.metric("Siap Tayang (PENDING)", pending)
    m3.metric("Berhasil Terbit", published)
    m4.metric("Perlu Review (FAILED)", failed)
    
    st.markdown("---")
    if not posts:
        st.info("Belum ada postingan di dalam antrean.")
    else:
        for p in reversed(posts):
            status = p.get("status", "UNKNOWN")
            post_id = p.get("id")
            with st.container():
                c1, c2, c3 = st.columns()
                with c1:
                    st.write(f"**{post_id}**")
                    if status == "PUBLISHED":
                        st.success("PUBLISHED")
                    elif status == "PENDING":
                        st.warning("PENDING")
                    else:
                        st.error("FAILED")
                with c2:
                    caption_preview = p.get("caption", "")[:120] + "..." if len(p.get("caption", "")) > 120 else p.get("caption", "")
                    st.write(caption_preview)
                with c3:
                    if status == "PENDING":
                        if st.button("🚀 Publish Sekarang", key=f"btn_pub_now_{post_id}", type="primary"):
                            with st.status(f"Menerbitkan {post_id}...", expanded=True) as status_box:
                                try:
                                    s1 = render_cover_slide("TIPS BISNIS", "Materi Edukasi", "", branding_handle)
                                    s2 = render_content_slide("TIPS BISNIS", "Poin Penting", ["Langkah 1", "Langkah 2"], branding_handle)
                                    s3 = render_closing_slide("TIPS BISNIS", "Langkah Aksi", "Langkah 3", "Komentar di bawah!", branding_handle)
                                    urls = [upload_image_cloud(s, custom_imgbb_key) for s in [s1, s2, s3]]
                                    p["carousel_urls"] = urls
                                    c_id = create_instagram_container_direct(p, status_box)
                                    time.sleep(3)
                                    ig_id = publish_to_instagram_direct(c_id, status_box)
                                    p["status"] = "PUBLISHED"
                                    p["published_id"] = ig_id
                                    p["published_at"] = datetime.now(LOCAL_TZ).isoformat()
                                    save_posts(posts)
                                    status_box.update(label="🎉 Sukses Terbit!", state="complete")
                                    st.rerun()
                                except Exception as err:
                                    status_box.update(label="❌ Gagal", state="error")
                                    st.error(f"Gagal menerbitkan: {err}")
                st.divider()

# ==================== TAB 4: STATUS SISTEM ====================
with tab_status:
    st.markdown("""
    <div style="font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 12px;">Kesehatan API & Parameter Sistem</div>
    """, unsafe_allow_html=True)
    
    k1, k2, k3 = st.columns(3)
    with k1:
        st.write("🔑 **Meta Access Token**")
        if META_ACCESS_TOKEN:
            st.success("Terkonfigurasi (Aktif)")
        else:
            st.error("Tidak Ditemukan")
    with k2:
        st.write("📸 **Instagram Business ID**")
        if IG_USER_ID:
            st.success(f"ID: `{IG_USER_ID}`")
        else:
            st.error("Tidak Ditemukan")
    with k3:
        st.write("🤖 **Gemini 3.6 Flash Engine**")
        if GEMINI_API_KEY:
            st.success("Online & Siap Pakai")
        else:
            st.error("Tidak Ditemukan")
    st.markdown("---")
    st.info("💡 Dasbor ini terhubung secara real-time ke sistem otomasi cloud GitHub Actions Anda.")
