import os
import json
import requests
import sys

# Bersihkan API Key dari spasi/tanda kutip
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
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

def get_best_available_model() -> str:
    """Otomatis mengambil model Gemini yang aktif untuk akun Anda dari Google."""
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    res = requests.get(list_url)
    data = res.json()

    if "error" in data:
        raise Exception(f"Google API Key Error: {data['error']}")

    available_models = []
    for m in data.get("models", []):
        methods = m.get("supportedGenerationMethods", [])
        name = m.get("name", "")
        # Pilih model yang mendukung generateContent dan berbasis Gemini
        if "generateContent" in methods and "gemini" in name.lower():
            available_models.append(name)

    if not available_models:
        raise Exception(f"Tidak ada model Gemini yang aktif untuk API key ini. Respon Google: {data}")

    # Prioritaskan model tipe 'flash' agar respon cepat dan hemat kuota
    selected = available_models[0]
    for m in available_models:
        if "flash" in m.lower():
            selected = m
            break
            
    return selected

def generate_caption(topic: str) -> str:
    if not GEMINI_API_KEY:
        raise Exception("Kunci GEMINI_API_KEY belum terpasang di GitHub Secrets.")

    # 1. Deteksi otomatis model yang bisa dipakai
    model_name = get_best_available_model()
    print(f"🚀 Menggunakan model aktif Google: {model_name}")

    # 2. Kirim prompt ke model tersebut
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
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
    topic = "Strategi membangun aset digital dan otomasi bisnis untuk pemula"
    media_url = ""
    media_type = "IMAGE"

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
    print("--- PRATINJAU KONTEN ---")
    print(caption)
    print("------------------------\n")

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
