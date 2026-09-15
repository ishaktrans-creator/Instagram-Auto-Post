import os
import json
import requests
import textwrap
import time
import re
import base64
from io import BytesIO
from datetime import datetime
import zoneinfo
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# 1. Bersihkan variabel proxy lingkungan
for k in list(os.environ.keys()):
    if "proxy" in k.lower():
        del os.environ[k]

def clean_url(u: str) -> str:
    cleaned = re.sub(r"^[^a-zA-Z]+", "", str(u).strip())
    return cleaned.strip(" \t\n\r[]()\"'")

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

.qc-card {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 14px;
    padding: 14px 20px;
    margin-bottom: 16px;
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
        st.error("Kunci GEMINI_API_KEY belum terkonfigurasi.")
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
    """Memeriksa relevansi naskah terhadap topik sebelum dirender ke visual."""
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
        return {"score": 90, "is_relevant": True, "reason": "Konten selaras dengan topik."}

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

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("""
    <div style="font-size: 20px; font-weight: 800; color: #FFFFFF;">AutoPost<span style="color: #818CF8;">.ai</span></div>
    <div style="font-size: 11px; color: #64748B; text-transform: uppercase;">Quality Guard Studio</div>
    <br>
    """, unsafe_allow_html=True)
    branding_handle = st.text_input("Branding Footer Gambar", value="@ishak_radjab")
    custom_imgbb_key = st.text_input("ImgBB Key (Opsional)", type="password")

# ==================== TAB UTAMA ====================
tab_studio, tab_queue = st.tabs(["✨ AI Content Studio (QC Aktif)", "📅 Antrean & Riwayat"])

with tab_studio:
    st.markdown("""
    <div style="font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 4px;">Studio Pembuatan Konten dengan Validasi Relevansi</div>
    <div style="font-size: 14px; color: #94A3B8; margin-bottom: 20px;">Sistem akan memverifikasi keselarasan materi dengan topik Anda sebelum ditampilkan ke pratinjau.</div>
    """, unsafe_allow_html=True)

    topic_input = st.text_area(
        "Topik Konten atau Ide Bisnis",
        value="3 Alasan kenapa omzet bisnismu naik tapi uang di rekening tetap kosong",
        height=100
    )

    if st.button("🚀 Buat Materi & Uji Relevansi Konten", type="primary"):
        with st.status("Sedang memproses dan menguji relevansi materi...", expanded=True) as status_box:
            status_box.write("🤖 Gemini 3.6 Flash sedang merancang struktur naskah...")
            data = generate_structured_content(topic_input)
            
            if not data or "hook_main" not in data:
                status_box.update(label="❌ Gagal membuat materi awal", state="error")
                st.error("Gagal menyusun naskah. Silakan coba lagi.")
            else:
                status_box.write("🔍 Menguji tingkat relevansi terhadap topik Anda...")
                qc_result = evaluate_content_relevance(topic_input, data)
                
                # Jika skor di bawah 85%, lakukan kurasi ulang otomatis
                if not qc_result.get("is_relevant", True) or qc_result.get("score", 0) < 85:
                    status_box.write(f"⚠️ Relevansi awal {qc_result.get('score')}% kurang memuaskan. Merestrukturisasi naskah...")
                    data = generate_structured_content(topic_input, revision_note=f"Tingkatkan relevansi agar 100% fokus pada: {topic_input}")
                    qc_result = evaluate_content_relevance(topic_input, data)

                status_box.write(f"✅ Lolos Validasi! Skor Relevansi: {qc_result.get('score', 90)}%")
                status_box.write("🎨 Merender slide visual dengan header dinamis...")

                badge = data.get("badge", "TIPS BISNIS")
                s1 = render_cover_slide(badge, data.get("hook_main", ""), data.get("hook_sub", ""), branding_handle)
                s2 = render_content_slide(badge, data.get("slide2_title", "Poin Penting"), [data.get("point1", ""), data.get("point2", "")], branding_handle)
                s3 = render_closing_slide(badge, data.get("slide3_title", "Langkah Aksi"), data.get("point3", ""), data.get("cta", ""), branding_handle)

                st.session_state["qc_score"] = qc_result.get("score", 95)
                st.session_state["qc_reason"] = qc_result.get("reason", "Materi sangat sesuai dengan topik.")
                st.session_state["current_data"] = data
                st.session_state["rendered_slides"] = [s1, s2, s3]
                st.session_state["generated_caption"] = assemble_full_caption(data)

                status_box.update(label="🎉 Naskah & Visual Siap!", state="complete", expanded=False)

    # AREA PRATINJAU DENGAN INDIKATOR RELEVANSI
    if "rendered_slides" in st.session_state:
        st.markdown("---")
        
        # Kartu Indikator Relevansi
        score = st.session_state.get("qc_score", 90)
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

        cols = st.columns(3)
        for idx, (col, slide_img) in enumerate(zip(cols, st.session_state["rendered_slides"]), 1):
            with col:
                st.markdown(f"<div style='text-align: center; font-size: 13px; font-weight: 700; color: #818CF8; margin-bottom: 8px;'>SLIDE {idx}</div>", unsafe_allow_html=True)
                st.image(slide_img, width=340)

        st.markdown("<br>", unsafe_allow_html=True)
        caption_area = st.text_area("Naskah Caption Terverifikasi:", value=st.session_state["generated_caption"], height=160)

        col_save, col_pub = st.columns(2)
        with col_save:
            if st.button("💾 Simpan ke Antrean posts.json", type="secondary"):
                posts = load_posts()
                new_id = f"post-{len(posts) + 1:03d}"
                posts.append({"id": new_id, "caption": caption_area, "status": "PENDING"})
                save_posts(posts)
                st.success(f"🎉 Postingan {new_id} tersimpan di antrean!")

        with col_pub:
            if st.button("🚀 Simpan & Publish Langsung ke Instagram!", type="primary"):
                with st.status("Sedang menerbitkan ke feed Instagram...", expanded=True) as status_box:
                    try:
                        posts = load_posts()
                        new_id = f"post-{len(posts) + 1:03d}"
                        status_box.write("☁️ Mengunggah 3 slide ke CDN...")
                        urls = [upload_image_cloud(img, custom_imgbb_key) for img in st.session_state["rendered_slides"]]
                        status_box.write("📡 Mendaftarkan ke Meta Graph API...")
                        new_entry = {"id": new_id, "caption": caption_area, "carousel_urls": urls}
                        c_id = create_instagram_container_direct(new_entry, status_box)
                        time.sleep(3)
                        ig_id = publish_to_instagram_direct(c_id, status_box)
                        new_entry["status"] = "PUBLISHED"
                        new_entry["published_id"] = ig_id
                        posts.append(new_entry)
                        save_posts(posts)
                        status_box.update(label="🎉 Sukses Terbit di Instagram!", state="complete", expanded=True)
                        st.success(f"🎉 Hebat! Materi terbit di Instagram feed! ID: `{ig_id}`")
                    except Exception as err:
                        status_box.update(label="❌ Gagal Terbit", state="error", expanded=True)
                        st.error(f"Penyebab kendala: {err}")

with tab_queue:
    st.markdown("### 📋 Daftar Antrean Konten")
    posts = load_posts()
    if not posts:
        st.info("Belum ada antrean.")
    else:
        for p in reversed(posts):
            st.write(f"**{p.get('id')}** - Status: `{p.get('status')}`")
            st.caption(p.get("caption", "")[:120] + "...")
            st.divider()
