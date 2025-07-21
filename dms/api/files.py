import os, re, json, mimetypes

import frappe
from pypika import Order
from .permissions import get_teams, user_has_permission
from pathlib import Path
from werkzeug.wrappers import Response
from werkzeug.utils import secure_filename, send_file
from io import BytesIO
import mimemapper
import jwt

from dms.utils.files import (
    get_home_folder,
    get_file_type,
    get_new_title,
    update_file_size,
    if_folder_exists,
    FileManager,
)
from datetime import date, timedelta
import magic
from datetime import datetime
from dms.api.notifications import notify_mentions
from dms.api.storage import storage_bar_data
from pathlib import Path
from io import BytesIO
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file
from dms.locks.distributed_lock import DistributedLock


@frappe.whitelist()
def upload_file(team, personal=None, fullpath=None, parent=None, last_modified=None, embed=0):
    """
    Accept chunked file contents via a multipart upload, store the file on
    disk, and insert a corresponding DMSEntity doc.

    :param fullpath: Full path of the uploaded file
    :param parent: Document-name of the parent folder. Defaults to the user directory
    :raises PermissionError: If the user does not have write access to the specified parent folder
    :raises FileExistsError: If a file with the same name already exists in the specified parent folder
    :raises ValueError: If the size of the stored file does not match the specified filesize
    :return: DMSEntity doc once the entire file has been uploaded
    """
    home_folder = get_home_folder(team)
    parent = parent or home_folder["name"]
    is_private = personal or frappe.get_value("DMS File", parent, "is_private")
    embed = int(embed)

    if fullpath:
        dirname = os.path.dirname(fullpath).split("/")
        for i in dirname:
            parent = if_folder_exists(team, i, parent, is_private)

    # Validate: team members can upload to team folders, and permissions
    is_team_member = team in get_teams() and not is_private
    if not is_team_member and not frappe.has_permission(
        doctype="DMS File", doc=parent, ptype="write", user=frappe.session.user
    ):
        frappe.throw("Ask the folder owner for upload access.", frappe.PermissionError)

    storage_data = storage_bar_data(team)
    if (storage_data["limit"] - storage_data["total_size"]) < int(
        frappe.form_dict.total_file_size
    ):
        frappe.throw("You're out of storage!", ValueError)

    file = frappe.request.files["file"]
    upload_session = frappe.form_dict.uuid
    title = get_new_title(frappe.form_dict.filename if embed else file.filename, parent)
    current_chunk = int(frappe.form_dict.chunk_index)
    total_chunks = int(frappe.form_dict.total_chunk_count)

    temp_path = get_upload_path(home_folder["name"], f"{upload_session}_{secure_filename(title)}")
    with temp_path.open("ab") as f:
        f.seek(int(frappe.form_dict.chunk_byte_offset))
        f.write(file.stream.read())
        if (
            not f.tell() >= int(frappe.form_dict.total_file_size)
            or current_chunk != total_chunks - 1
        ):
            return

    # Validate that file size is matching
    file_size = temp_path.stat().st_size
    if file_size != int(frappe.form_dict.total_file_size):
        temp_path.unlink()
        frappe.throw("Size on disk does not match specified filesize.", ValueError)

    mime_type = mimemapper.get_mime_type(str(temp_path), native_first=False)
    if mime_type is None:
        mime_type = magic.from_buffer(open(temp_path, "rb").read(2048), mime=True)

    # Create DB record
    dms_file = create_dms_file(
        team,
        is_private,
        title,
        parent,
        file_size,
        mime_type,
        last_modified,
        lambda n: Path(home_folder["name"])
        / f"{'embeds' if embed else ''}"
        / f"{n}{temp_path.suffix}",
    )

    # Upload and update parent folder size
    manager = FileManager()
    manager.upload_file(str(temp_path), dms_file.path, dms_file if not embed else None)
    update_file_size(parent, file_size)

    return dms_file


@frappe.whitelist(allow_guest=True)
def upload_chunked_file(personal=0, parent=None, last_modified=None):
    """
    Accept chunked file contents via a multipart upload, store the file on
    disk, and insert a corresponding DMSEntity doc.

    :param fullpath: Full path of the uploaded file
    :param parent: Document-name of the parent folder. Defaults to the user directory
    :raises PermissionError: If the user does not have write access to the specified parent folder
    :raises FileExistsError: If a file with the same name already exists in the specified parent folder
    :raises ValueError: If the size of the stored file does not match the specified filesize
    :return: DMSEntity doc once the entire file has been uploaded
    """
    dms_entity = frappe.get_value(
        "DMS File",
        parent,
        ["document", "title", "mime_type", "file_size", "owner", "team"],
        as_dict=1,
    )
    home_directory = get_home_folder(dms_entity.team)
    embed_directory = Path(
        frappe.get_site_path("private/files"),
        home_directory.name,
        "embeds",
    )
    if not frappe.has_permission(
        doctype="DMS File", doc=parent, ptype="write", user=frappe.session.user
    ):
        frappe.throw("Ask the folder owner for upload access.", frappe.PermissionError)

    file = frappe.request.files["file"]

    name = frappe.form_dict.uuid
    title, file_ext = os.path.splitext(frappe.form_dict.file_name)
    mime_type = frappe.form_dict.mime_type
    current_chunk = int(frappe.form_dict.chunk_index)
    total_chunks = int(frappe.form_dict.total_chunk_count)
    file_size = int(frappe.form_dict.total_file_size)
    save_path = Path(embed_directory) / f"{secure_filename(name+file_ext)}"
    if current_chunk == 0 and save_path.exists():
        frappe.throw(f"File '{title}' already exists", FileExistsError)

    if not mime_type:
        mime_type = magic.from_buffer(open(save_path, "rb").read(2048), mime=True)

    with save_path.open("ab") as f:
        f.seek(int(frappe.form_dict.chunk_byte_offset))
        f.write(file.stream.read())

    if current_chunk + 1 == total_chunks:
        file_size = save_path.stat().st_size

    if file_size != int(frappe.form_dict.total_file_size):
        save_path.unlink()
        frappe.throw("Size on disk does not match specified filesize", ValueError)
    dms_file = create_dms_file(
        dms_entity.team,
        personal,
        title,
        parent,
        file_size,
        mime_type,
        last_modified,
        lambda n: Path(home_directory["name"]) / "embeds" / f"{n}{save_path.suffix}",
    )
    os.rename(save_path, Path(frappe.get_site_path("private/files")) / dms_file.path)

    return dms_file.name + save_path.suffix


@frappe.whitelist()
def get_thumbnail(entity_name):
    dms_file = frappe.get_value(
        "DMS File",
        entity_name,
        ["is_group", "path", "title", "mime_type", "file_size", "owner", "team", "document"],
        as_dict=1,
    )
    if not dms_file or dms_file.is_group or dms_file.is_link:
        frappe.throw("No thumbnail for this type.", ValueError)
    if not frappe.has_permission(
        doctype="DMS File", doc=dms_file.name, ptype="write", user=frappe.session.user
    ):
        frappe.throw("Cannot upload due to insufficient permissions", frappe.PermissionError)

    with DistributedLock(dms_file.path, exclusive=False):
        thumbnail_data = None
        if frappe.cache().exists(entity_name):
            thumbnail_data = frappe.cache().get_value(entity_name)

        if not thumbnail_data:
            thumbnail_data = None
            try:
                manager = FileManager()
                thumbnail = manager.get_thumbnail(dms_file.team, entity_name)
                thumbnail_data = BytesIO(thumbnail.read())
                frappe.cache().set_value(entity_name, thumbnail_data, expires_in_sec=60 * 60)
            except FileNotFoundError:
                if dms_file.mime_type.startswith("text"):
                    with manager.get_file(dms_file.path) as f:
                        thumbnail_data = f.read()[:1000].decode("utf-8").replace("\n", "<br/>")
                elif dms_file.mime_type == "frappe_doc":
                    html = frappe.get_value("DMS Document", dms_file.document, "raw_content")
                    thumbnail_data = html[:1000]
                if thumbnail_data:
                    frappe.cache().set_value(entity_name, thumbnail_data, expires_in_sec=60 * 60)

    if isinstance(thumbnail_data, BytesIO):
        response = Response(
            wrap_file(frappe.request.environ, thumbnail_data),
            direct_passthrough=True,
        )
        response.headers.set("Content-Type", "image/jpeg")
        response.headers.set("Content-Disposition", "inline", filename=entity_name)
        return response
    else:
        return thumbnail_data


@frappe.whitelist()
def create_document_entity(title, personal, team, content, parent=None):
    home_directory = get_home_folder(team)
    parent = parent or home_directory.name

    if not frappe.has_permission(
        doctype="DMS File",
        doc=parent,
        ptype="write",
        user=frappe.session.user,
    ):
        frappe.throw(
            "Cannot access folder due to insufficient permissions",
            frappe.PermissionError,
        )
    dms_doc = frappe.new_doc("DMS Document")
    dms_doc.title = title
    dms_doc.content = content
    dms_doc.version = 2
    dms_doc.save()

    entity = create_dms_file(
        team,
        personal,
        title,
        parent,
        0,
        "frappe_doc",
        None,
        lambda _: "",
        document=dms_doc.name,
    )
    return entity


def get_upload_path(team_name, file_name):
    uploads_path = Path(frappe.get_site_path("private/files"), team_name, "uploads")
    if not os.path.exists(uploads_path):
        uploads_path = Path(frappe.get_site_path("private/files"), team_name, "uploads")
        uploads_path.mkdir()
    return uploads_path / file_name


def create_dms_file(
    team, personal, title, parent, file_size, mime_type, last_modified, entity_path, document=None
):
    dms_file = frappe.get_doc(
        {
            "doctype": "DMS File",
            "team": team,
            "is_private": personal,
            "title": title,
            "parent_entity": parent,
            "file_size": file_size,
            "mime_type": mime_type,
            "document": document,
        }
    )
    dms_file.flags.file_created = True
    dms_file.insert()
    dms_file.path = str(entity_path(dms_file.name))
    dms_file.save()
    if last_modified:
        dt_object = datetime.fromtimestamp(int(last_modified) / 1000.0)
        formatted_datetime = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")
        dms_file.db_set("modified", formatted_datetime, update_modified=False)
    return dms_file


@frappe.whitelist()
def create_folder(team, title, personal=False, parent=None):
    """
    Create a new folder.

    :param title: Folder name
    :param parent: Document-name of the parent folder. Defaults to the user directory
    :raises PermissionError: If the user does not have write access to the specified parent folder
    :raises FileExistsError: If a folder with the same name already exists in the specified parent folder
    :return: DMSEntity doc of the new folder
    """
    home_folder = get_home_folder(team)
    parent = parent or home_folder.name

    if not frappe.has_permission(
        doctype="DMS File", doc=parent, ptype="write", user=frappe.session.user
    ):
        frappe.throw(
            "Cannot create folder due to insufficient permissions",
            frappe.PermissionError,
        )

    if not personal:
        entity_exists = frappe.db.exists(
            {
                "doctype": "DMS File",
                "parent_entity": parent,
                "is_group": 1,
                "title": title,
                "is_active": 1,
                "is_private": 0,
            }
        )
    else:
        entity_exists = frappe.db.exists(
            {
                "doctype": "DMS File",
                "parent_entity": parent,
                "title": title,
                "is_group": 1,
                "is_active": 1,
                "owner": frappe.session.user,
                "is_private": 1,
            }
        )
    # BROKEN: capitlization?
    if entity_exists:
        suggested_name = get_new_title(title, parent, folder=True)
        frappe.throw(
            f"Folder '{title}' already exists.\n Suggested: {suggested_name}",
            FileExistsError,
        )

    dms_file = frappe.get_doc(
        {
            "doctype": "DMS File",
            "title": title,
            "team": team,
            "is_group": 1,
            "parent_entity": parent,
            "color": "#525252",
            "is_private": personal,
        }
    )
    dms_file.insert()

    return dms_file


@frappe.whitelist()
def create_link(team, title, link, personal=False, parent=None):
    home_folder = get_home_folder(team)
    parent = parent or home_folder.name

    if not frappe.has_permission(
        doctype="DMS File", doc=parent, ptype="write", user=frappe.session.user
    ):
        frappe.throw(
            "Cannot create folder due to insufficient permissions",
            frappe.PermissionError,
        )
    if not personal:
        entity_exists = frappe.db.exists(
            {
                "doctype": "DMS File",
                "parent_entity": parent,
                "title": title,
                "is_active": 1,
                "is_link": 1,
            }
        )
    else:
        entity_exists = frappe.db.exists(
            {
                "doctype": "DMS File",
                "parent_entity": parent,
                "title": title,
                "is_link": 1,
                "is_active": 1,
                "owner": frappe.session.user,
                "is_private": 1,
            }
        )
    if entity_exists:
        suggested_name = get_new_title(title, parent, folder=True)
        frappe.throw(
            f"File '{title}' already exists.\n Suggested: {suggested_name}",
            FileExistsError,
        )

    dms_file = frappe.get_doc(
        {
            "doctype": "DMS File",
            "title": title,
            "team": team,
            "path": link,
            "is_link": 1,
            "mime_type": "link/unknown",
            "parent_entity": parent,
            "is_private": personal,
        }
    )
    dms_file.insert()

    return dms_file


@frappe.whitelist()
def save_doc(entity_name, doc_name, raw_content, content, file_size, mentions, settings=None):
    write_perms = user_has_permission(
        frappe.get_doc("DMS File", entity_name), "write", frappe.session.user
    )
    comment_perms = user_has_permission(
        frappe.get_doc("DMS File", entity_name), "comment", frappe.session.user
    )
    # BROKEN - comment access is write access
    if not write_perms and not comment_perms:
        raise frappe.PermissionError("You do not have permission to view this file")
    if settings:
        frappe.db.set_value("DMS Document", doc_name, "settings", json.dumps(settings))
    file_size = len(content.encode("utf-8")) + len(raw_content.encode("utf-8"))
    update_modifed = comment_perms and not write_perms
    frappe.db.set_value("DMS Document", doc_name, "content", content)
    frappe.db.set_value("DMS Document", doc_name, "raw_content", raw_content)
    frappe.db.set_value("DMS Document", doc_name, "mentions", json.dumps(mentions))
    if (
        frappe.db.get_value("DMS File", entity_name, "file_size") != int(file_size)
        and write_perms
    ):
        frappe.db.set_value("DMS File", entity_name, "file_size", file_size)
    if json.dumps(mentions):
        frappe.enqueue(
            notify_mentions,
            queue="long",
            job_id=f"fdoc_{doc_name}",
            deduplicate=True,
            timeout=None,
            now=False,
            at_front=False,
            entity_name=entity_name,
            document_name=doc_name,
        )
    return


@frappe.whitelist()
def create_doc_version(entity_name, doc_name, snapshot_data, snapshot_message):
    if not frappe.has_permission(
        doctype="DMS File",
        doc=entity_name,
        ptype="write",
        user=frappe.session.user,
    ):
        raise frappe.permissionerror("you do not have permission to view this file")
    new_version = frappe.new_doc("DMS Document Version")
    new_version.snapshot_data = snapshot_data
    new_version.parent_entity = entity_name
    new_version.snapshot_message = snapshot_message
    new_version.parent_document = doc_name
    new_version.snapshot_size = len(snapshot_data.encode("utf-8"))
    new_version.save()
    return


@frappe.whitelist()
def get_doc_version_list(entity_name):
    if not frappe.has_permission(
        doctype="DMS File",
        doc=entity_name,
        ptype="write",
        user=frappe.session.user,
    ):
        raise frappe.PermissionError("You do not have permission to view this file")
    return frappe.get_list(
        "DMS Document Version",
        filters={"parent_entity": entity_name},
        order_by="creation desc",
        fields=["*"],
    )


@frappe.whitelist()
def create_auth_token(entity_name):
    if not frappe.has_permission(
        doctype="DMS File",
        doc=entity_name,
        ptype="read",
        user=frappe.session.user,
    ):
        raise frappe.PermissionError("You do not have permission to view this file")
    settings = frappe.get_single("DMS Site Settings")
    key = settings.get_password("jwt_key", raise_exception=False)
    return jwt.encode(
        {"name": entity_name, "expiry": (datetime.now() + timedelta(minutes=1)).timestamp()},
        key=key,
    )


@frappe.whitelist(allow_guest=True)
def get_file_content(entity_name, trigger_download=0, jwt_token=None):
    """
    Stream file content and optionally trigger download

    :param entity_name: Document-name of the file whose content is to be streamed
    :param trigger_download: 1 to trigger the "Save As" dialog. Defaults to 0
    :type trigger_download: int
    :raises ValueError: If the DMSEntity doc does not exist or is not a file
    :raises PermissionError: If the current user does not have permission to read the file
    :raises FileLockedError: If the file has been writer-locked

    JWT tokens are a vulnerability - if used, they bypass all permissions and give the file.
    Only the file name and secret token is needed to get access to all files.

    A more secure way would be a DB-stored auth token that can only be created by someone with read access.
    """
    if jwt_token:
        settings = frappe.get_single("DMS Site Settings")
        auth = jwt.decode(jwt_token, key=settings.get_password("jwt_key"), algorithms=["HS256"])
        if datetime.now().timestamp() > auth["expiry"] or auth["name"] != entity_name:
            raise frappe.PermissionError("You do not have permission to view this file")
    elif not frappe.has_permission(
        doctype="DMS File",
        doc=entity_name,
        ptype="read",
        user=frappe.session.user,
    ):
        raise frappe.PermissionError("You do not have permission to view this file")

    trigger_download = int(trigger_download)
    dms_file = frappe.get_value(
        "DMS File",
        {"name": entity_name, "is_active": 1},
        [
            "is_group",
            "is_link",
            "path",
            "title",
            "mime_type",
            "file_size",
            "is_active",
            "owner",
            "document",
        ],
        as_dict=1,
    )
    if not dms_file or dms_file.is_group or dms_file.is_link or dms_file.is_active != 1:
        frappe.throw("Not found", frappe.NotFound)

    if dms_file.document:
        html = frappe.get_value("DMS Document", dms_file.document, "raw_content")
        return html
    else:
        manager = FileManager()
        return send_file(
            manager.get_file(dms_file.path),
            mimetype=dms_file.mime_type,
            as_attachment=trigger_download,
            conditional=True,
            max_age=3600,
            download_name=dms_file.title,
            environ=frappe.request.environ,
        )


def stream_file_content(dms_file, range_header):
    """
    Stream file content and optionally trigger download

    :param entity_name: Document-name of the file whose content is to be streamed
    :param dms_file: DMS File record object
    """
    path = Path(frappe.get_site_path("private/files")) / dms_file.path
    size = os.path.getsize(path)
    byte1, byte2 = 0, None

    m = re.search("(\d+)-(\d*)", range_header)
    g = m.groups()

    if g[0]:
        byte1 = int(g[0])
    if g[1]:
        byte2 = int(g[1])

    length = size - byte1

    max_length = 20 * 1024 * 1024  # 20 MB in bytes
    if length > max_length:
        length = max_length

    if byte2 is not None:
        length = byte2 - byte1

    data = None
    with open(path, "rb") as f:
        f.seek(byte1)
        data = f.read(length)

    res = Response(data, 206, mimetype=mimetypes.guess_type(path)[0], direct_passthrough=True)
    res.headers.add("Content-Range", "bytes {0}-{1}/{2}".format(byte1, byte1 + length - 1, size))
    return res


@frappe.whitelist(allow_guest=True)
def list_entity_comments(entity_name):
    Comment = frappe.qb.DocType("Comment")
    User = frappe.qb.DocType("User")
    selectedFields = [
        Comment.comment_by,
        Comment.comment_email,
        Comment.creation,
        Comment.content,
        User.user_image,
    ]

    query = (
        frappe.qb.from_(Comment)
        .inner_join(User)
        .on(Comment.comment_email == User.name)
        .select(*selectedFields)
        .where(
            (Comment.comment_type == "Comment")
            & (Comment.reference_doctype == "DMS File")
            & (Comment.reference_name == entity_name)
        )
        .orderby(Comment.creation, order=Order.asc)
    )
    return query.run(as_dict=True)


def delete_background_job(entity, ignore_permissions):
    frappe.delete_doc("DMS File", entity, ignore_permissions=ignore_permissions)


@frappe.whitelist()
def delete_entities(entity_names=None, clear_all=None):
    """
    Delete DMSEntities

    :param entity_names: List of document-names
    :type entity_names: list[str]
    :raises ValueError: If decoded entity_names is not a list
    """
    if clear_all:
        entity_names = frappe.db.get_list(
            "DMS File", {"is_active": 0, "owner": frappe.session.user}, pluck="name"
        )
    elif isinstance(entity_names, str):
        entity_names = json.loads(entity_names)
    elif not isinstance(entity_names, list) or not entity_names:
        frappe.throw(f"Expected non-empty list but got {type(entity_names)}", ValueError)

    for entity in entity_names:
        frappe.get_doc("DMS File", entity).permanent_delete()


@frappe.whitelist()
def set_favourite(entities=None, clear_all=False):
    """
    Favouite or unfavourite DMSEntities for specified user

    :param entities: List[dict] of document names and whether favorite
    :type entity_names: list[str]
    :raises ValueError: If decoded entity_names is not a list
    """
    if clear_all:
        return frappe.db.delete("DMS Favourite", {"user": frappe.session.user})

    if not isinstance(entities, list):
        frappe.throw(f"Expected list but got {type(entities)}", ValueError)

    for entity in entities:
        existing_doc = frappe.db.exists(
            {
                "doctype": "DMS Favourite",
                "entity": entity["name"],
                "user": frappe.session.user,
            }
        )
        if not entity.get("is_favourite"):
            entity["is_favourite"] = not existing_doc

        if not isinstance(entity["is_favourite"], bool):
            entity["is_favourite"] = json.loads(entity["is_favourite"])

        if not entity["is_favourite"] and existing_doc:
            frappe.delete_doc("DMS Favourite", existing_doc)
        elif entity["is_favourite"] and not existing_doc:
            frappe.get_doc(
                {
                    "doctype": "DMS Favourite",
                    "entity": entity["name"],
                    "user": frappe.session.user,
                }
            ).insert()


# def toggle_is_active(doc):
#     doc.is_active = 0 if doc.is_active else 1
#     frappe.db.set_value('DMS File', doc.name, 'is_active',doc.is_active)
#     for child in doc.get_children():
#         toggle_is_active(child)


@frappe.whitelist()
def remove_or_restore(entity_names, team=None, ocr=False):
    """
    To move entities to or restore entities from the trash

    :param entity_names: List of document-names
    :type entity_names: list[str]
    """
    ocr = frappe.parse_json(ocr) if isinstance(ocr, str) else ocr
    if isinstance(entity_names, str):
        entity_names = json.loads(entity_names)
    if not isinstance(entity_names, list):
        frappe.throw(f"Expected list but got {type(entity_names)}", ValueError)

    if ocr:
        # OCR logic: delete or restore from OCR File table
        for entity in entity_names:
            doc = frappe.get_doc("DMS OCR", entity)
            doc.is_active = 0
            doc.save()
        return  # <--- THIS IS CRITICAL

    storage_data = storage_bar_data(team)

    def depth_zero_toggle_is_active(doc):
        if doc.is_active:
            flag = 0
        else:
            if (storage_data["limit"] - storage_data["total_size"]) < doc.file_size:
                frappe.throw("You're out of storage!", ValueError)
            flag = 1

        doc.is_active = flag
        folder_size = frappe.db.get_value("DMS File", doc.parent_entity, "file_size")
        frappe.db.set_value(
            "DMS File",
            doc.parent_entity,
            "file_size",
            folder_size + doc.file_size * (1 if flag else -1),
        )

        doc.save()

    for entity in entity_names:
        doc = frappe.get_doc("DMS File", entity)
        if not frappe.has_permission(
            doctype="DMS File", user=frappe.session.user, doc=doc, ptype="write"
        ):
            raise frappe.PermissionError("You do not have permission to remove this file")
        depth_zero_toggle_is_active(doc)


@frappe.whitelist(allow_guest=True)
def call_controller_method(entity_name, method):
    """
    Call a whitelisted DMS File controller method

    :param entity_name: Document-name of the document on which the controller method is to be called
    :param method: The controller method to be called
    :raises ValueError: If the entity does not exist
    :return: The result of the controller method
    """
    # broken
    dms_file = frappe.get_doc("DMS File", frappe.local.form_dict.pop("entity_name"))
    if not dms_file:
        frappe.throw("Entity does not exist", ValueError)
    method = frappe.local.form_dict.pop("method")
    dms_file.is_whitelisted(method)
    frappe.local.form_dict.pop("cmd")
    return dms_file.run_method(method, **frappe.local.form_dict)


@frappe.whitelist()
def remove_recents(entity_names=[], clear_all=False):
    """
    Clear recent DMSEntities for specified user

    :param entity_names: List of document-names
    :type entity_names: list[str]
    :raises ValueError: If decoded entity_names is not a list
    """

    if clear_all:
        return frappe.db.delete("DMS Entity Log", {"user": frappe.session.user})

    if not isinstance(entity_names, list):
        frappe.throw(f"Expected list but got {type(entity_names)}", ValueError)

    for entity in entity_names:
        existing_doc = frappe.db.exists(
            {
                "doctype": "DMS Entity Log",
                "entity_name": entity,
                "user": frappe.session.user,
            }
        )
        if existing_doc:
            frappe.delete_doc("DMS Entity Log", existing_doc)


@frappe.whitelist()
def get_children_count(dms_file):
    children_count = frappe.db.count("DMS File", {"parent_entity": dms_file, "is_active": 1})
    return children_count


@frappe.whitelist()
def does_entity_exist(name=None, parent_entity=None):
    result = frappe.db.exists("DMS File", {"parent_entity": parent_entity, "title": name})
    return bool(result)


def auto_delete_from_trash():
    days_before = (date.today() - timedelta(days=30)).isoformat()
    result = frappe.db.get_all(
        "DMS File",
        filters={"is_active": 0, "last_modified": ["<", days_before]},
        fields=["name"],
    )
    delete_entities(result)


def clear_deleted_files():
    print("DELETINGGG")
    days_before = (date.today() + timedelta(days=30)).isoformat()
    result = frappe.db.get_all(
        "DMS File",
        filters={"is_active": -1, "modified": ["<", days_before]},
        fields=["name"],
    )
    print(result)
    for entity in result:
        doc = frappe.get_doc("DMS File", entity, ignore_permissions=True)
        doc.delete()
        print("deleted", doc)


@frappe.whitelist()
def get_title(entity_name):
    """
    Toggle allow download for entity

    """
    if not frappe.has_permission(
        doctype="DMS File", doc=entity_name, ptype="write", user=frappe.session.user
    ):
        frappe.throw("Not permitted", frappe.PermissionError)
    return frappe.db.get_value("DMS File", entity_name, "title")


@frappe.whitelist()
def move(entity_names, new_parent=None, is_private=None):
    """
    Move file or folder to the new parent folder

    :param new_parent: Document-name of the new parent folder. Defaults to the user directory
    :raises NotADirectoryError: If the new_parent is not a folder, or does not exist
    :raises FileExistsError: If a file or folder with the same name already exists in the specified parent folder
    :return: DMSEntity doc once file is moved
    """
    print("HAHAHAH", entity_names)
    if isinstance(entity_names, str):
        entity_names = json.loads(entity_names)
    if not entity_names or not isinstance(entity_names, list):
        frappe.throw(f"Expected a non-empty list but got {type(entity_names)}", ValueError)

    for entity in entity_names:
        doc = frappe.get_doc("DMS File", entity)
        res = doc.move(new_parent, is_private)
    print(res)
    if res["title"] == "DMS - " + res["team"]:
        res["title"] = "Home" if res["is_private"] else "Team"

    return res


@frappe.whitelist()
def search(query, team):
    """
    Basic search implementation
    """
    text = frappe.db.escape(" ".join(k + "*" for k in query.split()))
    user = frappe.db.escape(frappe.session.user)
    team = frappe.db.escape(team)
    try:
        result = frappe.db.sql(
            f"""
        SELECT  `tabDMS File`.name,
                `tabDMS File`.title,
                `tabDMS File`.is_group,
                `tabDMS File`.is_link,
                `tabDMS File`.mime_type,
                `tabDMS File`.document,
                `tabDMS File`.color,
                `tabUser`.name AS user_name,
                `tabUser`.user_image,
                `tabUser`.full_name
        FROM `tabDMS File`
        LEFT JOIN `tabUser` ON `tabDMS File`.`owner` = `tabUser`.`name`
        WHERE `tabDMS File`.team = {team}
            AND `tabDMS File`.`is_active` = 1
            AND (`tabDMS File`.`owner` = {user} OR `tabDMS File`.is_private = 0)
            AND `tabDMS File`.`parent_entity` <> ''
            AND MATCH(title) AGAINST ({text} IN BOOLEAN MODE)
        GROUP  BY `tabDMS File`.`name`
        """,
            as_dict=1,
        )
        for r in result:
            r["file_type"] = get_file_type(r)
        return result
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Frappe DMS Search Error")
        return {"error": str(e)}


@frappe.whitelist()
def get_ancestors_of(entity_name):
    """
    Return all parent nodes till the root node
    """
    # CONCAT_WS('/', t.title, gp.path),
    entity_name = frappe.db.escape(entity_name)
    result = frappe.db.sql(
        f"""
        WITH RECURSIVE generated_path as (
        SELECT
            `tabDMS File`.name,
            `tabDMS File`.parent_entity
        FROM `tabDMS File`
        WHERE `tabDMS File`.name = {entity_name}

        UNION ALL

        SELECT
            t.name,
            t.parent_entity
        FROM generated_path as gp
        JOIN `tabDMS File` as t ON t.name = gp.parent_entity)
        SELECT name FROM generated_path;
    """,
        as_dict=0,
    )
    # Match the output of frappe/nested.py get_ancestors_of
    flattened_list = [item for sublist in result for item in sublist]
    flattened_list.pop(0)
    return flattened_list


@frappe.whitelist()
def get_translate():
    return {
        l["old_name"]: l["name"]
        for l in frappe.get_list("DMS File", fields=["old_name", "name"])
        if l["old_name"]
    }


@frappe.whitelist()
def export_media(entity_name):
    return frappe.get_list(
        "DMS File", filters={"parent_entity": entity_name}, fields=["name", "title"]
    )
