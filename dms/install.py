import frappe
import subprocess
import os

def after_install():
    index_check = frappe.db.sql(
        """SHOW INDEX FROM `tabDMS File` WHERE Key_name = 'dms_file_title_fts_idx'"""
    )
    if not index_check:
        frappe.db.sql(
            """ALTER TABLE `tabDMS File` ADD FULLTEXT INDEX dms_file_title_fts_idx (title)"""
        )



def install_requirements():
    # Go one directory above the app module to find requirements.txt
    app_module_path = frappe.get_app_path("dms")  # returns apps/dms/dms
    app_base_path = os.path.dirname(app_module_path)  # returns apps/dms
    requirements_file = os.path.join(app_base_path, "requirements.txt")
 
    if os.path.exists(requirements_file):
        print(f"Installing requirements from {requirements_file} ...")
        subprocess.check_call(["pip", "install", "-r", requirements_file])
    else:
        print("No requirements.txt found in app directory.")