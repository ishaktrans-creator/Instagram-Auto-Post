import os
import json
import requests
import time
from datetime import datetime
import zoneinfo

LOCAL_TZ = zoneinfo.ZoneInfo("Asia/Makassar")

# Sanitasi token
raw_token = os.getenv("META_ACCESS_TOKEN", "").strip().strip('"').strip("'")
if ":" in raw_token:
    raw_token = raw_token.split(":")[-1].strip().strip('"').strip("'")
ACCESS_TOKEN = raw_token

IG_USER_ID = os.getenv("IG_USER_ID", "").strip()
GRAPH_API_URL = "https://graph.facebook.com/v21.0"

def create_container(post: dict) -> str:
    """Membuat Container untuk Foto atau Video Reels."""
    url = f"{GRAPH_API_URL}/{IG_USER_ID}/media"
    
    # Mode 1: Video / Reels
    if "video_url" in post and post["video_url"]:
        params = {
            "media_type": "REELS",
            "video_url": post["video_url"],
            "caption": post.get("caption", ""),
            "share_to_feed": "true",  # Muncul di Tab Reels sekaligus di Grid Feed Utama
            "access_token": ACCESS_TOKEN
        }
        print("Mendaftarkan media tipe: REELS...")
    # Mode 2: Foto Biasa
    else:
        params = {
            "image_url": post["image_url"],
            "caption": post.get("caption", ""),
            "access_token": ACCESS_TOKEN
        }
        print("Mendaftarkan media tipe: IMAGE...")

    res = requests.post(url, params=params)
    data = res.json()
    if "id" not in data:
        raise Exception(f"Gagal membuat container: {data}")
    return data["id"]

def wait_for_media_ready(container_id: str, max_wait_seconds: int = 180) -> bool:
    """Menunggu server Instagram selesai mengolah video (status: FINISHED)."""
    url = f"{GRAPH_API_URL}/{container_id}"
    params = {
        "fields": "status_code",
        "access_token": ACCESS_TOKEN
    }
    
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        res = requests.get(url, params=params)
        data = res.json()
        status = data.get("status_code")
        print(f"Status proses media: {status}")

        if status == "FINISHED":
            return True
        elif status == "ERROR":
            raise Exception(f"Meta gagal memproses video: {data}")
        elif status == "EXPIRED":
            raise Exception("Media container kedaluwarsa.")
        
        # Tunggu 10 detik sebelum cek status berikutnya
        time.sleep(10)
        
    raise TimeoutError("Waktu tunggu pemrosesan video melebihi batas (Timeout).")

def publish_media(creation_id: str) -> str:
    """Mempublikasikan media yang sudah siap ke Instagram."""
    url = f"{GRAPH_API_URL}/{IG_USER_ID}/media_publish"
    params = {
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN
    }
    res = requests.post(url, params=params)
    data = res.json()
    if "id" not in data:
        raise Exception(f"Gagal menerbitkan postingan: {data}")
    return data["id"]

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
            print(f"Memproses postingan ID: {post.get('id')}...")
            try:
                # 1. Buat Container
                container_id = create_container(post)
                print(f"Container ID: {container_id}")

                # 2. Jika Video, tunggu sampai proses encoding Meta selesai
                if "video_url" in post and post["video_url"]:
                    print("Menunggu server Instagram meng-encode video...")
                    wait_for_media_ready(container_id)
                else:
                    # Foto hanya butuh jeda singkat
                    time.sleep(5)

                # 3. Terbitkan ke Instagram
                published_id = publish_media(container_id)
                print(f"Sukses tayang di Instagram! Post ID: {published_id}")

                post["status"] = "PUBLISHED"
                post["published_id"] = published_id
                post["published_at"] = now.isoformat()
                if "error_message" in post:
                    del post["error_message"]
                updated = True
                break
            except Exception as e:
                print(f"Gagal mempublikasikan: {e}")
                post["status"] = "FAILED"
                post["error_message"] = str(e)
                updated = True
                break

    if updated:
        with open(post_file, "w", encoding="utf-8") as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        print("File posts.json berhasil diperbarui.")

if __name__ == "__main__":
    main()
