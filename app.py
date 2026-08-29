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


# =========================================================
# 1. PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="𐙚 Slide & Scribble",
    page_icon="🎀",
    layout="wide",
)


# =========================================================
# 2. SESSION STATE
# =========================================================
# Semua key diberi prefix "sas_" supaya tidak bentrok
# dengan widget/state dari versi aplikasi sebelumnya.

if "sas_slides" not in st.session_state:
    st.session_state.sas_slides = []

if "sas_notes" not in st.session_state:
    st.session_state.sas_notes = {}

if "sas_mini_notes" not in st.session_state:
    st.session_state.sas_mini_notes = {}

if "sas_drawings" not in st.session_state:
    st.session_state.sas_drawings = {}

if "sas_history" not in st.session_state:
    st.session_state.sas_history = {}

if "sas_current_slide" not in st.session_state:
    st.session_state.sas_current_slide = 0

if "sas_canvas_revision" not in st.session_state:
    st.session_state.sas_canvas_revision = 0


# =========================================================
# 3. THEME
# =========================================================

THEMES = {
    "🎀 Coquette Soft": {
        "bg_sidebar": "#FFF0F3",
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
        "bg_sidebar": "#F0F8FF",
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
        "bg_sidebar": "#FFF3E0",
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
        "bg_sidebar": "#F2F5F3",
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


# =========================================================
# 4. THEME SELECTOR
# =========================================================

with st.sidebar:

    st.header("🎨 Pilih Tema")

    theme_options = list(THEMES.keys())

    selected_theme = st.selectbox(
        "Suasana tampilan:",
        theme_options,
        index=0,
        key="sas_theme_selector",
    )


t = THEMES[selected_theme]


# =========================================================
# 5. CSS
# =========================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: {t["card"]};
    }}

    [data-testid="stSidebar"] {{
        background-color: {t["bg_sidebar"]};
    }}

    h1, h2, h3 {{
        color: {t["text"]} !important;
    }}

    .stButton > button {{
        background-color: {t["primary"]} !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
    }}

    .study-badge {{
        background-color: {t["bg_sidebar"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
        padding: 5px 13px;
        border-radius: 20px;
        display: inline-block;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 8px;
    }}

    .slide-card {{
        background: white;
        padding: 8px;
        border-radius: 16px;
        box-shadow: 0 5px 22px rgba(0,0,0,0.10);
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 6. HELPER: COLOR
# =========================================================

def hex_to_rgba(hex_code, alpha=0.4):

    hex_code = hex_code.replace("#", "")

    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)

    return f"rgba({r},{g},{b},{alpha})"


# =========================================================
# 7. PDF → IMAGE
# =========================================================

def pdf_to_images(pdf_bytes):

    images = []

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf",
    )

    for page in document:

        pixmap = page.get_pixmap(
            dpi=150,
            alpha=False,
        )

        image = Image.frombytes(
            "RGB",
            [
                pixmap.width,
                pixmap.height,
            ],
            pixmap.samples,
        )

        images.append(image)

    document.close()

    return images


# =========================================================
# 8. CANVAS SIZE
# =========================================================

def get_canvas_size(image):

    width = 900

    ratio = (
        image.height /
        image.width
    )

    height = int(
        width * ratio
    )

    return width, height


# =========================================================
# 9. RENDER OBJECTS FOR EXPORT
# =========================================================

def render_objects_on_image(
    background,
    canvas_data,
):

    result = background.copy().convert(
        "RGBA"
    )

    if not canvas_data:
        return result.convert("RGB")

    objects = canvas_data.get(
        "objects",
        [],
    )

    canvas_width = canvas_data.get(
        "width",
        result.width,
    )

    scale = (
        result.width /
        canvas_width
    )

    overlay = Image.new(
        "RGBA",
        result.size,
        (255, 255, 255, 0),
    )

    draw = ImageDraw.Draw(
        overlay
    )

    for obj in objects:

        obj_type = obj.get(
            "type",
            "",
        )

        # -------------------------------------------------
        # FREE DRAWING
        # -------------------------------------------------

        if obj_type == "path":

            path = obj.get(
                "path",
                [],
            )

            points = []

            for command in path:

                if len(command) < 3:
                    continue

                command_name = command[0]

                if command_name in [
                    "M",
                    "L",
                ]:

                    x = (
                        float(command[1])
                        * scale
                    )

                    y = (
                        float(command[2])
                        * scale
                    )

                    points.append(
                        (x, y)
                    )

                elif command_name == "Q":

                    if len(command) >= 5:

                        x = (
                            float(command[3])
                            * scale
                        )

                        y = (
                            float(command[4])
                            * scale
                        )

                        points.append(
                            (x, y)
                        )

            if len(points) >= 2:

                stroke = obj.get(
                    "stroke",
                    "#FF0000",
                )

                width = max(
                    1,
                    int(
                        float(
                            obj.get(
                                "strokeWidth",
                                3,
                            )
                        ) * scale
                    ),
                )

                draw.line(
                    points,
                    fill=stroke,
                    width=width,
                    joint="curve",
                )

        # -------------------------------------------------
        # RECTANGLE
        # -------------------------------------------------

        elif obj_type == "rect":

            left = (
                float(
                    obj.get(
                        "left",
                        0,
                    )
                ) * scale
            )

            top = (
                float(
                    obj.get(
                        "top",
                        0,
                    )
                ) * scale
            )

            width = (
                float(
                    obj.get(
                        "width",
                        0,
                    )
                ) * scale
            )

            height = (
                float(
                    obj.get(
                        "height",
                        0,
                    )
                ) * scale
            )

            stroke = obj.get(
                "stroke",
                "#FF0000",
            )

            stroke_width = max(
                1,
                int(
                    float(
                        obj.get(
                            "strokeWidth",
                            3,
                        )
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

        # -------------------------------------------------
        # CIRCLE
        # -------------------------------------------------

        elif obj_type == "circle":

            left = (
                float(
                    obj.get(
                        "left",
                        0,
                    )
                ) * scale
            )

            top = (
                float(
                    obj.get(
                        "top",
                        0,
                    )
                ) * scale
            )

            radius = (
                float(
                    obj.get(
                        "radius",
                        0,
                    )
                ) * scale
            )

            stroke = obj.get(
                "stroke",
                "#FF0000",
            )

            stroke_width = max(
                1,
                int(
                    float(
                        obj.get(
                            "strokeWidth",
                            3,
                        )
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

        # -------------------------------------------------
        # LINE
        # -------------------------------------------------

        elif obj_type == "line":

            x1 = (
                float(
                    obj.get(
                        "x1",
                        0,
                    )
                ) * scale
            )

            y1 = (
                float(
                    obj.get(
                        "y1",
                        0,
                    )
                ) * scale
            )

            x2 = (
                float(
                    obj.get(
                        "x2",
                        0,
                    )
                ) * scale
            )

            y2 = (
                float(
                    obj.get(
                        "y2",
                        0,
                    )
                ) * scale
            )

            stroke = obj.get(
                "stroke",
                "#FF0000",
            )

            stroke_width = max(
                1,
                int(
                    float(
                        obj.get(
                            "strokeWidth",
                            3,
                        )
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

        # -------------------------------------------------
        # TEXT
        # -------------------------------------------------

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

            left = (
                float(
                    obj.get(
                        "left",
                        0,
                    )
                ) * scale
            )

            top = (
                float(
                    obj.get(
                        "top",
                        0,
                    )
                ) * scale
            )

            fill = obj.get(
                "fill",
                "#000000",
            )

            font_size = max(
                8,
                int(
                    float(
                        obj.get(
                            "fontSize",
                            20,
                        )
                    ) * scale
                ),
            )

            try:

                font = ImageFont.truetype(
                    "DejaVuSans.ttf",
                    font_size,
                )

            except Exception:

                font = ImageFont.load_default()

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
        result,
        overlay,
    )

    return result.convert("RGB")


# =========================================================
# 10. EXPORT PDF
# =========================================================

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

    note_style = ParagraphStyle(
        "StudyNote",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )

    title_style = ParagraphStyle(
        "SlideTitle",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
    )

    story = []

    for index, slide in enumerate(
        st.session_state.sas_slides
    ):

        drawing = (
            st.session_state
            .sas_drawings
            .get(index)
        )

        final_slide = (
            render_objects_on_image(
                slide,
                drawing,
            )
        )

        image_buffer = io.BytesIO()

        final_slide.save(
            image_buffer,
            format="PNG",
        )

        image_buffer.seek(0)

        story.append(
            Paragraph(
                f"<b>Slide {index + 1}</b>",
                title_style,
            )
        )

        max_width = 500

        image_ratio = (
            final_slide.height /
            final_slide.width
        )

        max_height = (
            max_width *
            image_ratio
        )

        story.append(
            RLImage(
                image_buffer,
                width=max_width,
                height=max_height,
            )
        )

        story.append(
            Spacer(1, 12)
        )

        mini = (
            st.session_state
            .sas_mini_notes
            .get(
                index,
                "",
            )
            .strip()
        )

        note = (
            st.session_state
            .sas_notes
            .get(
                index,
                "",
            )
            .strip()
        )

        if mini:

            safe_mini = (
                html.escape(mini)
                .replace(
                    "\n",
                    "<br/>",
                )
            )

            story.append(
                Paragraph(
                    f"<b>📌 Mini Notes</b><br/>{safe_mini}",
                    note_style,
                )
            )

        if note:

            story.append(
                Paragraph(
                    "<b>📝 Catatan Utama</b>",
                    note_style,
                )
            )

            for line in note.split("\n"):

                safe_line = html.escape(
                    line
                )

                story.append(
                    Paragraph(
                        safe_line,
                        note_style,
                    )
                )

        if not mini and not note:

            story.append(
                Paragraph(
                    "<i>Tidak ada catatan.</i>",
                    note_style,
                )
            )

        story.append(
            PageBreak()
        )

    document.build(story)

    output.seek(0)

    return output


# =========================================================
# 11. GOOGLE DRIVE
# =========================================================

def get_drive_service():

    credentials_dict = st.secrets[
        "gcp_service_account"
    ]

    credentials = (
        service_account
        .Credentials
        .from_service_account_info(
            credentials_dict,
            scopes=[
                "https://www.googleapis.com/auth/drive.file"
            ],
        )
    )

    return build(
        "drive",
        "v3",
        credentials=credentials,
    )


def upload_to_drive(
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

        uploaded = (
            service.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id",
            )
            .execute()
        )

        return uploaded.get("id")

    except Exception as error:

        st.error(
            f"Gagal menyimpan ke Google Drive: {error}"
        )

        return None


# =========================================================
# 12. HEADER
# =========================================================

st.markdown(
    f"""
    <div class="study-badge">
        {t["main"]} My Personal Study Space
    </div>
    """,
    unsafe_allow_html=True,
)

st.title(
    f"𐙚 Slide & Scribble {t['main']}"
)

st.caption(
    "Upload materi → edit langsung di atas slide → "
    "tambahkan notes → simpan sebagai PDF."
)


# =========================================================
# 13. UPLOAD SIDEBAR
# =========================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{t['file']} Materi Kuliah"
    )

    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        key="sas_pdf_uploader",
    )

    if uploaded_file:

        if st.button(
            "🔄 Muat Materi Baru",
            key="sas_load_pdf",
            use_container_width=True,
        ):

            with st.spinner(
                "Membaca slide..."
            ):

                pdf_bytes = (
                    uploaded_file.read()
                )

                slides = pdf_to_images(
                    pdf_bytes
                )

                st.session_state.sas_slides = slides

                st.session_state.sas_notes = {}

                st.session_state.sas_mini_notes = {}

                st.session_state.sas_drawings = {}

                st.session_state.sas_history = {}

                st.session_state.sas_current_slide = 0

                st.session_state.sas_canvas_revision += 1

                st.success(
                    f"{len(slides)} slide berhasil dimuat! 🎉"
                )


# =========================================================
# 14. TOOLS SIDEBAR
# =========================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{t['draw']} Drawing Tools"
    )

    tool_options = {
        "✏️ Pen — Coret": "freedraw",
        "🔤 Text — Tulis": "text",
        "📏 Line — Garis": "line",
        "🔲 Rectangle — Kotak": "rect",
        "⚪ Circle — Lingkaran": "circle",
        "✋ Select — Pilih": "transform",
    }

    selected_tool = st.selectbox(
        "Pilih alat:",
        list(tool_options.keys()),
        key="sas_tool_selector",
    )

    drawing_mode = tool_options[
        selected_tool
    ]


    # -----------------------------------------------------
    # PEN TYPE
    # -----------------------------------------------------

    if drawing_mode == "freedraw":

        pen_type = st.radio(
            "Jenis:",
            [
                "✏️ Pen",
                "🖍️ Stabilo",
            ],
            key="sas_pen_type",
        )

    else:

        pen_type = "✏️ Pen"


    # -----------------------------------------------------
    # COLOR
    # -----------------------------------------------------

    if pen_type == "🖍️ Stabilo":

        color_options = [
            "🟡 Kuning",
            "💖 Pink",
            "🟢 Mint",
            "🩵 Biru",
            "🎨 Custom",
        ]

        selected_color = st.radio(
            "Warna stabilo:",
            color_options,
            key="sas_highlighter_color",
        )

        highlighter_colors = {

            "🟡 Kuning":
                "rgba(255,235,59,0.40)",

            "💖 Pink":
                "rgba(255,105,180,0.40)",

            "🟢 Mint":
                "rgba(144,238,144,0.40)",

            "🩵 Biru":
                "rgba(135,206,250,0.40)",
        }

        if selected_color == "🎨 Custom":

            custom = st.color_picker(
                "Warna custom:",
                "#FFFF00",
                key="sas_custom_highlighter",
            )

            stroke_color = hex_to_rgba(
                custom,
                0.40,
            )

        else:

            stroke_color = highlighter_colors[
                selected_color
            ]

        default_size = 16

    else:

        color_options = [
            "🔴 Merah",
            "🔵 Biru",
            "🟢 Hijau",
            "⚫ Hitam",
            "🎨 Custom",
        ]

        selected_color = st.radio(
            "Warna:",
            color_options,
            key="sas_pen_color",
        )

        pen_colors = {

            "🔴 Merah":
                "#FF0000",

            "🔵 Biru":
                "#0055FF",

            "🟢 Hijau":
                "#00AA44",

            "⚫ Hitam":
                "#000000",
        }

        if selected_color == "🎨 Custom":

            stroke_color = st.color_picker(
                "Warna custom:",
                "#FF0000",
                key="sas_custom_pen",
            )

        else:

            stroke_color = pen_colors[
                selected_color
            ]

        default_size = 3


    stroke_width = st.slider(
        "Ukuran coretan:",
        1,
        30,
        default_size,
        key="sas_stroke_width",
    )


# =========================================================
# 15. MAIN APP
# =========================================================

if not st.session_state.sas_slides:

    st.info(
        f"""
        {t["file"]} **Belum ada materi.**

        Upload PDF melalui sidebar untuk mulai
        menggunakan **Slide & Scribble** {t["sub"]}
        """
    )

    st.stop()


# =========================================================
# 16. SLIDE NAVIGATION
# =========================================================

total_slides = len(
    st.session_state.sas_slides
)


nav_left, nav_center, nav_right = st.columns(
    [1, 5, 1]
)


with nav_left:

    if st.button(
        "←",
        key="sas_previous_slide",
        use_container_width=True,
        disabled=(
            st.session_state.sas_current_slide == 0
        ),
    ):

        st.session_state.sas_current_slide -= 1

        st.session_state.sas_canvas_revision += 1

        st.rerun()


with nav_center:

    selected_slide = st.slider(
        "Slide",
        min_value=1,
        max_value=total_slides,
        value=(
            st.session_state.sas_current_slide + 1
        ),
        key="sas_slide_selector",
    )

    new_slide = selected_slide - 1

    if (
        new_slide !=
        st.session_state.sas_current_slide
    ):

        st.session_state.sas_current_slide = new_slide

        st.session_state.sas_canvas_revision += 1

        st.rerun()


with nav_right:

    if st.button(
        "→",
        key="sas_next_slide",
        use_container_width=True,
        disabled=(
            st.session_state.sas_current_slide
            >= total_slides - 1
        ),
    ):

        st.session_state.sas_current_slide += 1

        st.session_state.sas_canvas_revision += 1

        st.rerun()


slide_index = (
    st.session_state.sas_current_slide
)


st.markdown(
    f"### {t['sub']} Slide {slide_index + 1} / {total_slides}"
)


# =========================================================
# 17. EDITOR + NOTES
# =========================================================

editor_column, notes_column = st.columns(
    [3, 2]
)


# =========================================================
# 18. SLIDE EDITOR
# =========================================================

with editor_column:

    st.markdown(
        f"#### 🖼️ Edit langsung di slide {t['draw']}"
    )

    current_slide = (
        st.session_state
        .sas_slides[
            slide_index
        ]
    )

    canvas_width, canvas_height = (
        get_canvas_size(
            current_slide
        )
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


    # -----------------------------------------------------
    # IMPORTANT:
    # background_image = SLIDE
    #
    # Jadi slide tidak dibuat sebagai st.image()
    # terpisah. Slide langsung menjadi background
    # dari area yang bisa dicoret.
    # -----------------------------------------------------

    canvas_result = st_canvas(

        fill_color=(
            "rgba(255,255,255,0)"
        ),

        stroke_width=stroke_width,

        stroke_color=stroke_color,

        background_image=resized_slide,

        height=canvas_height,

        width=canvas_width,

        drawing_mode=drawing_mode,

        display_toolbar=True,

        update_streamlit=True,

        key=(
            "sas_canvas_"
            f"{slide_index}_"
            f"{st.session_state.sas_canvas_revision}"
        ),
    )


    # -----------------------------------------------------
    # SAVE DRAWING
    # -----------------------------------------------------

    if canvas_result.json_data is not None:

        new_data = (
            canvas_result.json_data
        )

        old_data = (
            st.session_state
            .sas_drawings
            .get(slide_index)
        )

        if new_data != old_data:

            if old_data is not None:

                history = (
                    st.session_state
                    .sas_history
                    .setdefault(
                        slide_index,
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

            st.session_state.sas_drawings[
                slide_index
            ] = new_data


    # -----------------------------------------------------
    # EDIT CONTROLS
    # -----------------------------------------------------

    st.write("")

    edit1, edit2, edit3 = st.columns(3)


    with edit1:

        if st.button(
            "↩️ Undo",
            key="sas_undo",
            use_container_width=True,
        ):

            history = (
                st.session_state
                .sas_history
                .get(
                    slide_index,
                    [],
                )
            )

            if history:

                previous = history.pop()

                st.session_state.sas_drawings[
                    slide_index
                ] = previous

                st.session_state.sas_canvas_revision += 1

                st.rerun()

            else:

                st.toast(
                    "Belum ada aksi yang bisa di-undo."
                )


    with edit2:

        if st.button(
            "🗑️ Hapus Semua",
            key="sas_clear",
            use_container_width=True,
        ):

            st.session_state.sas_drawings[
                slide_index
            ] = None

            st.session_state.sas_history[
                slide_index
            ] = []

            st.session_state.sas_canvas_revision += 1

            st.rerun()


    with edit3:

        if st.button(
            "🔄 Reset Slide",
            key="sas_reset",
            use_container_width=True,
        ):

            st.session_state.sas_drawings[
                slide_index
            ] = None

            st.session_state.sas_history[
                slide_index
            ] = []

            st.session_state.sas_canvas_revision += 1

            st.rerun()


    st.caption(
        "💡 Pilih 🔤 Text lalu klik di slide untuk menambahkan teks."
    )


# =========================================================
# 19. NOTES
# =========================================================

with notes_column:

    st.subheader(
        f"{t['note']} Mini Notes"
    )

    existing_mini = (
        st.session_state
        .sas_mini_notes
        .get(
            slide_index,
            "",
        )
    )

    mini_note = st.text_input(
        "Kata kunci / rumus:",
        value=existing_mini,
        key=f"sas_mini_{slide_index}",
        placeholder=(
            "Contoh: BEP = FC / (P - VC)"
        ),
    )

    st.session_state.sas_mini_notes[
        slide_index
    ] = mini_note


    st.subheader(
        "📝 Catatan Utama"
    )

    existing_note = (
        st.session_state
        .sas_notes
        .get(
            slide_index,
            "",
        )
    )

    main_note = st.text_area(
        "Penjelasan materi:",
        value=existing_note,
        height=280,
        key=f"sas_note_{slide_index}",
        placeholder=(
            "Tulis penjelasan materi "
            "dengan bahasa kamu sendiri..."
        ),
    )

    st.session_state.sas_notes[
        slide_index
    ] = main_note


    st.info(
        "✨ Notes otomatis mengikuti slide yang sedang kamu buka."
    )


# =========================================================
# 20. EXPORT
# =========================================================

st.divider()

st.subheader(
    f"📤 Simpan Materi {t['sub']}"
)

export_pdf_col, export_drive_col = st.columns(2)


# =========================================================
# PDF
# =========================================================

with export_pdf_col:

    if st.button(
        "📄 Generate PDF",
        key="sas_generate_pdf",
        use_container_width=True,
    ):

        with st.spinner(
            "Menyusun PDF..."
        ):

            pdf_file = create_pdf()

            st.download_button(
                "⬇️ Unduh Hasil PDF",
                data=pdf_file,
                file_name=(
                    "Hasil_Edit_Slide.pdf"
                ),
                mime="application/pdf",
                key="sas_download_pdf",
                use_container_width=True,
            )


# =========================================================
# GOOGLE DRIVE
# =========================================================

with export_drive_col:

    if st.button(
        f"{t['cloud']} Simpan ke Google Drive",
        key="sas_save_drive",
        use_container_width=True,
    ):

        with st.spinner(
            "Mengunggah ke Google Drive..."
        ):

            pdf_bytes = (
                create_pdf()
                .getvalue()
            )

            file_id = upload_to_drive(
                pdf_bytes
            )

            if file_id:

                st.success(
                    "Berhasil disimpan ke Google Drive! 🎉"
                )
