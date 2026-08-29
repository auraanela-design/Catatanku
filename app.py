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

# 1. Konfigurasi Halaman
st.set_page_config(
    page_title="Laaura's Resume",
    page_icon="🩰",
    layout="wide"
)

# 2. Daftar Tema dengan Full Screen Gradient & Emotikon Spesifik
THEMES = {
    "🩰 Coquette Pink": {
        "gradient": "linear-gradient(135deg, #FFE4E1 0%, #FFC0CB 50%, #E6E6FA 100%)",
        "card_bg": "rgba(255, 255, 255, 0.65)",
        "text": "#5C2C3B",
        "accent": "#E899AC",
        "emojis": "🩰 🎀 🕯️ 🦢 🎀",
        "header_color": colors.HexColor("#D87093")
    },
    "☁️ Langit Cerah": {
        "gradient": "linear-gradient(135deg, #E0F7FA 0%, #B3E5FC 50%, #E1BEE7 100%)",
        "card_bg": "rgba(255, 255, 255, 0.65)",
        "text": "#1F3A52",
        "accent": "#81D4FA",
        "emojis": "☁️ 🌙 🕊️ 💫 🌤️",
        "header_color": colors.HexColor("#0288D1")
    },
    "🍵 Matcha Soft": {
        "gradient": "linear-gradient(135deg, #F1F8E9 0%, #DCEDC8 50%, #C8E6C9 100%)",
        "card_bg": "rgba(255, 255, 255, 0.65)",
        "text": "#2D4A27",
        "accent": "#AED581",
        "emojis": "🍵 🍃 🌱 🫖 🧁",
        "header_color": colors.HexColor("#558B2F")
    },
    "🍂 Earth Warm": {
        "gradient": "linear-gradient(135deg, #FDFBF7 0%, #F5E6D3 50%, #E2D1C3 100%)",
        "card_bg": "rgba(255, 255, 255, 0.65)",
        "text": "#4A3B32",
        "accent": "#D7B596",
        "emojis": "🍂 ☕ 🧸 🪵 🌾",
        "header_color": colors.HexColor("#8B5A2B")
    }
}

# 3. Sidebar Selection
selected_theme_name = st.sidebar.selectbox("🎨 Pilih Tema:", list(THEMES.keys()))
theme = THEMES[selected_theme_name]
emojis = theme['emojis'].split()

# CSS untuk Full Screen Gradient
st.markdown(f"""
    <style>
    /* Full Page Gradient */
    .stApp {{
        background: {theme['gradient']};
        background-attachment: fixed;
        color: {theme['text']};
        font-family: 'Quicksand', 'Poppins', sans-serif;
    }}
    
    /* Title & Watermark Styles */
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
    
    /* Container & Card Styling */
    div[data-testid="stExpander"], div[data-testid="stFileUploader"] {{
        background-color: {theme['card_bg']};
        border-radius: 15px;
        padding: 10px;
    }}

    /* Button Styling */
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

# 6. Pembuat Rangkuman
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
        
    summary = ". ".join(sentences[:limit]) + "."
    return summary

# 7. Pembuat PDF Bertema dengan Watermark "Created by Laaura"
def create_pdf(summary_text, images, theme_info):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=theme_info['header_color'],
        alignment=1,
        spaceAfter=8
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
        fontSize=10,
        leading=15,
        spaceAfter=10
    )

    story = []
    
    # Title & Header
    story.append(Paragraph(f"{theme_info['emojis']} Laaura's Resume {theme_info['emojis']}", title_style))
    story.append(Paragraph("<b>Created by Laaura ✨</b>", author_style))
    story.append(Spacer(1, 10))
    
    # Teks Rangkuman
    for paragraph in summary_text.split('\n'):
        if paragraph.strip():
            story.append(Paragraph(paragraph, body_style))
            story.append(Spacer(1, 6))
            
    # Lampiran Gambar
    if images:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>{emojis[2]} Lampiran Gambar:</b>", body_style))
        for img in images[:5]:
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            rl_img = RLImage(img_buffer, width=280, height=180)
            story.append(rl_img)
            story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    return buffer

# 8. Antarmuka Utama
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
        
        # Galeri Gambar Ekstraksi
        if images:
            st.markdown(f"### {emojis[2]} Galeri Gambar ({len(images)})")
            cols = st.columns(min(3, len(images)))
            for idx, img in enumerate(images[:6]):
                with cols[idx % 3]:
                    st.image(img, caption=f"Gambar {idx+1}", use_column_width=True)
                    
        # Tombol Download PDF
        pdf_bytes = create_pdf(summary, images, theme)
        st.download_button(
            label="✨ Download PDF Rangkuman (Created by Laaura)",
            data=pdf_bytes,
            file_name=f"Laaura_Resume_{uploaded_file.name}.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("Tidak ditemukan teks yang dapat dibaca dari dokumen ini.")
