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

if "sas_zoom" not in st.session_state:
    st.session_state.sas_zoom = 70

if "sas_canvas_version" not in st.session_state:
    st.session_state.sas_canvas_version = 0

if "sas_loaded_filename" not in st.session_state:
    st.session_state.sas_loaded_filename = ""


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
# THEME
# ============================================================

with st.sidebar:

    st.header("🎨 Pilih Tema")

    selected_theme = st.selectbox(
        "Suasana tampilan:",
        list(THEMES.keys()),
        key="sas_theme_selector_v7",
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

    .study-badge {{
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        background-color: {theme['bg']};
        border: 1px solid {theme['border']};
        color: {theme['text']};
        font-weight: 600;
        margin-bottom: 8px;
    }}

    .slide-info {{
        padding: 10px 14px;
        border-radius: 12px;
        background-color: {theme['bg']};
        border: 1px solid {theme['border']};
        margin-bottom: 10px;
        text-align: center;
        color: {theme['text']};
        font-weight: 600;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PDF → PIL
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
                (
                    pix.width,
                    pix.height,
                ),
                pix.samples,
            )

            images.append(image)

    finally:

        document.close()

    return images


# ============================================================
# CANVAS SIZE
# ============================================================

def calculate_canvas_size(
    image,
    zoom,
):

    base_width = 900

    width = int(
        base_width * zoom / 100
    )

    ratio = (
        image.height /
        image.width
    )

    height = int(
        width * ratio
    )

    return width, height


# ============================================================
# RESIZE IMAGE
# ============================================================

def resize_slide(
    image,
    width,
    height,
):

    return image.resize(
        (
            width,
            height,
        ),
        Image.Resampling.LANCZOS,
    )


# ============================================================
# CLEAN DRAWING DATA
# ============================================================

def clean_drawing(data):

    if not data:
        return None

    cleaned = copy.deepcopy(data)

    objects = cleaned.get(
        "objects",
        [],
    )

    # Hanya annotation.
    cleaned["objects"] = [
        obj
        for obj in objects
        if obj.get("type") != "image"
    ]

    if not cleaned["objects"]:
        return None

    return cleaned


# ============================================================
# DRAWING EMPTY?
# ============================================================

def drawing_empty(data):

    if not data:
        return True

    objects = data.get(
        "objects",
        [],
    )

    return len(objects) == 0


# ============================================================
# RENDER DRAWINGS KE SLIDE
# ============================================================

def render_annotations(
    background,
    drawing,
):

    result = background.copy().convert(
        "RGBA"
    )

    if not drawing:
        return result.convert("RGB")

    objects = drawing.get(
        "objects",
        [],
    )

    if not objects:
        return result.convert("RGB")

    canvas_width = drawing.get(
        "canvas_width",
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


    # ========================================================
    # PATH
    # ========================================================

    for obj in objects:

        obj_type = obj.get(
            "type",
            "",
        )

        if obj_type == "path":

            path = obj.get(
                "path",
                [],
            )

            points = []

            for command in path:

                if len(command) < 3:
                    continue

                command_type = command[0]

                try:

                    if command_type in (
                        "M",
                        "L",
                    ):

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

                    elif (
                        command_type == "Q"
                        and len(command) >= 5
                    ):

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
                    continue


            if len(points) >= 2:

                stroke = obj.get(
                    "stroke",
                    "#FF0000",
                )

                try:

                    width = int(
                        float(
                            obj.get(
                                "strokeWidth",
                                3,
                            )
                        )
                        * scale
                    )

                except Exception:

                    width = 3

                width = max(
                    1,
                    width,
                )

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

        elif obj_type in (
            "text",
            "textbox",
            "i-text",
        ):

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
# PDF EXPORT
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

        drawing = (
            st.session_state
            .sas_drawings
            .get(index)
        )

        final_image = render_annotations(
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
                f"<b>Slide {index + 1}</b>",
                title_style,
            )
        )


        max_width = 500

        ratio = (
            final_image.height /
            final_image.width
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
            Spacer(
                1,
                12,
            )
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

            story.append(
                Paragraph(
                    (
                        "<b>📌 Mini Notes</b><br/>"
                        +
                        html.escape(
                            mini
                        ).replace(
                            "\n",
                            "<br/>",
                        )
                    ),
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

            for line in note.split(
                "\n"
            ):

                if line.strip():

                    story.append(
                        Paragraph(
                            html.escape(
                                line
                            ),
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


        if index < (
            len(
                st.session_state
                .sas_slides
            ) - 1
        ):

            story.append(
                PageBreak()
            )


    document.build(
        story
    )

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
            "parents": [
                folder_id
            ],
        }

        media = MediaIoBaseUpload(
            io.BytesIO(
                file_bytes
            ),
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

        return uploaded.get(
            "id"
        )

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
    "Upload materi → coret → tulis → buat notes → export."
)


# ============================================================
# UPLOAD PDF
# ============================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{theme['file']} Materi Kuliah"
    )

    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        key="sas_pdf_upload_v7",
    )


    if uploaded_file:

        if st.button(
            "📥 Muat Materi",
            key="sas_load_pdf_v7",
            use_container_width=True,
        ):

            with st.spinner(
                "Membaca materi..."
            ):

                try:

                    slides = pdf_to_images(
                        uploaded_file.getvalue()
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

                        st.session_state.sas_zoom = 70

                        st.session_state.sas_canvas_version += 1

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
# DRAWING TOOL
# ============================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{theme['draw']} Drawing Tools"
    )


    tools = {

        "✏️ Pen": "freedraw",

        "🖍️ Stabilo": "freedraw",

        "🔤 Text": "text",

        "📏 Line": "line",

        "🔲 Rectangle": "rect",

        "⚪ Circle": "circle",

        "✋ Select": "transform",

    }


    selected_tool = st.selectbox(
        "Alat:",
        list(tools.keys()),
        key="sas_drawing_tool_v7",
    )


    drawing_mode = tools[
        selected_tool
    ]


    # ========================================================
    # NORMAL PEN
    # ========================================================

    if selected_tool == "✏️ Pen":

        stroke_color = st.color_picker(
            "Warna pen:",
            "#FF0000",
            key="sas_pen_color_v7",
        )

        stroke_width = st.slider(
            "Ukuran pen:",
            1,
            15,
            3,
            key="sas_pen_width_v7",
        )


    # ========================================================
    # HIGHLIGHTER
    # ========================================================

    elif selected_tool == "🖍️ Stabilo":

        highlighter = st.selectbox(
            "Warna stabilo:",
            [
                "Kuning",
                "Pink",
                "Hijau",
                "Biru",
            ],
            key="sas_highlighter_v7",
        )


        highlighter_colors = {

            "Kuning":
                "rgba(255,235,59,0.40)",

            "Pink":
                "rgba(255,105,180,0.40)",

            "Hijau":
                "rgba(144,238,144,0.40)",

            "Biru":
                "rgba(135,206,250,0.40)",
        }


        stroke_color = (
            highlighter_colors[
                highlighter
            ]
        )

        stroke_width = st.slider(
            "Ukuran stabilo:",
            8,
            30,
            18,
            key="sas_highlighter_width_v7",
        )


    else:

        stroke_color = st.color_picker(
            "Warna:",
            "#FF0000",
            key="sas_shape_color_v7",
        )

        stroke_width = st.slider(
            "Ketebalan:",
            1,
            15,
            3,
            key="sas_shape_width_v7",
        )


# ============================================================
# EMPTY STATE
# ============================================================

if not st.session_state.sas_slides:

    st.info(
        f"""
        {theme['file']} **Belum ada materi.**

        Upload PDF dari sidebar untuk mulai menggunakan
        **Slide & Scribble** {theme['sub']}.
        """
    )

    st.stop()


# ============================================================
# SLIDE INDEX
# ============================================================

total_slides = len(
    st.session_state.sas_slides
)


if (
    st.session_state.sas_current_slide
    >= total_slides
):

    st.session_state.sas_current_slide = (
        total_slides - 1
    )


if (
    st.session_state.sas_current_slide
    < 0
):

    st.session_state.sas_current_slide = 0


slide_index = (
    st.session_state.sas_current_slide
)


# ============================================================
# NAVIGATION
# ============================================================

nav1, nav2, nav3 = st.columns(
    [1, 5, 1]
)


with nav1:

    if st.button(
        "⬅️",
        key="sas_previous_v7",
        use_container_width=True,
        disabled=(
            slide_index == 0
        ),
    ):

        st.session_state.sas_current_slide -= 1

        # Canvas dibuat ulang untuk slide baru.
        st.session_state.sas_canvas_version += 1

        st.rerun()


with nav2:

    selected_slide = st.slider(
        "Slide",
        1,
        total_slides,
        slide_index + 1,
        key="sas_slide_navigation_v7",
    )


    if (
        selected_slide - 1
        != slide_index
    ):

        st.session_state.sas_current_slide = (
            selected_slide - 1
        )

        st.session_state.sas_canvas_version += 1

        st.rerun()


with nav3:

    if st.button(
        "➡️",
        key="sas_next_v7",
        use_container_width=True,
        disabled=(
            slide_index
            >= total_slides - 1
        ),
    ):

        st.session_state.sas_current_slide += 1

        st.session_state.sas_canvas_version += 1

        st.rerun()


# ============================================================
# CURRENT SLIDE
# ============================================================

current_slide = (
    st.session_state
    .sas_slides[
        slide_index
    ]
)


st.markdown(
    f"""
    <div class="slide-info">
        {theme['sub']} Slide {slide_index + 1} / {total_slides}
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ZOOM
# ============================================================

zoom1, zoom2, zoom3 = st.columns(
    [1, 4, 1]
)


with zoom1:

    if st.button(
        "➖",
        key="sas_zoom_minus_v7",
        use_container_width=True,
    ):

        st.session_state.sas_zoom = max(
            40,
            st.session_state.sas_zoom - 10,
        )

        st.session_state.sas_canvas_version += 1

        st.rerun()


with zoom2:

    zoom_value = st.slider(
        "🔍 Ukuran Slide",
        min_value=40,
        max_value=120,
        value=st.session_state.sas_zoom,
        step=10,
        format="%d%%",
        key="sas_zoom_slider_v7",
    )


    if zoom_value != st.session_state.sas_zoom:

        st.session_state.sas_zoom = zoom_value

        st.session_state.sas_canvas_version += 1

        st.rerun()


with zoom3:

    if st.button(
        "➕",
        key="sas_zoom_plus_v7",
        use_container_width=True,
    ):

        st.session_state.sas_zoom = min(
            120,
            st.session_state.sas_zoom + 10,
        )

        st.session_state.sas_canvas_version += 1

        st.rerun()


# ============================================================
# SIZE
# ============================================================

canvas_width, canvas_height = (
    calculate_canvas_size(
        current_slide,
        st.session_state.sas_zoom,
    )
)


# ============================================================
# EDITOR / NOTES
# ============================================================

editor_col, notes_col = st.columns(
    [3, 2]
)


# ============================================================
# SLIDE EDITOR
# ============================================================

with editor_col:

    st.markdown(
        f"#### 🖼️ Slide {slide_index + 1} {theme['draw']}"
    )


    st.caption(
        f"Ukuran tampilan: "
        f"**{canvas_width} × {canvas_height}px**"
    )


    # ========================================================
    # RESIZE BACKGROUND
    # ========================================================

    canvas_background = resize_slide(
        current_slide,
        canvas_width,
        canvas_height,
    )


    # ========================================================
    # CURRENT DRAWING
    # ========================================================

    current_drawing = (
        st.session_state
        .sas_drawings
        .get(slide_index)
    )


    # ========================================================
    # IMPORTANT
    #
    # Background hanya berupa PIL image.
    # Tidak ada image object Fabric.
    # Tidak ada initial_drawing image object.
    # ========================================================

    canvas_key = (
        "sas_canvas_v7_"
        f"{slide_index}_"
        f"{st.session_state.sas_canvas_version}"
    )


    # ========================================================
    # CANVAS
    # ========================================================

    canvas_result = st_canvas(

        fill_color="rgba(255,255,255,0)",

        stroke_width=stroke_width,

        stroke_color=stroke_color,

        background_color="white",

        background_image=canvas_background,

        update_streamlit=True,

        height=canvas_height,

        width=canvas_width,

        drawing_mode=drawing_mode,

        display_toolbar=True,

        key=canvas_key,
    )


    # ========================================================
    # SAVE DRAWING
    # ========================================================

    if canvas_result is not None:

        canvas_json = canvas_result.json_data


        if canvas_json is not None:

            new_drawing = clean_drawing(
                canvas_json
            )


            # =================================================
            # Tambahkan ukuran canvas supaya koordinat
            # bisa dikonversi saat export.
            # =================================================

            if new_drawing:

                new_drawing[
                    "canvas_width"
                ] = canvas_width

                new_drawing[
                    "canvas_height"
                ] = canvas_height


            old_drawing = (
                st.session_state
                .sas_drawings
                .get(slide_index)
            )


            # =================================================
            # Jangan masukkan perubahan kosong
            # berulang-ulang ke history.
            # =================================================

            if new_drawing != old_drawing:

                if old_drawing:

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
                            old_drawing
                        )
                    )


                    # Maksimal 30 undo.

                    if len(history) > 30:

                        history.pop(0)


                st.session_state.sas_drawings[
                    slide_index
                ] = new_drawing


    # ========================================================
    # ACTION BUTTONS
    # ========================================================

    st.write("")


    undo_col, clear_col, reset_col = st.columns(
        3
    )


    # ========================================================
    # UNDO
    # ========================================================

    with undo_col:

        if st.button(
            "↩️ Undo",
            key="sas_undo_v7",
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


                # Paksa canvas dibuat ulang.
                st.session_state.sas_canvas_version += 1

                st.rerun()

            else:

                st.toast(
                    "Belum ada yang bisa di-undo."
                )


    # ========================================================
    # CLEAR
    # ========================================================

    with clear_col:

        if st.button(
            "🗑️ Hapus Semua",
            key="sas_clear_v7",
            use_container_width=True,
        ):

            existing = (
                st.session_state
                .sas_drawings
                .get(slide_index)
            )


            if existing:

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
                        existing
                    )
                )


                if len(history) > 30:

                    history.pop(0)


            # =================================================
            # BENAR-BENAR HAPUS.
            # =================================================

            st.session_state.sas_drawings[
                slide_index
            ] = None


            # =================================================
            # CANVAS BARU.
            #
            # Karena key berubah, canvas lama tidak digunakan.
            # =================================================

            st.session_state.sas_canvas_version += 1

            st.rerun()


    # ========================================================
    # RESET
    # ========================================================

    with reset_col:

        if st.button(
            "🔄 Reset",
            key="sas_reset_v7",
            use_container_width=True,
        ):

            st.session_state.sas_drawings[
                slide_index
            ] = None


            st.session_state.sas_history[
                slide_index
            ] = []


            st.session_state.sas_canvas_version += 1

            st.rerun()


    st.caption(
        "🗑️ Hapus Semua = bersihkan seluruh coretan slide ini. "
        "↩️ Undo = kembalikan coretan sebelumnya."
    )


# ============================================================
# NOTES
# ============================================================

with notes_col:

    st.subheader(
        f"{theme['note']} Mini Notes"
    )


    mini_value = (
        st.session_state
        .sas_mini_notes
        .get(
            slide_index,
            "",
        )
    )


    mini_note = st.text_input(
        "Kata kunci / rumus:",
        value=mini_value,
        key=f"sas_mini_note_v7_{slide_index}",
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


    note_value = (
        st.session_state
        .sas_notes
        .get(
            slide_index,
            "",
        )
    )


    main_note = st.text_area(
        "Penjelasan materi:",
        value=note_value,
        height=280,
        key=f"sas_main_note_v7_{slide_index}",
        placeholder=(
            "Tulis penjelasan materi "
            "dengan bahasa kamu sendiri..."
        ),
    )


    st.session_state.sas_notes[
        slide_index
    ] = main_note


    st.info(
        "✨ Catatan otomatis tersimpan berdasarkan slide."
    )


# ============================================================
# EXPORT
# ============================================================

st.divider()


st.subheader(
    f"📤 Simpan Materi {theme['sub']}"
)


pdf_col, drive_col = st.columns(
    2
)


# ============================================================
# PDF
# ============================================================

with pdf_col:

    if st.button(
        "📄 Generate PDF",
        key="sas_generate_pdf_v7",
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
                    key="sas_download_pdf_v7",
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
        key="sas_save_drive_v7",
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
