from odoo import api, fields, models, _

class DeviceHistory(models.Model):
    _name = "device.history"
    
    name = fields.Char("Name")
    serial_number_id = fields.Many2one("stock.lot", "Device Serial Number")
    device_history_line = fields.One2many("device.history.line", "history_id", "Device History Line")
    
    # @api.multi
    def get_device_history(self):
        device_history = self.env["device.history.line"]
        self.env.cr.execute("""delete from device_history_line where history_id=%s """ % self.id)
        self.env.cr.execute("""select so.id sale_id ,so.name so_name,so.sale_type so_type from sale_order so join sale_order_line sol
                                on sol.order_id=so.id join stock_production_lot spl 
                                on spl.product_id=sol.product_id where spl.id=%s """ % self.serial_number_id.id)
        
        sale_order_id = self.env.cr.dictfetchall()
        for order in sale_order_id:
            self.env.cr.execute("""select co.id contract,co.contract_start_date start_date,co.contract_end_date end_date
                                    from contract_order co join project_project pp
                                    on pp.id=co.project_id join sale_order so on so.id=pp.sale_order_id 
                                    where so.id=%s """ % (order["sale_id"]))
            contract = self.env.cr.dictfetchall()
            device_history.create({
                    'sale_order_id': order["sale_id"],
                    'name': order["so_name"],
                    'sale_type': order["so_type"],
                    'history_id': self.id,
                              })
            for contract_id in contract:    
                device_history.create({                       
                        'contract_id': contract_id['contract'],
                        'contract_start_date': contract_id['start_date'],
                        'contract_end_date': contract_id['end_date'],
                })


class DeviceHistoryLine(models.Model):
    _name = "device.history.line"
    
    name = fields.Char("Sale Order Reference")
    history_id = fields.Many2one("device.history","Device History Reference")
    sale_order_id = fields.Many2one("sale.order","Sale Order")
    contract_id = fields.Many2one("contract.order","Contract")
    contract_start_date = fields.Date("Contract Start Date")
    contract_end_date = fields.Date("Contract End Date")
    sale_type = fields.Selection([('cash', 'Walk In/Cash Sale'),
                                  ('purchase', 'Purchase Sale'),
                                  ('lease', 'Lease Sale'),
                                  ('rental', 'Rental Sale'),
                                  ('pilot', 'Pilot Sale'),
                                  ('service', 'Service')], string='Sale Type')


class VehicleHistory(models.Model):
    _name = "vehicle.history"
    
    name = fields.Char("Name")
    vehicle_id = fields.Many2one("vehicle.master", "Vehicle number")
    vehicle_history_line = fields.One2many("vehicle.history.line", "history_id", "Vehicle History Line")
    
    @api.onchange('vehicle_id')
    def _get_vehicle_history(self):
        if self.vehicle_id:
            job_card_obj = self.env['job.card'].search(['|', ('vehicle_number', '=', self.vehicle_id.id), ('vehicle_number_old', '=', self.vehicle_id.id)])
            data = []
            for job in job_card_obj:
                vals = {'name': job.task_id.id}
                subscription_obj = self.env['sale.order'].search([('job_card_id', '=', job.id), ('is_subscription', '=', True)])
                for subscription in subscription_obj:
                    vals.update({
                        'history_id': self.id,
                        'subscription_id': subscription.id,
                        'subscription_status': subscription.subscription_status,
                    })
                data.append(vals)
            self.update({'vehicle_history_line': data})


class VehicleHistoryLine(models.Model):
    _name = "vehicle.history.line"

    name = fields.Many2one('project.task', "Job Order")
    history_id = fields.Many2one("vehicle.history", "Device History Reference")
    subscription_id = fields.Many2one('sale.order', 'Subscription',  domain=[('is_subscription', '=', True)])
    subscription_status = fields.Char(string='Subscription Status')
