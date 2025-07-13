import frappe


def execute():
    for user in frappe.db.get_list("User", pluck="name"):
        teams = frappe.get_all(
            "DMS Team Member",
            pluck="parent",
            filters=[
                ["parenttype", "=", "DMS Team"],
                ["user", "=", user],
            ],
        )
        if teams:
            if not frappe.db.exists("DMS Settings", {"user": user}):
                frappe.get_doc(
                    {
                        "doctype": "DMS Settings",
                        "user": user,
                        "single_click": 1,
                        "default_team": teams[0],
                    }
                ).insert()
