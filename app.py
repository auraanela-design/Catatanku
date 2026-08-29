import io
import fitz  # PyMuPDF
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image

st.set_page_config(page_title="Editor Slide & Catatan", layout="wide")

if "slides" not in st.session_state:
    st.session_state.slides = []
if "edited_notes" not in st.session_state:
    st.session_state.edited_notes = {}

st.title("📝 Editor Slide & Catatan Digital")
st.caption("Unggah PDF, edit teks/catatan tiap slide, dan ekspor hasilnya secara langsung.")

uploaded_file = st.sidebar.file_uploader("Unggah File PDF Slide", type=["pdf"])

if uploaded_file and st.sidebar.button("Proses Slide"):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    st.session_state.slides = images
    st.session_state.edited_notes = {i: "" for i in range(len(images))}
    st.success(f"Berhasil memuat {len(images)} slide!")

if st.session_state.slides:
    total_slides = len(st.session_state.slides)
    slide_idx = st.slider("Pilih Slide:", 1, total_slides, 1) - 1

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(f"🖼️ Tampilan Slide {slide_idx + 1}")
        st.image(st.session_state.slides[slide_idx], use_column_width=True)

    with col2:
        st.subheader("✏️ Edit Catatan / Teks Tambahan")
        current_text = st.session_state.edited_notes.get(slide_idx, "")
        updated_text = st.text_area(
            "Masukkan ringkasan atau perubahan teks untuk slide ini:",
            value=current_text,
            height=300,
            key=f"text_{slide_idx}"
        )
        st.session_state.edited_notes[slide_idx] = updated_text

    st.divider()

    # Ekspor ke PDF
    if st.button("📄 Ekspor Slide + Catatan Lengkap (PDF)"):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        for i, img in enumerate(st.session_state.slides):
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            story.append(Paragraph(f"<b>Slide {i + 1}</b>", styles['Heading2']))
            story.append(RLImage(img_byte_arr, width=450, height=250))
            story.append(Spacer(1, 10))

            note = st.session_state.edited_notes.get(i, "").strip()
            if note:
                story.append(Paragraph("<b>Catatan Editor:</b>", styles['Bold']))
                story.append(Paragraph(note, styles['Normal']))
            story.append(PageBreak())

        doc.build(story)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Unduh PDF Hasil Edit",
            data=buffer,
            file_name="Slide_Hasil_Edit.pdf",
            mime="application/pdf"
        )
