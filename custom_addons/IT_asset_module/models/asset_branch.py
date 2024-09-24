from odoo import models, fields, api, _, exceptions


class AssetBranch(models.Model):
    _name = "asset.branch"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Branch")
    stock_location = fields.Many2one('stock.location', string="Stock Location")
    regional_wh_manager = fields.Many2one('res.users', string="Regional WH Manager")
    asset_reorder = fields.One2many('asset.reordering', 'branch_id', string="Reorder")

    def _get_count(self, a_list):
        """Return the count of item in a list"""
        a_dict = {}
        set_list = set(a_list)
        for item in set_list:
            a_dict.update({item: a_list.count(item)})
        return a_dict

    def process_scheduler(self):
        self.asset_reorder.unlink()
        asset_rec = self.env['account.asset.asset'].search([('state', '=', 'open'),
                                                              ('asset_status', '=', 'unallocated')])

        new_dict = {}
        asset_records = []
        out_dict = {}

        for record in asset_rec:
            if record.initial_location:
                for branch_rec in self.search([]):
                    if record.initial_location.name == branch_rec.name:
                        res = {branch_rec.name: record.asset_model.name}
                        asset_records.append(res)

        for in_d in asset_records:
            for k, v in in_d.items():
                out_dict.setdefault(k, []).append(v)

        for item in out_dict:
            a = self.get_count(out_dict[item])
            new_dict.update({item: a})

        for location_obj in new_dict:
            branch_obj = self.search([('name', '=', location_obj)])
            if branch_obj:
                branch_obj.asset_reorder.unlink()
                for value, qty in new_dict[location_obj].items():
                    self.asset_reorder.create({
                        'model_id': value,
                        'branch_id': branch_obj.id,
                        'qty': qty
                    })

            for get_branch in branch_obj.asset_reorder:
                model_rec = self.env['asset.model'].search([('name', '=', get_branch.model_id)])
                if get_branch.qty <= model_rec.reordering_rule:
                    mail_mail = self.env['mail.mail']
                    notification_body = "<p>Dear " + str(branch_obj.regional_wh_manager.name) + ",</p> <p>" \
                                        + str(get_branch.model_id) + " for " + str(location_obj) + \
                                        " is getting out of stock."\
                                        + "<p>Thanks</p>" \
                                        + "<p>Asset MGT team.</p>"

                    notification_body_mail_values = {
                        'auto_delete': True,
                        'body_html': notification_body,
                        'email_cc': False,
                        'email_to': str(branch_obj.regional_wh_manager.login),
                        'mail_server_id': False,
                        'model': 'asset.branch',
                        'subject': "Asset Reorder."
                    }

                    notification_id = mail_mail.sudo().create(notification_body_mail_values)
                    notification_id.sudo().send()


class AssetReRecord(models.Model):
    _name = 'asset.reordering'

    model_id = fields.Char(string="Model")

    branch_id = fields.Many2one('asset.branch', string="Branch")

    qty = fields.Integer(string="Qty")



