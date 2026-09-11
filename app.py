import os
import json
import requests
import textwrap
import time
import re
from io import BytesIO
from datetime import datetime
import zoneinfo
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

st.set_page_config(
    page_title="AutoPost Studio - Enterprise Instagram Automation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

LOCAL_TZ = zoneinfo.ZoneInfo("Asia/Makassar")
POST_FILE = "content/posts.json"
GRAPH_API_URL = "https://graph.facebook.com/v21.0"

def get_secret(key, default=""):
    if hasattr(st, "secrets") and key in st.secrets:
        return str(st.secrets[key]).strip().strip('"').strip("'")
    return os.getenv(key, default).strip().strip('"').strip("'")

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
META_ACCESS_TOKEN = get_secret("META_ACCESS_TOKEN")
IG_USER_ID = get_secret("IG_USER_ID")

# Inject Custom High-End SaaS CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Deep Obsidian Background */
.stApp {
    background: radial-gradient(circle at 50% 0%, #171E31 0%, #0B0F19 65%, #06080E 100%) !important;
    color: #F8FAFC !important;
}

/* Glassmorphism Sidebar */
[data-testid="stSidebar"] {
    background: rgba(13, 18, 30, 0.9) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

/* Primary Button Styling */
button[kind="primary"] {
    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #EC4899 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4) !important;
    transition: all 0.3s ease !important;
}

button[kind="primary"]:hover {
    box-shadow: 0 6px 28px rgba(236, 72, 153, 0.5) !important;
    transform: translateY(-2px);
}

/* Secondary Button Styling */
button[kind="secondary"] {
    background: rgba(30, 41, 59, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    color: #F8FAFC !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}

button[kind="secondary"]:hover {
    background: rgba(51, 65, 85, 0.9) !important;
    border-color: rgba(255, 255, 255, 0.3) !important;
}

/* Modern Form Inputs */
.stTextInput>div>div, .stTextArea>div>div, .stSelectbox>div>div {
    background: rgba(15, 23, 42, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 12px !important;
    color: #F8FAFC !important;
}

.stTextInput>div>div:focus-within, .stTextArea>div>div:focus-within {
    border-color: #818CF8 !important;
    box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.25) !important;
}

/* Custom Tabs */
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

/* Metrics Cards */
[data-testid="stMetric"] {
    background: rgba(18, 24, 38, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 16px 20px;
    backdrop-filter: blur(12px);
}
</style>
""", unsafe_allow_html=True)

PROMPT_TEMPLATE = """
Bertindaklah sebagai Content Strategist & Copywriter Senior untuk Instagram bisnis dan edukasi.
Buatkan satu materi caption Instagram lengkap berbahasa Indonesia dengan topik: "{topic}".

Format output WAJIB mengikuti struktur ini secara berurutan:
1. Baris 1: Badge Kategori dalam tanda kurung siku, contoh: [FINANCE], [TIPS BISNIS], atau [MOTIVATIONAL].
2. Baris 2: Judul / HOOK yang tajam dan menghentikan scrolling (1-2 kalimat menarik).
3. Baris 3-6: Poin-poin edukasi atau wawasan praktis (gunakan penomoran 1, 2, 3) yang padat, bernas, dan mudah dipahami.
4. Baris 7: Call to Action (CTA) interaktif (contoh: "Ketik kata kunci tertentu di komentar untuk diskusi lebih lanjut!").
5. Baris 8: 5 sampai 8 hashtag yang relevan dan bertarget.

PENTING: Jangan tambahkan kata pengantar atau basa-basi apa pun. Tulis langsung teks caption-nya dari baris pertama hingga terakhir.
"""

THEMATIC_BACKGROUNDS = {
    "FINANCE": "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1080&h=1080&fit=crop&q=80",
    "TIPS BISNIS": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1080&h=1080&fit=crop&q=80",
    "MOTIVATIONAL": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1080&h=1080&fit=crop&q=80"
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

def generate_caption_ai(topic: str) -> str:
    if not GEMINI_API_KEY:
        st.error("Kunci GEMINI_API_KEY belum dikonfigurasi di Streamlit Secrets.")
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": PROMPT_TEMPLATE.format(topic=topic)}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
    }

    for attempt in range(1, 4):
        try:
            res = requests.post(url, json=payload, timeout=60).json()
            if "candidates" in res and res["candidates"]:
                parts = res["candidates"][0]["content"].get("parts", [])
                return "".join([p.get("text", "") for p in parts]).strip()
            elif "error" in res and res["error"].get("code") in [503, 429]:
                time.sleep(3)
                continue
            else:
                st.error(f"Respon Google AI: {res}")
                return ""
        except requests.exceptions.Timeout:
            if attempt < 3:
                time.sleep(2)
                continue
            st.error("Koneksi ke server Google AI melebihi batas waktu (Timeout).")
        except Exception as e:
            if attempt < 3:
                time.sleep(2)
                continue
            st.error(f"Koneksi ke Gemini error: {e}")
    return ""

def parse_content(caption: str):
    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    badge = "TIPS BISNIS"
    hook = "Tips Edukasi Penting Hari Ini"
    points = []
    for line in lines:
        if line.startswith("[") and "]" in line:
            badge = line[1:line.find("]")].strip().upper()
        elif (not hook or hook == "Tips Edukasi Penting Hari Ini") and not line.startswith("[") and not line.startswith("#"):
            hook = line
        elif len(line) > 2 and line[0].isdigit() and (line == "." or line == ")"):
            points.append(line)
    if not points:
        points = ["Fokus pada eksekusi konsisten", "Evaluasi arus kas secara teratur", "Bangun sistem bisnis yang terukur"]
    return badge, hook, points

def render_slide_image(badge: str, title: str, body_lines: list, footer_text: str):
    W, H = 1080, 1080
    bg_url = THEMATIC_BACKGROUNDS.get(badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    try:
        r = requests.get(bg_url, timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 195))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        f_badge = ImageFont.truetype(font_bold, 30)
        f_title = ImageFont.truetype(font_bold, 52)
        f_body = ImageFont.truetype(font_reg, 36)
        f_footer = ImageFont.truetype(font_bold, 30)
    except Exception:
        f_badge = f_title = f_body = f_footer = ImageFont.load_default()

    badge_label = f"  {badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 130
    draw.rounded_rectangle([bx - 24, by - 12, bx + bw + 24, by + bh + 14], radius=24, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    t_lines = textwrap.wrap(title, width=28)
    ty = by + bh + 80
    for line in t_lines:
        l, t, r, b = draw.textbbox((0, 0), line, font=f_title)
        tw = r - l
        draw.text(((W - tw) // 2, ty), line, font=f_title, fill=(255, 255, 255))
        ty += 68

    ty += 25
    draw.line([(W // 2 - 60, ty), (W // 2 + 60, ty)], fill=(13, 148, 136), width=4)
    ty += 50

    for item in body_lines:
        s_lines = textwrap.wrap(item, width=38)
        for sl in s_lines:
            l, t, r, b = draw.textbbox((0, 0), sl, font=f_body)
            sw = r - l
            draw.text(((W - sw) // 2, ty), sl, font=f_body, fill=(226, 232, 240))
            ty += 52
        ty += 24

    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 110), footer_text, font=f_footer, fill=(148, 163, 184))

    return bg

def upload_image_cloud(pil_img):
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    files = {"fileToUpload": ("slide.jpg", buf, "image/jpeg")}
    try:
        r = requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype": "fileupload", "time": "72h"}, files=files, timeout=25)
        if r.status_code == 200 and r.text.strip().startswith("http"):
            return r.text.strip()
    except Exception:
        pass
    buf.seek(0)
    try:
        r = requests.post("https://freeimage.host/api/1/upload", data={"key": "6d207e02198a847aa98d0a2a901485a5", "action": "upload", "format": "json"}, files={"source": ("slide.jpg", buf, "image/jpeg")}, timeout=25).json()
        if "image" in r and "url" in r["image"]:
            return r["image"]["url"]
    except Exception:
        pass
    return ""

# ==================== SIDEBAR BRANDING ====================
with st.sidebar:
    # High-End Modern Vector Logo
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 24px; padding: 4px 0;">
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
    
    st.markdown("""
    <div style="background: rgba(18, 24, 38, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px; margin-top: 24px;">
      <div style="font-size: 12px; color: #94A3B8;">⏰ <b>Jadwal Publikasi:</b></div>
      <div style="font-size: 13px; color: #818CF8; font-weight: 600; margin-top: 4px;">09:00 & 17:00 WITA</div>
      <div style="font-size: 11px; color: #64748B; margin-top: 4px;">Serverless Cloud Runner</div>
    </div>
    """, unsafe_allow_html=True)

# ==================== MAIN BANNER ====================
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
    Platform orkestrasi konten otomatis: copywriting cerdas dengan Gemini AI, generator desain visual beresolusi tinggi, dan manajemen antrean cloud mandiri.
  </p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["✨ AI Content Studio", "📅 Antrean & Kalender Jadwal", "⚙️ Status Sistem & Kredensial"])

with tab1:
    st.markdown("""
    <div style="font-size: 18px; font-weight: 700; color: #FFFFFF; margin-bottom: 12px;">Studio Pembuatan Konten</div>
    """, unsafe_allow_html=True)
    
    col_input, col_config = st.columns(2)
    with col_input:
        topic_input = st.text_area(
            "Topik Konten atau Ide Bisnis",
            value="3 Cara Melipatgandakan Omzet Usaha Tanpa Tambah Modal Besar",
            help="Tuliskan ide apa pun, AI akan menyusun hook, edukasi, CTA, dan hashtag."
        )
    with col_config:
        media_type = st.selectbox("Format Konten Media", ["CAROUSEL (3 Slide)", "IMAGE (1 Foto)", "REELS (Video)"])
        custom_media = st.text_input("Link Media Khusus (Opsional)", placeholder="https://...")
    
    if st.button("🚀 Buat Materi & Render Desain Visual", type="primary"):
        with st.spinner("Gemini AI sedang menyusun materi & mesin grafis merender desain visual..."):
            caption = generate_caption_ai(topic_input)
            if caption:
                st.session_state["generated_caption"] = caption
                badge, hook, points = parse_content(caption)
                if "CAROUSEL" in media_type:
                    s1 = render_slide_image(badge, hook, ["Geser ke kiri untuk baca selengkapnya ➡️"], branding_handle)
                    s2 = render_slide_image(badge, "Pembahasan Materi (Bagian 1)", points[:2], branding_handle)
                    s3 = render_slide_image(badge, "Langkah Tindakan (Aksi Nyata)", points[2:] + ["Ketik 'SETUJU' di komentar jika konten ini bermanfaat!"], branding_handle)
                    st.session_state["rendered_slides"] = [s1, s2, s3]
                elif "IMAGE" in media_type:
                    s = render_slide_image(badge, hook, points, branding_handle)
                    st.session_state["rendered_slides"] = [s]
                else:
                    st.session_state["rendered_slides"] = []

    if "generated_caption" in st.session_state:
        st.markdown("---")
        st.markdown("""
        <div style="font-size: 18px; font-weight: 700; color: #FFFFFF; margin-bottom: 16px;">Pratinjau Hasil Desain (Live Mockup)</div>
        """, unsafe_allow_html=True)
        
        if "rendered_slides" in st.session_state and st.session_state["rendered_slides"]:
            cols = st.columns(len(st.session_state["rendered_slides"]))
            for idx, (col, slide_img) in enumerate(zip(cols, st.session_state["rendered_slides"]), 1):
                with col:
                    st.markdown(f"<div style='font-size: 13px; font-weight: 600; color: #818CF8; margin-bottom: 6px;'>Slide {idx}</div>", unsafe_allow_html=True)
                    st.image(slide_img, use_container_width=True)
        
        with st.expander("📝 Tinjau & Edit Naskah Caption", expanded=True):
            caption_edited = st.text_area("Naskah Caption Siap Terbit:", value=st.session_state["generated_caption"], height=180)
        
        if st.button("💾 Simpan ke Antrean Terjadwal (posts.json)", type="secondary"):
            with st.spinner("Mengunggah aset visual ke cloud dan memperbarui antrean..."):
                posts = load_posts()
                new_id = f"post-{len(posts) + 1:03d}"
                new_entry = {
                    "id": new_id,
                    "caption": caption_edited,
                    "status": "PENDING"
                }
                if "CAROUSEL" in media_type:
                    urls = [upload_image_cloud(img) for img in st.session_state["rendered_slides"]]
                    new_entry["carousel_urls"] = urls
                elif "IMAGE" in media_type:
                    new_entry["image_url"] = upload_image_cloud(st.session_state["rendered_slides"][0])
                elif "REELS" in media_type:
                    new_entry["video_url"] = custom_media if custom_media else "https://files.catbox.moe/ez3k5w.mp4"
                posts.append(new_entry)
                save_posts(posts)
                st.success(f"🎉 Sukses! Draf `{new_id}` berhasil dimasukkan ke antrean posts.json bertanda PENDING!")

with tab2:
    st.markdown("""
    <div style="font-size: 18px; font-weight: 700; color: #FFFFFF; margin-bottom: 12px;">Manajemen Antrean & Kalender Jadwal</div>
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
            with st.container():
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**{p.get('id')}**")
                    if status == "PUBLISHED":
                        st.success("PUBLISHED")
                    elif status == "PENDING":
                        st.warning("PENDING")
                    else:
                        st.error("FAILED")
                with c2:
                    caption_preview = p.get("caption", "")[:120] + "..." if len(p.get("caption", "")) > 120 else p.get("caption", "")
                    st.write(caption_preview)
                    if "carousel_urls" in p:
                        st.caption(f"Tipe: Karosel ({len(p['carousel_urls'])} Slide)")
                    elif "video_url" in p:
                        st.caption("Tipe: Video Reels (9:16)")
                    else:
                        st.caption("Tipe: Foto Feed Tunggal")
                with c3:
                    if status != "PENDING":
                        if st.button("Set PENDING", key=f"btn_pend_{p.get('id')}"):
                            p["status"] = "PENDING"
                            save_posts(posts)
                            st.rerun()
                st.divider()

with tab3:
    st.markdown("""
    <div style="font-size: 18px; font-weight: 700; color: #FFFFFF; margin-bottom: 12px;">Kesehatan API & Parameter Sistem</div>
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
