import frappe
from pathlib import Path
import shutil
import time


def execute():
    print(
        "This migration to an alpha release might CORRUPT your data. Do NOT run this before taking a complete backup. You have two minutes left to cancel this deployment. "
    )
    time.sleep(120)

    frappe.reload_doc("DMS", "doctype", "DMS Team Member")
    frappe.reload_doc("DMS", "doctype", "DMS Team")
    frappe.reload_doc("DMS", "doctype", "DMS File")
    frappe.reload_doc("DMS", "doctype", "DMS Permission")
    frappe.reload_doc("DMS", "doctype", "DMS Entity Activity Log")

    if frappe.db.get_list("DMS Team"):
        print("A DMS Team already exists, going ahead might corrupt your database.")
        return

    frappe.db.delete("DMS Team")
    frappe.db.delete("DMS File")
    frappe.db.delete("DMS Permission")
    team = frappe.get_doc({"doctype": "DMS Team", "title": "DMS"})
    team.insert()

    home_folder = frappe.db.get_list("DMS File", {"team": team.name})[0].name
    entities = frappe.db.sql("select * from `tabDMS Entity`", as_dict=True)
    homes = []
    translate = {}

    for k in entities:
        try:
            if not k["parent_dms_entity"]:
                homes.append(k["name"])
                continue
            k["old_name"] = k.pop("name")
            doc = frappe.get_doc(
                {"doctype": "DMS File", **k, "team": team.name, "is_private": 1}
            )
            if k["path"]:
                path_els = k["path"].split("/")
                if "files" in path_els:
                    doc.path = (
                        home_folder + "/" + "/".join(path_els[path_els.index("files") + 2 :])
                    )
                else:
                    doc.path = (
                        home_folder + "/" + "/".join(path_els[path_els.index("private") + 2 :])
                    )
                p = Path(k["path"])
                old_path = frappe.get_site_path("/".join(str(p).split("/")[1:]))
                try:
                    shutil.copy(
                        old_path, str(Path(frappe.get_site_path("private/files")) / doc.path)
                    )
                except:
                    print(
                        "Moving failed for",
                        old_path,
                        "->",
                        Path(frappe.get_site_path("private/files")) / (doc.path),
                    )
            doc.insert()

            translate[k["old_name"]] = doc.name
        except Exception as e:
            print(f"{k['title']} failed, with:", e)
    frappe.db.commit()

    for k in entities:
        if not k.get("old_name") in translate:
            continue
        name = translate[k["old_name"]]
        frappe.db.set_value("DMS File", name, "owner", k["owner"], update_modified=False)
        frappe.db.set_value("DMS File", name, "creation", k["creation"], update_modified=False)
        frappe.db.set_value("DMS File", name, "modified", k["modified"], update_modified=False)
        frappe.db.set_value(
            "DMS File", name, "modified_by", k["modified_by"], update_modified=False
        )
        if k["parent_dms_entity"] in homes:
            frappe.db.set_value(
                "DMS File",
                name,
                "parent_entity",
                home_folder,
                update_modified=False,
            )
        else:
            frappe.db.set_value(
                "DMS File",
                name,
                "parent_entity",
                translate[k["parent_dms_entity"]],
                update_modified=False,
            )

    shares = frappe.db.sql("select * from `tabDMS DocShare`", as_dict=True)
    for s in shares:
        entity = translate.get(s["share_name"])
        if not entity:
            continue
        elif s["everyone"]:
            frappe.db.set_value(
                "DMS File",
                entity,
                "is_private",
                0,
                update_modified=False,
            )
        else:
            frappe.get_doc(
                {
                    "doctype": "DMS Permission",
                    "user": "" if s.public else s.user_name,
                    "entity": entity,
                    "read": s["read"],
                    "share": s["share"],
                    "write": s["share"],
                    "comment": 1,
                    "valid_until": s["valid_until"],
                }
            ).insert()

    RENAME_MAP = {
        "DMS Notification": "notif_doctype_name",
        "DMS Favourite": "entity",
        "DMS Document Version": "parent_entity",
        "DMS Entity Activity Log": "entity",
        "DMS Entity Log": "entity_name",
    }

    for doctype, field in RENAME_MAP.items():
        for k in frappe.get_list(doctype, fields=["name", field]):
            if k[field] not in translate:
                continue
            frappe.db.set_value(
                doctype,
                k["name"],
                field,
                translate[k[field]],
                update_modified=False,
            )
