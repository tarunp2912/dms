# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from dms.api.notifications import notify_share


class DMSPermission(Document):
    def after_insert(self):
        if self.user:
            frappe.enqueue(
                notify_share,
                queue="long",
                job_id=f"fdocperm_{self.name}",
                deduplicate=True,
                timeout=None,
                now=False,
                at_front=False,
                entity_name=self.entity,
                docperm_name=self.name,
            )
