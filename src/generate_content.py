import os
import json
import requests
import sys

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

# Model resmi terbaru dari Google AI
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
    for model in MODELS_TO_TRY:
        print(f"🚀 Menghubungi Google Model: {model}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
        res = requests.post(url, json=payload)
        data = res.json()
        
        if "candidates" in data and data["candidates"]:
            # Menggabungkan seluruh bagian teks agar kalimat tidak terpotong
            parts = data["candidates"][0]["content"].get("parts", [])
            full_caption = "".join([p.get("text", "") for p in parts]).strip()
            return full_caption
        else:
            last_error = data

    raise Exception(f"Gagal generate konten dari Gemini: {last_error}")

def main():
    topic = "Strategi membangun aset digital dan otomasi bisnis untuk pemula"
    media_url = ""
    media_type = "IMAGE"

    # Ambil argumen secara aman
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
    print("✅ Caption lengkap berhasil dibuat oleh AI!\n")
    print("--- PRATINJAU KONTEN LENGKAP ---")
    print(caption)
    print("--------------------------------\n")

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

    if media_type.upper() == "REELS":
        new_post["video_url"] = media_url
    else:
        new_post["image_url"] = media_url if media_url else "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&q=80"

    posts.append(new_post)

    os.makedirs("content", exist_ok=True)
    with open(POST_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"🎉 Berhasil menambahkan draf baru ({new_id}) ke posts.json dengan status PENDING!")

if __name__ == "__main__":
    main()
