import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from pptx import Presentation
from PIL import Image
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Konfigurasi Halaman & Tema Cute
st.set_page_config(
    page_title="Rangkuman Cute Nela Aura",
    page_icon="🌸",
    layout="wide"
)

# Pilihan Tema Warna dan Emotikon
THEMES = {
    "🌸 Sakura Pink": {
        "primary": "#FFB7C5",
        "bg": "#FFF0F5",
        "text": "#8B2252",
        "emojis": "🌸 🍓 🧋 🦄 ✨",
        "header_color": colors.HexColor("#FF69B4")
    },
    "🧸 Warm Teddy": {
        "primary": "#D2B48C",
        "bg": "#FAF0E6",
        "text": "#5C4033",
        "emojis": "🧸 ☕ 🧇 🍪 🍂",
        "header_color": colors.HexColor("#8B4513")
    },
    "🎀 Coquette Bow": {
        "primary": "#FFC0CB",
        "bg": "#FFFFFF",
        "text": "#4A4A4A",
        "emojis": "🎀 🕯️ 🩰 🦢 💫",
        "header_color": colors.HexColor("#DB7093")
    },
    "🍵 Matcha Cream": {
        "primary": "#C1E1C1",
        "bg": "#F4F9F4",
        "text": "#2E4A2E",
        "emojis": "🍵 🍃 🐸 🍏 🧁",
        "header_color": colors.HexColor("#4A7C59")
    },
    "☁️ Cloud Lavender": {
        "primary": "#E6E6FA",
        "bg": "#F8F8FF",
        "text": "#4B0082",
        "emojis": "☁️ 🌙 💜 🔮 🍰",
        "header_color": colors.HexColor("#9370DB")
    }
}

# Apply CSS Styling berdasarkan Tema Pilihan
selected_theme_name = st.sidebar.selectbox("🎨 Pilih Tema Cute:", list(THEMES.keys()))
theme = THEMES[selected_theme_name]

st.markdown(f"""
    <style>
    .stApp {{
        background-color: {theme['bg']};
        color: {theme['text']};
    }}
    .main-title {{
        text-align: center;
        color: {theme['text']};
        font-family: 'Comic Sans MS', cursive, sans-serif;
    }}
    .watermark-tag {{
        text-align: center;
        font-size: 14px;
        color: {theme['text']};
        font-weight: bold;
        margin-bottom: 20px;
    }}
    .stButton>button {{
        background-color: {theme['primary']};
        color: black;
        border-radius: 15px;
        border: none;
        font-weight: bold;
    }}
    </style>
""", unsafe_allow_html=True)

# 2. Header Utama
st.markdown(f"<h1 class='main-title'>{theme['emojis'].split()[0]} Pembuat Rangkuman Cute {theme['emojis'].split()[1]}</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='watermark-tag'>✨ Created specially by Nela Aura ✨</p>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center;'>Ekstrak teks & gambar dari dokumen PDF, PPT, atau Word secara otomatis!</p>", unsafe_allow_html=True)

# 3. Fungsi Pembaca Dokumen & Ekstraksi Gambar
def extract_from_pdf(uploaded_file):
    text = ""
    images = []
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        text += page.get_text() + "\n"
        for img_index, img in enumerate(page.get_images()):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            images.append(Image.open(io.BytesIO(image_bytes)))
    return text, images

def extract_from_docx(uploaded_file):
    doc = Document(uploaded_file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text])
    images = []
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            img_data = rel.target_part.blob
            images.append(Image.open(io.BytesIO(img_data)))
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
            if shape.shape_type == 13:  # Picture
                image_bytes = shape.image.blob
                images.append(Image.open(io.BytesIO(image_bytes)))
    return text, images

# 4. Fungsi Rangkuman Sederhana (Text Summarizer Engine)
def generate_summary(text, length_option):
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
    if not sentences:
        return "Tidak dapat menemukan teks yang cukup untuk dirangkum."
    
    if length_option == "Singkat":
        limit = max(3, len(sentences) // 4)
    elif length_option == "Sedang":
        limit = max(5, len(sentences) // 2)
    else:
        limit = max(8, int(len(sentences) * 0.75))
        
    summary = ". ".join(sentences[:limit]) + "."
    return summary

# 5. Fungsi Export PDF Bertema & Berhias
def create_pdf(summary_text, images, theme_info):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=theme_info['header_color'],
        alignment=1,
        spaceAfter=10
    )
    
    author_style = ParagraphStyle(
        'AuthorStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.gray,
        alignment=1,
        spaceAfter=20
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        spaceAfter=12
    )

    story = []
    
    # Title & Watermark Nela Aura
    story.append(Paragraph(f"{theme_info['emojis']} Rangkuman Catatan Cute {theme_info['emojis']}", title_style))
    story.append(Paragraph("<b>Dokumen Rangkuman Resmi oleh: Nela Aura ✨</b>", author_style))
    story.append(Spacer(1, 12))
    
    # Text Rangkuman
    for paragraph in summary_text.split('\n'):
        if paragraph.strip():
            story.append(Paragraph(paragraph, body_style))
            story.append(Spacer(1, 8))
            
    # Menyertakan Gambar
    if images:
        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>📷 Lampiran Gambar dari Dokumen:</b>", body_style))
        for img in images[:5]:  # Batasi maksimal 5 gambar
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            rl_img = RLImage(img_buffer, width=300, height=200)
            story.append(rl_img)
            story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return buffer

# 6. Interaksi Pengguna
st.sidebar.subheader("⚙️ Pengaturan Rangkuman")
summary_length = st.sidebar.radio("Panjang Rangkuman:", ["Singkat", "Sedang", "Lengkap"])

uploaded_file = st.file_uploader(
    "Unggah dokumen kamu di sini (PDF, PPTX, atau DOCX):", 
    type=["pdf", "pptx", "docx"]
)

if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    with st.spinner("Sedang membaca dokumen & mengekstrak gambar... 🌸"):
        if file_type == "pdf":
            raw_text, images = extract_from_pdf(uploaded_file)
        elif file_type == "docx":
            raw_text, images = extract_from_docx(uploaded_file)
        elif file_type == "pptx":
            raw_text, images = extract_from_pptx(uploaded_file)

    if raw_text.strip():
        summary = generate_summary(raw_text, summary_length)
        
        st.subheader("📝 Hasil Rangkuman")
        st.write(summary)
        
        # Display Images jika ada
        if images:
            st.subheader(f"🖼️ Gambar Ditemukan ({len(images)})")
            cols = st.columns(min(3, len(images)))
            for idx, img in enumerate(images[:6]):
                with cols[idx % 3]:
                    st.image(img, caption=f"Gambar {idx+1}", use_column_width=True)
                    
        # Tombol Download PDF
        pdf_bytes = create_pdf(summary, images, theme)
        st.download_button(
            label="✨ Download PDF Rangkuman (Versi Nela Aura)",
            data=pdf_bytes,
            file_name=f"Rangkuman_Cute_Nela_Aura_{uploaded_file.name}.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("Dokumen ini tidak memiliki teks yang dapat dibaca.")
