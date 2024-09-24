# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BBISITCJobCardInherit(models.Model):
    _inherit = "job.card"

    itc_permit_count = fields.Integer(compute="count_itc_permit", string="ITC Permit")

    # Find out the count of itc permits.
    def count_itc_permit(self):
        for rec in self:
            permit_ids = self.env['itc.permit'].search([('job_card_id', '=', rec.id)])
            if permit_ids:
                rec.itc_permit_count = len(permit_ids)



    # Code for adding the ITC Permit in job card.
    #@api.multi
    def itc_permit_create(self):
        job_card_itc = self.env['itc.permit'].search([('job_card_id', '=', self.id)])
        if job_card_itc:
            raise ValidationError(_("Already there is an ITC Permit entered for this Vehicle."))

        itc_permits_obj = self.env['itc.permit']
        check_itc_dept = self.env.user.has_group('bbis_itc_permits.group_itc_permit_users')
        if not check_itc_dept:
            raise UserError(_("You are not able to create ITC Permits"))

        # Creating the ITC permit by using the values from Job Card.
        values = {
            'sale_order_id': self.sale_order_id.id,
            'vehicle_no': self.vehicle_number.id,
            'device_no': self.device_serial_number_new_id.name,
            'sim_card_no': self.gsm_number,
            'chassis_no': self.chassis_no,
            'partner_id': self.company_id.id,
            'po_number': self.sale_order_id.purchase_order_no,
            'po_date': self.sale_order_id.purchase_order_date,
            'job_card_id': self.id,
            'state': 'draft'
        }
        itc_permits_obj.create(values)

    # Redirect to the ITC screen from job card while clicking the smart button.
    def number_of_itc_permits(self):
        permit_ids = self.env['itc.permit'].search([('job_card_id', '=', self.id)])
        return {
            'name': _('Permits'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'itc.permit',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', permit_ids.ids)],
        }
