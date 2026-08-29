import io
import copy
import base64
import html
import json

import fitz
import streamlit as st

from PIL import Image, ImageDraw

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
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="𐙚 Slide & Scribble",
    page_icon="🎀",
    layout="wide",
)


# =========================================================
# SESSION STATE
# =========================================================

if "slides_images" not in st.session_state:
    st.session_state.slides_images = []

if "slide_notes" not in st.session_state:
    st.session_state.slide_notes = {}

if "mini_notes" not in st.session_state:
    st.session_state.mini_notes = {}

if "drawings" not in st.session_state:
    st.session_state.drawings = {}

if "drawing_history" not in st.session_state:
    st.session_state.drawing_history = {}

if "current_slide" not in st.session_state:
    st.session_state.current_slide = 0

if "canvas_key" not in st.session_state:
    st.session_state.canvas_key = 0


# =========================================================
# THEME
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
        background-color: {t["card_bg"]};
    }}

    [data-testid="stSidebar"] {{
        background-color: {t["bg_sidebar"]};
    }}

    h1, h2, h3 {{
        color: {t["text_header"]} !important;
    }}

    .stButton > button {{
        background-color: {t["primary"]} !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: bold;
    }}

    .user-badge {{
        background-color: {t["bg_sidebar"]};
        color: {t["text_header"]};
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 14px;
        font-weight: bold;
        border: 1px solid {t["border"]};
        display: inline-block;
        margin-bottom: 10px;
    }}

    .slide-frame {{
        position: relative;
        width: 100%;
        margin: auto;
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 5px 20px rgba(0,0,0,0.12);
        background: white;
    }}

    .slide-image {{
        width: 100%;
        display: block;
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
# PDF TO IMAGE
# =========================================================

def convert_pdf_to_images(pdf_bytes):

    images = []

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf",
    )

    for page in doc:

        pix = page.get_pixmap(
            dpi=150,
            alpha=False,
        )

        image = Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples,
        )

        images.append(image)

    doc.close()

    return images


# =========================================================
# IMAGE → DATA URL
# =========================================================

def image_to_data_url(image):

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    return f"data:image/png;base64,{encoded}"


# =========================================================
# DRAWING RENDERER
# =========================================================

def render_canvas_objects(
    background,
    canvas_json,
    target_width=None,
):

    if background is None:
        return None

    bg = background.copy().convert("RGBA")

    if target_width is not None:

        ratio = bg.height / bg.width

        target_height = int(
            target_width * ratio
        )

        bg = bg.resize(
            (
                target_width,
                target_height,
            ),
            Image.Resampling.LANCZOS,
        )

    if not canvas_json:
        return bg.convert("RGB")

    overlay = Image.new(
        "RGBA",
        bg.size,
        (255, 255, 255, 0),
    )

    draw = ImageDraw.Draw(
        overlay
    )

    objects = canvas_json.get(
        "objects",
        [],
    )

    canvas_original_width = canvas_json.get(
        "width",
        bg.width,
    )

    scale = (
        bg.width /
        canvas_original_width
    )

    for obj in objects:

        obj_type = obj.get(
            "type",
            "",
        )

        # =================================================
        # PATH / FREE DRAW
        # =================================================

        if obj_type == "path":

            path = obj.get(
                "path",
                [],
            )

            points = []

            for command in path:

                if not command:
                    continue

                command_type = command[0]

                if command_type == "M":

                    if len(command) >= 3:

                        points.append(
                            (
                                command[1] * scale,
                                command[2] * scale,
                            )
                        )

                elif command_type == "L":

                    if len(command) >= 3:

                        points.append(
                            (
                                command[1] * scale,
                                command[2] * scale,
                            )
                        )

                elif command_type == "Q":

                    if len(command) >= 5:

                        points.append(
                            (
                                command[3] * scale,
                                command[4] * scale,
                            )
                        )

        # =================================================
        # RECTANGLE
        # =================================================

        elif obj_type == "rect":

            left = obj.get(
                "left",
                0,
            ) * scale

            top = obj.get(
                "top",
                0,
            ) * scale

            width = obj.get(
                "width",
                0,
            ) * scale

            height = obj.get(
                "height",
                0,
            ) * scale

            angle = obj.get(
                "angle",
                0,
            )

            stroke = obj.get(
                "stroke",
                "#FF0000",
            )

            stroke_width = max(
                1,
                int(
                    obj.get(
                        "strokeWidth",
                        3,
                    ) * scale
                ),
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

        # =================================================
        # CIRCLE
        # =================================================

        elif obj_type == "circle":

            left = obj.get(
                "left",
                0,
            ) * scale

            top = obj.get(
                "top",
                0,
            ) * scale

            radius = obj.get(
                "radius",
                0,
            ) * scale

            stroke = obj.get(
                "stroke",
                "#FF0000",
            )

            stroke_width = max(
                1,
                int(
                    obj.get(
                        "strokeWidth",
                        3,
                    ) * scale
                ),
            )

            draw.ellipse(
                [
                    left,
                    top,
                    left + radius * 2,
                    top + radius * 2,
                ],
                outline=stroke,
                width=stroke_width,
            )

        # =================================================
        # LINE
        # =================================================

        elif obj_type == "line":

            x1 = obj.get(
                "x1",
                0,
            ) * scale

            y1 = obj.get(
                "y1",
                0,
            ) * scale

            x2 = obj.get(
                "x2",
                0,
            ) * scale

            y2 = obj.get(
                "y2",
                0,
            ) * scale

            stroke = obj.get(
                "stroke",
                "#FF0000",
            )

            stroke_width = max(
                1,
                int(
                    obj.get(
                        "strokeWidth",
                        3,
                    ) * scale
                ),
            )

            draw.line(
                [
                    x1,
                    y1,
                    x2,
                    y2,
                ],
                fill=stroke,
                width=stroke_width,
            )

        # =================================================
        # TEXT
        # =================================================

        elif obj_type in [
            "textbox",
            "i-text",
            "text",
        ]:

            text = obj.get(
                "text",
                "",
            )

            if not text:
                continue

            left = obj.get(
                "left",
                0,
            ) * scale

            top = obj.get(
                "top",
                0,
            ) * scale

            fill = obj.get(
                "fill",
                "#000000",
            )

            font_size = int(
                obj.get(
                    "fontSize",
                    20,
                ) * scale
            )

            try:

                from PIL import ImageFont

                font = ImageFont.truetype(
                    "DejaVuSans.ttf",
                    max(8, font_size),
                )

            except Exception:

                font = None

            draw.text(
                (
                    left,
                    top,
                ),
                text,
                fill=fill,
                font=font,
            )

    result = Image.alpha_composite(
        bg,
        overlay,
    )

    return result.convert("RGB")


# =========================================================
# SAVE DRAWING
# =========================================================

def save_canvas_data(
    slide_num,
    canvas_result,
):

    if canvas_result is None:
        return

    json_data = canvas_result.json_data

    if json_data is None:
        return

    old_data = (
        st.session_state.drawings
        .get(slide_num)
    )

    if old_data == json_data:
        return

    if old_data:

        history = (
            st.session_state
            .drawing_history
            .setdefault(
                slide_num,
                [],
            )
        )

        history.append(
            copy.deepcopy(
                old_data
            )
        )

        if len(history) > 30:
            history.pop(0)

    st.session_state.drawings[
        slide_num
    ] = json_data


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

    for idx, slide in enumerate(
        st.session_state.slides_images
    ):

        drawing = (
            st.session_state
            .drawings
            .get(idx)
        )

        final_image = render_canvas_objects(
            slide,
            drawing,
        )

        image_buffer = io.BytesIO()

        final_image.save(
            image_buffer,
            format="PNG",
        )

        image_buffer.seek(0)

        story.append(
            Paragraph(
                f"<b>Slide {idx + 1}</b>",
                title_style,
            )
        )

        max_width = 500

        ratio = (
            final_image.height /
            final_image.width
        )

        image_height = (
            max_width * ratio
        )

        story.append(
            RLImage(
                image_buffer,
                width=max_width,
                height=image_height,
            )
        )

        story.append(
            Spacer(1, 10)
        )

        mini_note = (
            st.session_state
            .mini_notes
            .get(
                idx,
                "",
            )
            .strip()
        )

        main_note = (
            st.session_state
            .slide_notes
            .get(
                idx,
                "",
            )
            .strip()
        )

        if mini_note:

            safe_mini = html.escape(
                mini_note
            ).replace(
                "\n",
                "<br/>",
            )

            story.append(
                Paragraph(
                    f"<b>📌 Mini Notes:</b><br/>{safe_mini}",
                    note_style,
                )
            )

        if main_note:

            story.append(
                Paragraph(
                    "<b>📝 Catatan Utama:</b>",
                    styles["Bold"],
                )
            )

            for line in main_note.split("\n"):

                safe_line = html.escape(
                    line
                )

                story.append(
                    Paragraph(
                        safe_line,
                        note_style,
                    )
                )

        if not mini_note and not main_note:

            story.append(
                Paragraph(
                    "<i>Tidak ada catatan.</i>",
                    note_style,
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
        credentials=creds,
    )


def upload_to_gdrive(
    file_bytes,
    filename="Hasil_Edit_Slide.pdf",
):

    try:

        service = get_drive_service()

        folder_id = st.secrets[
            "FOLDER_ID"
        ]

        metadata = {
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
                body=metadata,
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
    unsafe_allow_html=True,
)

st.title(
    f"𐙚 Slide & Scribble {t['e_main']}"
)

st.caption(
    "Unggah materi kuliah, coret langsung di atas slide, "
    "tambahkan teks, stabilo, dan buat catatan belajar."
)


# =========================================================
# UPLOAD
# =========================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{t['e_file']} Unggah Berkas"
    )

    uploaded_file = st.file_uploader(
        "Pilih file PDF",
        type=["pdf"],
    )

    if uploaded_file:

        if st.button(
            "🔄 Proses Berkas Baru"
        ):

            with st.spinner(
                "Memproses slide..."
            ):

                file_bytes = (
                    uploaded_file.read()
                )

                slides = (
                    convert_pdf_to_images(
                        file_bytes
                    )
                )

                st.session_state.slides_images = slides

                st.session_state.slide_notes = {}

                st.session_state.mini_notes = {}

                st.session_state.drawings = {}

                st.session_state.drawing_history = {}

                st.session_state.current_slide = 0

                st.session_state.canvas_key += 1

                st.success(
                    f"Berhasil memuat {len(slides)} slide! 🎉"
                )


# =========================================================
# TOOLS
# =========================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{t['e_draw']} Tools"
    )

    mode_map = {

        "✏️ Pen — Coret":
            "freedraw",

        "🔤 Text — Tulis":
            "text",

        "📏 Line — Garis":
            "line",

        "🔲 Rectangle — Kotak":
            "rect",

        "⚪ Circle — Lingkaran":
            "circle",

        "✋ Select — Pilih":
            "transform",
    }

    selected_mode = st.selectbox(
        "Pilih alat:",
        list(mode_map.keys()),
    )

    drawing_mode = mode_map[
        selected_mode
    ]


    # =====================================================
    # PEN / STABILO
    # =====================================================

    if drawing_mode == "freedraw":

        tool_type = st.radio(
            "Jenis:",
            [
                "✏️ Pen",
                "🖍️ Stabilo",
            ],
        )

    else:

        tool_type = "✏️ Pen"


    if tool_type == "🖍️ Stabilo":

        preset_color = st.radio(
            "Warna Stabilo:",
            [
                "🟡 Kuning",
                "💖 Pink",
                "🟢 Mint",
                "🩵 Biru",
                "🎨 Custom",
            ],
        )

        stabilo_map = {

            "🟡 Kuning":
                "rgba(255,235,59,0.40)",

            "💖 Pink":
                "rgba(255,105,180,0.40)",

            "🟢 Mint":
                "rgba(144,238,144,0.40)",

            "🩵 Biru":
                "rgba(135,206,250,0.40)",
        }

        if preset_color == "🎨 Custom":

            custom_color = st.color_picker(
                "Warna:",
                "#FFFF00",
            )

            stroke_color = hex_to_rgba(
                custom_color,
                0.40,
            )

        else:

            stroke_color = stabilo_map[
                preset_color
            ]

        default_width = 16

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
                "Warna:",
                "#FF0000",
            )

        else:

            stroke_color = pen_map[
                preset_color
            ]

        default_width = 3


    stroke_width = st.slider(
        "Ukuran:",
        1,
        30,
        default_width,
    )


# =========================================================
# MAIN EDITOR
# =========================================================

if st.session_state.slides_images:

    total_slides = len(
        st.session_state.slides_images
    )


    # =====================================================
    # NAVIGATION
    # =====================================================

    nav1, nav2, nav3 = st.columns(
        [1, 4, 1]
    )

    with nav1:

        if st.button(
            "←",
            use_container_width=True,
            disabled=(
                st.session_state.current_slide == 0
            ),
        ):

            st.session_state.current_slide -= 1

            st.session_state.canvas_key += 1

            st.rerun()


    with nav2:

        selected_slide = st.slider(
            "Pilih Slide",
            min_value=1,
            max_value=total_slides,
            value=(
                st.session_state.current_slide + 1
            ),
        ) - 1

        if (
            selected_slide !=
            st.session_state.current_slide
        ):

            st.session_state.current_slide = (
                selected_slide
            )

            st.session_state.canvas_key += 1

            st.rerun()


    with nav3:

        if st.button(
            "→",
            use_container_width=True,
            disabled=(
                st.session_state.current_slide
                == total_slides - 1
            ),
        ):

            st.session_state.current_slide += 1

            st.session_state.canvas_key += 1

            st.rerun()


    slide_num = (
        st.session_state.current_slide
    )


    st.markdown(
        f"### {t['e_sub']} Slide {slide_num + 1} / {total_slides}"
    )


    # =====================================================
    # EDITOR + NOTES
    # =====================================================

    col_editor, col_notes = st.columns(
        [3, 2]
    )


    # =====================================================
    # EDITOR
    # =====================================================

    with col_editor:

        st.markdown(
            f"#### 🖼️ Edit langsung di slide {t['e_draw']}"
        )

        current_slide = (
            st.session_state
            .slides_images[
                slide_num
            ]
        )


        # -------------------------------------------------
        # IMPORTANT:
        # Canvas menggunakan ukuran yang sama dengan slide.
        # Background image diberikan langsung ke canvas.
        # -------------------------------------------------

        canvas_width = 900

        aspect_ratio = (
            current_slide.height /
            current_slide.width
        )

        canvas_height = int(
            canvas_width *
            aspect_ratio
        )

        resized_slide = (
            current_slide.resize(
                (
                    canvas_width,
                    canvas_height,
                ),
                Image.Resampling.LANCZOS,
            )
        )


        # -------------------------------------------------
        # CANVAS
        # -------------------------------------------------

        canvas_result = st_canvas(

            fill_color=(
                "rgba(255,255,255,0)"
            ),

            stroke_width=stroke_width,

            stroke_color=stroke_color,

            background_image=resized_slide,

            update_streamlit=True,

            height=canvas_height,

            width=canvas_width,

            drawing_mode=drawing_mode,

            display_toolbar=True,

            key=(
                f"canvas_"
                f"{slide_num}_"
                f"{st.session_state.canvas_key}"
            ),
        )


        # -------------------------------------------------
        # SAVE DRAWING
        # -------------------------------------------------

        save_canvas_data(
            slide_num,
            canvas_result,
        )


        # -------------------------------------------------
        # BUTTONS
        # -------------------------------------------------

        st.write("")

        b1, b2, b3 = st.columns(3)


        with b1:

            if st.button(
                "↩️ Undo",
                use_container_width=True,
            ):

                history = (
                    st.session_state
                    .drawing_history
                    .get(
                        slide_num,
                        [],
                    )
                )

                if history:

                    previous = history.pop()

                    st.session_state.drawings[
                        slide_num
                    ] = previous

                    st.session_state.canvas_key += 1

                    st.rerun()

                else:

                    st.toast(
                        "Belum ada yang bisa di-undo."
                    )


        with b2:

            if st.button(
                "🗑️ Hapus Coretan",
                use_container_width=True,
            ):

                st.session_state.drawings[
                    slide_num
                ] = None

                st.session_state.drawing_history[
                    slide_num
                ] = []

                st.session_state.canvas_key += 1

                st.rerun()


        with b3:

            if st.button(
                "🔄 Reset",
                use_container_width=True,
            ):

                st.session_state.drawings[
                    slide_num
                ] = None

                st.session_state.drawing_history[
                    slide_num
                ] = []

                st.session_state.canvas_key += 1

                st.rerun()


        st.caption(
            "💡 Untuk teks: pilih 🔤 Text, lalu klik area slide dan ketik."
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
                "",
            )
        )

        mini_note = st.text_input(
            "Kata kunci / rumus:",
            value=current_mini,
            key=f"mini_note_{slide_num}",
            placeholder=(
                "Contoh: Rumus BEP / Definisi X"
            ),
        )

        st.session_state.mini_notes[
            slide_num
        ] = mini_note


        st.subheader(
            "📝 Catatan Utama"
        )

        current_note = (
            st.session_state
            .slide_notes
            .get(
                slide_num,
                "",
            )
        )

        main_note = st.text_area(
            "Penjelasan materi:",
            value=current_note,
            height=280,
            key=f"main_note_{slide_num}",
            placeholder=(
                "Tulis penjelasan materi di sini..."
            ),
        )

        st.session_state.slide_notes[
            slide_num
        ] = main_note


        st.info(
            "✨ Catatan mengikuti slide yang sedang dibuka."
        )


    # =====================================================
    # EXPORT
    # =====================================================

    st.divider()

    st.subheader(
        f"📤 Simpan Materi {t['e_sub']}"
    )

    export1, export2 = st.columns(2)


    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    with export1:

        if st.button(
            "📄 Generate PDF",
            use_container_width=True,
        ):

            with st.spinner(
                "Menyusun PDF..."
            ):

                pdf_data = (
                    generate_exported_pdf()
                )

                st.download_button(
                    "⬇️ Unduh Hasil PDF",
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

    with export2:

        if st.button(
            f"{t['e_cloud']} Simpan ke Google Drive",
            use_container_width=True,
        ):

            with st.spinner(
                "Mengunggah..."
            ):

                pdf_bytes = (
                    generate_exported_pdf()
                    .getvalue()
                )

                file_id = upload_to_gdrive(
                    pdf_bytes
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

        Upload PDF melalui sidebar untuk mulai
        menggunakan **Slide & Scribble** {t['e_sub']}
        """
    )
