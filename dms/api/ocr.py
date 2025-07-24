import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils.data import now
from frappe.utils.response import build_response
from frappe.utils import cint
import os
from frappe.utils import formatdate, now_datetime
from frappe.utils import format_datetime
from dms.utils.files import FileManager


@frappe.whitelist(allow_guest=True, methods=["POST"])
def upload():
    import tempfile
    import mimetypes
    import traceback

    ocr_text = ""
    file = None
    if hasattr(frappe.request, "files"):
        file = frappe.request.files.get("file")
    if not file and hasattr(frappe.local, "request"):
        file = frappe.local.request.files.get("file")
    if not file:
        frappe.throw("No file uploaded")
    file_name = file.filename
    content = file.read()
    file_size = len(content)  # Get file size in bytes

    # Save file to cloud (S3) or local, like team section
    team = frappe.db.get_value("DMS Team", {}, "name")
    manager = FileManager()
    # Use a path similar to team uploads
    file_path = f"{team}/ocr/{file_name}"
    temp_file_path = f"/tmp/{file_name}"
    with open(temp_file_path, "wb") as f:
        f.write(content)
    manager.upload_file(temp_file_path, file_path)
    file_url = f"/files/{file_path}"

    # OCR/TEXT extraction logic
    try:
        ext = file_name.lower().split(".")[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        if ext == "pdf":
            from PyPDF2 import PdfReader

            reader = PdfReader(tmp_path)
            ocr_text = "\n".join([page.extract_text() or "" for page in reader.pages])
        elif ext == "docx":
            from docx import Document

            doc = Document(tmp_path)
            ocr_text = "\n".join([para.text for para in doc.paragraphs])
        elif ext in ["png", "jpg", "jpeg", "bmp", "tiff"]:
            import cv2, pytesseract

            image = cv2.imread(tmp_path)
            if image is not None:
                ocr_text = pytesseract.image_to_string(image)
            else:
                ocr_text = "Could not read image."
        else:
            ocr_text = "Unsupported file type."
    except Exception as e:
        ocr_text = f"OCR error: {e}\n{traceback.format_exc()}"
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    doc = frappe.new_doc("DMS OCR")
    doc.file_name = file_name
    doc.owner = frappe.session.user
    doc.is_active = 1
    doc.file_url = file_url
    doc.uploaded_on = now()
    doc.file_size = file_size  # Store file size
    doc.ocr_text = ocr_text
    if team:
        doc.team = team
    doc.insert()
    frappe.db.commit()
    return {"name": doc.name, "url": file_url, "is_active": doc.is_active}


@frappe.whitelist()
def list():
    files = frappe.get_all(
        "DMS OCR",
        fields=["name", "file_name", "owner", "modified", "file_url", "file_size"],
        filters={"is_active": 1},
        order_by="modified desc",
    )

    def pretty_size(size):
        if not size:
            return "—"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    for f in files:
        if not f.get("file_name"):
            f["file_name"] = f.get("name")
        f["title"] = f.get("file_name") or f.get("name")
        f["file_size_pretty"] = pretty_size(f.get("file_size") or 0)
        f["is_group"] = 0
        f["document"] = None
        f["write"] = True
        f["read"] = True
        f["share"] = False
        f["comment"] = False
        f["share_count"] = 0
        # Add this line to format the modified date
        f["relativeModified"] = format_datetime(f.get("modified")) if f.get("modified") else "-"
        f["relativeAccessed"] = "-"
    return files


@frappe.whitelist(allow_guest=True)
def get_result(name):
    doc = frappe.get_doc("DMS OCR", name)
    return {"text": getattr(doc, "ocr_text", ""), "image_url": doc.file_url}


@frappe.whitelist()
def delete(name):
    doc = frappe.get_doc("DMS OCR", name)
    doc.delete()
    frappe.db.commit()
    return {"status": "deleted", "name": name}
