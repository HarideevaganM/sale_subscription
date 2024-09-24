from odoo import api, models, _
from odoo.exceptions import ValidationError


class BbisSaleQuotatioOrderInclusiveReport(models.AbstractModel):
    _name = 'report.bbis_reports.sale_quotation_order_inclusive'
    _description = 'BBIS Sale Quotation and Order Report'

    #@api.multi
    def has_contract_period(self, order_line):
        has_contract = False

        for o in order_line:
            if o.product_id.type in ('product','service') and o.product_id.categ_id.enable_total:
                has_contract = True
                break
        return has_contract

    #@api.multi
    def convert_num_to_word(self, data, amount):
        amount_in_words = data.currency_id.with_context(lang=data.partner_id.lang or 'es_ES'). \
            amount_to_text(amount).title()
        return amount_in_words + ' ONLY'

    def _get_price_vat(self, order_ids):
        total_vat = []
        for order in order_ids:
            tax_amount = sum(order.tax_id.mapped('amount'))/100
            price_vat = order.price_unit * tax_amount
            total_vat.append(price_vat)
        return sum(total_vat)

    # check if order lines has unique products. only used for lease/rental
    def _get_unique_products(self, order_ids):
        products = []
        price_units = []
        for order in order_ids:
            if order.product_id not in products:
                products.append(order.product_id)

            if order.price_unit not in price_units:
                price_units.append(order.price_unit)

        data = {'products': len(products), 'price_units': len(price_units)}

        return data

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

        for order in docs:
            if not order.inclusive_order_line:
                raise ValidationError(_('There is no Inclusive Order Lines record. Please make sure to add.'))

            addons_discounts = order.addons_accessories_line.mapped('discount_line')
            optional_discounts = order.addons_service_line.mapped('discount_line')

            if order.sale_type in ('lease', 'rental'):
                amount_total = order.period_amount_total
            else:
                amount_total = order.amount_total

            if round(amount_total) != round(order.amount_total_inclusive):
                raise ValidationError(_('Order lines total amount ({}) is not equal to Inclusive order lines total '
                                        'amount ({}). Please make sure to make it equal.')
                                      .format(amount_total, order.amount_total_inclusive))

            for order_line in order.inclusive_order_line:
                if not len(order_line.order_line_ids):
                    raise ValidationError(_('Please remove items with Zero quantity or no Products added '
                                            'from the Order lines'))

        vehicle_details = self._get_vehicle_details(docs)

        single_discounts = []
        for order in docs.mapped('inclusive_order_line'):
            single_discounts.append(float(order.discount))

        return {
            'doc_model': 'sale.order',
            'docs': docs,
            'get_price_vat': self.get_price_vat,
            'convert_num_to_word': self.convert_num_to_word,
            'single_total_discount': sum(single_discounts),
            'addons_discounts': sum(addons_discounts),
            'optional_discounts': sum(optional_discounts),
            'vehicles': vehicle_details,
            'get_unique_products': self.get_unique_products,
            'has_contract_period': self.has_contract_period,
        }
