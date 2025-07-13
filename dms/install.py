import frappe


def after_install():
    index_check = frappe.db.sql(
        """SHOW INDEX FROM `tabDMS File` WHERE Key_name = 'dms_file_title_fts_idx'"""
    )
    if not index_check:
        frappe.db.sql(
            """ALTER TABLE `tabDMS File` ADD FULLTEXT INDEX dms_file_title_fts_idx (title)"""
        )
