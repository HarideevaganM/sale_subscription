# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BbisMrpRepairOrderInherit(models.Model):
    _inherit = 'repair.order'

    #@api.multi
    @api.depends('repair_job_type')
    def _get_new_device_no(self):
        for r in self:
            if r.repair_job_type == 'defective_device_replacement':
                r.new_device_no_tmp = r.diff_lot_id.name
            elif r.repair_job_type in ('removal', 'removal_returned'):
                r.new_device_no_tmp = ''
            else:
                r.new_device_no_tmp = r.lot_id.name

    #@api.multi
    @api.depends('repair_job_type')
    def _get_new_vehicle(self):
        for r in self:
            if r.repair_job_type == 're_installation':
                if r.service_sub_type in ('exist_reinstall', 'new_reinstall'):
                    r.new_vehicle_tmp = r.vechicle_id.name
                    r.old_vehicle_tmp = ''
                elif r.service_sub_type == 'remove_reinstall':
                    r.new_vehicle_tmp = r.vechicle_id.name
                    r.old_vehicle_tmp = r.vehicle_id.name
                elif r.service_sub_type in ('remove_retain', 'remove_return'):
                    r.new_vehicle_tmp = ''
                    r.old_vehicle_tmp = r.vehicle_id.name
                else:
                    r.new_vehicle_tmp = r.vehicle_id.name
                    r.old_vehicle_tmp = r.vehicle_id.name
            else:
                r.new_vehicle_tmp = ''
                r.old_vehicle_tmp = ''

    #@api.multi
    @api.depends('picking_ids')
    def _get_new_location(self):
        for r in self:
            if r.repair_job_type == 'defective_device_replacement':
                res = self.env['stock.picking'].search([('repair_id', '=', r.id),
                                                        ('picking_type_code', '=', 'outgoing'),
                                                        ('state', '=', 'done')], limit=1)
                new_location = res.location_dest_id.display_name
                old_location = res.location_id.display_name
            else:
                res = self.env['stock.picking'].search([('repair_id', '=', r.id),
                                                        ('picking_type_code', '=', 'incoming'),
                                                        ('state', '=', 'done')], limit=1)
                new_location = res.location_id.display_name
                old_location = res.location_dest_id.display_name

            if res:
                r.new_location_tmp = new_location
                r.old_location_tmp = old_location

    new_device_no_tmp = fields.Char(compute='_get_new_device_no',
                                    string='New Device No.', readonly=True, store=False)
    new_vehicle_tmp = fields.Char(compute='_get_new_vehicle',
                                    string='New Vehicle', readonly=True, store=False)
    old_vehicle_tmp = fields.Char(compute='_get_new_vehicle',
                                  string='Old Vehicle', readonly=True, store=False)
    new_location_tmp = fields.Char(compute='_get_new_location',
                                  string='New Location', readonly=True, store=False)
    old_location_tmp = fields.Char(compute='_get_new_location',
                                   string='Old Location', readonly=True, store=False)

    @api.onchange('location_id')
    def onchange_location_id(self):
        """
        Remove default onchange
        Because under Support Ticket, you already defining the Source and Destination Location
        So make the destination location the same
        """
        self.location_dest_id = self.location_dest_id





