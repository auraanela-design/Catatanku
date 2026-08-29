import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from pptx import Presentation
from PIL import Image
import io
import base64
from weasyprint import HTML

# 1. Konfigurasi Halaman
st.set_page_config(
    page_title="Laaura's Resume",
    page_icon="🩰",
    layout="wide"
)

# 2. Daftar Tema dengan Full Screen Gradient & Warna PDF Custom
THEMES = {
    "🩰 Coquette Pink": {
        "gradient": "linear-gradient(135deg, #FFE4E1 0%, #FFC0CB 50%, #E6E6FA 100%)",
        "card_bg": "rgba(255, 255, 255, 0.65)",
        "text": "#5C2C3B",
        "accent": "#E899AC",
        "emojis": "🩰 🎀 🕯️ 🦢 🎀",
        "pdf_bg": "#FFF0F5",
        "pdf_border": "#FFB6C1",
        "pdf_header": "#D87093"
    },
    "☁️ Langit Cerah": {
        "gradient": "linear-gradient(135deg, #E0F7FA 0%, #B3E5FC 50%, #E1BEE7 100%)",
        "card_bg": "rgba(255, 255, 255, 0.65)",
        "text": "#1F3A52",
        "accent": "#81D4FA",
        "emojis": "☁️ 🌙 🕊️ 💫 🌤️",
        "pdf_bg": "#F0F8FF",
        "pdf_border": "#B0E0E6",
        "pdf_header": "#0288D1"
    },
    "🍵 Matcha Soft": {
        "gradient": "linear-gradient(135deg, #F1F8E9 0%, #DCEDC8 50%, #C8E6C9 100%)",
        "card_bg": "rgba(255, 255, 255, 0.65)",
        "text": "#2D4A27",
        "accent": "#AED581",
        "emojis": "🍵 🍃 🌱 🫖 🧁",
        "pdf_bg": "#F4F9F4",
        "pdf_border": "#C8E6C9",
        "pdf_header": "#558B2F"
    },
    "🍂 Earth Warm": {
        "gradient": "linear-gradient(135deg, #FDFBF7 0%, #F5E6D3 50%, #E2D1C3 100%)",
        "card_bg": "rgba(255, 255, 255, 0.65)",
        "text": "#4A3B32",
        "accent": "#D7B596",
        "emojis": "🍂 ☕ 🧸 🪵 🌾",
        "pdf_bg": "#FAF0E6",
        "pdf_border": "#E2D1C3",
        "pdf_header": "#8B5A2B"
    }
}

# 3. Sidebar Selection
selected_theme_name = st.sidebar.selectbox("🎨 Pilih Tema:", list(THEMES.keys()))
theme = THEMES[selected_theme_name]
emojis = theme['emojis'].split()

# Styling CSS untuk Streamlit UI
st.markdown(f"""
    <style>
    .stApp {{
        background: {theme['gradient']};
        background-attachment: fixed;
        color: {theme['text']};
        font-family: 'Quicksand', 'Poppins', sans-serif;
    }}
    .main-title {{
        text-align: center;
        color: {theme['text']};
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0px;
    }}
    .watermark-tag {{
        text-align: center;
        font-size: 1.1rem;
        color: {theme['text']};
        font-weight: 600;
        letter-spacing: 1px;
        margin-top: 5px;
        margin-bottom: 25px;
        opacity: 0.9;
    }}
    div[data-testid="stExpander"], div[data-testid="stFileUploader"] {{
        background-color: {theme['card_bg']};
        border-radius: 15px;
        padding: 10px;
    }}
    .stButton>button {{
        background-color: {theme['accent']} !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.5rem 1.5rem !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.12);
    }}
    </style>
""", unsafe_allow_html=True)

# 4. Header Section
st.markdown(f"<h1 class='main-title'>{emojis[0]} Laaura's Resume {emojis[1]}</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='watermark-tag'>✨ Created by Laaura ✨</p>", unsafe_allow_html=True)

# 5. Ekstraksi Dokumen & Gambar
def extract_from_pdf(uploaded_file):
    text = ""
    images = []
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        text += page.get_text() + "\n"
        for img in page.get_images():
            xref = img[0]
            base_image = doc.extract_image(xref)
            images.append(Image.open(io.BytesIO(base_image["image"])))
    return text, images

def extract_from_docx(uploaded_file):
    doc = Document(uploaded_file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text])
    images = []
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            images.append(Image.open(io.BytesIO(rel.target_part.blob)))
    return text, images

def extract_from_pptx(uploaded_file):
    prs = Presentation(uploaded_file)
    text = ""
    images = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text += paragraph.text + "\n"
            if shape.shape_type == 13:
                images.append(Image.open(io.BytesIO(shape.image.blob)))
    return text, images

# 6. Generator Rangkuman Teks
def generate_summary(text, length_option):
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
    if not sentences:
        return "Tidak ada teks yang cukup untuk dirangkum."
    
    if length_option == "Singkat":
        limit = max(3, len(sentences) // 4)
    elif length_option == "Sedang":
        limit = max(5, len(sentences) // 2)
    else:
        limit = max(8, int(len(sentences) * 0.75))
        
    return ". ".join(sentences[:limit]) + "."

# 7. Fungsi Generator PDF Estetis Menggunakan HTML & WeasyPrint
def generate_pdf_weasyprint(summary_text, images, theme_info):
    img_html_list = []
    for img in images[:4]:
        buffered = io.BytesIO()
        img.convert('RGB').save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        img_html_list.append(f'<img src="data:image/jpeg;base64,{img_str}" class="summary-img" />')
    
    images_container = "".join(img_html_list)
    paragraphs = "".join([f"<p>{p.strip()}.</p>" for p in summary_text.split('.') if p.strip()])

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 15mm 12mm;
                background-color: {theme_info['pdf_bg']};
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                color: #333333;
                margin: 0;
                padding: 0;
            }}
            .header-card {{
                background-color: #ffffff;
                border: 2px dashed {theme_info['pdf_border']};
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                margin-bottom: 25px;
            }}
            .title {{
                color: {theme_info['pdf_header']};
                font-size: 24pt;
                font-weight: bold;
                margin: 0 0 5px 0;
            }}
            .subtitle {{
                color: #777777;
                font-size: 11pt;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            .content-box {{
                background-color: #ffffff;
                border-radius: 12px;
                padding: 20px;
                border-left: 6px solid {theme_info['pdf_header']};
                line-height: 1.6;
                font-size: 11pt;
            }}
            .content-box p {{
                margin-bottom: 12px;
            }}
            .section-title {{
                color: {theme_info['pdf_header']};
                font-size: 14pt;
                margin-top: 25px;
                margin-bottom: 15px;
                border-bottom: 2px solid {theme_info['pdf_border']};
                padding-bottom: 5px;
            }}
            .gallery {{
                text-align: center;
            }}
            .summary-img {{
                width: 45%;
                max-height: 180px;
                object-fit: cover;
                border-radius: 10px;
                margin: 5px;
                border: 1px solid #eeeeee;
            }}
        </style>
    </head>
    <body>
        <div class="header-card">
            <div class="title">{theme_info['emojis'].split()[0]} Laaura's Resume {theme_info['emojis'].split()[1]}</div>
            <div class="subtitle">✨ Created by Laaura ✨</div>
        </div>

        <div class="content-box">
            {paragraphs}
        </div>

        {f'<div class="section-title">{theme_info["emojis"].split()[2]} Lampiran Visual</div><div class="gallery">' + images_container + '</div>' if img_html_list else ''}
    </body>
    </html>
    """
    
    pdf_bytes = io.BytesIO()
    HTML(string=html_content).write_pdf(pdf_bytes)
    pdf_bytes.seek(0)
    return pdf_bytes

# 8. Antarmuka Utama Aplikasi
st.sidebar.subheader(f"{emojis[2]} Pengaturan Rangkuman")
summary_length = st.sidebar.radio("Jenis Rangkuman:", ["Singkat", "Sedang", "Panjang"])

uploaded_file = st.file_uploader(
    f"{emojis[3]} Unggah dokumen kamu (PDF, PPTX, atau DOCX):", 
    type=["pdf", "pptx", "docx"]
)

if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    with st.spinner(f"Sedang merangkum dokumen kamu... {emojis[4]}"):
        if file_type == "pdf":
            raw_text, images = extract_from_pdf(uploaded_file)
        elif file_type == "docx":
            raw_text, images = extract_from_docx(uploaded_file)
        elif file_type == "pptx":
            raw_text, images = extract_from_pptx(uploaded_file)

    if raw_text.strip():
        summary = generate_summary(raw_text, summary_length)
        
        st.markdown(f"### {emojis[0]} Hasil Rangkuman")
        st.write(summary)
        
        if images:
            st.markdown(f"### {emojis[2]} Galeri Gambar ({len(images)})")
            cols = st.columns(min(3, len(images)))
            for idx, img in enumerate(images[:6]):
                with cols[idx % 3]:
                    st.image(img, caption=f"Gambar {idx+1}", use_column_width=True)
                    
        # Download PDF
        pdf_file = generate_pdf_weasyprint(summary, images, theme)
        st.download_button(
            label="✨ Download PDF Rangkuman (Created by Laaura)",
            data=pdf_file,
            file_name=f"Laaura_Resume_{uploaded_file.name}.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("Tidak ditemukan teks yang dapat dibaca dari dokumen ini.")
