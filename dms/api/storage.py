import frappe
from pypika import functions as fn
from dms.utils.files import get_file_type

MEGA_BYTE = 1024**2
DMSFile = frappe.qb.DocType("DMS File")


@frappe.whitelist()
def storage_breakdown(team, owned_only):
    limit = frappe.get_value("DMS Team", team, "quota" if owned_only else "storage") * MEGA_BYTE
    filters = {
        "team": team,
        "is_group": False,
        "is_active": 1,
        "file_size": [">=", limit / 200],
    }
    if owned_only:
        filters["owner"] = frappe.session.user

    # Get is_link because file type check requires it
    entities = frappe.db.get_list(
        "DMS File",
        filters=filters,
        order_by="file_size desc",
        fields=["name", "title", "owner", "file_size", "mime_type", "is_group", "is_link"],
    )
    for r in entities:
        r["file_type"] = get_file_type(r)

    query = (
        frappe.qb.from_(DMSFile)
        .select(DMSFile.mime_type, fn.Sum(DMSFile.file_size).as_("file_size"))
        .where((DMSFile.is_group == 0) & (DMSFile.is_active == 1) & (DMSFile.team == team))
    )
    if owned_only:
        query = query.where(DMSFile.owner == frappe.session.user)
    else:
        query = query.where(DMSFile.is_private == 0)
    return {
        "limit": limit,
        "total": query.groupby(DMSFile.mime_type).run(as_dict=True),
        "entities": entities,
    }


@frappe.whitelist()
def storage_bar_data(team):
    query = (
        frappe.qb.from_(DMSFile)
        .where(
            (DMSFile.team == team)
            & (DMSFile.is_group == 0)
            & (DMSFile.owner == frappe.session.user)
            & (DMSFile.is_active == 1)
        )
        .select(fn.Coalesce(fn.Sum(DMSFile.file_size), 0).as_("total_size"))
    )
    result = query.run(as_dict=True)[0]
    result["limit"] = frappe.get_value("DMS Team", team, "quota") * MEGA_BYTE
    return result
