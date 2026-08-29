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

# Config Halaman & Judul Tab Browser
st.set_page_config(page_title="𐙚 Slide & Scribble", page_icon="📝", layout="wide")

# Inisialisasi Session State
if "slides_images" not in st.session_state:
    st.session_state.slides_images = []
if "slide_notes" not in st.session_state:
    st.session_state.slide_notes = {}
if "annotated_slides" not in st.session_state:
    st.session_state.annotated_slides = {}

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
        if note_text:
            story.append(Paragraph("<b>Catatan:</b>", styles['Bold']))
            for line in note_text.split("\n"):
                story.append(Paragraph(line, note_style))
        else:
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
st.title("𐙚 Slide & Scribble")
st.caption("Unggah materi kuliah (PDF), corat-coret slide, tambah catatan, dan unduh/simpan hasilnya.")

# Sidebar Pengaturan
with st.sidebar:
    st.header("📂 Unggah Berkas")
    uploaded_file = st.file_uploader("Pilih file PDF", type=["pdf"])
    
    if uploaded_file:
        if st.button("🔄 Proses Berkas Baru"):
            with st.spinner("Memproses slide..."):
                file_bytes = uploaded_file.read()
                st.session_state.slides_images = convert_pdf_to_images(file_bytes)
                st.session_state.slide_notes = {}
                st.session_state.annotated_slides = {}
                st.success(f"Berhasil memuat {len(st.session_state.slides_images)} slide!")

    st.divider()
    st.header("🎨 Alat Coret-Coret")
    drawing_mode = st.selectbox("Mode Gambar:", ("freedraw", "line", "rect", "circle", "transform"))
    stroke_width = st.slider("Ukuran Kuas/Garis:", 1, 25, 3)
    
    preset_color = st.radio(
        "Pilih Warna Cepat:",
        ["🔴 Merah", "🔵 Biru", "🟢 Hijau", "🟡 Kuning (Highlighter)", "⚫ Hitam", "🎨 Warna Kustom"],
        index=0
    )

    color_map = {
        "🔴 Merah": "#FF0000",
        "🔵 Biru": "#0055FF",
        "🟢 Hijau": "#00AA44",
        "🟡 Kuning (Highlighter)": "#FFFF00",
        "⚫ Hitam": "#000000"
    }

    if preset_color == "🎨 Warna Kustom":
        stroke_color = st.color_picker("Pilih Warna Bebas:", "#FF0000")
    else:
        stroke_color = color_map[preset_color]

# Editor Utama
if st.session_state.slides_images:
    total_slides = len(st.session_state.slides_images)
    
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav2:
        slide_num = st.slider("Pilih Slide:", 1, total_slides, 1) - 1

    st.markdown(f"### Slide {slide_num + 1} dari {total_slides}")
    
    col_canvas, col_notes = st.columns([3, 2])
    
    with col_canvas:
        st.subheader("🖼️ Canvas Slide")
        current_bg = st.session_state.slides_images[slide_num]
        
        canvas_width = 650
        aspect_ratio = current_bg.height / current_bg.width
        canvas_height = int(canvas_width * aspect_ratio)
        
        resized_bg = current_bg.resize((canvas_width, canvas_height))

        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 0, 0.3)" if "Kuning" in preset_color else "rgba(255, 165, 0, 0.3)",
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
        st.subheader("📌 Catatan Slide")
        current_note = st.session_state.slide_notes.get(slide_num, "")
        updated_note = st.text_area(
            "Tulis catatan penjelas di sini:", 
            value=current_note, 
            height=300,
            key=f"note_{slide_num}"
        )
        st.session_state.slide_notes[slide_num] = updated_note

    st.divider()
    
    # Ekspor & GDrive
    col_exp1, col_exp2 = st.columns([1, 1])
    with col_exp1:
        if st.button("📄 Generate PDF Local Download"):
            with st.spinner("Menyusun PDF..."):
                pdf_data = generate_exported_pdf()
                st.download_button(
                    label="⬇️ Unduh Berkas PDF",
                    data=pdf_data,
                    file_name="Hasil_Edit_Slide.pdf",
                    mime="application/pdf"
                )
    
    with col_exp2:
        if st.button("☁️ Simpan Langsung ke Google Drive"):
            with st.spinner("Mengunggah ke Google Drive..."):
                pdf_bytes_data = generate_exported_pdf().getvalue()
                file_id = upload_to_gdrive(pdf_bytes_data)
                if file_id:
                    st.success("Berhasil disimpan ke Google Drive kamu! 🎉")
else:
    st.info("Silakan unggah berkas PDF materi kuliahmu melalui sidebar di sebelah kiri untuk memulai.")
