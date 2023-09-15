from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_activities_and_comments(ref_docname):
	events = get_activities(ref_docname)
	comments = get_comments(ref_docname)
	
	activities = events + comments
	
	return {"activities": activities}
	
def get_activities(ref_docname):
	sql_query = ("""
		SELECT 
		`tabEvent`.`name`,
		`tabEvent`.`subject`,
		`tabEvent`.`event_category`,
		`tabEvent`.`starts_on`,
		`tabEvent`.`ends_on`,
		`tabEvent`.`description`
		FROM `tabEvent`
		LEFT JOIN `tabEvent Participants` ON `tabEvent`.`name` = `tabEvent Participants`.`parent`
		WHERE `tabEvent Participants`.`reference_doctype` = 'Opportunity' 
		AND  `tabEvent Participants`.`reference_docname` = '{ref_docname}' 
		AND  `tabEvent`.`status` ='Open' 
		ORDER BY `tabEvent`.`creation` DESC
		LIMIT 3""".format(ref_docname=ref_docname))
	events = frappe.db.sql(sql_query, as_dict=True)

	return events

def get_comments(ref_docname):
	sql_query = ("""
		SELECT 
		`tabComment`.`name`,
		`tabComment`.`creation`,
		`tabEmployee`.`employee_name`,
		`tabComment`.`content`
		FROM `tabComment`
		LEFT JOIN `tabEmployee` ON `tabComment`.`comment_email` = `tabEmployee`.`user_id`
		WHERE `tabComment`.`reference_doctype` = 'Opportunity'
		AND  `tabComment`.`comment_type` = 'Comment' 
		AND  `tabComment`.`reference_name` = '{ref_docname}'
		ORDER BY `tabComment`.`creation` DESC
		LIMIT 3""".format(ref_docname=ref_docname))
	comments = frappe.db.sql(sql_query, as_dict=True)

	return comments
