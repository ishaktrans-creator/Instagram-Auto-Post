import os
import json
import requests
import sys
import textwrap
import time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Bersihkan API Key dari spasi atau tanda kutip
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
POST_FILE = "content/posts.json"

PROMPT_TEMPLATE = """
Bertindaklah sebagai Content Strategist & Copywriter Senior untuk Instagram bisnis dan edukasi.
Buatkan satu materi caption Instagram lengkap berbahasa Indonesia dengan topik: "{topic}".

Format output WAJIB mengikuti struktur ini secara berurutan:
1. Baris 1: Badge Kategori dalam tanda kurung siku, contoh: [FINANCE], [TIPS BISNIS], atau [MOTIVATIONAL].
2. Baris 2: Judul / HOOK yang tajam dan menghentikan scrolling (1-2 kalimat menarik).
3. Baris 3-6: Poin-poin edukasi atau wawasan praktis (gunakan penomoran 1, 2, 3) yang padat, bernas, dan mudah dipahami.
4. Baris 7: Call to Action (CTA) interaktif (contoh: "Ketik kata kunci tertentu di komentar untuk diskusi lebih lanjut!").
5. Baris 8: 5 sampai 8 hashtag yang relevan dan bertarget.

PENTING: Jangan tambahkan kata pengantar, salam pembuka, atau penjelasan apa pun. Tulis langsung teks caption-nya dari baris pertama hingga baris terakhir.
"""

THEMATIC_BACKGROUNDS = {
    "FINANCE": "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1080&h=1080&fit=crop&q=80",
    "TIPS BISNIS": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1080&h=1080&fit=crop&q=80",
    "MOTIVATIONAL": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1080&h=1080&fit=crop&q=80"
}

# Daftar model untuk penanganan failover 503 otomatis
MODELS_TO_TRY = ["models/gemini-3.6-flash", "models/gemini-2.5-flash", "models/gemini-2.0-flash"]

def generate_caption(topic: str) -> str:
    if not GEMINI_API_KEY:
        raise Exception("Kunci GEMINI_API_KEY belum terpasang di GitHub Secrets.")

    payload = {
        "contents": [{
            "parts": [{"text": PROMPT_TEMPLATE.format(topic=topic)}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1000
        }
    }
    
    last_error = None
    for model_name in MODELS_TO_TRY:
        print(f"🚀 Menghubungi model: {model_name}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
        
        # Coba hingga 2 kali per model jika terjadi lonjakan 503
        for attempt in range(2):
            try:
                res = requests.post(url, json=payload, timeout=25).json()
                if "candidates" in res and res["candidates"]:
                    parts = res["candidates"][0]["content"].get("parts", [])
                    return "".join([p.get("text", "") for p in parts]).strip()
                elif "error" in res and res["error"].get("code") == 503:
                    print(f"⚠️ Model {model_name} sedang sibuk (503). Menunggu 3 detik...")
                    time.sleep(3)
                else:
                    last_error = res
                    break
            except Exception as net_err:
                last_error = str(net_err)
                time.sleep(2)

    raise Exception(f"Gagal generate konten dari Gemini setelah mencoba model cadangan: {last_error}")

def parse_content(caption: str):
    """Ekstraksi badge, hook, dan poin materi dari teks AI."""
    lines = [l.strip() for l in caption.split("\n") if l.strip()]
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

def create_slide_image(badge: str, title: str, body_lines: list, footer_sub: str, output_path: str):
    """Merender kartu gambar modern dengan dark overlay elegan."""
    W, H = 1080, 1080
    bg_url = THEMATIC_BACKGROUNDS.get(badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    
    # Ambil background foto
    try:
        r = requests.get(bg_url, timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    # Dark overlay elegan
    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 195))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    f_badge = ImageFont.truetype(font_bold, 30)
    f_title = ImageFont.truetype(font_bold, 52)
    f_body = ImageFont.truetype(font_reg, 36)
    f_footer = ImageFont.truetype(font_bold, 28)

    # 1. Badge Kategori
    badge_label = f"  {badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 130
    draw.rounded_rectangle([bx - 24, by - 12, bx + bw + 24, by + bh + 14], radius=24, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    # 2. Judul / Hook
    t_lines = textwrap.wrap(title, width=28)
    ty = by + bh + 80
    for line in t_lines:
        l, t, r, b = draw.textbbox((0, 0), line, font=f_title)
        tw = r - l
        draw.text(((W - tw) // 2, ty), line, font=f_title, fill=(255, 255, 255))
        ty += 68

    # 3. Garis Aksen Pembatas
    ty += 25
    draw.line([(W // 2 - 60, ty), (W // 2 + 60, ty)], fill=(13, 148, 136), width=4)
    ty += 50

    # 4. Poin-Poin Materi
    for item in body_lines:
        s_lines = textwrap.wrap(item, width=38)
        for sl in s_lines:
            l, t, r, b = draw.textbbox((0, 0), sl, font=f_body)
            sw = r - l
            draw.text(((W - sw) // 2, ty), sl, font=f_body, fill=(226, 232, 240))
            ty += 52
        ty += 24

    # 5. Footer Branding
    footer_text = f"@ishak_radjab  •  {footer_sub}"
    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 110), footer_text, font=f_footer, fill=(148, 163, 184))

    bg.save(output_path, "JPEG", quality=95)
    print(f"🖼️ Berhasil merender kartu: {output_path}")

def upload_to_catbox(file_path: str) -> str:
    """Mengunggah kartu ke hosting Catbox untuk tautan gambar publik langsung."""
    url = "https://catbox.moe/user/api.php"
    with open(file_path, "rb") as f:
        files = {"fileToUpload": (os.path.basename(file_path), f, "image/jpeg")}
        data = {"reqtype": "fileupload"}
        res = requests.post(url, data=data, files=files, timeout=30)
        if res.status_code == 200 and res.text.startswith("http"):
            return res.text.strip()
    raise Exception(f"Gagal mengunggah gambar ke cloud: {res.text}")

def main():
    topic = "Strategi membangun aset digital dan otomasi bisnis untuk pemula"
    media_url = ""
    media_type = "CAROUSEL"

    args = sys.argv[1:]
    if args:
        val = args.pop(0).strip()
        if val:
            topic = val
    if args:
        val = args.pop(0).strip()
        if val:
            media_url = val
    if args:
        val = args.pop(0).strip()
        if val:
            media_type = val

    print(f"🤖 Meminta Gemini AI menulis konten tentang: '{topic}'...")
    caption = generate_caption(topic)
    print("✅ Caption berhasil dibuat oleh AI!\n")

    badge, hook, points = parse_content(caption)
    os.makedirs("/tmp/slides", exist_ok=True)

    if os.path.exists(POST_FILE):
        with open(POST_FILE, "r", encoding="utf-8") as f:
            try:
                posts = json.load(f)
            except Exception:
                posts = []
    else:
        posts = []

    new_id = f"post-{len(posts) + 1:03d}"
    new_post = {
        "id": new_id,
        "caption": caption,
        "status": "PENDING"
    }

    # PEMBUATAN ASET VISUAL OTOMATIS
    if media_type.upper() == "CAROUSEL":
        print("🎨 Merancang 3 Slide Karosel Edukasi...")
        slide_urls = []
        
        # Slide 1: Cover
        p1 = "/tmp/slides/slide1.jpg"
        create_slide_image(badge, hook, ["Geser ke kiri untuk baca selengkapnya ➡️"], "Mahir Digital", p1)
        slide_urls.append(upload_to_catbox(p1))
        
        # Slide 2: Poin 1 & 2
        p2 = "/tmp/slides/slide2.jpg"
        create_slide_image(badge, "Pembahasan Materi (Bagian 1)", points[:2], "Geser ke Slide Terakhir ➡️", p2)
        slide_urls.append(upload_to_catbox(p2))

        # Slide 3: Poin 3 & Penutup
        p3 = "/tmp/slides/slide3.jpg"
        create_slide_image(badge, "Langkah Tindakan (Aksi Nyata)", points[2:] + ["Ketik 'SETUJU' di komentar jika konten ini bermanfaat!"], "Simpan Postingan Ini 📌", p3)
        slide_urls.append(upload_to_catbox(p3))

        new_post["carousel_urls"] = slide_urls
        print(f"✅ 3 Slide Karosel berhasil diunggah: {slide_urls}")

    elif media_type.upper() == "IMAGE":
        print("🎨 Merancang 1 Kartu Gambar Infografis...")
        p = "/tmp/slides/single.jpg"
        create_slide_image(badge, hook, points, "Mahir Digital", p)
        new_post["image_url"] = upload_to_catbox(p)

    elif media_type.upper() == "REELS":
        new_post["video_url"] = media_url if media_url else "https://files.catbox.moe/ez3k5w.mp4"

    posts.append(new_post)

    os.makedirs("content", exist_ok=True)
    with open(POST_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"🎉 Sukses! Draf visual lengkap ({new_id}) tersimpan di posts.json bertanda PENDING!")

if __name__ == "__main__":
    main()
