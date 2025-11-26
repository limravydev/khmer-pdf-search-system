# utils.py
import base64
from io import BytesIO

PDF_SCROLL_CSS = """
<style>
.pdf-scroll {
    max-height: 800px;
    overflow-y: auto;
    overflow-x: hidden;
    border: 1px solid #e5e5e5;
    padding: 8px;
    border-radius: 6px;
    background-color: #fafafa;
}
.pdf-scroll img {
    max-width: 100% !important;
    height: auto !important;
    display: block;
}
</style>
"""

def pages_to_html(pages):
    """
    Convert a list of PIL images (one per PDF page)
    into a single HTML string with inline base64 PNGs.

    IMPORTANT: No Streamlit calls here. Only return a string.
    """
    html_parts = []

    for i, img in enumerate(pages, start=1):
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        html_parts.append(
            f"""
            <div style="margin-bottom: 16px;">
                <div style="font-size: 13px; color: #666; margin-bottom: 4px;">
                    Page {i}
                </div>
                <img src="data:image/png;base64,{b64}" />
            </div>
            """
        )

    return "\n".join(html_parts)