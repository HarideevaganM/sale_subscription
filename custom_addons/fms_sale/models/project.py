from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class ProjectInherit(models.Model):
    _inherit = "project.project"

    partner_id = fields.Many2one("res.partner", "Customer Name")
    job_number = fields.Char("Job Number")
    sale_order_id = fields.Many2one("sale.order", "Sale Reference")
    sale_type = fields.Selection([('cash', 'Walk In/Cash Sale'),
                                  ('purchase', 'Purchase Sale'),
                                  ('lease', 'Lease Sale'),
                                  ('rental', 'Rental Sale'),
                                  ], string='Sale Type')

    show_contract = fields.Boolean('Contract')
    ticket_id = fields.Many2one("website.support.ticket", "Ticket")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('project.project') or _('New')
        result = super(ProjectInherit, self).create(vals)
        return result


class ProjectTaskInherit(models.Model):
    _inherit = "project.task"

    # @api.multi
    def create_job_card(self):
        instruction_obj = self.env['job.instruction'].search([('job_id', '=', self.id)])
        project_obj = self.env['project.project'].search([('id', '=', self.project_id.id)])
        sale_obj = self.env['sale.order'].search([('id', '=', project_obj.sale_order_id.id)])
        job_card = self.env['job.card']
        material_req = self.env['material.purchase.requisition']
        for line in instruction_obj:
            if line.is_job_assigned is not True:
                for count in range(line.no_of_device):
                    job_card.create({
                        'engineer_id': line.user_id.id,
                        'supervisor_id': line.supervisor_id.id,
                        'task_id': self.id,
                        'company_id': self.partner_id.id,
                        'sale_type': sale_obj.sale_type,
                        'sale_order_id': sale_obj.id,
                        'installation_location_id': line.installation_location_id.id,
                        'job_card_type': 'sale',
                    })
                self.env.cr.execute("""update job_instruction set is_job_assigned=true where id=%s""" % line.id)

                self.env.cr.execute("""select  hr.id as id,hr.department_id as dept,hr.dest_location_id as eng_location
                                        from hr_employee hr join resource_resource rr
                                        on hr.resource_id=rr.id where rr.user_id=%s""" % line.user_id.id)
                hr_obj = self.env.cr.dictfetchall()
                if len(hr_obj) != 0:
                    source_location_obj = self.env['stock.location'].search([('location_code', '=', 'WH/S')])
                    picking_type_obj = self.env['stock.picking.type'].search([('picking_code', '=', 'IT')])
                    for emp_id in hr_obj:
                        if emp_id['eng_location']:
                            values = {
                                'task_id': self.id,
                                'employee_id': emp_id['id'],
                                'department_id': emp_id['dept'],
                                'project_id': self.project_id.id,
                                'partner_id': self.partner_id.id,
                                'location_id': source_location_obj.id,
                                'custom_picking_type_id': picking_type_obj.id,
                                'dest_location_id': emp_id['eng_location'],
                                'state': 'approve'
                            }
                            res = self.env['material.purchase.requisition'].create(values)
                            sale_order_line = self.env['sale.order.line'].search([('order_id', '=', sale_obj.id)])
                            material_req_line = self.env['material.purchase.requisition.line']
                            for order_line in sale_order_line:
                                if order_line.product_id.type == 'product':
                                    vals = {
                                        'requisition_type': 'internal',
                                        'product_id': order_line.product_id.id,
                                        'description': order_line.name,
                                        'qty': line.no_of_device,
                                        'uom': order_line.product_uom.id,
                                        'requisition_id': res.id
                                    }
                                    material_req_line.create(vals)
                        else:
                            raise UserError(_("Please check whether the location for this employee has been mapped"))
                else:
                    raise UserError(_("Please check whether the employee has been created for this user"))
            else:
                return None

    # To Count Job Card ##
    # @api.multi
    def count_job_card(self):
        for rec in self:
            rec.job_card_count = len(self.env["job.card"].search([('task_id', '=', rec.id)]).ids)

    # To view Job Card ##
    # @api.multi
    def open_job_card_view(self):
        var = []
        if self._context is None:
            context = {}
        # res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'job_order_action')
        res = self.env.ref('fms_sale.job_order_action')
        res['context'] = self._context
        job_order_id = self.env['job.card'].search([('task_id', '=', self.id)])
        for i in job_order_id:
            var.append(i.id)
        res['domain'] = [('id', 'in', var)]
        return res

    # To view material requisition view #
    # @api.multi
    def open_material_requisition_views(self):
        var = []
        # res = self.env['ir.actions.act_window'].for_xml_id('odoo_job_costing_management','action_material_purchase_requisition_job_costing')
        res = self.env.ref('odoo_job_costing_management.action_material_purchase_requisition_job_costing')
        material_req = self.env['material.purchase.requisition'].search([('task_id', '=', self.id)])
        for i in material_req:
            var.append(i.id)
        res['domain'] = [('id', 'in', var)]
        return res

    # To count material requisition view #
    # @api.multi
    def count_material_requisition(self):
        for rec in self:
            rec.count_requisition = len(self.env["material.purchase.requisition"].search([('task_id', '=', rec.id)]).ids)

    # Location and region as many2many field
    partner_id = fields.Many2one("res.partner", "Customer Name", related='project_id.partner_id', store=True)
    installation_region_ids = fields.Many2many('installation.region', string='Installation Region')
    installation_location_ids = fields.Many2many('installation.location', string='Installation Location')
    installation_country_id = fields.Many2one('res.country', 'Installation Country', ondelete='restrict')
    job_card_count = fields.Integer(compute="count_job_card", string="Job Card")
    count_requisition = fields.Integer(compute="count_material_requisition", string="Create Stock Move")
    work_order = fields.Char("Work Order")
    support_id = fields.Many2one("website.support.ticket", "Ticket")


class JobCard(models.Model):
    _name = "job.card"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('job.card') or _('New')
        result = super(JobCard, self).create(vals)
        return result

    ## To Count Certificate ##
    # @api.multi
    def certificate_count(self):
        for rec in self:
            rec.count_certificate = len(self.env["installation.certificate"].search([('job_card_id', '=', rec.id)]).ids)

    ## To Create Certificate ##
    # @api.multi
    def installation_certificate(self):
        certificate_obj = self.env["installation.certificate"]
        vals = {
            'serial_no': self.device_serial_number_new_id.id,
            'vehicle_number': self.vehicle_number.id,
            'fleet_description': self.vehicle_description,
            'vin_no': self.chassis_no,
            'job_card_id': self.id,
            'company_id': self.env.user.company_id.id,
            'partner_id': self.company_id.id,
            'installation_date': self.installation_date,
            'from_date': self.installation_date,
            'device_id': self.device_id.id,
        }
        certificate_obj.create(vals)

    ## To view Certificate ##
    # @api.multi
    def open_certificate_view(self):
        # res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'installation_certificate_action_id')
        # res = self.env.ref('fms_sale.installation_certificate_action_id')
        # print("---", res, "--res-\n")
        certificate_ids = self.env['installation.certificate'].search([('job_card_id', '=', self.id)])
        # res['domain'] = [('id', 'in', certificate_ids.ids)]
        return {
            'name': _('Installation Certificate'),
            'type': 'ir.actions.act_window',
            'res_model': 'installation.certificate',
            'domain': [('id', 'in', certificate_ids.ids)],
            'view_mode': 'tree,form',
        }

    ## To create Subscription ##
    # @api.multi
    def subscription_create(self):
        if self.task_id.support_id:
            subscription_obj = self.env['sale.order']
            subscription_device_id = self.env['sale.order'].search([('serial_no', '=', self.device_serial_number_new_id.id), ('is_subscription', '=', True)])
            if not subscription_device_id:
                if self.count_subscription != 1:
                    if self.env.user.has_group('account.group_account_manager') \
                            or self.env.user.has_group('account.group_account_invoice'):
                        line_obj = self.env["sale.order.line"].search([('order_id', '=', self.sale_order_id.id)])
                        values = {
                            'partner_id': self.task_id.support_id.partner_id and self.task_id.support_id.partner_id.id,
                            'code': 'SUB/' + self.name,
                            'template_id': 1,
                            'serial_no': self.device_serial_number_new_id.id,
                            'vehicle_number': self.vehicle_number,
                            'imei_no': self.imei_no,
                            'gsm_number': self.gsm_number,
                            'job_card_id': self.id,
                            'pricelist_id': self.task_id.support_id.partner_id.property_product_pricelist.id,
                            'activation_date': self.activation_date,
                            'installation_date': self.installation_date,
                            'is_subscription': True,
                        }
                        sale_subscription = subscription_obj.create(values)
                        if sale_subscription:
                            line_obj = self.env["sale.order.line"].search([('order_id', '=', self.id)])
                            line_value = {
                                'product_id': self.device_id.id,
                                'quantity': 1,
                                'price_unit': self.device_id.list_price,
                                'name': self.device_id.name,
                                'uom_id': self.device_id.uom_id.id,
                                'analytic_account_id': sale_subscription.id,

                            }
                            self.env['sale.order.line'].create(line_value)

                    else:
                        raise UserError(_("Only Account Persons Can Create The Subscription"))
                else:
                    raise UserError(_("You Can Create Only One Subscription For This Job Card"))
            else:
                raise UserError(_("Subscription for this serial no has already been created"))
        else:
            subscription_obj = self.env['sale.order']
            subscription_device_id = self.env['sale.order'].search([('serial_no', '=', self.device_serial_number_new_id.id), ('is_subscription', '=', True)])
            if not subscription_device_id:
                if self.count_subscription != 1:
                    if self.env.user.has_group('account.group_account_manager') \
                            or self.env.user.has_group('account.group_account_invoice'):
                        if self.sale_order_id:
                            if self.sale_order_id.subscription_template_id.name == 'Monthly':
                                subscription_temp = self.env['sale.order.template'].search([('name', '=', 'Monthly')])
                                values = {
                                    'sale_order_id': self.sale_order_id.id,
                                    'sale_type': self.sale_order_id.sale_type,
                                    'partner_id': self.sale_order_id.partner_id.id,
                                    'pricelist_id': self.sale_order_id.pricelist_id.id,
                                    'invoice_type': 'pre',
                                    'template_id': self.sale_order_id.subscription_template_id.id,
                                    'serial_no': self.device_serial_number_new_id.id,
                                    'vehicle_number': self.vehicle_number.id,
                                    'imei_no': self.imei_no,
                                    'gsm_number': self.gsm_number,
                                    'job_card_id': self.id,
                                    'activation_date': self.activation_date,
                                    'date_start': self.activation_date,
                                    'installation_date': self.installation_date,
                                    # 'subscription_period': self.sale_order_id.contract_period,
                                    'engineer_id': self.engineer_id.id,
                                    'device_id': self.device_id.id,
                                    'is_subscription': True,

                                }
                                sale_subscription = subscription_obj.create(values)
                                if sale_subscription:
                                    line_obj = self.env["sale.order.line"].search(
                                        [('order_id', '=', self.sale_order_id.id)])
                                    for line_val in line_obj:
                                        if self.sale_order_id.subscription_template_id.name == 'Monthly':
                                            product_price = (line_val.price_unit)
                                            period = int(self.sale_order_id.contract_period)
                                            price = product_price / period
                                            line_value = {
                                                'product_id': line_val.product_id.id,
                                                'quantity': 1,
                                                'price_unit': price,
                                                'name': line_val.name,
                                                'uom_id': line_val.product_id.uom_id.id,
                                                'analytic_account_id': sale_subscription.id,

                                            }
                                            self.env['sale.order.line'].create(line_value)
                            else:
                                subscription_temp = self.env['sale.order.template'].search([('name', '=', 'Yearly')])
                                fmt = '%Y-%m-%d'
                                today_date = datetime.strptime(str(self.activation_date), '%Y-%m-%d')
                                subscription_date = today_date + relativedelta(years=1)
                                values = {
                                    'sale_order_id': self.sale_order_id.id,
                                    'partner_id': self.sale_order_id.partner_id.id,
                                    'template_id': self.sale_order_id.subscription_template_id.id,
                                    'serial_no': self.device_serial_number_new_id.id,
                                    'vehicle_number': self.vehicle_number.id,
                                    'imei_no': self.imei_no,
                                    'gsm_number': self.gsm_number,
                                    'job_card_id': self.id,
                                    'date_start': subscription_date,
                                    'activation_date': self.activation_date,
                                    'installation_date': self.installation_date,
                                    'invoice_type': 'pre',
                                    'sale_type': self.sale_order_id.sale_type,
                                    # 'subscription_period': 12,
                                    'engineer_id': self.engineer_id.id,
                                    'device_id': self.device_id.id,
                                    'pricelist_id': self.sale_order_id.pricelist_id.id,

                                }
                                sale_subscription = subscription_obj.create(values)
                                line_obj = self.env["sale.order.line"].search(
                                    [('order_id', '=', self.sale_order_id.id)])
                                for line_val in line_obj:
                                    if line_val.product_id.hosting_charges == True:
                                        line_value = {
                                            'product_id': line_val.product_id.id,
                                            'quantity': 1,
                                            'price_unit': line_val.price_unit,
                                            'price_subtotal': line_val.price_subtotal,
                                            'name': line_val.name,
                                            'uom_id': line_val.product_id.uom_id.id,
                                            'analytic_account_id': sale_subscription.id,

                                        }
                                        self.env['sale.order.line'].create(line_value)
                        else:
                            subscription_temp = self.env['sale.order.template'].search([('name', '=', 'Monthly')])
                            values = {
                                'sale_type': self.sale_type,
                                'partner_id': self.company_id.id,
                                'pricelist_id': 1,
                                'invoice_type': 'pre',
                                'template_id': subscription_temp.id,
                                'serial_no': self.device_serial_number_new_id.id,
                                'vehicle_number': self.vehicle_number.id,
                                'imei_no': self.imei_no,
                                'gsm_number': self.gsm_number,
                                'job_card_id': self.id,
                                'activation_date': self.activation_date,
                                'date_start': self.activation_date,
                                'installation_date': self.installation_date,
                                'engineer_id': self.engineer_id.id,
                                'device_id': self.device_id.id,
                            }
                            sale_subscription = subscription_obj.create(values)
                            if sale_subscription:
                                line_obj = self.env["sale.order.line"].search(
                                    [('order_id', '=', self.sale_order_id.id)])
                                for line_val in line_obj:
                                    if self.sale_order_id.subscription_template_id.name == 'Monthly':
                                        product_price = (line_val.price_unit)
                                        period = int(self.sale_order_id.contract_period)
                                        price = product_price / period
                                        line_value = {
                                            'product_id': line_val.product_id.id,
                                            'quantity': 1,
                                            'price_unit': price,
                                            'name': line_val.name,
                                            'uom_id': line_val.product_id.uom_id.id,
                                            'analytic_account_id': sale_subscription.id,

                                        }
                                        self.env['sale.order.line'].create(line_value)
                    else:
                        raise UserError(_("Only Account Persons Can Create The Subscription"))
                else:
                    raise UserError(_("You Can Create Only One Subscription For This Job Card"))
            else:
                raise UserError(_("Subscription for this serial no has already been created"))

    ## To View Subscription ##
    # @api.multi
    def open_subscription_view(self):
        var = []
        # if self._context is None:
        #     context = {}
        # # res = self.env['ir.actions.act_window'].for_xml_id('sale_subscription', 'sale_subscription_action')
        # res = self.env.ref('sale_subscription.sale_subscription_action')
        # # print("-----", self._context, "----self._context-\n")
        # res['context'] = {}
        subscription_obj = self.env['sale.order'].search([('job_card_id', '=', self.id), ('is_subscription', '=', True)])
        for i in subscription_obj:
            var.append(i.id)
        # res['domain'] = [('id', 'in', var)]
        return {
            'name': _("Subscriptions"),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', var)],
        }

    ## To Count Subscription ##
    # @api.multi
    def subscription_count(self):
        for rec in self:
            rec.count_subscription = len(self.env["sale.order"].search([('job_card_id', '=', rec.id)]).ids)

    # To create Delivery Note ##
    # @api.multi
    def create_dc(self):
        line_obj = self.env["sale.order.line"].search([])
        order_ids = self.env["sale.order"].search([])

        if self.count_dc != 1:
            picking_obj = self.env["stock.picking"]
            location_obj = self.env["stock.location"].search([('location_code', '=', 'WH/S')])
            line_obj = self.env["sale.order.line"].search([('order_id', '=', self.sale_order_id.id)])
            # self.env.cr.execute("""select id from sale_order_line where order_id = %d""" % 335)
            # line_obj = self.env.cr.dictfetchall()
            stock_quant = self.env["stock.quant"].search(
                [('lot_id', '=', self.device_serial_number_new_id.id), ('quantity', '=', 1)])
            picking_type = ''
            dest_loc = ""
            loc = ""
            if self.sale_order_id.sale_type == 'lease':

                picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'LW')])
                picking_type = picking_type_obj.id
                dest_loc = picking_type_obj.default_location_dest_id.id
                loc = stock_quant.location_id.id

            elif self.sale_order_id.sale_type == 'rental':
                picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'RW')])
                picking_type = picking_type_obj.id
                dest_loc = picking_type_obj.default_location_dest_id.id
                loc = stock_quant.location_id.id
            elif self.sale_order_id.sale_type == 'cash':
                picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'DO')])
                picking_type = picking_type_obj.id
                dest_loc = picking_type_obj.default_location_dest_id.id
                loc = picking_type_obj.default_location_src_id.id

            elif self.sale_order_id.sale_type == 'purchase' and self.sale_order_id.purchase_type == 'project':
                picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'DO')])
                picking_type = picking_type_obj.id
                dest_loc = picking_type_obj.default_location_dest_id.id
                loc = picking_type_obj.default_location_src_id.id

            vals = {
                'partner_id': self.sale_order_id.partner_id.id,
                'job_card_id': self.id,
                'origin': self.sale_order_id.name,
                'sale_id': self.sale_order_id.id,
                'location_id': loc,
                'location_dest_id': dest_loc,
                'picking_type_id': picking_type,
                'product_lots_id': self.device_serial_number_new_id.id
            }
            picking = picking_obj.create(vals)
            if picking:
                move_line_obj = self.env["stock.move"]
                for rec in line_obj:
                    if rec.product_id.type == 'product':
                        line_vals = {
                            'product_id': self.device_id.id,
                            'name': self.device_id.name,
                            'product_uom_qty': 1,
                            'product_uom': self.device_id.uom_id.id,
                            'picking_id': picking.id,
                            'location_id': stock_quant.location_id.id,
                            'location_dest_id': dest_loc,
                            'reserved_availability': 1
                        }
                        move_line_obj.create(line_vals)
                self.env.cr.execute('''update stock_quant set reserved_quantity=1 where lot_id=%s''' % (
                    self.device_serial_number_new_id.id))
        else:
            raise UserError(_("You Can Create Only One Delivery Note For This Job Card"))

    # To view DC #
    # @api.multi
    def open_dc_view(self):
        var = []
        # res = self.env['ir.actions.act_window'].for_xml_id('stock', 'action_picking_tree_all')
        res = self.env.ref('stock.action_picking_tree_all')
        picking_obj = self.env['stock.picking'].search([('job_card_id', '=', self.id)])
        for i in picking_obj:
            var.append(i.id)
        res['domain'] = [('id', 'in', var)]
        return res

    ## To Count Delivery Note ##
    # @api.multi
    def count_delivery_note(self):
        for rec in self:
            rec.count_dc = len(self.env["stock.picking"].search([('job_card_id', '=', rec.id)]).ids)

    ## To get new serial number from engineer location ##
    @api.onchange('task_id', 'job_card_type')
    def onchange_serial_num(self):
        if self.job_card_type or self.task_id:
            task_obj = self.env['project.task'].search([('id', '=', self.task_id.id)])
            project_obj = self.env['project.project'].search([('id', '=', task_obj.project_id.id)])
            sale_obj = self.env['sale.order'].search([('id', '=', project_obj.sale_order_id.id)])
            self.update({'sale_order_id': sale_obj.id})
            self.update({'sale_type': sale_obj.sale_type})

            if self.job_card_type == 'sale':
                self.update({'company_id': sale_obj.partner_id.id})
            elif self.job_card_type in ['support', 'additional_service']:
                self.update({'company_id': task_obj.partner_id.id})
            else:
                return ''

            if sale_obj.sale_type in ['lease', 'rental'] or sale_obj.purchase_type == 'project':
                self.env.cr.execute("""select sq.lot_id lot from stock_production_lot spl
                                        join product_product pp on pp.id=spl.product_id
                                        join stock_quant sq on sq.product_id = pp.id
                                        join stock_location sl on sl.id=sq.location_id
                                        join hr_employee hr on hr.dest_location_id=sl.id
                                        join resource_resource rr on rr.id=hr.resource_id
                                        join res_users rs on rs.id=rr.user_id
                                        where rs.id=%s """ % (self.env.uid))
                lot_obj = self.env.cr.dictfetchall()
                lot = []
                for obj in lot_obj:
                    lot.append(obj['lot'])
                return {'domain': {'device_serial_number_new_id': [('id', 'in', list(set(lot)))]}}

    ## To update device name based on serial no in job card ##
    @api.onchange('device_serial_number_old_id', 'device_serial_number_new_id')
    def onchange_device(self):
        if self.device_serial_number_new_id or self.device_serial_number_old_id:
            vals = " "
            if self.device_serial_number_new_id:
                self.update({'device_id': self.device_serial_number_new_id.product_id.id})
            elif self.device_serial_number_old_id:
                self.update({'device_id': self.device_serial_number_old_id.product_id.id})
            else:
                return vals

    name = fields.Char("Job Card No", readonly=True)
    device_id = fields.Many2one("product.product", "Device Type", store=True)
    device_description = fields.Char(string="Device Description")
    imei_no = fields.Char("Satellite IMEI No", related='vehicle_number.satellite_imei_no', store=True)
    imei_no_old = fields.Char("Satellite IMEI No-Old", related='vehicle_number_old.satellite_imei_no', store=True)
    task_id = fields.Many2one("project.task", "Job Order ")
    sale_order_id = fields.Many2one("sale.order", "Sale Order")
    company_id = fields.Many2one("res.partner", "Client Name")
    device_serial_number_new_id = fields.Many2one("stock.lot", "Device ID", store=True)
    device_serial_number_old_id = fields.Many2one("stock.lot", "Device ID-Old", store=True)
    new_no = fields.Char("Existing Device No")
    vehicle_number = fields.Many2one('vehicle.master', "Vehicle Reg No")
    vehicle_number_old = fields.Many2one('vehicle.master', "Vehicle Reg No-Old")
    vehicle_description = fields.Char("Vehicle Description", related='vehicle_number.vehicle_name', store=True)
    model = fields.Char("Model/Year", related='vehicle_number.model', store=True)
    chassis_no = fields.Char("Chassis No/VIN No", related='vehicle_number.chassis_no', store=True)
    chassis_number_old = fields.Char("Chassis No/VIN No-Old", related='vehicle_number_old.chassis_no', store=True)
    job_card_type = fields.Selection([('sale', 'New Sale'),
                                      ('support', 'Support/Repair'),
                                      ('additional_service', 'Additional Service')
                                      ], string="Job Card Type")
    service_job_type = fields.Selection([('re_installation', 'Re-Installation'),
                                         ('testing', 'Testing and Calibration'),
                                         ('removal', 'Removal and Retained'),
                                         ('removal_returned', 'Removal and Returned'),
                                         ], string="Job Type")
    repair_job_type = fields.Selection([('re_installation', 'Re-Installation vehicle'),
                                        ('defective_device_replacement', 'Defective device replacement'),
                                        ('defective_component_replacement', 'Defective component replacement'),
                                        ('calibartion_testing', 'Calibration and Testing'),
                                        ('removal', 'Removal and Retained'),
                                        ('removal_returned', 'Removal and Returned'),
                                        ], string="Job Type")
    gsm_number = fields.Char("GSM Number", related='vehicle_number.gsm_no', store=True)
    gsm_number_old = fields.Char("GSM Number-Old", related='vehicle_number_old.gsm_no', store=True)
    speed_input = fields.Selection([('gsp', 'GPS'), ('gps', 'CAN'), ('vss', 'VSS')], string="Speed Input", default='gsp')
    can = fields.Selection([('can_h', 'CAN_H'), ('can_l', 'CAN_L')], string="")
    seat_belt = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="Driver Seat Belt")
    connection_type = fields.Selection([('normal', 'Normal'), ('relay', 'Relay'), ('can', 'CAN Interface')], string="Connection Type")
    panic_button = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="Panic Button")
    rpm = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="RPM")
    can_bus = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="Can Bus Interface")
    problem = fields.Text("Problem")
    rectification = fields.Text("Rectification")
    remarks = fields.Text("Remarks")
    installation_date = fields.Date("Installation Date")
    activation_date = fields.Date("Activation Date")
    installation_category = fields.Selection([('direct', 'Normal Customer'), ('partner', 'Reseller')], "Installation Category")
    installation_street = fields.Char('Street')
    installation_street2 = fields.Char('Street2')
    installation_zip = fields.Char('Zip', size=24)
    installation_city = fields.Char('City')
    installation_state_id = fields.Many2one("res.country.state", 'State', ondelete='restrict')
    installation_country_id = fields.Many2one('res.country', 'Country', ondelete='restrict')
    count_certificate = fields.Integer(compute='certificate_count', string="Certificates")
    count_subscription = fields.Integer(compute='subscription_count', string="Subscriptions")
    count_dc = fields.Integer(compute='count_delivery_note', string="Delivery")
    repair_count = fields.Integer("Repair", compute='count_repair')
    sale_type = fields.Selection([('cash', 'Cash Sale'),
                                  ('purchase', 'Unit Sale'),
                                  ('lease', 'Lease Sale'),
                                  ('rental', 'Rental Sale'),
                                  ('pilot', 'Renewal Sale'),
                                  ], string='Sale Type')
    device_status = fields.Selection([('active', 'Active'),('in_active', 'Inactive'),], string='Device Status')
    installation_region_id = fields.Many2one('installation.region', string='Installation Region')
    installation_location_id = fields.Many2one('installation.location', string='Installation Location')
    state = fields.Selection([('open', 'Open'),
                              ('configured', 'Configured'),
                              ('installed', 'Installed'),
                              ('submitted', 'Submitted'),
                              ('done', 'Done')],
                             default='open', string="Stage")
    invoice = fields.Selection([('chargeable', 'Chargeable'), ('non_chargeable', 'Non-Chargeable')], string="Invoice")
    firm_ware = fields.Char("Firmware")
    firm_ware_old = fields.Char("Firmware-Old")
    gsm_imei_no = fields.Char("SIM Serial No", related='vehicle_number.gsm_imei_no', store=True)
    gsm_imei_no_old = fields.Char("SIM Serial No-Old", related='vehicle_number_old.gsm_imei_no', store=True)
    component_line = fields.One2many('component.repair', 'job_id', string="Component")
    delivery_count = fields.Integer("Delivery", compute='compute_dc')
    unistallation_date = fields.Date("Uninstallation Date")
    deactivation_date = fields.Date("Deactivation Date")
    socket = fields.Char("Socket")
    pin = fields.Char("Pin")
    color = fields.Char("Color")
    pulse = fields.Char("Pulse")
    socket_canh = fields.Char("Socket CAN-H")
    pin_canh = fields.Char("Pin CAN-H")
    color_canh = fields.Char("Color CAN-H")
    socket_canl = fields.Char("Socket CAN-L")
    pin_canl = fields.Char("Pin CAN-L")
    color_canl = fields.Char("Color CAN-L")
    socket_rpm = fields.Char("Socket")
    pin_rpm = fields.Char("Pin")
    color_rpm = fields.Char("Color")
    pulse_rpm = fields.Char("Pulse")
    socket_driver = fields.Char("Socket")
    pin_driver = fields.Char("Pin")
    color_driver = fields.Char("Color")
    voltage_driver = fields.Char("Voltage")
    sat = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="SAT")
    voice = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="Voice")
    eagle_eye = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="Eagle Eye")
    dfms = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="DFMS")
    fuel = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="Fuel")
    fuse_box = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="Fuse Box")
    vehicle_voltage = fields.Selection([('12v', '12V'), ('24v', '24V')], string="Vehicle Voltage")
    operator = fields.Selection([('omantel', 'Omantel'), ('ooredoo', 'Ooredoo')], string="Operator")
    portal = fields.Selection([('gfms', 'GFMS'), ('bs', 'BP'), ('oxy', 'OXY')], string="Portal")
    card_line = fields.One2many('job.card.line', 'job_card_id', string="Job Details")
    bs_version = fields.Char("BS Version")
    bs_version_old = fields.Char("BS Version-Old")
    engineer_id = fields.Many2one("res.users", string="Engineer")
    supervisor_id = fields.Many2one("res.users", string="Supervisor")
    scheduled_date = fields.Date("Scheduled Date")
    support_id = fields.Many2one("website.support.ticket", "Ticket")
    checklist_ids = fields.One2many('task.checklist', 'task_id', string="Items")
    is_reseller = fields.Boolean("Reseller", default= False, store = True, related = 'company_id.is_reseller')
    vehicle_description_old = fields.Char("Vehicle Description", related='vehicle_number_old.vehicle_name', store=True)
    model_old = fields.Char("Model/Year", related='vehicle_number_old.model', store=True)
    order_line_id = fields.Many2one('sale.order.line', string="Order Line")
    
    @api.onchange('invoice')
    def onchange_invoice(self):
        if self.invoice == 'chargeable' and self.task_id.support_id:
            self.env.cr.execute(
                "UPDATE website_support_ticket set is_invoice=True where id=%d" % self.task_id.support_id.id)
        elif self.invoice == 'non_chargeable' and self.task_id.support_id:
            self.env.cr.execute(
                "UPDATE website_support_ticket set is_invoice=False where id=%d" % self.task_id.support_id.id)

    # @api.model
    def compute_dc(self):
        for rec in self:
            rec.delivery_count = len(self.env['stock.picking'].search([('job_id', '=', rec.id)]))

    ## To submit job card
    # @api.multi
    def submit_job_card(self):
        job_card_line_obj = self.env['job.card.line']
        job_card_line_obj.create({'name': self.env.uid,
                                  'job_card_id': self.id,
                                  'date_accomplished': fields.Date.today(),
                                  'state': 'submitted'
                                })
        res = fields.Date.today()
        if self.activation_date and self.activation_date > res:
            raise UserError(_("Activation date should not be greater than today date"))
        if self.installation_date and self.installation_date > res:
            raise UserError(_("Installation date should not be greater than today date"))

        # If sale type is pilot sale, make sure that the job card type must be pilot sale
        if self.sale_type == 'pilot_sale' and self.job_card_type != 'pilot_sale':
            raise UserError(_("Please make sure to add Pilot Testing under Job Card Type if sale type is Pilot Testing."))

        self.write({'state': 'submitted'})

    # @api.multi
    def to_configured(self):
        if not self.vehicle_number:
            raise UserError(_('Invalid action! Please provide Vehicle Reg No.'))
        job_card_line_obj = self.env['job.card.line']
        job_card_line_obj.create({'name': self.env.uid,
                                  'job_card_id': self.id,
                                  'date_accomplished': fields.Date.today(),
                                  'state': 'configured'})
        values = []
        checklist_obj = self.env['checklist.item'].search([])
        for checklist in checklist_obj:
            vals = {}
            if checklist.name:
                vals = (0, 0, {'name': checklist.name})
                values.append(vals)
            print("-----", values, "----values-\n")
        self.update({'checklist_ids': values})
        self.write({'state': 'configured'})

    # @api.multi
    def to_installed(self):
        if not self.activation_date:
            raise UserError(_('Invalid action! Please provide Activation date.'))
        if not self.installation_date:
            raise UserError(_('Invalid action! Please provide Installation date.'))
        job_card_line_obj = self.env['job.card.line']
        job_card_line_obj.create({'name': self.env.uid,
                                  'job_card_id': self.id,
                                  'date_accomplished': fields.Date.today(),
                                  'state': 'installed'
                                })
        self.write({'state': 'installed'})

    ## To close job card
    # @api.multi
    def close_job_card(self):
        if not self.activation_date:
            raise UserError(_('Invalid action! Please provide Activation date.'))
        if not self.installation_date:
            raise UserError(_('Invalid action! Please provide Installation date.'))
        if not self.installation_location_id:
            raise UserError(_('Invalid action! Please provide Installation Location.'))
        if not self.company_id:
            raise UserError(_('Invalid action! Please provide Client Name.'))
        if not self.device_serial_number_new_id:
            raise UserError(_('Invalid action! Please provide Device ID.'))
        if not self.device_id:
            raise UserError(_('Invalid action! Please provide Device Type.'))
        job_card_line_obj = self.env['job.card.line']
        job_card_line_obj.create({'name': self.env.uid,
                                  # 'checked_by': self.env.uid,
                                  'job_card_id': self.id,
                                  'date_accomplished': fields.Date.today(),
                                  'state': 'done'})
        if self.device_status == 'active':
            # self.write({'state':'done'})
            sale_obj = self.env['sale.order'].search([('id', '=', self.sale_order_id.id)])
            job_list = []
            job_test = self.env["job.card"].search([('sale_order_id', '=', self.sale_order_id.id)])
            for job in job_test:
                if job.state == 'done':
                    job_list.append(job.id)
            if self.sale_order_id:
                self.sale_order_id.installed_device_count = len(job_list)
        else:
            raise UserError(_("Device status is not active"))
        if self.job_card_type == 'sale':
            if self.vehicle_number:
                self.env.cr.execute("""update vehicle_master set
                installation_date='%s',activation_date='%s',installation_location_id='%s',partner_id='%s',serial_no='%s',device_duplicate='%s' where id=%s""" % (
                self.installation_date,
                self.activation_date,
                self.installation_location_id.id,
                self.company_id.id,
                self.device_serial_number_new_id.name,
                self.device_id.name,
                self.vehicle_number.id))
            else:
                raise UserError(_('Invalid action! Please provide vehicle details.'))
        self.write({'state': 'done'})


    # update vehicle master
    # @api.multi
    def update_vehicle_master(self):
        vehicle_master_obj = self.env['vehicle.master'].search([('name', '=', self.vehicle_number.name)])
        vehicle_master_obj.write({'satellite_imei_no': self.imei_no,
                                  'gsm_no': self.gsm_number,
                                  'gsm_imei_no': self.gsm_imei_no,
                                  'device_serial_number_id': self.device_serial_number_new_id.id,
                                  'device_id': self.device_id.id,
                                  'installation_location_id': self.installation_location_id.id,
                                  'chassis_no': self.chassis_no,
                                  'model': self.model,
                                })

    ## To approve job card
    ##  Approved functionality-Removed
    # ~ @api.multi
    # ~ def approve_job_card(self):
    # ~ self.write({'state':'approved'})

    # DELIVERY ORDER VIEW
    # @api.multi
    def action_delivery_view(self):
        if self._context is None:
            context = {}
        # obj = self.env["ir.actions.act_window"].for_xml_id("stock", 'action_picking_tree_all')
        obj = self.env.ref('stock.action_picking_tree_all')
        obj['context'] = self._context
        stock = self.env["stock.picking"].search([('job_id', '=', self.id)]).ids
        obj['domain'] = [('id', 'in', stock)]
        return obj

    # PRODUCT OLD LOT MOVE TO DEFECTIVE LOCATION
    # @api.multi
    def location_stock_defect(self):
        # self.state = 'done'

        picking_location = self.env['stock.quant'].search(
            [('lot_id', '=', self.device_serial_number_old_id.id),
             ('product_id', '=', self.device_serial_number_old_id.product_id.id), ('quantity', '=', 1)])
        picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'DO')])
        picking_type = picking_type_obj.id
        picking_type_des_id = self.env['stock.location'].search([('location_code', '=', 'WH/D')])
        values = {'job_id': self.id,
                  'partner_id': self.task_id.support_id.partner_id.id,
                  'scheduled_date': datetime.now().date(),
                  'location_id': picking_location.location_id.id,
                  'location_dest_id': picking_type_des_id.id,
                  'picking_type_id': picking_type,
                  'product_lots_id': self.device_serial_number_old_id.id}
        stock_pick = self.env['stock.picking'].create(values)
        line_values = {
            'product_id': self.device_serial_number_old_id.product_id.id,
            'name': self.device_serial_number_old_id.product_id.name,
            'product_uom_qty': 1,
            'product_uom': self.device_serial_number_old_id.product_id.uom_id.id,
            'location_id': picking_location.location_id.id,
            'location_dest_id': picking_type_des_id.id,
            'picking_id': stock_pick.id,
        }
        self.env['stock.move'].create(line_values)

    # Product Back To LEASE OR RENTAL OR CUSTOMER
    # @api.multi
    def move_to_customer_location(self):
        # self.state = 'submitted'
        if self.device_serial_number_old_id and self.device_serial_number_new_id:
            picking_location = self.env['stock.quant'].search(
                [('lot_id', '=', self.device_serial_number_old_id.id),
                 ('product_id', '=', self.device_serial_number_old_id.product_id.id), ('quantity', '=', 1)])
            picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'DO')])
            location_from = self.env['stock.quant'].search(
                [('lot_id', '=', self.device_serial_number_new_id.id),
                 ('product_id', '=', self.device_serial_number_new_id.product_id.id), ('quantity', '=', 1)])
            vals = {
                'job_id': self.id,
                'partner_id': self.task_id.support_id.partner_id.id,
                'scheduled_date': datetime.now().date(),
                'location_id': location_from.location_id.id,
                'location_dest_id': picking_location.location_id.id,
                'picking_type_id': picking_type_obj.id,
                'product_lots_id': self.device_serial_number_new_id.id

            }

            stock = self.env['stock.picking'].create(vals)
            line_value = {
                'product_id': self.device_serial_number_new_id.product_id.id,
                'name': self.device_serial_number_new_id.product_id.name,
                'product_uom_qty': 1,
                'product_uom': self.device_serial_number_new_id.product_id.uom_id.id,
                'location_id': location_from.location_id.id,
                'location_dest_id': picking_location.location_id.id,
                'picking_id': stock.id,
            }
            self.env['stock.move'].create(line_value)
        else:
            raise ValidationError("Please Select %s %s" % self.device_serial_number_old_id.name,
                                  self.device_serial_number_new_id.name)

    # Product Back To Stock
    # @api.multi
    def removal_repair(self):
        # self.state = 'done'
        stock_quant = self.env["stock.quant"].search(
            [('lot_id', '=', self.device_serial_number_old_id.id), ('quantity', '=', 1)])
        picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'DO')])
        location_id = self.env["stock.location"].search([('location_code', '=', 'WH/S')])

        vals = {
            'job_id': self.id,
            'partner_id': self.task_id.support_id.partner_id.id,
            'scheduled_date': datetime.now().date(),
            'location_id': stock_quant.location_id.id,
            'location_dest_id': location_id.id,
            'picking_type_id': picking_type_obj.id,
            'product_lots_id': self.device_serial_number_old_id.id

        }

        stock = self.env['stock.picking'].create(vals)
        line_value = {
            'product_id': self.device_id.id,
            'name': self.device_id.name,
            'product_uom_qty': 1,
            'product_uom': self.device_id.uom_id.id,
            'location_id': stock_quant.location_id.id,
            'location_dest_id': location_id.id,
            'picking_id': stock.id,
        }
        self.env['stock.move'].create(line_value)

    # COMPONENT REPLACEMENT FOR  SELECTED PRODUCT
    # @api.multi
    def location_move_component(self):
        if self.component_line:
            self.env.cr.execute("""SELECT ro.id,cr.product_id,cr.name,cr.quantity,cr.uom_id FROM job_card ro
                                            JOIN component_repair cr ON (ro.id=cr.job_id) WHERE cr.select_type='add' and ro.id=%d""" % self.id)
            add_delivery = self.env.cr.dictfetchall()
            if add_delivery != []:
                self.state = 'done'
                picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'DO')])
                picking_type_des_id = self.env['stock.location'].search([('location_code', '=', 'CUS')])
                picking_type_src_id = self.env['stock.location'].search([('location_code', '=', 'WH/S')])
                for adds in add_delivery:
                    vals = {
                        'job_id': adds['id'],
                        'partner_id': self.task_id.support_id.partner_id.id,
                        'scheduled_date': datetime.now().date(),
                        'location_id': picking_type_src_id.id,
                        'location_dest_id': picking_type_des_id.id,
                        'picking_type_id': picking_type_obj.id,

                    }
                    stock = self.env['stock.picking'].create(vals)
                    line_value = {
                        'product_id': adds['product_id'],
                        'name': adds['name'],
                        'product_uom_qty': adds['quantity'],
                        'product_uom': adds['uom_id'],
                        'location_id': picking_type_src_id.id,
                        'location_dest_id': picking_type_des_id.id,
                        'picking_id': stock.id,
                    }

                    self.env['stock.move'].create(line_value)
            else:
                raise ValidationError("Please Add Component")
        else:
            raise ValidationError("Please Add Component")


class ComponentRepair(models.Model):
    _name = 'component.repair'

    job_id = fields.Many2one('job.card', "Repair")
    select_type = fields.Selection(string="Select", selection=[('add', 'Add'), ('remove', 'Remove'), ], required=True, )
    name = fields.Char("Description")
    product_id = fields.Many2one('product.product', "Product", required=True)
    quantity = fields.Float("Quantity", default=1)
    uom_id = fields.Many2one("uom.uom", "Unit Of Measure")
    price_unit = fields.Float("Unit Price")

    # ONCHANGE FOR PRODUCT AND QUANTITY
    @api.onchange('product_id', 'quantity')
    def onchange_product_id(self):
        self.name = self.product_id.name
        self.price_unit = self.product_id.lst_price
        self.uom_id = self.product_id.uom_id.id
        self.price_unit = self.quantity * self.product_id.lst_price
        if self.select_type == 'add':
            self.env.cr.execute("""
                       select sum(quantity)  from stock_quant sq
                       JOIN stock_location sl ON (sq.location_id=sl.id) where sl.location_code='WH/S' and sq.product_id=%d""" % self.product_id.id)
            vals = self.env.cr.dictfetchall()
            for quant in vals:
                if quant['sum'] <= 0:
                    raise ValidationError("Insuffient Quantity for selected product %s" % self.name)
                elif quant['sum'] < self.quantity:
                    raise ValidationError("Insuffient Quantity for selected product %s" % self.name)


class MaterialPurchaseRequisitionLineInherit(models.Model):
    _inherit = "material.purchase.requisition.line"

    project_id = fields.Many2one('project.project', string="Project", related='requisition_id.project_id')


class MaterialPurchaseRequisitionInherit(models.Model):
    _inherit = "material.purchase.requisition"

    state = fields.Selection([
        ('draft', 'New'),
        ('dept_confirm', 'Waiting Department Approval'),
        ('ir_approve', 'Waiting IR Approved'),
        ('approve', 'Approved'),
        ('stock', 'Picking Created'),
        ('receive', 'Received'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')],
        default='draft',
        track_visibility='onchange',
    )

    # @api.multi
    def requisition_confirm(self):
        req_product_list = []
        line_qty = []
        result = True
        result1 = True
        purchase_req_line_obj = self.env["material.purchase.requisition.line"].search([('requisition_id', '=', self.id)])
        source_location_obj = self.env['stock.location'].search([('location_code', '=', 'WH/S')], limit=1)
        picking_type_obj = self.env['stock.picking.type'].search([('picking_code', '=', 'IT')], limit=1)
        req_line  = purchase_req_line_obj.filtered(lambda x: x.requisition_type and x.requisition_type == 'internal')
        if req_line:
            self.location_id = source_location_obj and source_location_obj.id
            self.custom_picking_type_id = picking_type_obj and picking_type_obj.id
        project_obj = self.env["project.project"].search([("id", "=", self.task_id.project_id.id)], limit=1)
        proj_task_obj = self.env["project.task"].search([("project_id", "=", project_obj.id)])
        sale_obj = self.env["sale.order"].search([("id", "=", project_obj.sale_order_id.id)], limit=1)
        sale_line_obj = self.env["sale.order.line"].search([("order_id", "=", sale_obj.id)])
        requisition_obj = self.env["material.purchase.requisition"].search([('project_id', '=', self.project_id.id)])
        for line in sale_line_obj:
            req_line_obj = self.env["material.purchase.requisition.line"].search(
                [('project_id', '=', project_obj.id), ('product_id', '=', line.product_id.id)])
            req_list = []
            for req in req_line_obj:
                req_list.append(req.qty)
            if line.product_uom_qty >= sum(req_list):
                result1 = True
            else:
                result1 = result = False
        if result1 == True and result == True:
            return super(MaterialPurchaseRequisitionInherit, self).requisition_confirm()

        elif result == False:
            raise UserError(_("Your requisition quantity has exceed the sale quantity"))


class InstallationRegion(models.Model):
    _name = "installation.region"

    name = fields.Char("Installation Region")


class InstallationLocation(models.Model):
    _name = "installation.location"

    name = fields.Char("Installation Location")


class JobCardLine(models.Model):
    _name = "job.card.line"

    name = fields.Many2one("res.users", domain="[('employee_ids', '!=', False)]", default=lambda self: self.env.user.id,
                           string="Job done by")
    job_time = fields.Char("Time Finished")
    date_accomplished = fields.Date("Date Accomplished")
    job_card_id = fields.Many2one('job.card', "Job Card Reference")
    job_start_time = fields.Float("Job Start Time ")
    job_end_time = fields.Float("Job End Time ")
    state = fields.Selection([('open', 'Open'),
                              ('configured', 'Configured'),
                              ('installed', 'Installed'),
                              ('submitted', 'Submitted'),
                              ('done', 'Done')],
                             string="Status")


class ChecklistItem(models.Model):
    _name = 'checklist.item'

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Name', required=True)


class ProjectChecklist(models.Model):
    _name = 'task.checklist'

    task_id = fields.Many2one('job.card', string="Job Card")
    item_id = fields.Many2one('checklist.item', string="Testing Points")
    is_required = fields.Selection([('done', 'Checked'), ('no', 'Not Checked')], string='Tested')
    state = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='State')
    remark = fields.Text(string='Remarks')
    name = fields.Char(string='Testing Points')

    def action_yes(self):
        self.write({'is_required': 'done'})
        self.write({'state': 'yes'})

    def action_no(self):
        self.write({'is_required': 'no'})
        self.write({'state': 'no'})

