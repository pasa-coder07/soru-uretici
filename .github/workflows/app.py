import streamlit as st
import openai
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
import json

# Sayfa Tasarımı
st.set_page_config(page_title="AI Soru Asistanı", page_icon="🎓", layout="centered")
st.title("🎓 Video & PDF Soru Üreteci")

# API Anahtarı Girişi (Sidebar'dan veya Secrets'tan alınır)
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

if not api_key:
    st.warning("Lütfen sol taraftan OpenAI API anahtarınızı girin.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

tab1, tab2 = st.tabs(["📄 PDF Yükle", "🎬 YouTube Linki"])

# --- PDF SEKMESİ ---
with tab1:
    pdf_dosya = st.file_uploader("Ders Notu / PDF Yükleyin", type=["pdf"])
    if pdf_dosya and st.button("PDF'den Soru Üret"):
        with st.spinner("PDF okunuyor ve sorular üretiliyor..."):
            reader = PdfReader(pdf_dosya)
            metin = ""
            for sayfa in reader.pages[:5]:  # İlk 5 sayfayı al
                metin += sayfa.extract_text() or ""
            
            prompt = f"Aşağıdaki metinden 3 adet çoktan seçmeli soru üret. Sadece JSON formatında ver:\n\n{metin[:3000]}"
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen bir öğretmensin. Soruları 'sorular': [{'soru':'', 'siklar':{'A':'','B':'','C':'','D':''}, 'dogru_cevap':'A', 'aciklama':''}] formatında JSON olarak ver."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            sorular = json.loads(response.choices[0].message.content).get("sorular", [])
            st.session_state["sorular"] = sorular

# --- YOUTUBE SEKMESİ ---
with tab2:
    video_url = st.text_input("YouTube Video Linki (Örn: https://www.youtube.com/watch?v=...)")
    if video_url and st.button("Videodan Soru Üret"):
        with st.spinner("Altyazılar çekiliyor ve sorular hazırlanıyor..."):
            try:
                # Video ID ayrıştırma
                if "v=" in video_url:
                    video_id = video_url.split("v=")[1].split("&")[0]
                else:
                    video_id = video_url.split("/")[-1]

                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['tr', 'en'])
                metin = " ".join([t['text'] for t in transcript[:100]]) # İlk kısımlar
                
                prompt = f"Bu video transkriptinden 3 adet soru üret:\n\n{metin}"
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Soruları JSON formatında 'sorular' dizisi olarak üret."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                sorular = json.loads(response.choices[0].message.content).get("sorular", [])
                st.session_state["sorular"] = sorular
            except Exception as e:
                st.error(f"Hata oluştu: Videoda altyazı bulunamadı veya link hatalı. ({e})")

# --- SORULARI GÖSTERME (QUIZ ALANI) ---
if "sorular" in st.session_state:
    st.write("---")
    st.subheader("📝 Hazırlanan Quiz")
    for i, s in enumerate(st.session_state["sorular"]):
        st.markdown(f"**Soru {i+1}: {s['soru']}**")
        secim = st.radio(f"Cevabınız ({i+1}):", list(s['siklar'].items()), format_func=lambda x: f"{x[0]}) {x[1]}", key=f"q_{i}")
        
        if st.button(f"Cevabı Kontrol Et #{i+1}", key=f"btn_{i}"):
            if secim[0] == s['dogru_cevap']:
                st.success(f"✅ Doğru! Açıklama: {s.get('aciklama', '')}")
            else:
                st.error(f"❌ Yanlış! Doğru Cevap: {s['dogru_cevap']}. Açıklama: {s.get('aciklama', '')}")
