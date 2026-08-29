import io
import fitz  # PyMuPDF
import streamlit as st
from pptx import Presentation
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Config Halaman awal
st.set_page_config(page_title="𐙚 Slide & Scribble", page_icon="🎀", layout="wide")

# Inisialisasi Session State
if "slides_images" not in st.session_state:
    st.session_state.slides_images = []
if "slide_notes" not in st.session_state:
    st.session_state.slide_notes = {}
if "annotated_slides" not in st.session_state:
    st.session_state.annotated_slides = {}
if "mini_notes" not in st.session_state:
    st.session_state.mini_notes = {}

# --- SISTEM TEMA & EMOJI DINAMIS ---
with st.sidebar:
    st.header("🎨 Pilih Tema Tampilan")
    selected_theme = st.selectbox(
        "Suasana Tampilan:",
        ["🎀 Coquette Soft", "☁️ Langit & Awan", "🍓 Buah-Buahan", "🌿 Sage Minimalis"]
    )

theme_styles = {
    "🎀 Coquette Soft": {
        "bg_sidebar": "#FFF0F3",
        "primary": "#FFB7C5",
        "text_header": "#800926",
        "card_bg": "#FFF8F9",
        "border": "#FFCCD5",
        "e_main": "🎀", "e_sub": "🩰", "e_file": "💌", "e_draw": "🪞", "e_note": "🧸", "e_cloud": "🌸"
    },
    "☁️ Langit & Awan": {
        "bg_sidebar": "#F0F8FF",
        "primary": "#87CEEB",
        "text_header": "#1E3D59",
        "card_bg": "#F9FCFF",
        "border": "#B0E0E6",
        "e_main": "☁️", "e_sub": "🌤️", "e_file": "✈️", "e_draw": "🩵", "e_note": "🌟", "e_cloud": "🕊️"
    },
    "🍓 Buah-Buahan": {
        "bg_sidebar": "#FFF3E0",
        "primary": "#FF8A65",
        "text_header": "#D84315",
        "card_bg": "#FFF9F5",
        "border": "#FFCCBC",
        "e_main": "🍓", "e_sub": "🍑", "e_file": "🧺", "e_draw": "🍒", "e_note": "🧃", "e_cloud": "🥑"
    },
    "🌿 Sage Minimalis": {
        "bg_sidebar": "#F2F5F3",
        "primary": "#87A96B",
        "text_header": "#2E4A3B",
        "card_bg": "#F9FAF9",
        "border": "#C9D6CE",
        "e_main": "🌿", "e_sub": "🍃", "e_file": "📑", "e_draw": "🍵", "e_note": "🪴", "e_cloud": "🕯️"
    }
}

t = theme_styles[selected_theme]

# Apply Style CSS Dinamis
st.markdown(f"""
    <style>
        .stApp {{
            background-color: {t['card_bg']};
        }}
        [data-testid="stSidebar"] {{
            background-color: {t['bg_sidebar']};
        }}
        h1, h2, h3 {{
            color: {t['text_header']} !important;
        }}
        .stButton>button {{
            background-color: {t['primary']} !important;
            color: white !important;
            border-radius: 12px !important;
            border: none !important;
            font-weight: bold;
        }}
        .user-badge {{
            background-color: {t['bg_sidebar']};
            color: {t['text_header']};
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 14px;
            font-weight: bold;
            border: 1px solid {t['border']};
            display: inline-block;
            margin-bottom: 10px;
        }}
    </style>
""", unsafe_allow_html=True)

def hex_to_rgba(hex_code, alpha=0.35):
    hex_code = hex_code.lstrip('#')
    r, g, b = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"

# Fungsi Konversi PDF ke Gambar
def convert_pdf_to_images(pdf_bytes):
    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images

# Fungsi Ekspor ke PDF
def generate_exported_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    note_style = ParagraphStyle('NoteStyle', parent=styles['Normal'], fontSize=11, leading=14, spaceAfter=10)
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading2'], fontSize=14, spaceAfter=8)

    story = []

    for idx, base_img in enumerate(st.session_state.slides_images):
        slide_img = st.session_state.annotated_slides.get(idx, base_img)
        
        img_byte_arr = io.BytesIO()
        slide_img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        story.append(Paragraph(f"<b>Slide {idx + 1}</b>", title_style))
        story.append(RLImage(img_byte_arr, width=500, height=280))
        story.append(Spacer(1, 10))
        
        note_text = st.session_state.slide_notes.get(idx, "").strip()
        mini_note = st.session_state.mini_notes.get(idx, "").strip()
        
        if mini_note:
            story.append(Paragraph(f"<b>📌 Mini Notes:</b><br/>{mini_note}", note_style))
            story.append(Spacer(1, 5))

        if note_text:
            story.append(Paragraph("<b>Catatan Utuh:</b>", styles['Bold']))
            for line in note_text.split("\n"):
                story.append(Paragraph(line, note_style))
        elif not mini_note:
            story.append(Paragraph("<i>Tidak ada catatan.</i>", note_style))
            
        story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer

# Fungsi Google Drive API
def get_drive_service():
    creds_dict = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    return build('drive', 'v3', credentials=creds)

def upload_to_gdrive(file_bytes, filename="Hasil_Edit_Slide.pdf"):
    try:
        service = get_drive_service()
        folder_id = st.secrets["FOLDER_ID"]
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype='application/pdf',
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return file.get('id')
    except Exception as e:
        st.error(f"Gagal upload ke Drive: {str(e)}")
        return None

# --- INTERFACE UTAMA ---
USER_NAME = "✨ Laaura's Study Desk"

st.markdown(f'<div class="user-badge">{t["e_main"]} {USER_NAME}</div>', unsafe_allow_html=True)
st.title(f"𐙚 Slide & Scribble {t['e_main']}")
st.caption(f"Unggah materi kuliah (PDF), corat-coret slide, catat poin penting, dan unduh/simpan hasilnya {t['e_sub']}")

# Sidebar Pengaturan
with st.sidebar:
    st.divider()
    st.header(f"{t['e_file']} Unggah Berkas")
    uploaded_file = st.file_uploader("Pilih file PDF", type=["pdf"])
    
    if uploaded_file:
        if st.button(f"🔄 Proses Berkas Baru {t['e_sub']}"):
            with st.spinner("Memproses slide..."):
                file_bytes = uploaded_file.read()
                st.session_state.slides_images = convert_pdf_to_images(file_bytes)
                st.session_state.slide_notes = {}
                st.session_state.annotated_slides = {}
                st.session_state.mini_notes = {}
                st.success(f"Berhasil memuat {len(st.session_state.slides_images)} slide!")

    st.divider()
    st.header(f"{t['e_draw']} Alat Coret-Coret")
    
    mode_indo_map = {
        "✏️ Coret Bebas (Pensil)": "freedraw",
        "📏 Garis Lurus": "line",
        "🔲 Kotak": "rect",
        "⚪ Lingkaran": "circle",
        "✋ Geser / Pilih Objek": "transform"
    }
    selected_mode_label = st.selectbox("Mode Alat:", list(mode_indo_map.keys()))
    drawing_mode = mode_indo_map[selected_mode_label]
    
    # Pengaturan Jenis Alat & Warna Stabilo Bebas
    tool_type = st.radio("Jenis Kuas:", ["✏️ Pen Biasa", "🖍️ Stabilo (Transparan)"], index=0)

    if tool_type == "🖍️ Stabilo (Transparan)":
        preset_color = st.radio(
            "Warna Stabilo:",
            ["🟡 Kuning", "💖 Pink", "🟢 Hijau Mint", "🩵 Biru Muda", "🎨 Warna Kustom"],
            index=0
        )
        stabilo_map = {
            "🟡 Kuning": "rgba(255, 235, 59, 0.4)",
            "💖 Pink": "rgba(255, 105, 180, 0.4)",
            "🟢 Hijau Mint": "rgba(144, 238, 144, 0.4)",
            "🩵 Biru Muda": "rgba(135, 206, 250, 0.4)"
        }
        if preset_color == "🎨 Warna Kustom":
            custom_hex = st.color_picker("Pilih Warna Stabilo:", "#FFFF00")
            stroke_color = hex_to_rgba(custom_hex, 0.4)
        else:
            stroke_color = stabilo_map[preset_color]
        default_stroke_width = 16
    else:
        preset_color = st.radio(
            "Warna Pen:",
            ["🔴 Merah", "🔵 Biru", "🟢 Hijau", "⚫ Hitam", "🎨 Warna Kustom"],
            index=0
        )
        pen_map = {
            "🔴 Merah": "#FF0000",
            "🔵 Biru": "#0055FF",
            "🟢 Hijau": "#00AA44",
            "⚫ Hitam": "#000000"
        }
        if preset_color == "🎨 Warna Kustom":
            stroke_color = st.color_picker("Pilih Warna Pen:", "#FF0000")
        else:
            stroke_color = pen_map[preset_color]
        default_stroke_width = 3

    stroke_width = st.slider("Ukuran Kuas / Garis:", 1, 30, default_stroke_width)

# Editor Utama
if st.session_state.slides_images:
    total_slides = len(st.session_state.slides_images)
    
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav2:
        slide_num = st.slider("Pilih Slide:", 1, total_slides, 1) - 1

    st.markdown(f"### Slide {slide_num + 1} dari {total_slides} {t['e_sub']}")
    
    col_canvas, col_notes = st.columns([3, 2])
    
    with col_canvas:
        st.subheader(f"🖼️ Canvas Slide {t['e_draw']}")
        current_bg = st.session_state.slides_images[slide_num]
        
        canvas_width = 650
        aspect_ratio = current_bg.height / current_bg.width
        canvas_height = int(canvas_width * aspect_ratio)
        
        resized_bg = current_bg.resize((canvas_width, canvas_height))

        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 0, 0.2)",
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_image=resized_bg,
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode=drawing_mode,
            key=f"canvas_{slide_num}",
        )
        
        if canvas_result.image_data is not None:
            annotated_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            final_slide = Image.new("RGB", resized_bg.size, (255, 255, 255))
            final_slide.paste(resized_bg, (0, 0))
            final_slide.paste(annotated_img, (0, 0), mask=annotated_img)
            st.session_state.annotated_slides[slide_num] = final_slide

    with col_notes:
        st.subheader(f"{t['e_note']} Mini Notes (Rumus/Poin)")
        current_mini = st.session_state.mini_notes.get(slide_num, "")
        updated_mini = st.text_input(
            "Tulis kata kunci / istilah penting:",
            value=current_mini,
            key=f"mini_{slide_num}",
            placeholder="Contoh: Definisikan X / Rumus Y"
        )
        st.session_state.mini_notes[slide_num] = updated_mini
        
        st.subheader(f"📝 Catatan Utama Slide")
        current_note = st.session_state.slide_notes.get(slide_num, "")
        updated_note = st.text_area(
            "Tulis penjelasan materi di sini:", 
            value=current_note, 
            height=250,
            key=f"note_{slide_num}"
        )
        st.session_state.slide_notes[slide_num] = updated_note

    st.divider()
    
    # Ekspor & GDrive
    col_exp1, col_exp2 = st.columns([1, 1])
    with col_exp1:
        if st.button(f"📄 Generate PDF Local Download {t['e_sub']}"):
            with st.spinner("Menyusun PDF..."):
                pdf_data = generate_exported_pdf()
                st.download_button(
                    label=f"⬇️ Unduh Berkas PDF {t['e_main']}",
                    data=pdf_data,
                    file_name="Hasil_Edit_Slide.pdf",
                    mime="application/pdf"
                )
    
    with col_exp2:
        if st.button(f"{t['e_cloud']} Simpan Langsung ke Google Drive"):
            with st.spinner("Mengunggah ke Google Drive..."):
                pdf_bytes_data = generate_exported_pdf().getvalue()
                file_id = upload_to_gdrive(pdf_bytes_data)
                if file_id:
                    st.success(f"Berhasil disimpan ke Google Drive kamu! 🎉 {t['e_main']}")
else:
    st.info(f"Silakan unggah berkas PDF materi kuliahmu melalui sidebar di sebelah kiri untuk memulai {t['e_sub']}")
