from odoo import api, fields, models, _


class BBISSaleSubscriptionInherit(models.Model):
    _inherit = 'sale.order'
    _description = 'Sale Subscription'

    # Added the new selection option in sales tag. - Not Renewed.
    # sales_tag = fields.Selection(
    #     selection_add=[
    #         ('not_renewed', 'Not Renewed')
    #     ],
    #     ondelete={
    #         'not_renewed': 'set default'
    #     },
    #     tracking=True  # Replacing track_visibility='onchange' with tracking=True
    # )

    # sub_status = fields.Selection(track_visibility='onchange')
    sale_type = fields.Selection(track_visibility='onchange')


# Adding the product change option in wizard and a message post.
class BBISSaleSubscriptionLineInherit(models.Model):
    _inherit = "sale.order.line"

    product_id = fields.Many2one('product.product', string='Product', domain="[('recurring_invoice','=',True)]",
                                 required=True, track_visibility='onchange')
