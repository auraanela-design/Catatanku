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
# Semua key diberi prefix sas_
# agar tidak bentrok dengan widget lama.
# ============================================================

DEFAULT_STATE = {
    "sas_slides": [],
    "sas_notes": {},
    "sas_mini_notes": {},
    "sas_drawings": {},
    "sas_history": {},
    "sas_current_slide": 0,
    "sas_revision": 0,
}

for key, default in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ============================================================
# THEME
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
        key="sas_theme_selector_v3",
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
        background-color: {theme['primary']} !important;
        color: white !important;
        border: none !important;
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

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPER
# ============================================================

def hex_to_rgba(hex_color, alpha=0.4):

    hex_color = hex_color.replace("#", "")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return f"rgba({r},{g},{b},{alpha})"


# ============================================================
# PDF → PIL IMAGE
# ============================================================

def pdf_to_images(pdf_bytes):

    images = []

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf",
    )

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

    document.close()

    return images


# ============================================================
# IMAGE → DATA URI
#
# Slide dimasukkan ke canvas sebagai Fabric IMAGE OBJECT.
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

    return (
        "data:image/png;base64,"
        + encoded
    )


# ============================================================
# CANVAS SIZE
# ============================================================

def get_canvas_size(image):

    canvas_width = 900

    ratio = (
        image.height /
        image.width
    )

    canvas_height = int(
        canvas_width * ratio
    )

    return (
        canvas_width,
        canvas_height,
    )


# ============================================================
# CREATE INITIAL CANVAS
# ============================================================

def create_initial_canvas(
    slide,
    canvas_width,
    canvas_height,
    previous_drawing=None,
):

    resized = slide.resize(
        (
            canvas_width,
            canvas_height,
        ),
        Image.Resampling.LANCZOS,
    )

    data_uri = image_to_data_uri(
        resized
    )

    background_object = {
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
        "visible": True,

        "selectable": False,
        "evented": False,

        "src": data_uri,
    }

    if previous_drawing:

        try:

            objects = previous_drawing.get(
                "objects",
                [],
            )

            drawing_objects = [
                obj
                for obj in objects
                if obj.get("type") != "image"
            ]

            return {
                "version": "4.4.0",
                "objects": [
                    background_object
                ] + drawing_objects,
            }

        except Exception:
            pass

    return {
        "version": "4.4.0",
        "objects": [
            background_object
        ],
    }


# ============================================================
# REMOVE BACKGROUND IMAGE FROM SAVED DRAWING
# ============================================================

def get_annotation_only(canvas_json):

    if not canvas_json:
        return None

    cleaned = copy.deepcopy(
        canvas_json
    )

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
# RENDER ANNOTATIONS UNTUK EXPORT
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

    canvas_width = annotation_data.get(
        "width",
        900,
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

        # ----------------------------------------------------
        # FREE DRAW
        # ----------------------------------------------------

        if obj_type == "path":

            path = obj.get(
                "path",
                [],
            )

            points = []

            for command in path:

                if len(command) < 3:
                    continue

                name = command[0]

                if name in ["M", "L"]:

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

                elif name == "Q":

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
                    points,
                    fill=stroke,
                    width=stroke_width,
                    joint="curve",
                )

        # ----------------------------------------------------
        # RECTANGLE
        # ----------------------------------------------------

        elif obj_type == "rect":

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

        # ----------------------------------------------------
        # CIRCLE
        # ----------------------------------------------------

        elif obj_type == "circle":

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

        # ----------------------------------------------------
        # LINE
        # ----------------------------------------------------

        elif obj_type == "line":

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

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

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
# UPLOAD
# ============================================================

with st.sidebar:

    st.divider()

    st.header(
        f"{theme['file']} Materi Kuliah"
    )

    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        key="sas_pdf_uploader_v3",
    )

    if uploaded_file:

        if st.button(
            "🔄 Muat Materi Baru",
            key="sas_load_pdf_v3",
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
                st.session_state.sas_revision += 1

                st.success(
                    f"{len(slides)} slide berhasil dimuat! 🎉"
                )


# ============================================================
# TOOLS
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
        key="sas_tool_selector_v3",
    )

    drawing_mode = tool_options[
        selected_tool
    ]

    if drawing_mode == "freedraw":

        pen_type = st.radio(
            "Jenis:",
            [
                "✏️ Pen",
                "🖍️ Stabilo",
            ],
            key="sas_pen_type_v3",
        )

    else:

        pen_type = "✏️ Pen"


    # --------------------------------------------------------
    # HIGHLIGHTER
    # --------------------------------------------------------

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
            key="sas_highlighter_color_v3",
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
                key="sas_custom_highlighter_v3",
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
            key="sas_pen_color_v3",
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
                key="sas_custom_pen_v3",
            )

        else:

            stroke_color = pen_colors[
                selected_color
            ]

        default_width = 3


    stroke_width = st.slider(
        "Ukuran:",
        1,
        30,
        default_width,
        key="sas_stroke_width_v3",
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
# CURRENT SLIDE
# ============================================================

total_slides = len(
    st.session_state.sas_slides
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
        key="sas_previous_v3",
        use_container_width=True,
        disabled=(
            st.session_state.sas_current_slide == 0
        ),
    ):

        st.session_state.sas_current_slide -= 1
        st.session_state.sas_revision += 1

        st.rerun()


with nav_center:

    slide_number = st.slider(
        "Slide",
        1,
        total_slides,
        st.session_state.sas_current_slide + 1,
        key="sas_slide_slider_v3",
    )

    new_index = slide_number - 1

    if new_index != st.session_state.sas_current_slide:

        st.session_state.sas_current_slide = new_index
        st.session_state.sas_revision += 1

        st.rerun()


with nav_right:

    if st.button(
        "→",
        key="sas_next_v3",
        use_container_width=True,
        disabled=(
            st.session_state.sas_current_slide
            >= total_slides - 1
        ),
    ):

        st.session_state.sas_current_slide += 1
        st.session_state.sas_revision += 1

        st.rerun()


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
# EDITOR + NOTES
# ============================================================

editor_col, notes_col = st.columns(
    [3, 2]
)


# ============================================================
# SLIDE EDITOR
# ============================================================

with editor_col:

    st.markdown(
        f"#### 🖼️ Edit langsung di slide {theme['draw']}"
    )

    canvas_width, canvas_height = (
        get_canvas_size(
            current_slide
        )
    )


    previous_annotations = (
        st.session_state
        .sas_drawings
        .get(slide_index)
    )


    # --------------------------------------------------------
    # SLIDE DIMASUKKAN SEBAGAI FABRIC IMAGE OBJECT
    # --------------------------------------------------------

    initial_canvas = create_initial_canvas(
        current_slide,
        canvas_width,
        canvas_height,
        previous_annotations,
    )


    canvas_result = st_canvas(

        fill_color=(
            "rgba(255,255,255,0)"
        ),

        stroke_width=stroke_width,

        stroke_color=stroke_color,

        background_color=(
            "rgba(0,0,0,0)"
        ),

        initial_drawing=initial_canvas,

        height=canvas_height,

        width=canvas_width,

        drawing_mode=drawing_mode,

        display_toolbar=True,

        update_streamlit=True,

        key=(
            "sas_editor_canvas_v3_"
            f"{slide_index}_"
            f"{st.session_state.sas_revision}"
        ),
    )


    # --------------------------------------------------------
    # SAVE ANNOTATIONS
    # --------------------------------------------------------

    if canvas_result.json_data is not None:

        annotation_data = (
            get_annotation_only(
                canvas_result.json_data
            )
        )

        old_data = (
            st.session_state
            .sas_drawings
            .get(slide_index)
        )

        if annotation_data != old_data:

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
            ] = annotation_data


    # --------------------------------------------------------
    # CONTROLS
    # --------------------------------------------------------

    st.write("")

    btn1, btn2, btn3 = st.columns(3)


    with btn1:

        if st.button(
            "↩️ Undo",
            key="sas_undo_v3",
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

                st.session_state.sas_revision += 1

                st.rerun()

            else:

                st.toast(
                    "Belum ada yang bisa di-undo."
                )


    with btn2:

        if st.button(
            "🗑️ Hapus Coretan",
            key="sas_clear_v3",
            use_container_width=True,
        ):

            st.session_state.sas_drawings[
                slide_index
            ] = None

            st.session_state.sas_history[
                slide_index
            ] = []

            st.session_state.sas_revision += 1

            st.rerun()


    with btn3:

        if st.button(
            "🔄 Reset Slide",
            key="sas_reset_v3",
            use_container_width=True,
        ):

            st.session_state.sas_drawings[
                slide_index
            ] = None

            st.session_state.sas_history[
                slide_index
            ] = []

            st.session_state.sas_revision += 1

            st.rerun()


    st.caption(
        "💡 Pilih 🔤 Text lalu klik pada slide untuk menambahkan tulisan."
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
        key=f"sas_mini_note_{slide_index}_v3",
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
        key=f"sas_main_note_{slide_index}_v3",
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
        key="sas_generate_pdf_v3",
        use_container_width=True,
    ):

        with st.spinner(
            "Menyusun PDF..."
        ):

            pdf_file = create_pdf()

            st.download_button(
                "⬇️ Unduh Hasil PDF",
                data=pdf_file,
                file_name="Hasil_Edit_Slide.pdf",
                mime="application/pdf",
                key="sas_download_pdf_v3",
                use_container_width=True,
            )


# ============================================================
# GOOGLE DRIVE
# ============================================================

with drive_col:

    if st.button(
        f"{theme['cloud']} Simpan ke Google Drive",
        key="sas_save_drive_v3",
        use_container_width=True,
    ):

        with st.spinner(
            "Mengunggah..."
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
