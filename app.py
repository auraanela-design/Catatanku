import io
import copy
import html
import base64

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

DEFAULT_STATE = {
    "sas_slides": [],
    "sas_notes": {},
    "sas_mini_notes": {},
    "sas_drawings": {},
    "sas_history": {},

    "sas_current_slide": 0,

    # Dipakai untuk memaksa canvas dibuat ulang
    # hanya ketika diperlukan.
    "sas_canvas_reset": 0,

    # Zoom tampilan.
    "sas_zoom": 70,

    # Menandai bahwa canvas baru saja di-reset.
    "sas_ignore_canvas_once": False,

    # PDF terakhir.
    "sas_loaded_filename": "",
}


for key, default in DEFAULT_STATE.items():

    if key not in st.session_state:
        st.session_state[key] = default


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
        index=0,
        key="sas_theme_v6",
    )


theme = THEMES[selected_theme]


# ============================================================
# CSS
# ============================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: {theme['card']};
    }}

    [data-testid="stSidebar"] {{
        background-color: {theme['bg']};
    }}

    h1, h2, h3 {{
        color: {theme['text']} !important;
    }}

    .stButton > button {{
        border-radius: 12px !important;
        font-weight: 600 !important;
    }}

    .study-badge {{
        display: inline-block;
        padding: 5px 13px;
        border-radius: 20px;
        background-color: {theme['bg']};
        border: 1px solid {theme['border']};
        color: {theme['text']};
        font-weight: 600;
        margin-bottom: 8px;
    }}

    .zoom-box {{
        padding: 10px 15px;
        border-radius: 14px;
        border: 1px solid {theme['border']};
        background-color: {theme['bg']};
        margin-bottom: 15px;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def hex_to_rgba(hex_color, alpha=0.4):

    hex_color = hex_color.replace("#", "")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return f"rgba({r},{g},{b},{alpha})"


# ============================================================
# PDF → IMAGES
# ============================================================

def pdf_to_images(pdf_bytes):

    images = []

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf",
    )

    try:

        for page in document:

            pix = page.get_pixmap(
                dpi=150,
                alpha=False,
            )

            image = Image.frombytes(
                "RGB",
                [
                    pix.width,
                    pix.height,
                ],
                pix.samples,
            )

            images.append(image)

    finally:

        document.close()

    return images


# ============================================================
# IMAGE → DATA URI
# ============================================================

def image_to_data_uri(image):

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    return "data:image/png;base64," + encoded


# ============================================================
# CANVAS SIZE
# ============================================================

def get_canvas_size(
    image,
    zoom,
):

    base_width = 900

    canvas_width = int(
        base_width * zoom / 100
    )

    ratio = (
        image.height /
        image.width
    )

    canvas_height = int(
        canvas_width * ratio
    )

    return canvas_width, canvas_height


# ============================================================
# CREATE CANVAS
# ============================================================

def create_canvas(
    slide,
    canvas_width,
    canvas_height,
    annotations=None,
):

    resized = slide.resize(
        (
            canvas_width,
            canvas_height,
        ),
        Image.Resampling.LANCZOS,
    )

    image_uri = image_to_data_uri(
        resized
    )

    background = {

        "type": "image",

        "version": "4.4.0",

        "originX": "left",
        "originY": "top",

        "left": 0,
        "top": 0,

        "width": canvas_width,
        "height": canvas_height,

        "scaleX": 1,
        "scaleY": 1,

        "angle": 0,

        "opacity": 1,

        "selectable": False,
        "evented": False,

        "src": image_uri,
    }


    objects = [background]


    if annotations:

        try:

            saved_objects = annotations.get(
                "objects",
                [],
            )

            for obj in saved_objects:

                if obj.get("type") != "image":

                    objects.append(
                        copy.deepcopy(obj)
                    )

        except Exception:

            pass


    return {
        "version": "4.4.0",
        "objects": objects,
    }


# ============================================================
# ONLY ANNOTATIONS
# ============================================================

def annotations_only(data):

    if not data:
        return None

    cleaned = copy.deepcopy(data)

    objects = cleaned.get(
        "objects",
        [],
    )

    cleaned["objects"] = [
        obj
        for obj in objects
        if obj.get("type") != "image"
    ]

    return cleaned


# ============================================================
# CHECK EMPTY
# ============================================================

def annotations_are_empty(data):

    if not data:
        return True

    objects = data.get(
        "objects",
        [],
    )

    return len(objects) == 0


# ============================================================
# RENDER ANNOTATIONS
# ============================================================

def render_annotations(
    background,
    annotation_data,
):

    result = background.copy().convert(
        "RGBA"
    )

    if not annotation_data:
        return result.convert("RGB")

    objects = annotation_data.get(
        "objects",
        [],
    )

    if not objects:
        return result.convert("RGB")

    canvas_width = annotation_data.get(
        "width",
        900,
    )

    if not canvas_width:
        canvas_width = 900

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


        # ====================================================
        # PATH
        # ====================================================

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

                if command_name in ["M", "L"]:

                    try:

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

                    except Exception:
                        pass

                elif command_name == "Q":

                    if len(command) >= 5:

                        try:

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

                        except Exception:
                            pass


            if len(points) >= 2:

                stroke = obj.get(
                    "stroke",
                    "#FF0000",
                )

                try:

                    width = max(
                        1,
                        int(
                            float(
                                obj.get(
                                    "strokeWidth",
                                    3,
                                )
                            )
                            * scale
                        ),
                    )

                except Exception:

                    width = 3


                draw.line(
                    points,
                    fill=stroke,
                    width=width,
                    joint="curve",
                )


        # ====================================================
        # RECTANGLE
        # ====================================================

        elif obj_type == "rect":

            try:

                left = (
                    float(
                        obj.get(
                            "left",
                            0,
                        )
                    )
                    * scale
                )

                top = (
                    float(
                        obj.get(
                            "top",
                            0,
                        )
                    )
                    * scale
                )

                width = (
                    float(
                        obj.get(
                            "width",
                            0,
                        )
                    )
                    * scale
                )

                height = (
                    float(
                        obj.get(
                            "height",
                            0,
                        )
                    )
                    * scale
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
                        )
                        * scale
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

            except Exception:

                pass


        # ====================================================
        # CIRCLE
        # ====================================================

        elif obj_type == "circle":

            try:

                left = (
                    float(
                        obj.get(
                            "left",
                            0,
                        )
                    )
                    * scale
                )

                top = (
                    float(
                        obj.get(
                            "top",
                            0,
                        )
                    )
                    * scale
                )

                radius = (
                    float(
                        obj.get(
                            "radius",
                            0,
                        )
                    )
                    * scale
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
                        )
                        * scale
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

            except Exception:

                pass


        # ====================================================
        # LINE
        # ====================================================

        elif obj_type == "line":

            try:

                x1 = (
                    float(
                        obj.get(
                            "x1",
                            0,
                        )
                    )
                    * scale
                )

                y1 = (
                    float(
                        obj.get(
                            "y1",
                            0,
                        )
                    )
                    * scale
                )

                x2 = (
                    float(
                        obj.get(
                            "x2",
                            0,
                        )
                    )
                    * scale
                )

                y2 = (
                    float(
                        obj.get(
                            "y2",
                            0,
                        )
                    )
                    * scale
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
                        )
                        * scale
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

            except Exception:

                pass


        # ====================================================
        # TEXT
        # ====================================================

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

            try:

                left = (
                    float(
                        obj.get(
                            "left",
                            0,
                        )
                    )
                    * scale
                )

                top = (
                    float(
                        obj.get(
                            "top",
                            0,
                        )
                    )
                    * scale
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
                        )
                        * scale
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

            except Exception:

                pass


    return Image.alpha_composite(
        result,
        overlay,
    ).convert("RGB")


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

    title_style = ParagraphStyle(
        "SlideTitle",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
    )

    note_style = ParagraphStyle(
        "StudyNote",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )

    story = []

    for index, slide in enumerate(
        st.session_state.sas_slides
    ):

        annotations = (
            st.session_state
            .sas_drawings
            .get(index)
        )

        final_slide = render_annotations(
            slide,
            annotations,
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

        ratio = (
            final_slide.height /
            final_slide.width
        )

        max_height = (
            max_width * ratio
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

                if line.strip():

                    story.append(
                        Paragraph(
                            html.escape(line),
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

        if index < len(
            st.session_state.sas_slides
        ) - 1:

            story.append(
                PageBreak()
            )

    document.build(story)

    output.seek(0)

    return output


# ============================================================
# GOOGLE DRIVE
# ============================================================

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


# ============================================================
# HEADER
# ============================================================

st.markdown(
    f"""
    <div class="study-badge">
        {theme['main']} My Personal Study Space
    </div>
    """,
    unsafe_allow_html=True,
)

st.title(
    f"𐙚 Slide & Scribble {theme['main']}"
)

st.caption(
    "Upload materi → coret langsung di atas slide → "
    "tambahkan notes → export."
)


# ============================================================
# SIDEBAR — UPLOAD
# ============================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{theme['file']} Materi Kuliah"
    )

    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        key="sas_pdf_upload_v6",
    )

    if uploaded_file:

        if st.button(
            "🔄 Muat Materi Baru",
            key="sas_load_pdf_v6",
            use_container_width=True,
        ):

            with st.spinner(
                "Membaca slide..."
            ):

                try:

                    pdf_bytes = (
                        uploaded_file.getvalue()
                    )

                    slides = pdf_to_images(
                        pdf_bytes
                    )

                    if not slides:

                        st.error(
                            "PDF tidak memiliki halaman."
                        )

                    else:

                        st.session_state.sas_slides = slides

                        st.session_state.sas_notes = {}

                        st.session_state.sas_mini_notes = {}

                        st.session_state.sas_drawings = {}

                        st.session_state.sas_history = {}

                        st.session_state.sas_current_slide = 0

                        st.session_state.sas_canvas_reset += 1

                        st.session_state.sas_ignore_canvas_once = True

                        st.session_state.sas_loaded_filename = (
                            uploaded_file.name
                        )

                        st.success(
                            f"{len(slides)} slide berhasil dimuat! 🎉"
                        )

                        st.rerun()

                except Exception as error:

                    st.error(
                        f"Gagal membaca PDF: {error}"
                    )


# ============================================================
# SIDEBAR — TOOLS
# ============================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{theme['draw']} Drawing Tools"
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
        key="sas_tool_v6",
    )

    drawing_mode = tool_options[
        selected_tool
    ]


    # ========================================================
    # PEN
    # ========================================================

    if drawing_mode == "freedraw":

        pen_type = st.radio(
            "Jenis:",
            [
                "✏️ Pen",
                "🖍️ Stabilo",
            ],
            key="sas_pen_type_v6",
        )

    else:

        pen_type = "✏️ Pen"


    # ========================================================
    # HIGHLIGHTER
    # ========================================================

    if pen_type == "🖍️ Stabilo":

        selected_color = st.radio(
            "Warna stabilo:",
            [
                "🟡 Kuning",
                "💖 Pink",
                "🟢 Mint",
                "🩵 Biru",
                "🎨 Custom",
            ],
            key="sas_highlighter_v6",
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

            custom_color = st.color_picker(
                "Warna:",
                "#FFFF00",
                key="sas_custom_highlighter_v6",
            )

            stroke_color = hex_to_rgba(
                custom_color,
                0.40,
            )

        else:

            stroke_color = highlighter_colors[
                selected_color
            ]

        default_width = 16


    # ========================================================
    # PEN NORMAL
    # ========================================================

    else:

        selected_color = st.radio(
            "Warna:",
            [
                "🔴 Merah",
                "🔵 Biru",
                "🟢 Hijau",
                "⚫ Hitam",
                "🎨 Custom",
            ],
            key="sas_pen_color_v6",
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
                "Warna:",
                "#FF0000",
                key="sas_custom_pen_v6",
            )

        else:

            stroke_color = pen_colors[
                selected_color
            ]

        default_width = 3


    stroke_width = st.slider(
        "Ukuran coretan:",
        1,
        30,
        default_width,
        key="sas_stroke_width_v6",
    )


# ============================================================
# EMPTY STATE
# ============================================================

if not st.session_state.sas_slides:

    st.info(
        f"""
        {theme['file']} **Belum ada materi.**

        Upload PDF dari sidebar untuk mulai
        menggunakan **Slide & Scribble** {theme['sub']}.
        """
    )

    st.stop()


# ============================================================
# TOTAL SLIDES
# ============================================================

total_slides = len(
    st.session_state.sas_slides
)


# ============================================================
# SAFE SLIDE INDEX
# ============================================================

if st.session_state.sas_current_slide < 0:

    st.session_state.sas_current_slide = 0


if (
    st.session_state.sas_current_slide
    >= total_slides
):

    st.session_state.sas_current_slide = (
        total_slides - 1
    )


# ============================================================
# NAVIGATION
# ============================================================

nav_left, nav_center, nav_right = st.columns(
    [1, 5, 1]
)


with nav_left:

    if st.button(
        "←",
        key="sas_prev_v6",
        use_container_width=True,
        disabled=(
            st.session_state.sas_current_slide == 0
        ),
    ):

        st.session_state.sas_current_slide -= 1

        st.rerun()


with nav_center:

    slide_number = st.slider(
        "Slide",
        min_value=1,
        max_value=total_slides,
        value=(
            st.session_state.sas_current_slide
            + 1
        ),
        key="sas_slide_number_v6",
    )

    if (
        slide_number - 1
        != st.session_state.sas_current_slide
    ):

        st.session_state.sas_current_slide = (
            slide_number - 1
        )

        st.rerun()


with nav_right:

    if st.button(
        "→",
        key="sas_next_v6",
        use_container_width=True,
        disabled=(
            st.session_state.sas_current_slide
            >= total_slides - 1
        ),
    ):

        st.session_state.sas_current_slide += 1

        st.rerun()


# ============================================================
# CURRENT SLIDE
# ============================================================

slide_index = (
    st.session_state.sas_current_slide
)

current_slide = (
    st.session_state
    .sas_slides[
        slide_index
    ]
)


st.markdown(
    f"### {theme['sub']} Slide {slide_index + 1} / {total_slides}"
)


# ============================================================
# ZOOM CONTROL
# ============================================================

zoom_col1, zoom_col2, zoom_col3 = st.columns(
    [2, 4, 2]
)


with zoom_col1:

    if st.button(
        "➖ Kecilkan",
        key="sas_zoom_minus_v6",
        use_container_width=True,
    ):

        st.session_state.sas_zoom = max(
            40,
            st.session_state.sas_zoom - 10,
        )

        st.rerun()


with zoom_col2:

    zoom = st.slider(
        "🔍 Ukuran Slide",
        min_value=40,
        max_value=120,
        value=st.session_state.sas_zoom,
        step=10,
        format="%d%%",
        key="sas_zoom_main_v6",
    )

    st.session_state.sas_zoom = zoom


with zoom_col3:

    if st.button(
        "➕ Besarkan",
        key="sas_zoom_plus_v6",
        use_container_width=True,
    ):

        st.session_state.sas_zoom = min(
            120,
            st.session_state.sas_zoom + 10,
        )

        st.rerun()


st.caption(
    f"Ukuran tampilan slide: **{st.session_state.sas_zoom}%**"
)


# ============================================================
# EDITOR + NOTES
# ============================================================

editor_col, notes_col = st.columns(
    [3, 2]
)


# ============================================================
# EDITOR
# ============================================================

with editor_col:

    st.markdown(
        f"#### 🖼️ Edit langsung di slide {theme['draw']}"
    )


    canvas_width, canvas_height = (
        get_canvas_size(
            current_slide,
            st.session_state.sas_zoom,
        )
    )


    saved_annotations = (
        st.session_state
        .sas_drawings
        .get(slide_index)
    )


    initial_canvas = create_canvas(
        current_slide,
        canvas_width,
        canvas_height,
        saved_annotations,
    )


    # ========================================================
    # CANVAS KEY
    # ========================================================

    canvas_key = (
        f"sas_canvas_"
        f"{slide_index}_"
        f"{st.session_state.sas_canvas_reset}"
    )


    canvas_result = st_canvas(

        fill_color="rgba(255,255,255,0)",

        stroke_width=stroke_width,

        stroke_color=stroke_color,

        background_color="rgba(0,0,0,0)",

        initial_drawing=initial_canvas,

        height=canvas_height,

        width=canvas_width,

        drawing_mode=drawing_mode,

        display_toolbar=True,

        update_streamlit=True,

        key=canvas_key,
    )


    # ========================================================
    # SAVE CANVAS
    # ========================================================

    if canvas_result is not None:

        canvas_json = canvas_result.json_data


        if canvas_json is not None:

            new_annotations = annotations_only(
                canvas_json
            )


            # =================================================
            # IMPORTANT
            #
            # Jika baru saja reset canvas,
            # jangan biarkan state canvas lama
            # hidup kembali.
            # =================================================

            if st.session_state.sas_ignore_canvas_once:

                st.session_state.sas_ignore_canvas_once = False

            else:

                old_annotations = (
                    st.session_state
                    .sas_drawings
                    .get(slide_index)
                )


                if new_annotations != old_annotations:

                    # Jangan masukkan None / kosong
                    # sebagai history yang tidak berguna.

                    if old_annotations:

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
                                old_annotations
                            )
                        )


                        if len(history) > 30:

                            history.pop(0)


                    # Kalau kosong,
                    # simpan None secara eksplisit.

                    if annotations_are_empty(
                        new_annotations
                    ):

                        st.session_state.sas_drawings[
                            slide_index
                        ] = None

                    else:

                        st.session_state.sas_drawings[
                            slide_index
                        ] = new_annotations


    # ========================================================
    # ACTION BUTTONS
    # ========================================================

    st.write("")


    action1, action2, action3 = st.columns(3)


    # ========================================================
    # UNDO
    # ========================================================

    with action1:

        if st.button(
            "↩️ Undo",
            key="sas_undo_v6",
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


                st.session_state.sas_ignore_canvas_once = True

                st.session_state.sas_canvas_reset += 1

                st.rerun()

            else:

                st.toast(
                    "Belum ada coretan yang bisa di-undo."
                )


    # ========================================================
    # CLEAR ALL
    # ========================================================

    with action2:

        if st.button(
            "🗑️ Hapus Semua",
            key="sas_clear_v6",
            use_container_width=True,
        ):

            current_annotations = (
                st.session_state
                .sas_drawings
                .get(slide_index)
            )


            # Simpan keadaan sebelum dihapus
            # untuk kemungkinan Undo.

            if current_annotations:

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
                        current_annotations
                    )
                )


                if len(history) > 30:

                    history.pop(0)


            # =================================================
            # INI YANG PALING PENTING:
            #
            # State annotation DIKOSONGKAN.
            # =================================================

            st.session_state.sas_drawings[
                slide_index
            ] = None


            # =================================================
            # Canvas baru tidak boleh menyimpan
            # object lama.
            # =================================================

            st.session_state.sas_ignore_canvas_once = True

            st.session_state.sas_canvas_reset += 1

            st.rerun()


    # ========================================================
    # RESET
    # ========================================================

    with action3:

        if st.button(
            "🔄 Reset Slide",
            key="sas_reset_v6",
            use_container_width=True,
        ):

            st.session_state.sas_drawings[
                slide_index
            ] = None


            st.session_state.sas_history[
                slide_index
            ] = []


            st.session_state.sas_ignore_canvas_once = True

            st.session_state.sas_canvas_reset += 1

            st.rerun()


    st.caption(
        "💡 Gunakan 🔤 Text untuk menambahkan tulisan. "
        "🗑️ Hapus Semua menghapus semua coretan pada slide ini."
    )


# ============================================================
# NOTES
# ============================================================

with notes_col:

    st.subheader(
        f"{theme['note']} Mini Notes"
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
        key=f"sas_mini_note_v6_{slide_index}",
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
        key=f"sas_main_note_v6_{slide_index}",
        placeholder=(
            "Tulis penjelasan materi "
            "dengan bahasa kamu sendiri..."
        ),
    )


    st.session_state.sas_notes[
        slide_index
    ] = main_note


    st.info(
        "✨ Notes otomatis mengikuti slide yang sedang dibuka."
    )


# ============================================================
# EXPORT
# ============================================================

st.divider()


st.subheader(
    f"📤 Simpan Materi {theme['sub']}"
)


pdf_col, drive_col = st.columns(2)


# ============================================================
# PDF
# ============================================================

with pdf_col:

    if st.button(
        "📄 Generate PDF",
        key="sas_generate_pdf_v6",
        use_container_width=True,
    ):

        with st.spinner(
            "Menyusun PDF..."
        ):

            try:

                pdf_file = create_pdf()

                st.download_button(
                    "⬇️ Unduh Hasil PDF",
                    data=pdf_file.getvalue(),
                    file_name="Hasil_Edit_Slide.pdf",
                    mime="application/pdf",
                    key="sas_download_pdf_v6",
                    use_container_width=True,
                )

            except Exception as error:

                st.error(
                    f"Gagal membuat PDF: {error}"
                )


# ============================================================
# GOOGLE DRIVE
# ============================================================

with drive_col:

    if st.button(
        f"{theme['cloud']} Simpan ke Google Drive",
        key="sas_save_drive_v6",
        use_container_width=True,
    ):

        with st.spinner(
            "Mengunggah..."
        ):

            try:

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

            except Exception as error:

                st.error(
                    f"Gagal menyimpan ke Google Drive: {error}"
                )
