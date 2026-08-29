import io
import copy
import fitz
import streamlit as st

from pptx import Presentation
from PIL import Image

from streamlit_drawable_canvas import st_canvas

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Image as RLImage,
    Paragraph,
    Spacer,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="𐙚 Slide & Scribble",
    page_icon="🎀",
    layout="wide",
)


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "slides_images": [],
    "slide_notes": {},
    "mini_notes": {},
    "drawings": {},
    "drawing_history": {},
    "canvas_version": 0,
    "current_slide": 0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# TEMA
# =========================================================

with st.sidebar:
    st.header("🎨 Pilih Tema Tampilan")

    selected_theme = st.selectbox(
        "Suasana Tampilan:",
        [
            "🎀 Coquette Soft",
            "☁️ Langit & Awan",
            "🍓 Buah-Buahan",
            "🌿 Sage Minimalis",
        ],
    )


theme_styles = {

    "🎀 Coquette Soft": {
        "bg_sidebar": "#FFF0F3",
        "primary": "#FFB7C5",
        "text_header": "#800926",
        "card_bg": "#FFF8F9",
        "border": "#FFCCD5",
        "e_main": "🎀",
        "e_sub": "🩰",
        "e_file": "💌",
        "e_draw": "🪞",
        "e_note": "🧸",
        "e_cloud": "🌸",
    },

    "☁️ Langit & Awan": {
        "bg_sidebar": "#F0F8FF",
        "primary": "#87CEEB",
        "text_header": "#1E3D59",
        "card_bg": "#F9FCFF",
        "border": "#B0E0E6",
        "e_main": "☁️",
        "e_sub": "🌤️",
        "e_file": "✈️",
        "e_draw": "🩵",
        "e_note": "🌟",
        "e_cloud": "🕊️",
    },

    "🍓 Buah-Buahan": {
        "bg_sidebar": "#FFF3E0",
        "primary": "#FF8A65",
        "text_header": "#D84315",
        "card_bg": "#FFF9F5",
        "border": "#FFCCBC",
        "e_main": "🍓",
        "e_sub": "🍑",
        "e_file": "🧺",
        "e_draw": "🍒",
        "e_note": "🧃",
        "e_cloud": "🥑",
    },

    "🌿 Sage Minimalis": {
        "bg_sidebar": "#F2F5F3",
        "primary": "#87A96B",
        "text_header": "#2E4A3B",
        "card_bg": "#F9FAF9",
        "border": "#C9D6CE",
        "e_main": "🌿",
        "e_sub": "🍃",
        "e_file": "📑",
        "e_draw": "🍵",
        "e_note": "🪴",
        "e_cloud": "🕯️",
    },
}

t = theme_styles[selected_theme]


# =========================================================
# CSS
# =========================================================

st.markdown(
    f"""
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

        .stButton > button {{
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

        .slide-container {{
            border-radius: 14px;
            padding: 8px;
            background: white;
            box-shadow: 0 4px 18px rgba(0,0,0,0.08);
        }}

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPER
# =========================================================

def hex_to_rgba(hex_code, alpha=0.35):
    hex_code = hex_code.lstrip("#")

    r, g, b = tuple(
        int(hex_code[i:i + 2], 16)
        for i in (0, 2, 4)
    )

    return f"rgba({r}, {g}, {b}, {alpha})"


# =========================================================
# PDF → IMAGE
# =========================================================

def convert_pdf_to_images(pdf_bytes):

    images = []

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    for page in doc:

        pix = page.get_pixmap(
            dpi=150,
            alpha=False
        )

        img = Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples
        )

        images.append(img)

    return images


# =========================================================
# DRAWING → IMAGE
# =========================================================

def render_drawing_on_slide(
    background,
    drawing_data,
    canvas_width=900
):

    if background is None:
        return None

    aspect_ratio = background.height / background.width

    canvas_height = int(
        canvas_width * aspect_ratio
    )

    bg = background.resize(
        (canvas_width, canvas_height)
    )

    # Kalau belum ada coretan
    if not drawing_data:
        return bg.convert("RGB")

    try:

        drawing_image = Image.new(
            "RGBA",
            (canvas_width, canvas_height),
            (255, 255, 255, 0)
        )

        # Tidak menggambar ulang objek secara manual.
        # Canvas akan menangani rendering saat tampil.
        return bg.convert("RGB")

    except Exception:
        return bg.convert("RGB")


# =========================================================
# EXPORT PDF
# =========================================================

def generate_exported_pdf():

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    note_style = ParagraphStyle(
        "NoteStyle",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        spaceAfter=10,
    )

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
    )

    story = []

    for idx, base_img in enumerate(
        st.session_state.slides_images
    ):

        # Ambil versi terakhir dari canvas
        drawing_data = st.session_state.drawings.get(
            idx
        )

        canvas_width = 900

        aspect_ratio = (
            base_img.height /
            base_img.width
        )

        canvas_height = int(
            canvas_width * aspect_ratio
        )

        resized_bg = base_img.resize(
            (canvas_width, canvas_height)
        )

        # -------------------------------------------------
        # Buat canvas transparan untuk export
        # -------------------------------------------------

        overlay = Image.new(
            "RGBA",
            resized_bg.size,
            (255, 255, 255, 0)
        )

        # -------------------------------------------------
        # Render objek Fabric.js
        # -------------------------------------------------

        if drawing_data:

            try:

                from PIL import ImageDraw

                draw = ImageDraw.Draw(
                    overlay
                )

                objects = drawing_data.get(
                    "objects",
                    []
                )

                for obj in objects:

                    obj_type = obj.get(
                        "type"
                    )

                    # -------------------------------------
                    # FREE DRAWING
                    # -------------------------------------

                    if obj_type == "path":

                        path = obj.get(
                            "path",
                            []
                        )

                        points = []

                        for command in path:

                            if len(command) >= 3:

                                if command[0] == "M":
                                    points.append(
                                        (
                                            command[1],
                                            command[2]
                                        )
                                    )

                                elif command[0] == "L":
                                    points.append(
                                        (
                                            command[1],
                                            command[2]
                                        )
                                    )

                        if len(points) >= 2:

                            stroke = obj.get(
                                "stroke",
                                "#FF0000"
                            )

                            width = int(
                                obj.get(
                                    "strokeWidth",
                                    3
                                )
                            )

                            draw.line(
                                points,
                                fill=stroke,
                                width=width,
                                joint="curve"
                            )

                    # -------------------------------------
                    # RECTANGLE
                    # -------------------------------------

                    elif obj_type == "rect":

                        left = obj.get(
                            "left",
                            0
                        )

                        top = obj.get(
                            "top",
                            0
                        )

                        width = obj.get(
                            "width",
                            0
                        )

                        height = obj.get(
                            "height",
                            0
                        )

                        stroke = obj.get(
                            "stroke",
                            "#FF0000"
                        )

                        stroke_width = int(
                            obj.get(
                                "strokeWidth",
                                3
                            )
                        )

                        draw.rectangle(
                            [
                                left,
                                top,
                                left + width,
                                top + height,
                            ],
                            outline=stroke,
                            width=stroke_width,
                        )

                    # -------------------------------------
                    # CIRCLE
                    # -------------------------------------

                    elif obj_type == "circle":

                        left = obj.get(
                            "left",
                            0
                        )

                        top = obj.get(
                            "top",
                            0
                        )

                        radius = obj.get(
                            "radius",
                            0
                        )

                        stroke = obj.get(
                            "stroke",
                            "#FF0000"
                        )

                        draw.ellipse(
                            [
                                left,
                                top,
                                left + radius * 2,
                                top + radius * 2,
                            ],
                            outline=stroke,
                            width=int(
                                obj.get(
                                    "strokeWidth",
                                    3
                                )
                            ),
                        )

            except Exception:
                pass

        # Gabungkan slide + coretan
        final_slide = Image.alpha_composite(
            resized_bg.convert("RGBA"),
            overlay
        ).convert("RGB")

        # -------------------------------------------------
        # Simpan image temporary
        # -------------------------------------------------

        img_buffer = io.BytesIO()

        final_slide.save(
            img_buffer,
            format="PNG"
        )

        img_buffer.seek(0)

        # -------------------------------------------------
        # PDF
        # -------------------------------------------------

        story.append(
            Paragraph(
                f"<b>Slide {idx + 1}</b>",
                title_style
            )
        )

        story.append(
            RLImage(
                img_buffer,
                width=500,
                height=500 * (
                    final_slide.height /
                    final_slide.width
                ),
            )
        )

        story.append(
            Spacer(1, 10)
        )

        mini_note = (
            st.session_state
            .mini_notes
            .get(idx, "")
            .strip()
        )

        note_text = (
            st.session_state
            .slide_notes
            .get(idx, "")
            .strip()
        )

        if mini_note:

            story.append(
                Paragraph(
                    f"<b>📌 Mini Notes:</b><br/>{mini_note}",
                    note_style
                )
            )

        if note_text:

            story.append(
                Paragraph(
                    "<b>📝 Catatan Utama:</b>",
                    styles["Bold"]
                )
            )

            for line in note_text.split("\n"):

                story.append(
                    Paragraph(
                        line,
                        note_style
                    )
                )

        if not mini_note and not note_text:

            story.append(
                Paragraph(
                    "<i>Tidak ada catatan.</i>",
                    note_style
                )
            )

        story.append(
            PageBreak()
        )

    doc.build(story)

    buffer.seek(0)

    return buffer


# =========================================================
# GOOGLE DRIVE
# =========================================================

def get_drive_service():

    creds_dict = st.secrets[
        "gcp_service_account"
    ]

    creds = (
        service_account
        .Credentials
        .from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/drive.file"
            ],
        )
    )

    return build(
        "drive",
        "v3",
        credentials=creds
    )


def upload_to_gdrive(
    file_bytes,
    filename="Hasil_Edit_Slide.pdf"
):

    try:

        service = get_drive_service()

        folder_id = st.secrets[
            "FOLDER_ID"
        ]

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype="application/pdf",
            resumable=True,
        )

        file = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id",
            )
            .execute()
        )

        return file.get("id")

    except Exception as e:

        st.error(
            f"Gagal upload ke Drive: {str(e)}"
        )

        return None


# =========================================================
# HEADER
# =========================================================

USER_NAME = "✨ My Personal Study Space"

st.markdown(
    f"""
    <div class="user-badge">
        {t["e_main"]} {USER_NAME}
    </div>
    """,
    unsafe_allow_html=True
)

st.title(
    f"𐙚 Slide & Scribble {t['e_main']}"
)

st.caption(
    "Unggah materi kuliah, langsung coret di atas slide, "
    "tambahkan teks, stabilo, dan buat catatan belajar."
    f" {t['e_sub']}"
)


# =========================================================
# SIDEBAR — UPLOAD
# =========================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{t['e_file']} Unggah Berkas"
    )

    uploaded_file = st.file_uploader(
        "Pilih file PDF",
        type=["pdf"]
    )

    if uploaded_file:

        if st.button(
            f"🔄 Proses Berkas Baru {t['e_sub']}"
        ):

            with st.spinner(
                "Memproses slide..."
            ):

                file_bytes = (
                    uploaded_file.read()
                )

                slides = convert_pdf_to_images(
                    file_bytes
                )

                st.session_state.slides_images = slides

                st.session_state.slide_notes = {}

                st.session_state.mini_notes = {}

                st.session_state.drawings = {}

                st.session_state.drawing_history = {}

                st.session_state.current_slide = 0

                st.session_state.canvas_version += 1

                st.success(
                    f"Berhasil memuat {len(slides)} slide!"
                )


# =========================================================
# SIDEBAR — TOOLS
# =========================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{t['e_draw']} Tools"
    )

    mode_indo_map = {

        "✏️ Pen — Coret Bebas":
            "freedraw",

        "🔤 Text — Tambah Teks":
            "text",

        "📏 Line — Garis":
            "line",

        "🔲 Rectangle — Kotak":
            "rect",

        "⚪ Circle — Lingkaran":
            "circle",

        "✋ Select — Geser/Pilih":
            "transform",

    }

    selected_mode_label = st.selectbox(
        "Pilih alat:",
        list(mode_indo_map.keys())
    )

    drawing_mode = mode_indo_map[
        selected_mode_label
    ]

    # -----------------------------------------------------
    # TOOL TYPE
    # -----------------------------------------------------

    if drawing_mode == "freedraw":

        tool_type = st.radio(
            "Jenis Pen:",
            [
                "✏️ Pen",
                "🖍️ Stabilo"
            ],
            index=0
        )

    else:

        tool_type = "✏️ Pen"


    # -----------------------------------------------------
    # COLOR
    # -----------------------------------------------------

    if tool_type == "🖍️ Stabilo":

        preset_color = st.radio(
            "Warna Stabilo:",
            [
                "🟡 Kuning",
                "💖 Pink",
                "🟢 Hijau Mint",
                "🩵 Biru Muda",
                "🎨 Custom",
            ],
            index=0
        )

        stabilo_map = {

            "🟡 Kuning":
                "rgba(255, 235, 59, 0.40)",

            "💖 Pink":
                "rgba(255, 105, 180, 0.40)",

            "🟢 Hijau Mint":
                "rgba(144, 238, 144, 0.40)",

            "🩵 Biru Muda":
                "rgba(135, 206, 250, 0.40)",
        }

        if preset_color == "🎨 Custom":

            custom_hex = st.color_picker(
                "Pilih warna:",
                "#FFFF00"
            )

            stroke_color = hex_to_rgba(
                custom_hex,
                0.40
            )

        else:

            stroke_color = stabilo_map[
                preset_color
            ]

        default_stroke_width = 16

    else:

        preset_color = st.radio(
            "Warna:",
            [
                "🔴 Merah",
                "🔵 Biru",
                "🟢 Hijau",
                "⚫ Hitam",
                "🎨 Custom",
            ],
            index=0
        )

        pen_map = {

            "🔴 Merah":
                "#FF0000",

            "🔵 Biru":
                "#0055FF",

            "🟢 Hijau":
                "#00AA44",

            "⚫ Hitam":
                "#000000",
        }

        if preset_color == "🎨 Custom":

            stroke_color = st.color_picker(
                "Pilih warna:",
                "#FF0000"
            )

        else:

            stroke_color = pen_map[
                preset_color
            ]

        default_stroke_width = 3


    # -----------------------------------------------------
    # SIZE
    # -----------------------------------------------------

    stroke_width = st.slider(
        "Ukuran:",
        1,
        30,
        default_stroke_width
    )


# =========================================================
# EDITOR
# =========================================================

if st.session_state.slides_images:

    total_slides = len(
        st.session_state.slides_images
    )

    # -----------------------------------------------------
    # NAVIGASI SLIDE
    # -----------------------------------------------------

    st.divider()

    col_prev, col_num, col_next = st.columns(
        [1, 3, 1]
    )

    with col_prev:

        if st.button(
            "←",
            disabled=(
                st.session_state.current_slide <= 0
            ),
        ):

            st.session_state.current_slide -= 1

            st.session_state.canvas_version += 1

            st.rerun()


    with col_num:

        slide_num = st.slider(
            "Slide",
            1,
            total_slides,
            st.session_state.current_slide + 1,
            label_visibility="collapsed",
        ) - 1

        if slide_num != st.session_state.current_slide:

            st.session_state.current_slide = slide_num

            st.session_state.canvas_version += 1

            st.rerun()


    with col_next:

        if st.button(
            "→",
            disabled=(
                st.session_state.current_slide >= total_slides - 1
            ),
        ):

            st.session_state.current_slide += 1

            st.session_state.canvas_version += 1

            st.rerun()


    slide_num = st.session_state.current_slide

    st.markdown(
        f"### {t['e_sub']} Slide {slide_num + 1} / {total_slides}"
    )


    # -----------------------------------------------------
    # LAYOUT
    # -----------------------------------------------------

    col_editor, col_notes = st.columns(
        [3, 2]
    )


    # =====================================================
    # SLIDE EDITOR
    # =====================================================

    with col_editor:

        st.markdown(
            f"#### 🖼️ Edit langsung di slide {t['e_draw']}"
        )

        current_bg = (
            st.session_state.slides_images[
                slide_num
            ]
        )

        canvas_width = 900

        aspect_ratio = (
            current_bg.height /
            current_bg.width
        )

        canvas_height = int(
            canvas_width *
            aspect_ratio
        )

        resized_bg = current_bg.resize(
            (
                canvas_width,
                canvas_height
            )
        )


        # -------------------------------------------------
        # CURRENT DRAWING
        # -------------------------------------------------

        current_drawing = (
            st.session_state.drawings.get(
                slide_num
            )
        )


        # -------------------------------------------------
        # CANVAS LANGSUNG DI ATAS SLIDE
        # -------------------------------------------------

        canvas_result = st_canvas(

            fill_color="rgba(255,255,255,0)",

            stroke_width=stroke_width,

            stroke_color=stroke_color,

            background_image=resized_bg,

            update_streamlit=True,

            height=canvas_height,

            width=canvas_width,

            drawing_mode=drawing_mode,

            display_toolbar=False,

            key=(
                f"slide_editor_"
                f"{slide_num}_"
                f"{st.session_state.canvas_version}"
            ),
        )


        # -------------------------------------------------
        # SIMPAN HASIL CORETAAN
        # -------------------------------------------------

        if (
            canvas_result.json_data
            is not None
        ):

            new_data = (
                canvas_result.json_data
            )

            old_data = (
                st.session_state.drawings.get(
                    slide_num
                )
            )

            # Hanya simpan jika benar-benar berubah
            if new_data != old_data:

                # History untuk undo
                if old_data:

                    history = (
                        st.session_state
                        .drawing_history
                        .setdefault(
                            slide_num,
                            []
                        )
                    )

                    history.append(
                        copy.deepcopy(
                            old_data
                        )
                    )

                    # batasi history
                    if len(history) > 30:

                        history.pop(0)

                st.session_state.drawings[
                    slide_num
                ] = new_data


        # -------------------------------------------------
        # CONTROL
        # -------------------------------------------------

        st.write("")

        c1, c2, c3 = st.columns(3)

        with c1:

            if st.button(
                "↩️ Undo",
                use_container_width=True
            ):

                history = (
                    st.session_state
                    .drawing_history
                    .get(
                        slide_num,
                        []
                    )
                )

                if history:

                    previous = history.pop()

                    st.session_state.drawings[
                        slide_num
                    ] = previous

                    st.session_state.canvas_version += 1

                    st.rerun()

                else:

                    st.toast(
                        "Belum ada yang bisa di-undo."
                    )


        with c2:

            if st.button(
                "🗑️ Hapus Semua",
                use_container_width=True
            ):

                st.session_state.drawings[
                    slide_num
                ] = None

                st.session_state.drawing_history[
                    slide_num
                ] = []

                st.session_state.canvas_version += 1

                st.rerun()


        with c3:

            if st.button(
                "🔄 Reset Slide",
                use_container_width=True
            ):

                st.session_state.drawings[
                    slide_num
                ] = None

                st.session_state.drawing_history[
                    slide_num
                ] = []

                st.session_state.canvas_version += 1

                st.rerun()


        st.caption(
            "💡 Pilih Text lalu klik pada slide untuk menambahkan teks."
        )


    # =====================================================
    # NOTES
    # =====================================================

    with col_notes:

        st.subheader(
            f"{t['e_note']} Mini Notes"
        )

        current_mini = (
            st.session_state
            .mini_notes
            .get(
                slide_num,
                ""
            )
        )

        updated_mini = st.text_input(
            "Kata kunci / rumus:",
            value=current_mini,
            key=f"mini_{slide_num}",
            placeholder=(
                "Contoh: Definisi X / Rumus Y"
            ),
        )

        st.session_state.mini_notes[
            slide_num
        ] = updated_mini


        st.subheader(
            "📝 Catatan Utama"
        )

        current_note = (
            st.session_state
            .slide_notes
            .get(
                slide_num,
                ""
            )
        )

        updated_note = st.text_area(
            "Penjelasan materi:",
            value=current_note,
            height=280,
            key=f"note_{slide_num}",
            placeholder=(
                "Tulis penjelasan materi "
                "dengan bahasa kamu sendiri..."
            ),
        )

        st.session_state.slide_notes[
            slide_num
        ] = updated_note


        st.info(
            "✨ Catatan disimpan otomatis selama halaman ini aktif."
        )


    # =====================================================
    # EXPORT
    # =====================================================

    st.divider()

    st.subheader(
        f"📤 Simpan Materi {t['e_sub']}"
    )

    col_exp1, col_exp2 = st.columns(2)


    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    with col_exp1:

        if st.button(
            "📄 Generate PDF",
            use_container_width=True
        ):

            with st.spinner(
                "Menyusun PDF..."
            ):

                pdf_data = (
                    generate_exported_pdf()
                )

                st.download_button(
                    label="⬇️ Unduh PDF",
                    data=pdf_data,
                    file_name=(
                        "Hasil_Edit_Slide.pdf"
                    ),
                    mime="application/pdf",
                    use_container_width=True,
                )


    # -----------------------------------------------------
    # GOOGLE DRIVE
    # -----------------------------------------------------

    with col_exp2:

        if st.button(
            f"{t['e_cloud']} Simpan ke Google Drive",
            use_container_width=True
        ):

            with st.spinner(
                "Mengunggah..."
            ):

                pdf_bytes_data = (
                    generate_exported_pdf()
                    .getvalue()
                )

                file_id = upload_to_gdrive(
                    pdf_bytes_data
                )

                if file_id:

                    st.success(
                        "Berhasil disimpan ke Google Drive! 🎉"
                    )


# =========================================================
# EMPTY STATE
# =========================================================

else:

    st.info(
        f"""
        {t['e_file']} **Belum ada materi.**

        Upload file PDF melalui sidebar
        untuk mulai belajar dengan
        **Slide & Scribble** {t['e_sub']}
        """
    )
