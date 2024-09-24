from odoo import api, models, _
from odoo.exceptions import ValidationError


class BbisServiceQuotationOrderReport(models.AbstractModel):
    _name = 'report.bbis_reports.service_quotation_order'
    _description = 'BBIS Service Quotation / Order Report'

    #@api.multi
    def convert_num_to_word(self, data, amount):
        amount_in_words = data.company_id.currency_id.with_context(lang=data.partner_id.lang or 'es_ES'). \
            amount_to_text(amount).title()
        return amount_in_words + ' ONLY'

    # Get discount in amount per line
    def _get_discount(self, line):
        sub_total = line.product_uom_qty * line.price_unit
        discount = sub_total * (line.discount / 100)
        return discount

    #@api.multi
    def _get_ticket_no(self, so):
        wo_order = int(so.support_id)
        ticket = self.env["website.support.ticket"].search([('customer_support_id', '=', wo_order)], limit=1)
        return ticket

    #@api.multi
    def _get_rma(self, wo_order, ticket):
        rma = self.env["repair.order"].search([('customer_support_id', '=', wo_order), ('support_id', '=', ticket)],
                                            limit=1)
        return rma

    def _get_price_vat(self, order_ids):
        total_vat = []
        for order in order_ids:
            tax_amount = sum(order.tax_id.mapped('amount'))/100
            price_vat = order.price_unit * tax_amount
            total_vat.append(price_vat)
        return sum(total_vat)

    # Get Vehicle Details
    def _get_vehicle_details(self, sale_orders):
        vehicles = []
        for order_line in sale_orders.mapped('vehicle_details_ids'):
            vehicles.append({
                'client': order_line.partner_id.name,
                'device_name': order_line.device_id.name,
                'vehicle': order_line.vehicle_id.name,
                'vehicle_name': order_line.vehicle_id.vehicle_name,
                'serial': order_line.serial_no_id.name,
                'start_date': order_line.start_date,
                'end_date': order_line.end_date,
            })

        return vehicles

    @api.model
    def _get_report_values(self, ids, data=None):
        docs = self.env['sale.order'].search([('id', 'in', docids)])

        # vehicle_details = self._get_vehicle_details(docs)

        for doc in docs:
            if doc.sale_type not in ('service', 'support', 'purchase'):
                raise ValidationError(_('You can only print Service Quotation on this report.'))

        single_discounts = []
        for order in docs.mapped('order_line'):
            single_discounts.append(float(order.discount_amount))

        return {
            'doc_model': 'sale.order',
            'docs': docs,
            'convert_num_to_word': self.convert_num_to_word,
            'get_price_vat': self.get_price_vat,
            'vehicles': self._get_vehicle_details,
            'get_ticket_no': self.get_ticket_no,
            'get_rma': self.get_rma,
            'get_discount': self.get_discount,
            'single_total_discount': sum(single_discounts),
        }
