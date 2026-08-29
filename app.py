import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from pptx import Presentation
from PIL import Image
import io

# ReportLab Imports
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Page Configuration
st.set_page_config(
    page_title="Laaura's Resume",
    page_icon="🩰",
    layout="wide"
)

# 2. Themes Definition
THEMES = {
    "🩰 Coquette Pink": {
        "gradient": "linear-gradient(135deg, #FFE4E1 0%, #FFC0CB 50%, #E6E6FA 100%)",
        "card_bg": "rgba(255, 255, 255, 0.75)",
        "text": "#5C2C3B",
        "accent": "#E899AC",
        "emojis": "🩰 🎀 🕯️ 🦢 🎀",
        "pdf_bg": colors.HexColor("#FFF0F5"),
        "pdf_border": colors.HexColor("#FFB6C1"),
        "pdf_header": colors.HexColor("#D87093"),
        "line_color": "#FFC0CB"
    },
    "☁️ Langit Cerah": {
        "gradient": "linear-gradient(135deg, #E0F7FA 0%, #B3E5FC 50%, #E1BEE7 100%)",
        "card_bg": "rgba(255, 255, 255, 0.75)",
        "text": "#1F3A52",
        "accent": "#81D4FA",
        "emojis": "☁️ 🌙 🕊️ 💫 🌤️",
        "pdf_bg": colors.HexColor("#F0F8FF"),
        "pdf_border": colors.HexColor("#B0E0E6"),
        "pdf_header": colors.HexColor("#0288D1"),
        "line_color": "#B0E0E6"
    },
    "🍵 Matcha Soft": {
        "gradient": "linear-gradient(135deg, #F1F8E9 0%, #DCEDC8 50%, #C8E6C9 100%)",
        "card_bg": "rgba(255, 255, 255, 0.75)",
        "text": "#2D4A27",
        "accent": "#AED581",
        "emojis": "🍵 🍃 🌱 🫖 🧁",
        "pdf_bg": colors.HexColor("#F4F9F4"),
        "pdf_border": colors.HexColor("#C8E6C9"),
        "pdf_header": colors.HexColor("#558B2F"),
        "line_color": "#C8E6C9"
    },
    "🍂 Earth Warm": {
        "gradient": "linear-gradient(135deg, #FDFBF7 0%, #F5E6D3 50%, #E2D1C3 100%)",
        "card_bg": "rgba(255, 255, 255, 0.75)",
        "text": "#4A3B32",
        "accent": "#D7B596",
        "emojis": "🍂 ☕ 🧸 🪵 🌾",
        "pdf_bg": colors.HexColor("#FAF0E6"),
        "pdf_border": colors.HexColor("#E2D1C3"),
        "pdf_header": colors.HexColor("#8B5A2B"),
        "line_color": "#E2D1C3"
    }
}

# Fonts Definition (ReportLab built-in standard fonts & CSS fallbacks)
FONTS = {
    "Classic Serif (Times)": {"rl": "Times-Roman", "rl_bold": "Times-Bold", "css": "'Times New Roman', serif"},
    "Modern Sans (Helvetica)": {"rl": "Helvetica", "rl_bold": "Helvetica-Bold", "css": "'Helvetica Neue', Helvetica, Arial, sans-serif"},
    "Typewriter Monospace (Courier)": {"rl": "Courier", "rl_bold": "Courier-Bold", "css": "'Courier New', Courier, monospace"}
}

# 3. Sidebar Selection & Customization
st.sidebar.subheader("🎨 Custom Studio & Tema")
selected_theme_name = st.sidebar.selectbox("Pilih Tema Color Palette:", list(THEMES.keys()))
theme = THEMES[selected_theme_name]
emojis = theme['emojis'].split()

st.sidebar.subheader("📄 Kustomisasi Kertas & Font")
paper_style = st.sidebar.selectbox(
    "Pilih Pola Kertas:",
    ["Polos (Clean Blank)", "Buku Tulis (Ruled Lines)", "Kotak-Kotak (Grid)", "Bintik-Bintik (Dotted)"]
)

font_style_name = st.sidebar.selectbox("Pilih Gaya Font:", list(FONTS.keys()))
selected_font = FONTS[font_style_name]

summary_length = st.sidebar.radio("Jenis Rangkuman:", ["Singkat", "Sedang", "Panjang"])

# Inject CSS Dynamic Page & Background Styling
paper_bg_css = ""
if paper_style == "Buku Tulis (Ruled Lines)":
    paper_bg_css = f"background-image: repeating-linear-gradient(transparent, transparent 27px, {theme['line_color']} 28px);"
elif paper_style == "Kotak-Kotak (Grid)":
    paper_bg_css = f"""
    background-image: linear-gradient({theme['line_color']} 1px, transparent 1px), linear-gradient(90deg, {theme['line_color']} 1px, transparent 1px);
    background-size: 20px 20px;
    """
elif paper_style == "Bintik-Bintik (Dotted)":
    paper_bg_css = f"""
    background-image: radial-gradient({theme['line_color']} 1.5px, transparent 1.5px);
    background-size: 20px 20px;
    """

st.markdown(f"""
    <style>
    .stApp {{
        background: {theme['gradient']};
        background-attachment: fixed;
        color: {theme['text']};
        font-family: {selected_font['css']};
    }}
    .main-title {{
        text-align: center;
        color: {theme['text']};
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0px;
        font-family: {selected_font['css']};
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
        font-family: {selected_font['css']};
    }}
    div[data-testid="stExpander"], div[data-testid="stFileUploader"] {{
        background-color: {theme['card_bg']};
        border-radius: 15px;
        padding: 10px;
    }}
    .preview-paper {{
        background-color: #ffffff;
        border: 2px solid {theme['line_color']};
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.06);
        color: #333333;
        font-family: {selected_font['css']};
        line-height: 1.8;
        {paper_bg_css}
    }}
    .stButton>button {{
        background-color: {theme['accent']} !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.6rem 1.8rem !important;
        font-size: 1rem !important;
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

# 5. Extraction Functions
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

# 6. Summarizer
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

# 7. ReportLab PDF Generation with Paper Patterns
def create_custom_pdf(summary_text, images, theme_info, font_info, pattern_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=36, 
        leftMargin=36, 
        topMargin=36, 
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'HeaderTitleCustom',
        fontName=font_info['rl_bold'],
        fontSize=20,
        textColor=theme_info['pdf_header'],
        alignment=1,
        spaceAfter=4
    )
    
    sub_style = ParagraphStyle(
        'HeaderSubCustom',
        fontName=font_info['rl'],
        fontSize=11,
        textColor=colors.gray,
        alignment=1
    )

    body_style = ParagraphStyle(
        'BodyTextCustomPaper',
        fontName=font_info['rl'],
        fontSize=10.5,
        leading=16,
        textColor=colors.HexColor("#333333"),
        spaceAfter=8
    )

    story = []

    # Header Card
    header_data = [[
        Paragraph(f"<b>{theme_info['emojis']} Laaura's Resume {theme_info['emojis']}</b>", title_style),
    ], [
        Paragraph("<b>✨ Created by Laaura ✨</b>", sub_style)
    ]]
    
    header_table = Table(header_data, colWidths=[520])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOX', (0,0), (-1,-1), 1.5, theme_info['pdf_border']),
        ('PADDING', (0,0), (-1,-1), 12),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 18))

    # Summary Container
    formatted_summary = summary_text.replace('\n', '<br/><br/>')
    summary_paragraph = Paragraph(formatted_summary, body_style)
    
    summary_table = Table([[summary_paragraph]], colWidths=[520])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('LINELEFT', (0,0), (-1,-1), 4, theme_info['pdf_header']),
        ('BOX', (0,0), (-1,-1), 1, theme_info['pdf_border']),
        ('PADDING', (0,0), (-1,-1), 15),
    ]))
    
    story.append(summary_table)

    # Images
    if images:
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"<b>{emojis[2]} Lampiran Gambar:</b>", ParagraphStyle('ImgHeaderCustom', fontName=font_info['rl_bold'], fontSize=12, textColor=theme_info['pdf_header'])))
        story.append(Spacer(1, 8))
        
        for img in images[:4]:
            img_buffer = io.BytesIO()
            img.convert('RGB').save(img_buffer, format='JPEG')
            img_buffer.seek(0)
            rl_img = RLImage(img_buffer, width=240, height=150)
            
            img_table = Table([[rl_img]], colWidths=[520])
            img_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 6)
            ]))
            story.append(img_table)
            story.append(Spacer(1, 10))

    # Pattern Drawing Engine
    def draw_background_and_pattern(canvas, doc):
        canvas.saveState()
        # Draw Background Color
        canvas.setFillColor(theme_info['pdf_bg'])
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
        
        # Draw Paper Patterns
        line_col = theme_info['pdf_border']
        canvas.setStrokeColor(line_col)
        canvas.setFillColor(line_col)
        canvas.setLineWidth(0.5)
        
        width, height = doc.pagesize
        
        if pattern_name == "Buku Tulis (Ruled Lines)":
            y = 20
            while y < height:
                canvas.line(0, y, width, y)
                y += 24
        elif pattern_name == "Kotak-Kotak (Grid)":
            x = 0
            while x < width:
                canvas.line(x, 0, x, height)
                x += 20
            y = 0
            while y < height:
                canvas.line(0, y, width, y)
                y += 20
        elif pattern_name == "Bintik-Bintik (Dotted)":
            x = 10
            while x < width:
                y = 10
                while y < height:
                    canvas.circle(x, y, 1, fill=1, stroke=0)
                    y += 20
                x += 20
                
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_background_and_pattern, onLaterPages=draw_background_and_pattern)
    buffer.seek(0)
    return buffer

# 8. Interactive UI Workflow
uploaded_file = st.file_uploader(
    f"{emojis[3]} Unggah dokumen kamu (PDF, PPTX, atau DOCX):", 
    type=["pdf", "pptx", "docx"]
)

if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    if st.button("✨ Buat Rangkuman Custom"):
        with st.spinner(f"Sedang merangkum dan mendesain kertas kamu... {emojis[4]}"):
            if file_type == "pdf":
                raw_text, images = extract_from_pdf(uploaded_file)
            elif file_type == "docx":
                raw_text, images = extract_from_docx(uploaded_file)
            elif file_type == "pptx":
                raw_text, images = extract_from_pptx(uploaded_file)

            if raw_text.strip():
                st.session_state['summary'] = generate_summary(raw_text, summary_length)
                st.session_state['images'] = images
                st.session_state['file_name'] = uploaded_file.name
            else:
                st.warning("Tidak ditemukan teks yang dapat dibaca dari dokumen ini.")

if 'summary' in st.session_state:
    summary = st.session_state['summary']
    images = st.session_state['images']
    
    st.markdown("---")
    st.markdown(f"### {emojis[0]} Preview Hasil Rangkuman (Custom Paper: {paper_style})")
    
    # Paper Preview Frame
    st.markdown(f"""
        <div class="preview-paper">
            <h2 style="text-align: center; color: {theme['text']}; margin-top: 0;">{emojis[0]} Laaura's Resume {emojis[1]}</h2>
            <p style="text-align: center; color: #777; font-weight: bold; margin-bottom: 20px;">✨ Created by Laaura ✨</p>
            <p style="white-space: pre-line;">{summary}</p>
        </div>
    """, unsafe_allow_html=True)
    
    if images:
        st.markdown(f"#### {emojis[2]} Galeri Gambar ({len(images)})")
        cols = st.columns(min(3, len(images)))
        for idx, img in enumerate(images[:6]):
            with cols[idx % 3]:
                st.image(img, caption=f"Gambar {idx+1}", use_container_width=True)
                
    st.markdown("<br>", unsafe_allow_html=True)
    
    # PDF Generator Button
    pdf_bytes = create_custom_pdf(summary, images, theme, selected_font, paper_style)
    st.download_button(
        label="📥 Download Version PDF (Custom Designed)",
        data=pdf_bytes,
        file_name=f"Laaura_Resume_{st.session_state['file_name']}.pdf",
        mime="application/pdf"
    )
