# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from pathlib import Path
import shutil
from dms.utils.files import get_home_folder


class DMSTeam(Document):
    def on_update(self):
        """Creates the file on disk"""
        DMSFile = frappe.qb.DocType("DMS File")
        if (
            frappe.qb.from_(DMSFile)
            .where(((DMSFile.team == self.name) & DMSFile.parent_entity.isnull()))
            .select(DMSFile.name, DMSFile.path)
            .run(as_dict=True)
        ):
            return
        d = frappe.get_doc(
            {
                "doctype": "DMS File",
                "title": f"DMS - {self.name}",
                "is_group": 1,
                "team": self.name,
            }
        )
        d.insert()

        user_directory_path = Path(frappe.get_site_path("private/files"), d.name)
        user_directory_path.mkdir()
        (user_directory_path / "uploads").mkdir()
        (user_directory_path / "embeds").mkdir()
        (user_directory_path / "thumbnails").mkdir()
        d.path = d.name
        d.save()

    def on_trash(self):
        try:
            d = get_home_folder(self.name)
            user_directory_path = Path(frappe.get_site_path("private/files"), d.path)
            shutil.rmtree(str(user_directory_path))
        except FileNotFoundError:
            pass
        frappe.db.delete("DMS File", {"team": self.name})
        frappe.db.commit()
