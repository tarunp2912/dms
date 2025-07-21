import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils.data import now
from frappe.utils.response import build_response
from frappe.utils import cint
import os
from frappe.utils import formatdate, now_datetime
from frappe.utils import format_datetime

@frappe.whitelist(allow_guest=True, methods=["POST"])
def upload():
    file = None
    if hasattr(frappe.request, 'files'):
        file = frappe.request.files.get('file')
    if not file and hasattr(frappe.local, 'request'):
        file = frappe.local.request.files.get('file')
    if not file:
        frappe.throw('No file uploaded')
    file_name = file.filename
    content = file.read()
    file_size = len(content)  # Get file size in bytes
    file_doc = save_file(file_name, content, None, None, is_private=0)
    doc = frappe.new_doc("DMS OCR")
    doc.file_name = file_name
    doc.owner = frappe.session.user
    doc.is_active = 1
    doc.file_url = file_doc.file_url
    doc.uploaded_on = now()
    doc.file_size = file_size  # Store file size
    doc.insert()
    frappe.db.commit()
    return {'name': doc.name, 'url': file_doc.file_url, 'is_active': doc.is_active}

@frappe.whitelist()
def list():
    files = frappe.get_all(
        "DMS OCR",
        fields=["name", "file_name", "owner", "modified", "file_url", "file_size"],
        filters={"is_active": 1},
        order_by="modified desc"
    )
    def pretty_size(size):
        if not size:
            return "—"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
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
    return {
        "text": getattr(doc, "ocr_text", ""),
        "image_url": doc.file_url
    }