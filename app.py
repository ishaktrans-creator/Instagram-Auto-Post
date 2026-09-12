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
</style>
""", unsafe_allow_html=True)

THEMATIC_BACKGROUNDS = {
    "FINANCE": "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1080&h=1080&fit=crop&q=80",
    "TIPS BISNIS": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1080&h=1080&fit=crop&q=80",
    "MOTIVATIONAL": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1080&h=1080&fit=crop&q=80"
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
            ("5 Kesalahan pemula saat merekrut karyawan pertama", "Manajemen Tim", "CAROUSEL"),
            ("Rahasia warung kelontong bisa bertahan puluhan tahun di era modern", "Studi Kasus", "REELS"),
            ("Cara memisahkan uang pribadi dan uang operasional usaha", "Praktik Keuangan", "CAROUSEL"),
            ("3 Tanda bisnismu sedang jalan di tempat tanpa kamu sadari", "Evaluasi Bisnis", "IMAGE"),
            ("Rumus menentukan target pasar spesifik agar tidak boncos promosi", "Strategi Pemasaran", "CAROUSEL"),
            ("Kenapa pelanggan kabur ke kompetitor padahal hargamu lebih murah?", "Psikologi Pembeli", "REELS"),
            ("Cara menyusun SOP sederhana untuk bisnis kecil 1 orang", "Sistemasi Bisnis", "CAROUSEL"),
            ("3 Alat digital gratis yang wajib dipakai pemilik usaha pemula", "Rekomendasi Tools", "IMAGE"),
            ("Kapan waktu yang tepat untuk banting setir atau pivot bisnis?", "Strategi Arah", "REELS"),
            ("Cara mengelola stok barang agar tidak jadi uang mati di gudang", "Manajemen Inventaris", "CAROUSEL"),
            ("Tips menghadapi pembeli yang suka nawar sadis tanpa bikin sakit hati", "Komunikasi Pelanggan", "REELS"),
            ("5 Kebiasaan buruk solopreneur yang bikin cepat burnout", "Produktivitas", "CAROUSEL"),
            ("Cara membuat penawaran produk yang sulit ditolak calon pembeli", "Copywriting Penjualan", "CAROUSEL"),
            ("Kenapa diskon besar-besaran justru bisa membunuh bisnismu perlahan", "Strategi Harga", "IMAGE"),
            ("Cara membaca laporan laba rugi sederhana dalam 5 menit", "Literasi Finansial", "CAROUSEL"),
            ("3 Hal yang harus disiapkan sebelum mengajukan pinjaman usaha", "Manajemen Utang", "REELS"),
            ("Strategi retensi: cara mengubah pembeli pertama menjadi langganan setia", "Loyalitas Konsumen", "CAROUSEL"),
            ("Jangan jualan fitur, jual transformasi: ini contoh praktisnya", "Prinsip Branding", "IMAGE"),
            ("Cara membangun reputasi brand lokal terpercaya di kota sendiri", "Branding Lokal", "CAROUSEL"),
            ("5 Indikator kesehatan arus kas yang wajib dicek setiap akhir pekan", "Checklist Bisnis", "CAROUSEL"),
            ("Cara delegasi tugas harian agar kamu tidak terjebak kerja operasional", "Scale Up", "REELS"),
            ("Mitos kerja keras vs kerja pakai sistem dalam membangun aset bisnis", "Mindset Bisnis", "IMAGE"),
            ("Cara riset kompetitor tanpa perlu modal mahal atau mata-mata", "Riset Pasar", "CAROUSEL"),
            ("3 Kesalahan fatal saat memberi nama produk atau brand baru", "Studi Kasus Brand", "REELS"),
            ("Cara menyiapkan dana cadangan darurat khusus untuk kelangsungan usaha", "Proteksi Bisnis", "CAROUSEL"),
            ("Refleksi 30 hari: apakah bisnismu memberi kebebasan atau beban baru?", "Evaluasi Bulanan", "IMAGE")
        ]
    },
    {
        "id": "keuangan_investasi",
        "name": "💰 Keuangan Pribadi & Investasi",
        "category": "FINANCE",
        "ideas": [
            ("Gaji 5 juta bisa punya tabungan 50 juta? Ini simulasi realistisnya", "Perencanaan Anggaran", "CAROUSEL"),
            ("3 Jebakan pinjol legal yang sering tidak disadari anak muda", "Edukasi Utang", "REELS"),
            ("Urutan investasi yang benar: jangan beli saham sebelum bereskan ini", "Hirarki Keuangan", "CAROUSEL"),
            ("Cara membagi gaji dengan rumus 50-30-20 tanpa merasa tersiksa", "Budgeting", "IMAGE"),
            ("Perbedaan mendasar antara aset produktif vs aset konsumtif", "Mindset Finansial", "CAROUSEL"),
            ("Berapa dana darurat ideal untuk yang masih lajang vs berkeluarga?", "Dana Darurat", "IMAGE"),
            ("Kenapa menabung di rekening bank biasa bikin uangmu tergerus inflasi", "Edukasi Inflasi", "REELS"),
            ("5 Pengeluaran kecil harian yang diam-diam bikin dompet jebol", "Kebocoran Halus", "CAROUSEL"),
            ("Cara mulai investasi reksa dana pasar uang modal 100 ribu", "Tutorial Pemula", "CAROUSEL"),
            ("Mitos: Investasi harus nunggu kaya. Fakta: Kamu kaya karena mulai investasi", "Mitos vs Fakta", "IMAGE"),
            ("Tips memilih asuransi kesehatan murni tanpa embel-embel unit link", "Proteksi", "CAROUSEL"),
            ("Cara melunasi tumpukan utang kartu kredit dengan metode snowball", "Manajemen Utang", "CAROUSEL"),
            ("Bedah portofolio: cara diversifikasi aset di usia 20-an dan 30-an", "Alokasi Aset", "CAROUSEL"),
            ("Jangan beli rumah dulu jika kondisimu masih memenuhi 3 tanda ini", "Keputusan Besar", "REELS"),
            ("Pentingnya financial check-up berkala: ini 5 indikator utamanya", "Audit Finansial", "CAROUSEL"),
            ("Cara menyikapi fenomena FOMO investasi koin dan saham gorengan", "Psikologi Pasar", "REELS"),
            ("Berapa persen porsi maksimal cicilan bulanan dari total penghasilan?", "Rasio Keuangan", "IMAGE"),
            ("Cara menyiapkan dana pensiun mandiri sejak usia muda", "Rencana Hari Tua", "CAROUSEL"),
            ("Kenapa orang bergaji 30 juta masih bisa merasa kurang dan berutang?", "Gaya Hidup", "REELS"),
            ("Simulasi kekuatan bunga berbunga (compound interest) dalam 10 tahun", "Edukasi Investasi", "CAROUSEL"),
            ("Cara berhemat saat nongkrong tanpa dicap pelit oleh teman", "Tips Sosial", "IMAGE"),
            ("Pilih sewa rumah atau cicil KPR? Pertimbangkan 4 faktor krusial ini", "Analisis Properti", "CAROUSEL"),
            ("Cara mengatur uang THR atau bonus agar tidak langsung ludes", "Manajemen Bonus", "CAROUSEL"),
            ("3 Rekening bank wajib yang harus kamu punya untuk pos keuangan", "Sistem Rekening", "CAROUSEL"),
            ("Emas batangan vs perhiasan untuk investasi jangka panjang: pilih mana?", "Perbandingan Aset", "REELS"),
            ("Tanda-tanda kamu sudah terjebak fenomena 'lifestyle inflation'", "Evaluasi Diri", "IMAGE"),
            ("Cara menyiapkan dana pendidikan anak dari sekarang tanpa pusing", "Rencana Keluarga", "CAROUSEL"),
            ("5 Prinsip keuangan orang terkaya di dunia yang bisa kita tiru", "Kebiasaan Finansial", "CAROUSEL"),
            ("Cara berbicara soal keuangan dengan pasangan secara terbuka dan sehat", "Finansial Pasangan", "REELS"),
            ("Evaluasi akhir bulan: cara hitung net worth (kekayaan bersih) pribadimu", "Kekayaan Bersih", "CAROUSEL")
        ]
    },
    {
        "id": "marketing_ai",
        "name": "🤖 Digital Marketing & Teknologi AI",
        "category": "TIPS BISNIS",
        "ideas": [
            ("5 Prompt AI yang bikin kerjaan marketing selesai 5x lebih cepat", "Produktivitas AI", "CAROUSEL"),
            ("Kenapa postingan akun bisnismu sepi views? Ini audit algoritma terbaru", "Algoritma Sosmed", "REELS"),
            ("Cara riset konten viral menggunakan AI tanpa perlu mikir dari nol", "Riset Konten", "CAROUSEL"),
            ("Struktur hook 3 detik yang terbukti menghentikan scroll di media sosial", "Copywriting", "IMAGE"),
            ("3 Tools AI gratis untuk membuat visual dan poster dalam 1 menit", "Rekomendasi AI", "CAROUSEL"),
            ("Mitos: AI akan menggantikan manusia. Fakta: Manusia yang pakai AI yang menggantikan", "Opini Industri", "REELS"),
            ("Cara membangun database nomor WhatsApp pelanggan secara tertarget", "Lead Generation", "CAROUSEL"),
            ("5 Kesalahan umum saat pasang iklan berbayar yang bikin boncos", "Iklan Berbayar", "CAROUSEL"),
            ("Strategi konten organic vs paid ads: kapan harus mulai beriklan?", "Strategi Marketing", "IMAGE"),
            ("Cara mengubah 1 video panjang menjadi 10 konten mikro siap tayang", "Content Repurposing", "CAROUSEL"),
            ("Rahasia membuat judul penawaran yang dibuka dan dibaca calon pelanggan", "Penulisan Iklan", "CAROUSEL"),
            ("3 Trik psikologi harga yang membuat promomu terlihat menggiurkan", "Psikologi Harga", "REELS"),
            ("Cara riset hashtag Instagram yang benar: hindari banned dan spam", "Tips Instagram", "IMAGE"),
            ("Kenapa follower banyak tidak menjamin jualan laris? Ini faktanya", "Insight Bisnis", "REELS"),
            ("Panduan membuat carousel edukasi yang memicu tombol save & share", "Tutorial Konten", "CAROUSEL"),
            ("Cara memanfaatkan AI untuk membalas pesan calon pelanggan", "Otomasi Interaksi", "CAROUSEL"),
            ("Struktur halaman penawaran sederhana yang menghasilkan konversi tinggi", "Optimasi Web", "CAROUSEL"),
            ("5 Tipe konten yang disukai algoritma media sosial tahun ini", "Tren Algoritma", "CAROUSEL"),
            ("Cara membangun personal branding untuk mendatangkan klien berkualitas", "Personal Branding", "CAROUSEL"),
            ("Trik copywriting: rumus Problem-Agitate-Solution dalam caption", "Formula Copywriting", "IMAGE"),
            ("Cara mengukur metrik yang benar: jangan cuma tergiur vanity metrics", "Analitik Data", "REELS"),
            ("3 Cara mudah mencari ide konten saat merasa kehabisan ide kreatif", "Kreativitas", "CAROUSEL"),
            ("Kenapa video vertikal pendek (Reels) jadi raja distribusi konten saat ini", "Format Tren", "REELS"),
            ("Cara membuat kalender konten 30 hari dalam waktu kurang dari 2 jam", "Manajemen Konten", "CAROUSEL"),
            ("Strategi kolaborasi mikro-influencer yang ramah kantong bagi UMKM", "Influencer Marketing", "CAROUSEL"),
            ("3 Tanda bio profil Instagrammu bikin calon pembeli bingung", "Audit Bio", "IMAGE"),
            ("Cara menggunakan tren pencarian Google untuk riset produk laris", "Riset Tren", "CAROUSEL"),
            ("Tips membangun interaksi tinggi di Instagram Stories setiap hari", "Interaksi Stories", "REELS"),
            ("Cara menjaga konsistensi posting tanpa merasa lelah atau burnout", "Mindset Kreator", "IMAGE"),
            ("Evaluasi performa konten bulanan: cara memilih konten terbaik", "Audit Konten", "CAROUSEL")
        ]
    },
    {
        "id": "motivasi_diri",
        "name": "🚀 Motivasi & Pengembangan Diri",
        "category": "MOTIVATIONAL",
        "ideas": [
            ("Bukan karena kamu kurang pintar, tapi karena kamu terlalu banyak mikir", "Pola Pikir", "IMAGE"),
            ("5 Kebiasaan pagi sederhana orang sukses yang mengubah produktivitas", "Rutinitas Pagi", "CAROUSEL"),
            ("Cara mengatasi rasa malas dan menunda-nunda dengan aturan 5 detik", "Antiprokrastinasi", "REELS"),
            ("Untuk kamu yang hari ini merasa tertinggal dari teman seangkatan, baca ini", "Refleksi Diri", "CAROUSEL"),
            ("Kenapa motivasi selalu hilang setelah 3 hari, dan apa pengganti yang benar", "Disiplin vs Motivasi", "IMAGE"),
            ("Cara menghentikan kebiasaan overthinking sebelum tidur di malam hari", "Kesehatan Mental", "CAROUSEL"),
            ("3 Tipe teman beracun (toxic) yang diam-diam menghambat pertumbuhanmu", "Lingkungan Sosial", "REELS"),
            ("Mitos: Sukses itu cepat dan instan. Fakta: Proses di balik layar yang sunyi", "Realitas Hidup", "IMAGE"),
            ("Cara membangun fokus mendalam (deep work) di tengah ramainya notifikasi HP", "Fokus Kerja", "CAROUSEL"),
            ("Jangan merasa bersalah untuk istirahat: tubuhmu bukan mesin tanpa lelah", "Self-Care", "IMAGE"),
            ("5 Buku self-improvement yang mengubah cara pandang hidup ribuan orang", "Rekomendasi Buku", "CAROUSEL"),
            ("Cara mengubah kegagalan masa lalu menjadi bahan bakar kesuksesan baru", "Resiliensi", "REELS"),
            ("Kenapa orang cerdas sering kalah dengan orang yang konsisten setiap hari", "Konsistensi", "IMAGE"),
            ("Cara berani berkata 'TIDAK' tanpa merasa tidak enak hati pada orang lain", "Batasan Diri", "CAROUSEL"),
            ("3 Pertanyaan penting untuk menemukan tujuan hidup dan kariermu", "Penemuan Diri", "CAROUSEL"),
            ("Tanda-tanda kamu sedang bertumbuh meskipun rasanya sangat berat dan sepi", "Validasi Emosi", "REELS"),
            ("Cara melepaskan hal-hal di luar kendalimu dengan stoikisme praktis", "Stoikisme", "CAROUSEL"),
            ("Kenapa membandingkan diri di media sosial adalah pencuri kebahagiaan terbesar", "Media Sosial", "IMAGE"),
            ("5 Langkah keluar dari zona nyaman tanpa rasa cemas yang melumpuhkan", "Keberanian", "CAROUSEL"),
            ("Rahasia menjaga energi positif sepanjang hari kerja yang padat", "Manajemen Energi", "REELS"),
            ("Cara membangun rasa percaya diri dari dalam tanpa butuh validasi luar", "Kepercayaan Diri", "CAROUSEL"),
            ("Kenapa lingkaran pertemananmu makin kecil seiring bertambahnya usia", "Kedewasaan", "IMAGE"),
            ("Belajar memaafkan diri sendiri atas keputusan buruk yang pernah kamu buat", "Damai Batin", "REELS"),
            ("3 Kebiasaan malam yang membuat tidurmu nyenyak dan bangun berenergi", "Kualitas Tidur", "CAROUSEL"),
            ("Jangan biarkan kata orang lain menentukan siapa dirimu di masa depan", "Keteguhan Hati", "IMAGE"),
            ("Cara mengubah rasa iri menjadi inspirasi untuk memperbaiki diri", "Emosi Positif", "REELS"),
            ("5 Pelajaran hidup paling berharga yang sering disesali orang di usia tua", "Kebijaksanaan", "CAROUSEL"),
            ("Cara menghadapi rasa takut dihakimi saat mulai berkarya di media sosial", "Mental Berkarya", "CAROUSEL"),
            ("Pentingnya merayakan kemenangan kecil setiap hari sebelum tidur", "Apresiasi Diri", "IMAGE"),
            ("Refleksi akhir bulan: apakah kamu semakin dekat dengan impianmu?", "Evaluasi Hidup", "CAROUSEL")
        ]
    },
    {
        "id": "kuliner_fnb",
        "name": "🍳 Kuliner / F&B",
        "category": "TIPS BISNIS",
        "ideas": [
            ("Rahasia kenapa menu sambal tertentu bisa bikin pelanggan ketagihan balik lagi", "Resep Sukses", "REELS"),
            ("3 Kesalahan fatal pemula saat membuka kedai kopi atau kafe kecil", "Manajemen F&B", "CAROUSEL"),
            ("Cara menghitung Food Cost yang tepat agar margin usahamu tidak bocor", "Finansial F&B", "CAROUSEL"),
            ("Trik menata foto makanan pakai HP agar terlihat menggugah selera pembeli", "Food Photography", "IMAGE"),
            ("Kenapa menu yang terlalu banyak justru bikin pembeli batal memesan", "Psikologi Menu", "REELS"),
            ("Cara memilih kemasan makanan yang aman untuk pengiriman ojek online", "Packaging", "CAROUSEL"),
            ("Strategi membuat menu signature yang tidak mudah ditiru kompetitor", "Diferensiasi", "CAROUSEL"),
            ("5 Tips menjaga kebersihan dapur restoran agar selalu lolos standar kesehatan", "Operasional", "IMAGE"),
            ("Cara menentukan lokasi strategis untuk usaha kuliner kaki lima vs kafe", "Riset Lokasi", "CAROUSEL"),
            ("Trik upselling ramah: cara kasir menawarkan menu pendamping tanpa memaksa", "Pelayanan Kasir", "REELS"),
            ("Cara mengelola bahan baku segar agar tidak cepat busuk dan jadi sampah", "Waste Management", "CAROUSEL"),
            ("Kenapa aroma dapur terbuka bisa meningkatkan nafsu makan dan penjualan", "Panca Indera", "REELS"),
            ("5 Promo kuliner yang terbukti ramai tanpa merusak harga pasar", "Promosi F&B", "CAROUSEL"),
            ("Cara mendapatkan review bintang 5 dari pelanggan di aplikasi pesan antar", "Reputasi Online", "CAROUSEL"),
            ("Tips menghadapi komplain makanan dingin atau pesanan salah dengan senyuman", "Handling Komplain", "IMAGE"),
            ("Pentingnya konsistensi rasa: cara standarisasi takaran bumbu di dapur", "Quality Control", "CAROUSEL"),
            ("Strategi bundling minuman dan camilan untuk menaikkan rata-rata belanja", "Menu Engineering", "REELS"),
            ("Cara membuat video proses masak (behind the scenes) yang bikin ngiler", "Konten Kuliner", "REELS"),
            ("3 Tanda usaha kulinermu butuh perombakan menu (menu revamp)", "Audit Menu", "IMAGE"),
            ("Cara mencari supplier bahan pokok terpercaya dengan harga grosir bersaing", "Rantai Pasok", "CAROUSEL"),
            ("Pentingnya konsep halal dan sertifikasi resmi untuk meningkatkan kepercayaan", "Legalitas F&B", "CAROUSEL"),
            ("Tips mengelola antrean panjang saat jam makan siang agar pelanggan tidak kabur", "Kecepatan Layanan", "REELS"),
            ("Cara membangun komunitas pecinta kuliner di sekitar outlet tokomu", "Komunitas Lokal", "CAROUSEL"),
            ("5 Bumbu dapur rahasia yang bisa mengangkat cita rasa masakan sederhana", "Edukasi Rasa", "IMAGE"),
            ("Strategi pre-order (PO) untuk bisnis kue rumahan minim modal awal", "Bisnis Rumahan", "CAROUSEL"),
            ("Cara menghitung porsi ideal agar pelanggan kenyang tapi biaya tetap aman", "Porsi & Biaya", "CAROUSEL"),
            ("Trik membuat cerita di balik resep tradisional warisan keluarga", "Storytelling", "REELS"),
            ("Cara memanfaatkan momen musiman (Ramadhan, liburan) untuk lonjakan omzet", "Pemasaran Musim", "CAROUSEL"),
            ("Tips menjaga mood barista dan juru masak saat jam ramai pesanan", "Budaya Dapur", "IMAGE"),
            ("Evaluasi performa menu bulanan: menu mana yang jadi bintang vs beban", "Analisis Menu", "CAROUSEL")
        ]
    },
    {
        "id": "relationship",
        "name": "❤️ Relationship & Hubungan",
        "category": "MOTIVATIONAL",
        "ideas": [
            ("3 Tanda pasanganmu tidak hanya mencintaimu, tapi juga menghargai batasmu", "Hubungan Sehat", "CAROUSEL"),
            ("Kenapa silent treatment adalah racun paling berbahaya dalam hubungan", "Komunikasi", "REELS"),
            ("Cara mengungkapkan rasa kecewa ke pasangan tanpa memicu pertengkaran besar", "Resolusi Konflik", "CAROUSEL"),
            ("Mitos: Pasangan serasi tidak pernah bertengkar. Fakta: Ini cara ribut yang sehat", "Mitos Relasi", "IMAGE"),
            ("5 Bahasa kasih (Love Languages) dan cara menerapkannya dalam keseharian", "Bahasa Kasih", "CAROUSEL"),
            ("Tanda-tanda 'Red Flag' halus di awal perkenalan yang sering diabaikan", "Pencegahan", "REELS"),
            ("Cara membagi peran rumah tangga secara adil antara suami dan istri bekerja", "Kemitraan", "CAROUSEL"),
            ("Kenapa cemburu berlebihan bukan tanda cinta, melainkan rasa insecure", "Psikologi Relasi", "IMAGE"),
            ("3 Kebiasaan kecil setiap malam yang membuat ikatan pasangan makin erat", "Rutinitas Romantis", "CAROUSEL"),
            ("Cara memaafkan pasangan setelah kecewa tanpa melupakan pelajaran hidup", "Pengampunan", "REELS"),
            ("Trik menjaga api asmara tetap menyala setelah bertahun-tahun bersama", "Keintiman Emosional", "CAROUSEL"),
            ("Cara membicarakan topik sensitif (uang, mertua, anak) dengan kepala dingin", "Diskusi Kritis", "CAROUSEL"),
            ("5 Tanda hubunganmu sudah berubah menjadi 'Green Flag' yang membahagiakan", "Hubungan Positif", "IMAGE"),
            ("Kenapa kamu tidak boleh kehilangan identitas dan impianmu saat berpasangan", "Kemandirian", "REELS"),
            ("Cara mendengarkan pasangan yang sedang curhat tanpa langsung menggurui", "Empati Aktif", "CAROUSEL"),
            ("Pentingnya kencan berdua (date night) rutin meski sudah lama bersama", "Waktu Berdua", "IMAGE"),
            ("Tanda pasanganmu sedang butuh ruang sendiri (me-time), bukan menjauhimu", "Pengertian", "REELS"),
            ("Cara menyikapi perbedaan prinsip dengan keluarga pasangan atau mertua", "Keluarga Besar", "CAROUSEL"),
            ("3 Hal yang harus disepakati bersama sebelum melangkah ke jenjang serius", "Persiapan Komitmen", "CAROUSEL"),
            ("Kenapa membandingkan hubunganmu dengan postingan orang lain di sosmed itu keliru", "Ekspektasi Realistis", "IMAGE"),
            ("Cara membangun kembali kepercayaan yang pernah retak bersama pasangan", "Rekonstruksi Hubungan", "CAROUSEL"),
            ("Pentingnya mengucapkan terima kasih untuk hal-hal kecil yang dilakukan pasangan", "Apresiasi", "REELS"),
            ("Cara mengatasi rasa bosan dalam hubungan jangka panjang tanpa drama", "Penyegaran Hubungan", "CAROUSEL"),
            ("5 Tanda kamu sudah siap secara mental untuk memulai hubungan yang serius", "Kesiapan Diri", "CAROUSEL"),
            ("Jangan menuntut pasangan menjadi sempurna: belajarlah bertumbuh bersama", "Penerimaan", "IMAGE"),
            ("Cara menyelesaikan perbedaan cara mengatur keuangan dengan pasangan", "Finansial Pasangan", "CAROUSEL"),
            ("Tanda-tanda hubungan yang saling menguatkan karier dan impian masing-masing", "Dukungan Karier", "REELS"),
            ("Cara menghadapi rasa kesepian saat harus menjalani hubungan jarak jauh (LDR)", "LDR Tips", "CAROUSEL"),
            ("Pentingnya tertawa bersama: humor sebagai perekat terbaik dalam hubungan", "Keharmonisan", "IMAGE"),
            ("Refleksi bulanan: apakah kamu dan pasangan semakin dekat secara batin?", "Evaluasi Hubungan", "CAROUSEL")
        ]
    },
    {
        "id": "kesehatan_kebugaran",
        "name": "🏃 Kesehatan & Kebugaran",
        "category": "MOTIVATIONAL",
        "ideas": [
            ("3 Kebiasaan sederhana sebelum tidur yang menurunkan kadar gula darah", "Kesehatan Tubuh", "CAROUSEL"),
            ("Kenapa diet ekstrem selalu gagal dan bikin berat badan naik dua kali lipat", "Mitos Diet", "REELS"),
            ("Cara mudah memenuhi kebutuhan 2 liter air putih sehari tanpa terasa kembung", "Hidrasi", "IMAGE"),
            ("5 Gerakan peregangan 5 menit untuk pekerja kantoran yang sering sakit pinggang", "Ergonomi & Postur", "CAROUSEL"),
            ("Tanda-tanda tubuhmu sedang kekurangan tidur kronis meski merasa segar", "Kualitas Tidur", "REELS"),
            ("Mitos: Karbohidrat bikin gemuk. Fakta: Ini jenis karbohidrat yang sehat", "Edukasi Nutrisi", "CAROUSEL"),
            ("Cara memulai jalan kaki 8.000 langkah sehari untuk pemula yang sibuk", "Aktivitas Fisik", "IMAGE"),
            ("3 Gejala stres yang sering muncul di fisik tapi dikira penyakit lain", "Kesehatan Mental", "CAROUSEL"),
            ("Kenapa sarapan tinggi protein bikin kamu kenyang lebih lama sampai siang", "Tips Sarapan", "REELS"),
            ("Cara membaca tabel informasi nilai gizi pada makanan kemasan di minimarket", "Literasi Gizi", "CAROUSEL"),
            ("5 Alasan kenapa berat badanmu mandek (plateau) padahal sudah rajin olahraga", "Evaluasi Berat", "CAROUSEL"),
            ("Trik mengurangi konsumsi gula harian tanpa merasa tersiksa atau lemas", "Pola Makan", "REELS"),
            ("Pentingnya melatih kekuatan otot setelah usia 30 tahun untuk masa tua", "Kebugaran Jangka Panjang", "IMAGE"),
            ("Cara menjaga kesehatan mata untuk yang setiap hari menatap layar laptop", "Kesehatan Mata", "CAROUSEL"),
            ("Kenapa perut buncit berbahaya bagi jantung dan cara menguranginya secara alami", "Kesehatan Jantung", "REELS"),
            ("3 Minuman hangat alami yang membantu meredakan radang tenggorokan", "Obat Alami", "IMAGE"),
            ("Cara mengatasi rasa ingin ngemil (craving) manis di sore atau malam hari", "Kendali Nafsu Makan", "CAROUSEL"),
            ("Pentingnya cek darah rutin tahunan: 5 angka yang wajib kamu pantau", "Preventif Medis", "CAROUSEL"),
            ("Cara bernapas dalam (box breathing) untuk menurunkan kecemasan dalam 2 menit", "Relaksasi Cepat", "REELS"),
            ("Mitos susu, kopi, dan teh: mana yang sebenarnya baik untuk dikonsumsi pagi?", "Minuman Harian", "CAROUSEL"),
            ("5 Makanan super lokal Indonesia yang kaya antioksidan dan murah meriah", "Superfood Lokal", "CAROUSEL"),
            ("Cara konsisten berolahraga 20 menit sehari tanpa butuh langganan gym mahal", "Olahraga Rumahan", "IMAGE"),
            ("Kenapa duduk lebih dari 6 jam sehari setara bahayanya dengan merokok", "Gaya Hidup Sedentari", "REELS"),
            ("Tips memilih jenis olahraga yang cocok dengan tipe tubuh dan kepribadianmu", "Pemilihan Olahraga", "CAROUSEL"),
            ("Tanda-tanda ususmu sedang tidak sehat dan cara memperbaikinya dengan serat", "Kesehatan Pencernaan", "CAROUSEL"),
            ("Cara sederhana menjaga daya tahan tubuh saat cuaca sering berubah ekstrem", "Imunitas Tubuh", "IMAGE"),
            ("Kenapa olahraga berlebihan tanpa istirahat cukup justru melemahkan imun", "Pemulihan Tubuh", "REELS"),
            ("3 Trik mengatur jam makan malam agar asam lambung tidak naik saat tidur", "Cegah GERD", "CAROUSEL"),
            ("Pentingnya paparan sinar matahari pagi untuk kesehatan tulang dan mood", "Vitamin D Alami", "IMAGE"),
            ("Evaluasi kebugaran bulanan: apakah kamu merasa lebih bugar dari bulan lalu?", "Evaluasi Fisik", "CAROUSEL")
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

def generate_caption_ai(topic: str, revision_note: str = "") -> str:
    if not GEMINI_API_KEY:
        st.error("Kunci GEMINI_API_KEY belum dikonfigurasi di Streamlit Secrets.")
        return ""

    final_prompt = PROMPT_TEMPLATE.format(topic=topic)
    if revision_note:
        final_prompt += f"\n\nCATATAN REVISI TAMBAHAN DARI PENGGUNA: Tolong sesuaikan materi dengan instruksi khusus ini: '{revision_note}'."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": final_prompt}]}],
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

def research_30_ideas_ai(niche_name: str) -> list:
    if not GEMINI_API_KEY:
        st.error("Kunci GEMINI_API_KEY belum dikonfigurasi.")
        return []
        
    prompt = f"""
    Bertindaklah sebagai Viral Content Researcher profesional untuk Instagram.
    Buatkan daftar 30 ide konten viral terstruktur untuk niche '{niche_name}'.
    
    Output WAJIB berupa JSON murni dengan format array of objects:
    [
      {{
        "day": 1,
        "hook": "Judul hook memikat yang menghentikan scroll",
        "angle": "Sudut pandang konten (misal: Mitos vs Fakta / Studi Kasus / Audit)",
        "suggested_format": "CAROUSEL"
      }},
      ...
    ]
    Format yang diizinkan hanya: "CAROUSEL", "REELS", atau "IMAGE".
    Berikan JSON murni tanpa markdown pembungkus.
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4000}
    }
    
    try:
        res = requests.post(url, json=payload, timeout=60).json()
        if "candidates" in res and res["candidates"]:
            raw_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
            raw_text = re.sub(r"^```json\s*", "", raw_text)
            raw_text = re.sub(r"^```\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text).strip()
            return json.loads(raw_text)
    except Exception as e:
        st.error(f"Gagal meriset ide baru: {e}")
    return []

def parse_content(caption: str):
    lines = [l.strip() for l in caption.splitlines() if l.strip()]
    badge = "TIPS BISNIS"
    hook = "Tips Edukasi Penting Hari Ini"
    points = []
    cta_text = "Simak pembahasan lengkap dan bagikan pendapatmu di komentar!"

    for line in lines:
        if line.startswith("[") and "]" in line:
            badge = line[1:line.find("]")].strip().upper()
        elif (not hook or hook == "Tips Edukasi Penting Hari Ini") and not line.startswith("[") and not line.startswith("#"):
            hook = line
        elif len(line) > 2 and line[0].isdigit() and (line == "." or line == ")"):
            points.append(line)
        elif line.lower().startswith("ketik") or "komentar" in line.lower():
            cta_text = line

    if not points:
        points = [
            "1. Fokus Pada Eksekusi: Mulailah dari langkah nyata terkecil.",
            "2. Evaluasi Arus Kas: Disiplin mencatat pemasukan dan pengeluaran.",
            "3. Bangun Sistem: Otomasi alur kerja agar bisnis bertumbuh mandiri."
        ]
    return badge, hook, points, cta_text

def get_scalable_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default(size=size)

def render_cover_slide(badge: str, raw_hook: str, footer_text: str):
    """Slide 1 (Cover): Proporsional, Hook Besar 60px, Sub-Hook Rapi, dan Ruang Nafas Lega."""
    W, H = 1080, 1080
    bg_url = THEMATIC_BACKGROUNDS.get(badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    try:
        r = requests.get(bg_url, timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 205))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    f_badge = get_scalable_font(28, bold=True)
    f_title = get_scalable_font(60, bold=True)
    f_sub = get_scalable_font(32, bold=False)
    f_swipe = get_scalable_font(26, bold=True)
    f_footer = get_scalable_font(30, bold=True)

    # 1. Badge Pill
    badge_label = f"  {badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 130
    draw.rounded_rectangle([bx - 24, by - 12, bx + bw + 24, by + bh + 14], radius=24, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    # Pemisahan Kalimat Aman
    words = raw_hook.split()
    if "—" in raw_hook:
        parts = raw_hook.split("—", 1)
        main_title = parts[0].strip()
        sub_text = parts.strip()
    elif "-" in raw_hook and len(words) > 8:
        parts = raw_hook.split("-", 1)
        main_title = parts[0].strip()
        sub_text = parts.strip()
    elif ":" in raw_hook:
        parts = raw_hook.split(":", 1)
        main_title = parts[0].strip()
        sub_text = parts.strip()
    elif len(words) > 8:
        main_title = " ".join(words[:7])
        sub_text = " ".join(words[7:])
    else:
        main_title = raw_hook
        sub_text = "Geser slide ke kiri untuk membaca penjelasan lengkapnya! ➡️"

    # 2. Main Title (H1: Besar, Tebal, Putih)
    t_lines = textwrap.wrap(main_title, width=22)
    ty = by + bh + 85
    for line in t_lines:
        l, t, r, b = draw.textbbox((0, 0), line, font=f_title)
        tw = r - l
        draw.text(((W - tw) // 2, ty), line, font=f_title, fill=(255, 255, 255))
        ty += 76

    # 3. Garis Aksen Pembatas
    ty += 24
    draw.line([(W // 2 - 60, ty), (W // 2 + 60, ty)], fill=(13, 148, 136), width=4)
    ty += 40

    # 4. Sub-Hook (H2: Lembut, Rapi)
    s_lines = textwrap.wrap(sub_text, width=36)
    for line in s_lines:
        l, t, r, b = draw.textbbox((0, 0), line, font=f_sub)
        sw = r - l
        draw.text(((W - sw) // 2, ty), line, font=f_sub, fill=(203, 213, 225))
        ty += 48

    # 5. Tombol Swipe
    swipe_text = "GESER KE KIRI  ➡️"
    l, t, r, b = draw.textbbox((0, 0), swipe_text, font=f_swipe)
    swp_w = r - l
    swp_x = (W - swp_w) // 2
    swp_y = H - 210
    draw.rounded_rectangle([swp_x - 20, swp_y - 10, swp_x + swp_w + 20, swp_y + 36], radius=20, fill=(30, 41, 59))
    draw.text((swp_x, swp_y), swipe_text, font=f_swipe, fill=(248, 250, 252))

    # 6. Footer Branding
    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 90), footer_text, font=f_footer, fill=(148, 163, 184))

    return bg

def render_content_slide(badge: str, header_title: str, points_list: list, footer_text: str):
    """Slide 2 (Materi): Poin-poin dalam kartu gelap berdesain elegan."""
    W, H = 1080, 1080
    bg_url = THEMATIC_BACKGROUNDS.get(badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    try:
        r = requests.get(bg_url, timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 210))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    f_badge = get_scalable_font(26, bold=True)
    f_header = get_scalable_font(44, bold=True)
    f_point_num = get_scalable_font(34, bold=True)
    f_point_body = get_scalable_font(30, bold=False)
    f_footer = get_scalable_font(30, bold=True)

    # 1. Badge Top
    badge_label = f"  {badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 95
    draw.rounded_rectangle([bx - 20, by - 8, bx + bw + 20, by + bh + 10], radius=20, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    # Header
    l, t, r, b = draw.textbbox((0, 0), header_title, font=f_header)
    tw = r - l
    draw.text(((W - tw) // 2, by + bh + 45), header_title, font=f_header, fill=(255, 255, 255))

    dy = by + bh + 105
    draw.line([(W // 2 - 40, dy), (W // 2 + 40, dy)], fill=(13, 148, 136), width=3)

    # Poin dalam Card Box
    start_y = dy + 50
    for item in points_list:
        if ":" in item:
            p_title, p_desc = item.split(":", 1)
        else:
            p_title, p_desc = item, ""

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

    # Footer
    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 90), footer_text, font=f_footer, fill=(148, 163, 184))

    return bg

def render_closing_slide(badge: str, point_text: str, cta_text: str, footer_text: str):
    """Slide 3 (Aksi & CTA): Poin terakhir + Kotak Khusus Call to Action."""
    W, H = 1080, 1080
    bg_url = THEMATIC_BACKGROUNDS.get(badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    try:
        r = requests.get(bg_url, timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 210))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    f_badge = get_scalable_font(26, bold=True)
    f_header = get_scalable_font(44, bold=True)
    f_point_num = get_scalable_font(34, bold=True)
    f_point_body = get_scalable_font(30, bold=False)
    f_cta_title = get_scalable_font(30, bold=True)
    f_cta_body = get_scalable_font(32, bold=False)
    f_footer = get_scalable_font(30, bold=True)

    # 1. Badge Top
    badge_label = f"  {badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 95
    draw.rounded_rectangle([bx - 20, by - 8, bx + bw + 20, by + bh + 10], radius=20, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    # Header
    header_title = "Langkah Terakhir & Aksi"
    l, t, r, b = draw.textbbox((0, 0), header_title, font=f_header)
    tw = r - l
    draw.text(((W - tw) // 2, by + bh + 45), header_title, font=f_header, fill=(255, 255, 255))

    dy = by + bh + 105
    draw.line([(W // 2 - 40, dy), (W // 2 + 40, dy)], fill=(13, 148, 136), width=3)

    # Point 3 Card
    if ":" in point_text:
        p_title, p_desc = point_text.split(":", 1)
    else:
        p_title, p_desc = point_text, ""

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

    # CTA Card Box
    cta_y1 = box_y2 + 40
    cta_lines = textwrap.wrap(cta_text.strip(), width=34)
    cta_h = 40 + 36 + len(cta_lines) * 42 + 20
    cta_y2 = cta_y1 + cta_h

    draw.rounded_rectangle([box_x1, cta_y1, box_x2, cta_y2], radius=16, fill=(16, 32, 28), outline=(16, 185, 129), width=2)
    cy = cta_y1 + 24
    draw.text((box_x1 + 32, cy), "💬 BERIKAN PENDAPATMU:", font=f_cta_title, fill=(52, 211, 153))
    cy += 44
    for cl in cta_lines:
        draw.text((box_x1 + 32, cy), cl, font=f_cta_body, fill=(248, 250, 252))
        cy += 42

    # Footer
    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 90), footer_text, font=f_footer, fill=(148, 163, 184))

    return bg

def render_reels_cover_slide(badge: str, raw_hook: str, footer_text: str):
    """Cover / Thumbnail Khusus Reels Vertikal (9:16)."""
    W, H = 1080, 1920
    bg_url = THEMATIC_BACKGROUNDS.get(badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    try:
        r = requests.get(bg_url, timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 215))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    f_badge = get_scalable_font(32, bold=True)
    f_title = get_scalable_font(68, bold=True)
    f_sub = get_scalable_font(36, bold=False)
    f_footer = get_scalable_font(32, bold=True)

    badge_label = f"  {badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 450
    draw.rounded_rectangle([bx - 28, by - 14, bx + bw + 28, by + bh + 16], radius=28, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    t_lines = textwrap.wrap(raw_hook, width=22)
    ty = by + bh + 90
    for line in t_lines:
        l, t, r, b = draw.textbbox((0, 0), line, font=f_title)
        tw = r - l
        draw.text(((W - tw) // 2, ty), line, font=f_title, fill=(255, 255, 255))
        ty += 84

    ty += 30
    draw.line([(W // 2 - 80, ty), (W // 2 + 80, ty)], fill=(13, 148, 136), width=5)
    ty += 50

    watch_text = "🎬 TONTON VIDEO REELS LENGKAP"
    l, t, r, b = draw.textbbox((0, 0), watch_text, font=f_sub)
    sw = r - l
    draw.text(((W - sw) // 2, ty), watch_text, font=f_sub, fill=(203, 213, 225))

    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 200), footer_text, font=f_footer, fill=(148, 163, 184))

    return bg

def render_single_image(badge: str, hook: str, points: list, footer_text: str):
    """Render 1 foto tunggal feed proporsional."""
    W, H = 1080, 1080
    bg_url = THEMATIC_BACKGROUNDS.get(badge, THEMATIC_BACKGROUNDS["TIPS BISNIS"])
    try:
        r = requests.get(bg_url, timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    overlay = Image.new("RGBA", (W, H), (10, 15, 26, 205))
    bg.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(bg)

    f_badge = get_scalable_font(28, bold=True)
    f_title = get_scalable_font(52, bold=True)
    f_body = get_scalable_font(32, bold=False)
    f_footer = get_scalable_font(30, bold=True)

    badge_label = f"  {badge}  "
    l, t, r, b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw, bh = r - l, b - t
    bx = (W - bw) // 2
    by = 100
    draw.rounded_rectangle([bx - 20, by - 8, bx + bw + 20, by + bh + 10], radius=20, fill=(13, 148, 136))
    draw.text((bx, by), badge_label, font=f_badge, fill=(255, 255, 255))

    t_lines = textwrap.wrap(hook, width=28)
    ty = by + bh + 60
    for line in t_lines:
        l, t, r, b = draw.textbbox((0, 0), line, font=f_title)
        tw = r - l
        draw.text(((W - tw) // 2, ty), line, font=f_title, fill=(255, 255, 255))
        ty += 64

    ty += 20
    draw.line([(W // 2 - 50, ty), (W // 2 + 50, ty)], fill=(13, 148, 136), width=3)
    ty += 40

    for item in points[:3]:
        p_lines = textwrap.wrap(item, width=38)
        for pl in p_lines:
            l, t, r, b = draw.textbbox((0, 0), pl, font=f_body)
            pw = r - l
            draw.text(((W - pw) // 2, ty), pl, font=f_body, fill=(226, 232, 240))
            ty += 46
        ty += 18

    l, t, r, b = draw.textbbox((0, 0), footer_text, font=f_footer)
    fw = r - l
    draw.text(((W - fw) // 2, H - 90), footer_text, font=f_footer, fill=(148, 163, 184))

    return bg

def upload_image_cloud(pil_img):
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    files = {"fileToUpload": ("slide.jpg", buf, "image/jpeg")}
    try:
        r = requests.post("[https://litterbox.catbox.moe/resources/internals/api.php](https://litterbox.catbox.moe/resources/internals/api.php)", data={"reqtype": "fileupload", "time": "72h"}, files=files, timeout=25)
        if r.status_code == 200 and r.text.strip().startswith("http"):
            return r.text.strip()
    except Exception:
        pass
    buf.seek(0)
    try:
        r = requests.post("[https://freeimage.host/api/1/upload](https://freeimage.host/api/1/upload)", data={"key": "6d207e02198a847aa98d0a2a901485a5", "action": "upload", "format": "json"}, files={"source": ("slide.jpg", buf, "image/jpeg")}, timeout=25).json()
        if "image" in r and "url" in r["image"]:
            return r["image"]["url"]
    except Exception:
        pass
    return ""

# ==================== SIDEBAR ====================
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
    
    st.markdown("""
    <div style="background: rgba(18, 24, 38, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px; margin-top: 24px;">
      <div style="font-size: 12px; color: #94A3B8;">⏰ <b>Jadwal Publikasi:</b></div>
      <div style="font-size: 13px; color: #818CF8; font-weight: 600; margin-top: 4px;">09:00 & 17:00 WITA</div>
      <div style="font-size: 11px; color: #64748B; margin-top: 4px;">Serverless Cloud Runner</div>
    </div>
    """, unsafe_allow_html=True)

# ==================== BANNER ====================
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
    Pusat komando konten: riset ide viral 30 hari lintas niche, copywriting Gemini AI, visual render engine, dan penjadwalan cloud mandiri.
  </p>
</div>
""", unsafe_allow_html=True)

tab_ideas, tab_studio, tab_queue, tab_status = st.tabs([
    "💡 Bank Ide Viral (30 Hari)",
    "✨ AI Content Studio",
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

    col_niche, col_ai_refresh = st.columns(2)
    with col_niche:
        niche_options = {v["name"]: k for k, v in niche_db.items()}
        selected_niche_name = st.selectbox("Pilih Niche Konten:", list(niche_options.keys()))
        selected_niche_id = niche_options[selected_niche_name]
    
    with col_ai_refresh:
        st.write("")
        st.write("")
        if st.button("🔄 Riset 30 Ide Baru dengan AI", type="secondary"):
            with st.spinner(f"Gemini 3.6 Flash sedang meriset 30 ide baru untuk {selected_niche_name}..."):
                new_ideas = research_30_ideas_ai(selected_niche_name)
                if new_ideas and len(new_ideas) >= 10:
                    formatted_ideas = []
                    for idx, it in enumerate(new_ideas, 1):
                        formatted_ideas.append({
                            "day": idx,
                            "hook": it.get("hook", f"Ide Hari {idx}"),
                            "angle": it.get("angle", "Strategi Edukasi"),
                            "suggested_format": it.get("suggested_format", "CAROUSEL"),
                            "category": niche_db[selected_niche_id]["category"],
                            "status": "Tersedia"
                        })
                    niche_db[selected_niche_id]["ideas"] = formatted_ideas
                    save_niche_database(niche_db)
                    st.success(f"🎉 Sukses! 30 ide baru berhasil diriset dan disimpan ke database {selected_niche_name}!")
                    st.rerun()

    current_ideas = niche_db[selected_niche_id]["ideas"]
    total_ideas = len(current_ideas)
    avail_ideas = sum(1 for i in current_ideas if i.get("status") == "Tersedia")
    used_ideas = total_ideas - avail_ideas

    c_met1, c_met2, c_met3 = st.columns(3)
    c_met1.metric("Total Kalender", f"{total_ideas} Hari")
    c_met2.metric("Ide Tersedia", avail_ideas)
    c_met3.metric("Sudah Dipakai", used_ideas)

    st.markdown("---")

    filter_status = st.radio("Tampilkan Ide:", ["Semua", "Tersedia", "Sudah Dipakai"], horizontal=True)

    for item in current_ideas:
        item_status = item.get("status", "Tersedia")
        if filter_status != "Semua" and item_status != filter_status:
            continue
            
        day_num = item.get("day", 1)
        hook_text = item.get("hook", "")
        angle = item.get("angle", "Strategi Edukasi")
        sugg_fmt = item.get("suggested_format", "CAROUSEL")
        
        with st.container():
            col_info, col_act = st.columns(2)
            with col_info:
                badge_color = "#22C55E" if item_status == "Tersedia" else "#64748B"
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                  <span style="background: rgba(99, 102, 241, 0.2); color: #818CF8; font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 8px;">HARI {day_num}</span>
                  <span style="background: rgba(255, 255, 255, 0.08); color: #CBD5E1; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px;">{sugg_fmt}</span>
                  <span style="color: #64748B; font-size: 12px;">• {angle}</span>
                  <span style="margin-left: auto; color: {badge_color}; font-size: 11px; font-weight: 700; border: 1px solid {badge_color}; padding: 1px 8px; border-radius: 6px;">{item_status.upper()}</span>
                </div>
                <div style="font-size: 15px; font-weight: 700; color: #FFFFFF; line-height: 1.4;">{hook_text}</div>
                """, unsafe_allow_html=True)
            
            with col_act:
                st.write("")
                if st.button("Gunakan Ide ➡️", key=f"use_idea_{selected_niche_id}_{day_num}", type="primary"):
                    st.session_state["selected_topic"] = hook_text
                    if sugg_fmt == "CAROUSEL":
                        st.session_state["selected_media_type"] = "CAROUSEL (3 Slide)"
                    elif sugg_fmt == "REELS":
                        st.session_state["selected_media_type"] = "REELS (Video)"
                    else:
                        st.session_state["selected_media_type"] = "IMAGE (1 Foto)"
                        
                    item["status"] = "Sudah Dipakai"
                    save_niche_database(niche_db)
                    st.toast(f"✅ Ide Hari {day_num} berhasil dipilih! Silakan buka tab 'AI Content Studio'.")
                    st.rerun()
            st.divider()

# ==================== TAB 2: AI CONTENT STUDIO ====================
with tab_studio:
    st.markdown("""
    <div style="font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 4px;">Studio Pembuatan & Desain Konten</div>
    <div style="font-size: 14px; color: #94A3B8; margin-bottom: 20px;">Tulis atau gunakan ide dari Bank Ide, lalu biarkan AI meracik naskah dan merender kartu visualnya.</div>
    """, unsafe_allow_html=True)
    
    initial_topic = st.session_state.get("selected_topic", "3 Cara Melipatgandakan Omzet Usaha Tanpa Tambah Modal Besar")
    initial_fmt = st.session_state.get("selected_media_type", "CAROUSEL (3 Slide)")
    
    col_input, col_config = st.columns(2)
    with col_input:
        topic_input = st.text_area(
            "Topik Konten atau Ide Bisnis",
            value=initial_topic,
            height=120,
            help="Topik ini bisa diambil otomatis dari Bank Ide atau diketik sendiri secara bebas."
        )
    with col_config:
        fmt_options = ["CAROUSEL (3 Slide)", "IMAGE (1 Foto)", "REELS (Video)"]
        default_idx = fmt_options.index(initial_fmt) if initial_fmt in fmt_options else 0
        media_type = st.selectbox("Format Konten Media", fmt_options, index=default_idx)
        custom_media = st.text_input("Link Media Khusus (Opsional)", placeholder="https://...")
    
    if st.button("🚀 Buat Materi & Render Desain Visual", type="primary"):
        with st.spinner("Gemini 3.6 Flash sedang menyusun materi & mesin grafis merender kartu visual..."):
            caption = generate_caption_ai(topic_input)
            if caption:
                st.session_state["generated_caption"] = caption
                badge, hook, points, cta_text = parse_content(caption)
                if "CAROUSEL" in media_type:
                    s1 = render_cover_slide(badge, hook, branding_handle)
                    s2 = render_content_slide(badge, "Pondasi Utama yang Wajib Dibangun", points[:2], branding_handle)
                    s3 = render_closing_slide(badge, points[-1], cta_text, branding_handle)
                    st.session_state["rendered_slides"] = [s1, s2, s3]
                elif "IMAGE" in media_type:
                    s = render_single_image(badge, hook, points, branding_handle)
                    st.session_state["rendered_slides"] = [s]
                elif "REELS" in media_type:
                    # Render Cover/Thumbnail Vertikal (9:16) khusus untuk Reels
                    rc = render_reels_cover_slide(badge, hook, branding_handle)
                    st.session_state["rendered_slides"] = [rc]

    # PRATINJAU DENGAN TATA LETAK MOCKUP PROPORSIONAL & FITUR REVISI
    if "generated_caption" in st.session_state:
        st.markdown("---")
        st.markdown("""
        <div style="font-size: 18px; font-weight: 700; color: #FFFFFF; margin-bottom: 12px;">Pratinjau Hasil Desain (Smartphone Mockup)</div>
        """, unsafe_allow_html=True)
        
        if "rendered_slides" in st.session_state and st.session_state["rendered_slides"]:
            if len(st.session_state["rendered_slides"]) > 1:
                cols = st.columns(len(st.session_state["rendered_slides"]))
                for idx, (col, slide_img) in enumerate(zip(cols, st.session_state["rendered_slides"]), 1):
                    with col:
                        st.markdown(f"<div style='text-align: center; font-size: 13px; font-weight: 700; color: #818CF8; margin-bottom: 8px;'>SLIDE {idx}</div>", unsafe_allow_html=True)
                        st.image(slide_img, width=320)
            else:
                col_left, col_center, col_right = st.columns(3)
                with col_center:
                    label = "COVER / THUMBNAIL REELS (9:16)" if "REELS" in media_type else "PREVIEW POSTINGAN"
                    st.markdown(f"<div style='text-align: center; font-size: 13px; font-weight: 700; color: #818CF8; margin-bottom: 8px;'>{label}</div>", unsafe_allow_html=True)
                    st.image(st.session_state["rendered_slides"][0], width=320 if "REELS" in media_type else 380)

        # FITUR REVISI & SUNTINGAN LANGSUNG
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🛠️ Area Revisi & Penyempurnaan Desain / Naskah", expanded=True):
            caption_edited = st.text_area(
                "Naskah Caption (Bebas Anda edit kata-katanya di bawah ini):", 
                value=st.session_state["generated_caption"], 
                height=180
            )
            
            col_rev1, col_rev2 = st.columns(2)
            with col_rev1:
                if st.button("🎨 Render Ulang Gambar Sesuai Editan Naskah", type="secondary"):
                    with st.spinner("Menggambar ulang kartu visual dengan teks hasil editan Anda..."):
                        badge, hook, points, cta_text = parse_content(caption_edited)
                        if "CAROUSEL" in media_type:
                            s1 = render_cover_slide(badge, hook, branding_handle)
                            s2 = render_content_slide(badge, "Pondasi Utama yang Wajib Dibangun", points[:2], branding_handle)
                            s3 = render_closing_slide(badge, points[-1], cta_text, branding_handle)
                            st.session_state["rendered_slides"] = [s1, s2, s3]
                        elif "IMAGE" in media_type:
                            s = render_single_image(badge, hook, points, branding_handle)
                            st.session_state["rendered_slides"] = [s]
                        elif "REELS" in media_type:
                            rc = render_reels_cover_slide(badge, hook, branding_handle)
                            st.session_state["rendered_slides"] = [rc]
                            
                        st.session_state["generated_caption"] = caption_edited
                        st.success("✅ Kartu visual berhasil diperbarui sesuai teks editan Anda!")
                        st.rerun()

            with col_rev2:
                revision_note = st.text_input("Catatan Revisi Khusus untuk AI", placeholder="Contoh: Buat judul lebih pendek dan menusuk")
                if st.button("🔄 Minta AI Buat Ulang (Revisi Otomatis)", type="secondary"):
                    with st.spinner("Gemini AI sedang menulis ulang materi sesuai catatan revisi..."):
                        new_cap = generate_caption_ai(topic_input, revision_note)
                        if new_cap:
                            st.session_state["generated_caption"] = new_cap
                            badge, hook, points, cta_text = parse_content(new_cap)
                            if "CAROUSEL" in media_type:
                                s1 = render_cover_slide(badge, hook, branding_handle)
                                s2 = render_content_slide(badge, "Pondasi Utama yang Wajib Dibangun", points[:2], branding_handle)
                                s3 = render_closing_slide(badge, points[-1], cta_text, branding_handle)
                                st.session_state["rendered_slides"] = [s1, s2, s3]
                            elif "IMAGE" in media_type:
                                s = render_single_image(badge, hook, points, branding_handle)
                                st.session_state["rendered_slides"] = [s]
                            elif "REELS" in media_type:
                                rc = render_reels_cover_slide(badge, hook, branding_handle)
                                st.session_state["rendered_slides"] = [rc]
                            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        # Tombol Simpan
        if st.button("💾 Simpan ke Antrean Terjadwal (posts.json)", type="primary"):
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
                    new_entry["video_url"] = custom_media if custom_media else "[https://files.catbox.moe/ez3k5w.mp4](https://files.catbox.moe/ez3k5w.mp4)"
                posts.append(new_entry)
                save_posts(posts)
                st.success(f"🎉 Sukses! Draf `{new_id}` berhasil dimasukkan ke antrean posts.json bertanda PENDING!")

# ==================== TAB 3: ANTREAN & KALENDER ====================
with tab_queue:
    st.markdown("""
    <div style="font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 4px;">Manajemen Antrean & Kalender Jadwal</div>
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
