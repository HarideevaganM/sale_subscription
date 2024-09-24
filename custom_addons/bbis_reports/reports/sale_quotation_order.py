from odoo import api, models, _
from odoo.exceptions import ValidationError


class BbisSaleQuotatioOrderReport(models.AbstractModel):
    _name = 'report.bbis_reports.sale_quotation_order'
    _description = 'BBIS Sale Quotation and Order Report'

    #@api.multi
    def convert_num_to_word(self, data, amount):
        amount_in_words = data.currency_id.with_context(lang=data.partner_id.lang or 'es_ES'). \
            amount_to_text(amount).title()
        return amount_in_words + ' ONLY'

    def _get_lease_subtotal(self, order):
        lease_subtotal = (float(order.product_uom_qty) * int(order.contract_period)) * float(order.price_unit)
        return lease_subtotal

    def _get_price_vat(self, order_ids):
        total_vat = []
        for order in order_ids:
            tax_amount = sum(order.tax_id.mapped('amount'))/100
            price_vat = order.price_unit * tax_amount
            total_vat.append(price_vat)
        return sum(total_vat)

    # For renewal, rental, lease sales
    def _prepare_group_lines(self, sale_orders):
        for order_id in sale_orders:
            contract_period = int(order_id.contract_period)
            sale_type = order_id.sale_type
            self.env.cr.execute(
                """
                SELECT
                pp.id as product_id,
                so.order_id,
                MAX(so.id) as so_id,
                MIN(so.sequence) as order_sequence,
                pt.default_code,
                pt.name,
                MAX(so.name) as desc,
                SUM(so.product_uom_qty) total_quantity,
                SUM(so.discount_amount) total_discount,
                so.price_unit
                FROM sale_order_line so
                INNER JOIN product_product pp ON (pp.id = so.product_id)
                INNER JOIN product_template pt ON (pt.id = pp.product_tmpl_id)
                WHERE so.order_id = %d
                GROUP BY pt.name, pt.default_code, so.price_unit, pp.id, so.order_id
                ORDER BY order_sequence ASC, so_id ASC
                """ % int(order_id))

            grouped_sale_orders = self.env.cr.dictfetchall()

            group_so_lines = []
            for line in grouped_sale_orders:
                prod_id = line['product_id']
                order_id = line['order_id']
                price_unit = line['price_unit']
                order_lines = self.env['sale.order.line'].search([('product_id', '=', prod_id),
                                                                         ('order_id', '=', order_id),
                                                                         ('price_unit', '=', price_unit)])
                output_vat = []
                for prod in order_lines:
                    subtotal = prod.product_uom_qty * prod.price_unit

                    if sale_type == 'pilot':
                        after_discount = subtotal - prod.discount_amount
                    else:
                        # check if compute contract or not
                        compute_contract = prod.product_id.type in ('product', 'service') and prod.product_id.categ_id.enable_total

                        if compute_contract:
                            after_discount = (subtotal - prod.discount_amount) * contract_period
                            line['total_discount'] = line['total_discount'] * contract_period
                            line['contract_period'] = contract_period
                        else:
                            after_discount = subtotal - prod.discount_amount

                    amount = sum(prod.tax_id.mapped('amount'))
                    output_vat.append((after_discount * amount) / 100)

                sum_output_vat = sum(output_vat)
                subtotal = line['price_unit'] * line['total_quantity']

                if sale_type == 'pilot':
                    line['total_price_exclude_vat'] = subtotal - line['total_discount']
                    line['total_amount'] = subtotal + sum_output_vat - line['total_discount']
                else:
                    # get product type and product category
                    product_line = self.env['product.product'].browse(prod_id)

                    # check if you are going to compute contract period
                    compute_contract = product_line.type in ('product', 'service') and product_line.categ_id.enable_total

                    if compute_contract:
                        line['total_price_exclude_vat'] = (subtotal * contract_period) - line['total_discount']
                        line['total_amount'] = (subtotal * contract_period) + sum_output_vat - line['total_discount']
                    else:
                        line['total_price_exclude_vat'] = subtotal - line['total_discount']
                        line['total_amount'] = subtotal + sum_output_vat - line['total_discount']

                line['total_vat'] = sum_output_vat

                group_so_lines.append(line)

        return group_so_lines

    # Get Vehicle Details
    # Added sorted in the ORM method for sorting the vehicle details depends on the subscription start date.
    def _get_vehicle_details(self, sale_orders):
        vehicles = []
        for order_line in sale_orders.mapped('vehicle_number_ids').sorted(lambda move: move.start_date):
            vehicles.append({
                'serial': order_line.serial_no_id.name,
                'device': order_line.device_id.name,
                'vehicle': order_line.vehicle_id.name,
                'start_date': order_line.start_date,
                'end_date': order_line.end_date,
            })
        return vehicles

    @api.model
    def _get_report_values(self, ids, data=None):
        docs = self.env['sale.order'].search([('id', 'in', ids)])
        addons_discounts = []
        optional_discounts = []

        for doc in docs:
            if doc.sale_type in ('service', 'support'):
                raise ValidationError(_('You can only print Sales Quotation on this report.'))

            addons_discounts = doc.addons_accessories_line.mapped('discount_line')
            optional_discounts = doc.addons_service_line.mapped('discount_line')

        group_order_lines = self._prepare_group_lines(docs)
        vehicle_details = self._get_vehicle_details(docs)

        single_discounts = []
        for order in docs.mapped('order_line'):
            single_discounts.append(float(order.discount_amount))

        group_discounts = []
        for order in group_order_lines:
            group_discounts.append(float(order['total_discount']))

        return {
            'doc_model': 'sale.order',
            'docs': docs,
            'get_price_vat': self.get_price_vat,
            'convert_num_to_word': self.convert_num_to_word,
            'get_lease_subtotal': self.get_lease_subtotal,
            'group_order_lines': group_order_lines,
            # check if discount column will show/hide
            'group_total_discount': sum(group_discounts),
            'single_total_discount': sum(single_discounts),
            'addons_discounts': sum(addons_discounts),
            'optional_discounts': sum(optional_discounts),
            'vehicles': vehicle_details,
        }
