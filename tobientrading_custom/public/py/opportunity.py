import frappe
from frappe.desk.notifications import notify_mentions
from frappe.model.document import Document
from frappe.utils import cstr, now, today
from pypika import functions

@frappe.whitelist()
def get_open_activities(ref_doctype, ref_docname):
	events = get_open_events(ref_doctype, ref_docname)

	return {"events": events}

def get_open_events(ref_doctype, ref_docname):
	event = frappe.qb.DocType("Event")
	event_link = frappe.qb.DocType("Event Participants")

	query = (
		frappe.qb.from_(event)
		.join(event_link)
		.on(event_link.parent == event.name)
		.select(
			event.name,
			event.subject,
			event.event_category,
			event.starts_on,
			event.ends_on,
			event.description,
		)
		.where(
			(event_link.reference_doctype == ref_doctype)
			& (event_link.reference_docname == ref_docname)
			& (event.status == "Open")
		)
	)
	data = query.run(as_dict=True)

	return data
