import io
import fitz  # PyMuPDF
import streamlit as st
from pptx import Presentation
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="Slide Editor & Note Taker", page_icon="📝", layout="wide")

# Inisialisasi Session State
if "slides_images" not in st.session_state:
    st.session_state.slides_images = []
if "slide_notes" not in st.session_state:
    st.session_state.slide_notes = {}
if "annotated_slides" not in st.session_state:
    st.session_state.annotated_slides = {}

# Fungsi Konversi PPTX ke Teks / Gambar (Menggunakan PyMuPDF jika PDF, atau ekstraksi slide)
def convert_pdf_to_images(pdf_bytes):
    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images

def convert_pptx_to_pdf_bytes(pptx_bytes):
    # Catatan: Pembuatan gambar langsung dari PPTX di Python tanpa LibreOffice 
    # mengekstraksi slide sebagai gambar jika ada, atau mengolah teks.
    # Untuk hasil terbaik di Streamlit Cloud, pengguna disarankan mengunggah PDF atau PPTX yang berisi gambar.
    prs = Presentation(io.BytesIO(pptx_bytes))
    images = []
    for slide in prs.slides:
        # Buat canvas putih kosong untuk rendering sederhana PPTX jika tidak ada PDF conversion tool
        img = Image.new('RGB', (960, 540), color = (255, 255, 255))
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
        # Gunakan gambar yang sudah dicorat-coret jika ada, jika tidak pakai gambar asli
        slide_img = st.session_state.annotated_slides.get(idx, base_img)
        
        # Simpan gambar sementara ke buffer
        img_byte_arr = io.BytesIO()
        slide_img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Tambahkan ke PDF
        story.append(Paragraph(f"<b>Slide {idx + 1}</b>", title_style))
        story.append(RLImage(img_byte_arr, width=500, height=280))
        story.append(Spacer(1, 10))
        
        # Catatan
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

# --- INTERFACE UTAMA ---
st.title("📝 Slide Annotator & Note Taker")
st.caption("Unggah materi kuliah (PDF/PPTX), corat-coret slide, tambah catatan, dan unduh hasilnya.")

# Sidebar untuk Pengaturan & Upload
with st.sidebar:
    st.header("📂 Unggah Berkas")
    uploaded_file = st.file_uploader("Pilih file PDF atau PPTX", type=["pdf", "pptx"])
    
    if uploaded_file:
        if st.button("🔄 Proses Berkas Baru"):
            with st.spinner("Memproses slide..."):
                file_bytes = uploaded_file.read()
                if uploaded_file.name.endswith(".pdf"):
                    st.session_state.slides_images = convert_pdf_to_images(file_bytes)
                else:
                    # Jika PPTX disarankan konversi ke PDF dulu atau gunakan renderer
                    st.session_state.slides_images = convert_pdf_to_images(file_bytes) if uploaded_file.type == "application/pdf" else convert_pptx_to_images_fallback(file_bytes)
                
                st.session_state.slide_notes = {}
                st.session_state.annotated_slides = {}
                st.success(f"Berhasil memuat {len(st.session_state.slides_images)} slide!")

    st.divider()
    st.header("🎨 Alat Coret-Coret")
    drawing_mode = st.selectbox("Mode Gambar:", ("freedraw", "line", "rect", "circle", "transform"))
    stroke_width = st.slider("Ukuran Kuas/Garis:", 1, 25, 3)
    stroke_color = st.color_picker("Warna Garis/Teks:", "#FF0000")
    bg_color = "#FFFFFF"

# Tampilan Utama Editor
if st.session_state.slides_images:
    total_slides = len(st.session_state.slides_images)
    
    # Navigasi Slide
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav2:
        slide_num = st.slider("Pilih Slide:", 1, total_slides, 1) - 1

    st.markdown(f"### Slide {slide_num + 1} dari {total_slides}")
    
    col_canvas, col_notes = st.columns([3, 2])
    
    # Kolom Canvas untuk Coret-Coret
    with col_canvas:
        st.subheader("🖼️ Canvas Slide")
        current_bg = st.session_state.slides_images[slide_num]
        
        # Resize gambar background agar pas di canvas UI
        canvas_width = 650
        aspect_ratio = current_bg.height / current_bg.width
        canvas_height = int(canvas_width * aspect_ratio)
        
        resized_bg = current_bg.resize((canvas_width, canvas_height))

        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_image=resized_bg,
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode=drawing_mode,
            key=f"canvas_{slide_num}",
        )
        
        # Simpan hasil gabungan slide + coretan jika ada perubahan
        if canvas_result.image_data is not None:
            annotated_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            # Overlay gambar asli dengan coretan
            final_slide = Image.new("RGB", resized_bg.size, (255, 255, 255))
            final_slide.paste(resized_bg, (0, 0))
            final_slide.paste(annotated_img, (0, 0), mask=annotated_img)
            st.session_state.annotated_slides[slide_num] = final_slide

    # Kolom Catatan Teks
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
    
    # Ekspor PDF
    col_exp1, col_exp2 = st.columns([2, 1])
    with col_exp1:
        st.subheader("📥 Unduh Hasil Editing")
        st.caption("Gabungkan semua slide yang telah dicorat-coret beserta catatannya ke dalam satu file PDF.")
    with col_exp2:
        if st.button("📄 Generate PDF Final"):
            with st.spinner("Menyusun PDF..."):
                pdf_data = generate_exported_pdf()
                st.download_button(
                    label="⬇️ Unduh Berkas PDF",
                    data=pdf_data,
                    file_name="Hasil_Edit_Slide.pdf",
                    mime="application/pdf"
                )
else:
    st.info("Silakan unggah berkas PDF atau PPTX materi kuliahmu melalui sidebar di sebelah kiri untuk memulai.")