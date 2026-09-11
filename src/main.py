import os
import json
import requests
import time
from datetime import datetime
import zoneinfo

LOCAL_TZ = zoneinfo.ZoneInfo("Asia/Makassar")

# Sanitasi token Meta
raw_token = os.getenv("META_ACCESS_TOKEN", "").strip().strip('"').strip("'")
if ":" in raw_token:
    raw_token = raw_token.split(":")[-1].strip().strip('"').strip("'")
ACCESS_TOKEN = raw_token

IG_USER_ID = os.getenv("IG_USER_ID", "").strip()
GRAPH_API_URL = "https://graph.facebook.com/v21.0"

# Kredensial Notifikasi Telegram (Opsional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def send_telegram_notification(message: str):
    """Kirim notifikasi ke Telegram jika token tersedia."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Gagal mengirim notifikasi Telegram: {e}")

def create_instagram_container(post: dict) -> str:
    """Membuat Container Media di Instagram (Single Image, Reels, atau Carousel)."""
    url = f"{GRAPH_API_URL}/{IG_USER_ID}/media"
    caption = post.get("caption", "")

    # Mode 1: Karosel (Multi-Slide Gambar)
    if "carousel_urls" in post and isinstance(post["carousel_urls"], list) and len(post["carousel_urls"]) > 1:
        print(f"📸 Mendaftarkan Karosel Instagram ({len(post['carousel_urls'])} slide)...")
        children_ids = []
        for img_url in post["carousel_urls"]:
            child_payload = {
                "image_url": img_url,
                "is_carousel_item": "true",
                "access_token": ACCESS_TOKEN
            }
            c_res = requests.post(url, params=child_payload).json()
            if "id" not in c_res:
                raise Exception(f"Gagal upload slide karosel: {c_res}")
            children_ids.append(c_res["id"])
            time.sleep(2)

        parent_payload = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": ACCESS_TOKEN
        }
        res = requests.post(url, params=parent_payload).json()
        if "id" not in res:
            raise Exception(f"Gagal membuat container karosel: {res}")
        return res["id"]

    # Mode 2: Video Reels Vertikal (9:16)
    elif "video_url" in post and post["video_url"]:
        print("🎬 Mendaftarkan media tipe: REELS...")
        payload = {
            "media_type": "REELS",
            "video_url": post["video_url"],
            "caption": caption,
            "share_to_feed": "true",
            "access_token": ACCESS_TOKEN
        }
        res = requests.post(url, params=payload).json()
        if "id" not in res:
            raise Exception(f"Gagal membuat container Reels: {res}")
        return res["id"]

    # Mode 3: Foto Tunggal Feed
    else:
        print("🖼️ Mendaftarkan media tipe: IMAGE...")
        payload = {
            "image_url": post.get("image_url", ""),
            "caption": caption,
            "access_token": ACCESS_TOKEN
        }
        res = requests.post(url, params=payload).json()
        if "id" not in res:
            raise Exception(f"Gagal membuat container Image: {res}")
        return res["id"]

def wait_for_media_ready(container_id: str, max_wait_seconds: int = 180):
    """Menunggu proses transcode video selesai di server Instagram."""
    url = f"{GRAPH_API_URL}/{container_id}"
    params = {"fields": "status_code,status", "access_token": ACCESS_TOKEN}
    start = time.time()
    while time.time() - start < max_wait_seconds:
        res = requests.get(url, params=params).json()
        status = res.get("status_code")
        print(f"Status proses video: {status}")
        if status == "FINISHED":
            return
        elif status == "ERROR":
            raise Exception(f"Meta gagal memproses video: {res}")
        elif status == "EXPIRED":
            raise Exception("Container video kedaluwarsa.")
        time.sleep(10)
    raise TimeoutError("Waktu tunggu video di Meta melebihi batas waktu.")

def publish_to_instagram(container_id: str) -> str:
    """Menerbitkan container media ke Instagram."""
    url = f"{GRAPH_API_URL}/{IG_USER_ID}/media_publish"
    res = requests.post(url, params={"creation_id": container_id, "access_token": ACCESS_TOKEN}).json()
    if "id" not in res:
        raise Exception(f"Gagal publish ke Instagram: {res}")
    return res["id"]

def main():
    post_file = "content/posts.json"
    if not os.path.exists(post_file):
        print("File posts.json tidak ditemukan.")
        return

    with open(post_file, "r", encoding="utf-8") as f:
        posts = json.load(f)

    now = datetime.now(LOCAL_TZ)
    updated = False

    for post in posts:
        if post.get("status") == "PENDING":
            post_id = post.get("id")
            print(f"🚀 Memproses antrean: {post_id}...")
            try:
                # 1. Buat Container Media Instagram
                container_id = create_instagram_container(post)
                
                # 2. Jika Video, tunggu sampai proses encoding Meta selesai
                if "video_url" in post and post["video_url"]:
                    print("Menunggu encoding Reels...")
                    wait_for_media_ready(container_id)
                else:
                    time.sleep(5)

                # 3. Publikasikan ke Feed / Reels
                ig_post_id = publish_to_instagram(container_id)
                print(f"✅ Sukses tayang di Instagram! Post ID: {ig_post_id}")

                # Update status
                post["status"] = "PUBLISHED"
                post["published_id"] = ig_post_id
                post["published_at"] = now.isoformat()
                if "error_message" in post:
                    del post["error_message"]
                updated = True

                # Kirim notifikasi Telegram (jika aktif)
                send_telegram_notification(
                    f"🎉 *Postingan Instagram Berhasil Terbit!*\n\n"
                    f"📌 *ID*: `{post_id}`\n"
                    f"📸 *Tautan*: [Lihat di Instagram](https://www.instagram.com/ishak_radjab/)\n"
                    f"⏰ *Waktu*: {now.strftime('%d-%m-%Y %H:%M:%S')} WITA"
                )
                break
            except Exception as e:
                print(f"❌ Gagal memproses {post_id}: {e}")
                post["status"] = "FAILED"
                post["error_message"] = str(e)
                updated = True
                send_telegram_notification(f"⚠️ *Postingan Instagram Gagal!*\n\n📌 *ID*: `{post_id}`\n❌ *Error*: `{e}`")
                break

    if updated:
        with open(post_file, "w", encoding="utf-8") as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        print("File posts.json berhasil diperbarui.")

if __name__ == "__main__":
    main()
