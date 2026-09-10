import os
import json
import requests
import time
from datetime import datetime
import zoneinfo

LOCAL_TZ = zoneinfo.ZoneInfo("Asia/Makassar")
IG_USER_ID = os.getenv("IG_USER_ID")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
GRAPH_API_URL = "https://graph.facebook.com/v21.0"

def create_media_container(image_url: str, caption: str) -> str:
    """Langkah 1: Membuat wadah media di Instagram."""
    url = f"{GRAPH_API_URL}/{IG_USER_ID}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    res = requests.post(url, data=payload)
    data = res.json()
    if "id" not in data:
        raise Exception(f"Gagal membuat container: {data}")
    return data["id"]

def publish_media(creation_id: str) -> str:
    """Langkah 2: Mempublikasikan wadah media ke feed Instagram."""
    url = f"{GRAPH_API_URL}/{IG_USER_ID}/media_publish"
    payload = {
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN
    }
    res = requests.post(url, data=payload)
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
            print(f"Memproses postingan: {post.get('id')}...")
            try:
                # 1. Buat Container Media
                container_id = create_media_container(post["image_url"], post["caption"])
                print(f"Container ID berhasil dibuat: {container_id}")

                # Jeda sejenak agar server Instagram selesai memproses gambar
                time.sleep(5)

                # 2. Publish ke Instagram Feed
                published_id = publish_media(container_id)
                print(f"Sukses tayang di Instagram! Post ID: {published_id}")

                post["status"] = "PUBLISHED"
                post["published_id"] = published_id
                post["published_at"] = now.isoformat()
                updated = True
                break  # Terbitkan satu postingan per siklus
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
