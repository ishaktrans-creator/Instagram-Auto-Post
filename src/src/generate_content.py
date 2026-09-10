import os
import json
import requests
import sys

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
POST_FILE = "content/posts.json"

PROMPT_TEMPLATE = """
Bertindaklah sebagai Content Strategist & Copywriter Senior untuk Instagram.
Buatkan satu materi caption Instagram lengkap berbahasa Indonesia dengan topik: "{topic}".

Kriteria penulisan:
1. Awali baris pertama dengan badge kategori, contoh: [FINANCE], [TIPS BISNIS], atau [MOTIVATIONAL].
2. Baris berikutnya adalah HOOK yang tajam, memikat, dan menghentikan scrolling dalam 3 detik pertama.
3. Bagian tubuh (body text) berisi 2-3 poin edukasi/insight praktis yang mudah dicerna dan tidak bertele-tele.
4. Akhiri dengan Call to Action (CTA) yang memicu interaksi di kolom komentar (misalnya mengajak mengetik kata kunci tertentu).
5. Berikan 5-8 hashtag yang sangat relevan di baris paling bawah.
6. Berikan langsung teks caption-nya saja tanpa pengantar atau basa-basi apa pun.
"""

def generate_caption(topic: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [{"text": PROMPT_TEMPLATE.format(topic=topic)}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 600
        }
    }
    
    res = requests.post(url, json=payload)
    data = res.json()
    
    if "candidates" not in data or not data["candidates"]:
        raise Exception(f"Gagal generate konten dari Gemini: {data}")
        
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def main():
    # Ambil topik dan link media dari input parameter (atau gunakan default jika kosong)
    topic = sys.argv if len(sys.argv) > 1 and sys.argv.strip() else "Strategi membangun aset digital dan otomasi bisnis untuk pemula"
    media_url = sys.argv if len(sys.argv) > 2 and sys.argv.strip() else ""
    media_type = sys.argv if len(sys.argv) > 3 and sys.argv.strip() else "IMAGE"

    print(f"🤖 Meminta Gemini AI menulis konten tentang: '{topic}'...")
    caption = generate_caption(topic)
    print("✅ Caption berhasil dibuat oleh AI!\n")

    # Buka posts.json
    if os.path.exists(POST_FILE):
        with open(POST_FILE, "r", encoding="utf-8") as f:
            try:
                posts = json.load(f)
            except Exception:
                posts = []
    else:
        posts = []

    # Buat ID baru
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

    with open(POST_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"🎉 Berhasil menambahkan draf baru ({new_id}) ke posts.json dengan status PENDING!")

if __name__ == "__main__":
    main()
