# -*- coding: utf-8 -*-
"""Allow third-party (Streckengeschaeft) addresses on sales/purchase documents.

ERPNext's AccountsController.validate_company_linked_addresses enforces that all
linked address fields belong to the transaction's company. For third-party deals
Tobien Trading routinely uses:

    - a delivery/loading address (sales: ``dispatch_address_name``) that is not
      our own company address, and
    - a shipping address (purchase: ``shipping_address``) at a third-party stock
      location.

Upstream only exempts these two fields when the drop-ship feature is used
(``is_drop_ship``), which we do not want to enable. This override re-implements
the validation, always skipping the dispatch/shipping field while keeping the
``company_address`` / ``billing_address`` checks strict (those must remain our
own company addresses).

Wired up via ``override_doctype_class`` in hooks.py so no ERPNext code is
touched and the behaviour survives ``bench update``.
"""

import frappe
from frappe import _, bold

from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from erpnext.buying.doctype.supplier_quotation.supplier_quotation import SupplierQuotation
from erpnext.selling.doctype.quotation.quotation import Quotation
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt


class AllowThirdPartyAddressMixin:
	def validate_company_linked_addresses(self):
		sales_doctypes = ("Quotation", "Sales Order", "Delivery Note", "Sales Invoice")
		purchase_doctypes = ("Purchase Order", "Purchase Receipt", "Purchase Invoice", "Supplier Quotation")

		if self.doctype in sales_doctypes:
			# dispatch_address_name (loading address) may be a third party
			address_fields = ["company_address"]
		elif self.doctype in purchase_doctypes:
			# shipping_address (third-party stock location) may be a third party
			address_fields = ["billing_address"]
		else:
			return

		for field in address_fields:
			address = self.get(field)

			if address and not frappe.db.exists(
				"Dynamic Link",
				{
					"parent": address,
					"parenttype": "Address",
					"link_doctype": "Company",
					"link_name": self.company,
				},
			):
				frappe.throw(
					_("{0} does not belong to the Company {1}.").format(
						_(self.meta.get_label(field)), bold(self.company)
					)
				)


class CustomQuotation(AllowThirdPartyAddressMixin, Quotation):
	pass


class CustomSalesOrder(AllowThirdPartyAddressMixin, SalesOrder):
	pass


class CustomDeliveryNote(AllowThirdPartyAddressMixin, DeliveryNote):
	pass


class CustomSalesInvoice(AllowThirdPartyAddressMixin, SalesInvoice):
	pass


class CustomPurchaseOrder(AllowThirdPartyAddressMixin, PurchaseOrder):
	pass


class CustomPurchaseReceipt(AllowThirdPartyAddressMixin, PurchaseReceipt):
	pass


class CustomPurchaseInvoice(AllowThirdPartyAddressMixin, PurchaseInvoice):
	pass


class CustomSupplierQuotation(AllowThirdPartyAddressMixin, SupplierQuotation):
	pass
