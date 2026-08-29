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

# 1. Page Configuration
st.set_page_config(
    page_title="Nela Aura's Aesthetic Studio",
    page_icon="🌸",
    layout="wide"
)

# 2. Themes Definition with Aesthetic Gradient & Themed Emojis
THEMES = {
    "🌸 Sakura Dream": {
        "gradient": "linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%)",
        "card_bg": "#FFFFFFB3",
        "text": "#5E3A4D",
        "accent": "#FF9AA2",
        "emojis": "🌸 🍓 🧋 🎀 ✨",
        "header_color": colors.HexColor("#D87093")
    },
    "🧸 Warm Latte": {
        "gradient": "linear-gradient(135deg, #FDFBF7 0%, #E2D1C3 100%)",
        "card_bg": "#FFFFFFD9",
        "text": "#4A3B32",
        "accent": "#C4A482",
        "emojis": "🧸 ☕ 🧇 🍪 🍂",
        "header_color": colors.HexColor("#8B5A2B")
    },
    "🍵 Matcha Latte": {
        "gradient": "linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%)",
        "card_bg": "#FFFFFFD9",
        "text": "#2D4A3E",
        "accent": "#81C784",
        "emojis": "🍵 🍃 🐸 🍏 🧁",
        "header_color": colors.HexColor("#388E3C")
    },
    "☁️ Cloud Lavender": {
        "gradient": "linear-gradient(135deg, #E6E6FA 0%, #F3E5F5 100%)",
        "card_bg": "#FFFFFFD9",
        "text": "#4A3E56",
        "accent": "#B39DDB",
        "emojis": "☁️ 🌙 💜 🔮 🍰",
        "header_color": colors.HexColor("#7E57C2")
    },
    "🌊 Coastal Breeze": {
        "gradient": "linear-gradient(135deg, #E0F7FA 0%, #B2EBF2 100%)",
        "card_bg": "#FFFFFFD9",
        "text": "#1A4D54",
        "accent": "#4DD0E1",
        "emojis": "🌊 🐚 🐳 🍧 🫧",
        "header_color": colors.HexColor("#00838F")
    }
}

# 3. Sidebar - Theme Selector
selected_theme_name = st.sidebar.selectbox("🎨 Select Aesthetic Theme", list(THEMES.keys()))
theme = THEMES[selected_theme_name]

# Apply Dynamic CSS with Gradient Background
st.markdown(f"""
    <style>
    .stApp {{
        background: {theme['gradient']};
        color: {theme['text']};
        font-family: 'Quicksand', 'Poppins', sans-serif;
    }}
    .main-title {{
        text-align: center;
        color: {theme['text']};
        font-weight: 700;
        font-size: 2.3rem;
        margin-bottom: 0px;
    }}
    .watermark-tag {{
        text-align: center;
        font-size: 1rem;
        color: {theme['text']};
        font-weight: 600;
        letter-spacing: 1px;
        margin-top: 5px;
        margin-bottom: 25px;
        opacity: 0.85;
    }}
    .stButton>button {{
        background-color: {theme['accent']} !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.5rem 1.5rem !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.1);
    }}
    </style>
""", unsafe_allow_html=True)

# 4. Header Section
emojis = theme['emojis'].split()
st.markdown(f"<h1 class='main-title'>{emojis[0]} Aesthetic Summary Studio {emojis[1]}</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='watermark-tag'>✨ Crafted with love by Nela Aura ✨</p>", unsafe_allow_html=True)

# 5. Functions for Extracting Text & Images
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

# 6. Text Summarizer Engine
def generate_summary(text, length_option):
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
    if not sentences:
        return "No sufficient text found to summarize."
    
    if length_option == "Concise":
        limit = max(3, len(sentences) // 4)
    elif length_option == "Balanced":
        limit = max(5, len(sentences) // 2)
    else:
        limit = max(8, int(len(sentences) * 0.75))
        
    summary = ". ".join(sentences[:limit]) + "."
    return summary

# 7. Function to Create Aesthetic PDF
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
        spaceAfter=10
    )
    
    author_style = ParagraphStyle(
        'AuthorStyle',
        parent=styles['Normal'],
        fontSize=10,
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
    
    # Title & Watermark Nela Aura
    story.append(Paragraph(f"{theme_info['emojis']} Aesthetic Summary Notes {theme_info['emojis']}", title_style))
    story.append(Paragraph("<b>Curated specially by: Nela Aura ✨</b>", author_style))
    story.append(Spacer(1, 12))
    
    # Summary Content
    for paragraph in summary_text.split('\n'):
        if paragraph.strip():
            story.append(Paragraph(paragraph, body_style))
            story.append(Spacer(1, 6))
            
    # Include Visual Elements/Images
    if images:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>{emojis[2]} Visual Highlights:</b>", body_style))
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

# 8. Main Application Interface
st.sidebar.subheader(f"{emojis[2]} Summary Preferences")
summary_length = st.sidebar.radio("Length Mode:", ["Concise", "Balanced", "Detailed"])

uploaded_file = st.file_uploader(
    f"{emojis[3]} Upload your document (PDF, PPTX, or DOCX):", 
    type=["pdf", "pptx", "docx"]
)

if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    with st.spinner(f"Curating and extracting content... {emojis[4]}"):
        if file_type == "pdf":
            raw_text, images = extract_from_pdf(uploaded_file)
        elif file_type == "docx":
            raw_text, images = extract_from_docx(uploaded_file)
        elif file_type == "pptx":
            raw_text, images = extract_from_pptx(uploaded_file)

    if raw_text.strip():
        summary = generate_summary(raw_text, summary_length)
        
        st.markdown(f"### {emojis[0]} Summary Overview")
        st.write(summary)
        
        # Display Extracted Images
        if images:
            st.markdown(f"### {emojis[2]} Visual Gallery ({len(images)})")
            cols = st.columns(min(3, len(images)))
            for idx, img in enumerate(images[:6]):
                with cols[idx % 3]:
                    st.image(img, caption=f"Highlight {idx+1}", use_column_width=True)
                    
        # Export PDF Button
        pdf_bytes = create_pdf(summary, images, theme)
        st.download_button(
            label=f"✨ Download Summary Notes (Nela Aura Edition)",
            data=pdf_bytes,
            file_name=f"Summary_NelaAura_{uploaded_file.name}.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("No readable text found in this document.")
