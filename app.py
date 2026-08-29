import io
import copy
import html

import fitz
import streamlit as st

from PIL import Image, ImageDraw, ImageFont

from streamlit_drawable_canvas import st_canvas

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Image as RLImage,
    Paragraph,
    Spacer,
    PageBreak,
)
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="𐙚 Slide & Scribble",
    page_icon="🎀",
    layout="wide",
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "sas_slides": [],
    "sas_notes": {},
    "sas_mini_notes": {},
    "sas_drawings": {},
    "sas_history": {},
    "sas_current_slide": 0,
    "sas_zoom": 70,
    "sas_canvas_version": 0,
    "sas_loaded_filename": "",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# THEMES
# ============================================================

THEMES = {
    "🎀 Coquette Soft": {
        "bg": "#FFF0F3",
        "primary": "#FFB7C5",
        "text": "#800926",
        "card": "#FFF8F9",
        "border": "#FFCCD5",
        "main": "🎀",
        "sub": "🩰",
        "file": "💌",
        "draw": "🪞",
        "note": "🧸",
        "cloud": "🌸",
    },
    "☁️ Langit & Awan": {
        "bg": "#F0F8FF",
        "primary": "#87CEEB",
        "text": "#1E3D59",
        "card": "#F9FCFF",
        "border": "#B0E0E6",
        "main": "☁️",
        "sub": "🌤️",
        "file": "✈️",
        "draw": "🩵",
        "note": "🌟",
        "cloud": "🕊️",
    },
    "🍓 Buah-Buahan": {
        "bg": "#FFF3E0",
        "primary": "#FF8A65",
        "text": "#D84315",
        "card": "#FFF9F5",
        "border": "#FFCCBC",
        "main": "🍓",
        "sub": "🍑",
        "file": "🧺",
        "draw": "🍒",
        "note": "🧃",
        "cloud": "🥑",
    },
    "🌿 Sage Minimalis": {
        "bg": "#F2F5F3",
        "primary": "#87A96B",
        "text": "#2E4A3B",
        "card": "#F9FAF9",
        "border": "#C9D6CE",
        "main": "🌿",
        "sub": "🍃",
        "file": "📑",
        "draw": "🍵",
        "note": "🪴",
        "cloud": "🕯️",
    },
}


# ============================================================
# THEME SELECTOR
# ============================================================

with st.sidebar:
    st.header("🎨 Pilih Tema")
    selected_theme = st.selectbox(
        "Suasana tampilan:",
        list(THEMES.keys()),
        key="sas_theme_v8",
    )

theme = THEMES[selected_theme]


# ============================================================
# CSS
# ============================================================

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {theme["card"]};
    }}
    [data-testid="stSidebar"] {{
        background-color: {theme["bg"]};
    }}
    h1, h2, h3 {{
        color: {theme["text"]} !important;
    }}
    .study-badge {{
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        background-color: {theme["bg"]};
        border: 1px solid {theme["border"]};
        color: {theme["text"]};
        font-weight: 600;
        margin-bottom: 8px;
    }}
    .slide-info {{
        padding: 10px 14px;
        border-radius: 12px;
        background-color: {theme["bg"]};
        border: 1px solid {theme["border"]};
        margin-bottom: 10px;
        text-align: center;
        color: {theme["text"]};
        font-weight: 600;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PDF → IMAGES
# ============================================================

def pdf_to_images(pdf_bytes):
    images = []
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page in document:
            pix = page.get_pixmap(dpi=120, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            images.append(image)
    finally:
        document.close()
    return images


# ============================================================
# CANVAS SIZE
# ============================================================

def calculate_canvas_size(image, zoom):
    base_width = 850
    width = int(base_width * zoom / 100)
    ratio = image.height / image.width
    height = int(width * ratio)
    return width, height


# ============================================================
# RESIZE IMAGE
# ============================================================

def resize_image(image, width, height):
    return image.resize((width, height), Image.Resampling.LANCZOS)


# ============================================================
# CLEAN DRAWING
# ============================================================

def clean_drawing(canvas_json, canvas_width, canvas_height):
    if not canvas_json:
        return None
    objects = canvas_json.get("objects", [])
    if not objects:
        return None

    cleaned_objects = []
    for obj in objects:
        if obj.get("type") == "image":
            continue
        cleaned_objects.append(copy.deepcopy(obj))

    if not cleaned_objects:
        return None

    return {
        "version": canvas_json.get("version", "4.4.0"),
        "objects": cleaned_objects,
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
    }


# ============================================================
# RENDER ANNOTATIONS
# ============================================================

def render_annotations(background, drawing):
    result = background.copy().convert("RGBA")
    if not drawing:
        return result.convert("RGB")

    objects = drawing.get("objects", [])
    if not objects:
        return result.convert("RGB")

    canvas_width = drawing.get("canvas_width", 850) or 850
    scale = result.width / canvas_width

    overlay = Image.new("RGBA", result.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    for obj in objects:
        obj_type = obj.get("type", "")

        if obj_type == "path":
            path = obj.get("path", [])
            points = []
            for command in path:
                if len(command) < 3:
                    continue
                try:
                    command_type = command[0]
                    if command_type in ("M", "L"):
                        x = float(command[1]) * scale
                        y = float(command[2]) * scale
                        points.append((x, y))
                    elif command_type == "Q" and len(command) >= 5:
                        x = float(command[3]) * scale
                        y = float(command[4]) * scale
                        points.append((x, y))
                except Exception:
                    pass

            if len(points) >= 2:
                stroke = obj.get("stroke", "#FF0000")
                try:
                    stroke_width = int(float(obj.get("strokeWidth", 3)) * scale)
                except Exception:
                    stroke_width = 3
                stroke_width = max(1, stroke_width)

                draw.line(points, fill=stroke, width=stroke_width, joint="curve")

        elif obj_type == "rect":
            try:
                left = float(obj.get("left", 0)) * scale
                top = float(obj.get("top", 0)) * scale
                width = float(obj.get("width", 0)) * scale
                height = float(obj.get("height", 0)) * scale
                stroke = obj.get("stroke", "#FF0000")
                stroke_width = max(1, int(float(obj.get("strokeWidth", 3)) * scale))

                draw.rectangle([left, top, left + width, top + height], outline=stroke, width=stroke_width)
            except Exception:
                pass

        elif obj_type == "circle":
            try:
                left = float(obj.get("left", 0)) * scale
                top = float(obj.get("top", 0)) * scale
                radius = float(obj.get("radius", 0)) * scale
                stroke = obj.get("stroke", "#FF0000")
                stroke_width = max(1, int(float(obj.get("strokeWidth", 3)) * scale))

                draw.ellipse([left, top, left + radius * 2, top + radius * 2], outline=stroke, width=stroke_width)
            except Exception:
                pass

        elif obj_type == "line":
            try:
                x1 = float(obj.get("x1", 0)) * scale
                y1 = float(obj.get("y1", 0)) * scale
                x2 = float(obj.get("x2", 0)) * scale
                y2 = float(obj.get("y2", 0)) * scale
                stroke = obj.get("stroke", "#FF0000")
                stroke_width = max(1, int(float(obj.get("strokeWidth", 3)) * scale))

                draw.line([x1, y1, x2, y2], fill=stroke, width=stroke_width)
            except Exception:
                pass

        elif obj_type in ("text", "textbox", "i-text"):
            text = obj.get("text", "")
            if not text:
                continue
            try:
                left = float(obj.get("left", 0)) * scale
                top = float(obj.get("top", 0)) * scale
                fill = obj.get("fill", "#000000")
                font_size = max(8, int(float(obj.get("fontSize", 20)) * scale))

                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", font_size)
                except Exception:
                    font = ImageFont.load_default()

                draw.text((left, top), text, fill=fill, font=font)
            except Exception:
                pass

    return Image.alpha_composite(result, overlay).convert("RGB")


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf():
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("SlideTitleV8", parent=styles["Heading2"], fontSize=14, spaceAfter=8)
    note_style = ParagraphStyle("NoteV8", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=8)

    story = []

    for index, slide in enumerate(st.session_state.sas_slides):
        drawing = st.session_state.sas_drawings.get(index)
        final_image = render_annotations(slide, drawing)

        image_buffer = io.BytesIO()
        final_image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        story.append(Paragraph(f"<b>Slide {index + 1}</b>", title_style))

        max_width = 500
        ratio = final_image.height / final_image.width
        max_height = max_width * ratio

        story.append(RLImage(image_buffer, width=max_width, height=max_height))
        story.append(Spacer(1, 12))

        mini = st.session_state.sas_mini_notes.get(index, "").strip()
        note = st.session_state.sas_notes.get(index, "").strip()

        if mini:
            formatted_mini = html.escape(mini).replace("\n", "<br/>")
            story.append(
                Paragraph(
                    f"<b>📌 Mini Notes</b><br/>{formatted_mini}",
                    note_style,
                )
            )

        if note:
            story.append(Paragraph("<b>📝 Catatan Utama</b>", note_style))
            for line in note.split("\n"):
                if line.strip():
                    story.append(Paragraph(html.escape(line), note_style))

        if not mini and not note:
            story.append(Paragraph("<i>Tidak ada catatan.</i>", note_style))

        if index < (len(st.session_state.sas_slides) - 1):
            story.append(PageBreak())

    document.build(story)
    output.seek(0)
    return output


# ============================================================
# GOOGLE DRIVE
# ============================================================

def get_drive_service():
    credentials_dict = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    return build("drive", "v3", credentials=credentials)


def upload_to_drive(file_bytes, filename="Hasil_Edit_Slide.pdf"):
    try:
        service = get_drive_service()
        folder_id = st.secrets["FOLDER_ID"]
        metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype="application/pdf",
            resumable=True,
        )

        uploaded = service.files().create(body=metadata, media_body=media, fields="id").execute()
        return uploaded.get("id")
    except Exception as error:
        st.error(f"Gagal menyimpan ke Google Drive: {error}")
        return None


# ============================================================
# HEADER
# ============================================================

st.markdown(
    f"""
    <div class="study-badge">
        {theme["main"]} My Personal Study Space
    </div>
    """,
    unsafe_allow_html=True,
)

st.title(f"𐙚 Slide & Scribble {theme['main']}")
st.caption("Upload materi → coret → tulis → notes → export.")


# ============================================================
# SIDEBAR — UPLOAD
# ============================================================

with st.sidebar:
    st.divider()
    st.header(f"{theme['file']} Materi Kuliah")
    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        key="sas_upload_v8",
    )

    if uploaded_file:
        if st.button("📥 Muat Materi", key="sas_load_v8", use_container_width=True):
            try:
                with st.spinner("Membaca materi..."):
                    slides = pdf_to_images(uploaded_file.getvalue())

                if not slides:
                    st.error("PDF tidak memiliki halaman.")
                else:
                    st.session_state.sas_slides = slides
                    st.session_state.sas_notes = {}
                    st.session_state.sas_mini_notes = {}
                    st.session_state.sas_drawings = {}
                    st.session_state.sas_history = {}
                    st.session_state.sas_current_slide = 0
                    st.session_state.sas_zoom = 70
                    st.session_state.sas_canvas_version += 1
                    st.session_state.sas_loaded_filename = uploaded_file.name
                    st.success(f"{len(slides)} slide berhasil dimuat! 🎉")
                    st.rerun()
            except Exception as error:
                st.error(f"Gagal membaca PDF: {error}")


# ============================================================
# SIDEBAR — TOOLS
# ============================================================

with st.sidebar:
    st.divider()
    st.header(f"{theme['draw']} Drawing Tools")

    tool_list = [
        "✏️ Pen",
        "🖍️ Stabilo",
        "🔤 Text",
        "📏 Line",
        "🔲 Rectangle",
        "⚪ Circle",
        "✋ Select",
    ]

    selected_tool = st.selectbox(
        "Pilih alat:",
        tool_list,
        key="sas_tool_v8",
    )

    tool_map = {
        "✏️ Pen": "freedraw",
        "🖍️ Stabilo": "freedraw",
        "🔤 Text": "text",
        "📏 Line": "line",
        "🔲 Rectangle": "rect",
        "⚪ Circle": "circle",
        "✋ Select": "transform",
    }

    drawing_mode = tool_map[selected_tool]

    if selected_tool == "✏️ Pen":
        stroke_color = st.color_picker("Warna:", "#FF0000", key="sas_pen_color_v8")
        stroke_width = st.slider("Ukuran:", 1, 15, 3, key="sas_pen_width_v8")

    elif selected_tool == "🖍️ Stabilo":
        highlighter = st.selectbox(
            "Warna stabilo:",
            ["Kuning", "Pink", "Hijau", "Biru"],
            key="sas_highlighter_v8",
        )
        highlighter_colors = {
            "Kuning": "rgba(255,235,59,0.40)",
            "Pink": "rgba(255,105,180,0.40)",
            "Hijau": "rgba(144,238,144,0.40)",
            "Biru": "rgba(135,206,250,0.40)",
        }
        stroke_color = highlighter_colors[highlighter]
        stroke_width = st.slider("Ukuran:", 8, 30, 18, key="sas_highlighter_width_v8")

    else:
        stroke_color = st.color_picker("Warna:", "#FF0000", key="sas_shape_color_v8")
        stroke_width = st.slider("Ketebalan:", 1, 15, 3, key="sas_shape_width_v8")


# ============================================================
# EMPTY STATE
# ============================================================

if not st.session_state.sas_slides:
    st.info(
        f"""
        {theme['file']} **Belum ada materi.**

        Upload PDF dari sidebar untuk mulai menggunakan **Slide & Scribble** {theme['sub']}.
        """
    )
    st.stop()


# ============================================================
# SLIDE INDEX
# ============================================================

total_slides = len(st.session_state.sas_slides)

if st.session_state.sas_current_slide >= total_slides:
    st.session_state.sas_current_slide = total_slides - 1

if st.session_state.sas_current_slide < 0:
    st.session_state.sas_current_slide = 0

slide_index = st.session_state.sas_current_slide


# ============================================================
# NAVIGATION
# ============================================================

nav_left, nav_center, nav_right = st.columns([1, 5, 1])

with nav_left:
    if st.button("⬅️", key="sas_prev_v8", use_container_width=True, disabled=(slide_index == 0)):
        st.session_state.sas_current_slide -= 1
        st.session_state.sas_canvas_version += 1
        st.rerun()

with nav_center:
    selected_slide = st.slider(
        "Slide",
        1,
        total_slides,
        slide_index + 1,
        key="sas_slide_nav_v8",
    )

    if selected_slide - 1 != slide_index:
        st.session_state.sas_current_slide = selected_slide - 1
        st.session_state.sas_canvas_version += 1
        st.rerun()

with nav_right:
    if st.button("➡️", key="sas_next_v8", use_container_width=True, disabled=(slide_index >= total_slides - 1)):
        st.session_state.sas_current_slide += 1
        st.session_state.sas_canvas_version += 1
        st.rerun()


# ============================================================
# CURRENT SLIDE & ZOOM
# ============================================================

current_slide = st.session_state.sas_slides[slide_index]

st.markdown(
    f"""
    <div class="slide-info">
        {theme['sub']} Slide {slide_index + 1} / {total_slides}
    </div>
    """,
    unsafe_allow_html=True,
)

zoom_left, zoom_center, zoom_right = st.columns([1, 4, 1])

with zoom_left:
    if st.button("➖", key="sas_zoom_minus_v8", use_container_width=True):
        st.session_state.sas_zoom = max(40, st.session_state.sas_zoom - 10)
        st.session_state.sas_canvas_version += 1
        st.rerun()

with zoom_center:
    zoom_value = st.slider(
        "🔍 Ukuran Slide",
        min_value=40,
        max_value=120,
        value=st.session_state.sas_zoom,
        step=10,
        format="%d%%",
        key="sas_zoom_v8",
    )

    if zoom_value != st.session_state.sas_zoom:
        st.session_state.sas_zoom = zoom_value
        st.session_state.sas_canvas_version += 1
        st.rerun()

with zoom_right:
    if st.button("➕", key="sas_zoom_plus_v8", use_container_width=True):
        st.session_state.sas_zoom = min(120, st.session_state.sas_zoom + 10)
        st.session_state.sas_canvas_version += 1
        st.rerun()


# ============================================================
# CANVAS SIZE
# ============================================================

canvas_width, canvas_height = calculate_canvas_size(
    current_slide,
    st.session_state.sas_zoom,
)


# ============================================================
# EDITOR + NOTES
# ============================================================

editor_col, notes_col = st.columns([3, 2])

with editor_col:
    st.markdown(f"#### 🖼️ Editor {theme['draw']}")
    st.caption(f"Ukuran tampilan: **{canvas_width} × {canvas_height}px**")

    # Background slide
    background = resize_image(current_slide, canvas_width, canvas_height)

    # Key canvas yang unik agar tidak blank
    canvas_key = f"canvas_{slide_index}_{st.session_state.sas_canvas_version}"
    initial_drawing = st.session_state.sas_drawings.get(slide_index)

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 0, 0.2)",
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_image=background,
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode=drawing_mode,
        initial_drawing=initial_drawing,
        key=canvas_key,
    )

    # Simpan hasil coretan saat pengguna menggambar
    if canvas_result.json_data is not None:
        cleaned = clean_drawing(canvas_result.json_data, canvas_width, canvas_height)
        if cleaned:
            st.session_state.sas_drawings[slide_index] = cleaned

with notes_col:
    st.markdown(f"#### {theme['note']} Mini Notes (Poin/Rumus)")
    current_mini = st.session_state.sas_mini_notes.get(slide_index, "")
    updated_mini = st.text_input(
        "Kata kunci / istilah penting:",
        value=current_mini,
        key=f"mini_input_{slide_index}",
        placeholder="Contoh: Rumus X = Y + Z",
    )
    st.session_state.sas_mini_notes[slide_index] = updated_mini

    st.markdown("#### 📝 Catatan Utama Slide")
    current_note = st.session_state.sas_notes.get(slide_index, "")
    updated_note = st.text_area(
        "Penjelasan rinci materi:",
        value=current_note,
        height=250,
        key=f"note_input_{slide_index}",
    )
    st.session_state.sas_notes[slide_index] = updated_note


# ============================================================
# EXPORT & DRIVE
# ============================================================

st.divider()

exp_col1, exp_col2 = st.columns([1, 1])

with exp_col1:
    if st.button(f"📄 Generate PDF {theme['sub']}", use_container_width=True):
        with st.spinner("Menyusun file PDF..."):
            pdf_data = create_pdf()
            st.download_button(
                label=f"⬇️ Unduh Berkas PDF {theme['main']}",
                data=pdf_data,
                file_name="Hasil_Edit_Slide.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

with exp_col2:
    if st.button(f"{theme['cloud']} Simpan ke Google Drive", use_container_width=True):
        with st.spinner("Mengunggah ke Google Drive..."):
            pdf_bytes_data = create_pdf().getvalue()
            file_id = upload_to_drive(pdf_bytes_data)
            if file_id:
                st.success(f"Berhasil diunggah ke Google Drive! 🎉 (File ID: {file_id})")
