from odoo import api, fields, models, _
from datetime import datetime, timedelta,date
from dateutil import relativedelta, parser
from odoo.exceptions import UserError, AccessError,ValidationError


class ProductTemplateInherit(models.Model):
    _inherit = "product.template"

    no_of_days = fields.Char("Required Time")
    monthly_rate = fields.Float("Monthly Rate")
    installation_charges = fields.Float("Installation Charges")
    hosting_charges = fields.Boolean('Hosting Charges')


class InstructionInherit(models.Model):
    _inherit = "job.instruction"

    location = fields.Char("Location")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    product_id = fields.Many2one("product.product","Device")
    device_serial_id = fields.Many2one("stock.lot","Device Serial Number")
    no_of_days = fields.Char(related="product_id.no_of_days",string="Job Completion Time")
    installation_location_id = fields.Many2one('installation.location',string='Installation Location')
    no_of_device = fields.Integer("No Of Devices")
    no_of_device_per_day = fields.Integer("No Of Devices/Day")
    user_id = fields.Many2one(
        'res.users',
        string='Engineer',
        default=lambda self: self.env.user.id,
        required=True,
    )
    job_status = fields.Selection([('in_progress', 'In Progress'),
                                            ('completed', 'Completed'),
                                            ], string='Job Status')
    is_job_assigned = fields.Boolean('Job Assigned')

    @api.onchange('start_date', 'end_date')
    def instruction_date_onchange(self):
        if self.no_of_device and self.no_of_device_per_day and self.start_date and self.end_date:
            no_of_days = self.no_of_device/self.no_of_device_per_day
            st_date = datetime.strptime(str(self.start_date), '%Y-%m-%d')
            en_date = datetime.strptime(str(self.end_date), '%Y-%m-%d')
            allowed_date = st_date + timedelta(no_of_days)
            instruction_obj = self.env['job.instruction'].search([])
            if en_date > allowed_date:
                raise UserError(_('End date has exceed the allocated days'))
            for obj in instruction_obj:
                if obj.user_id == self.user_id:
                    if (self.start_date >= obj.start_date and self.start_date <= obj.end_date) or \
                            (self.end_date >= obj.start_date and self.end_date <= obj.end_date):
                        raise UserError(_('This engineer is not available in this dates'))



## REMOVED WARNING FUCNTIONALITY

    #~ @api.onchange('start_date','end_date')
    #~ def instruction_warning_alert(self):
        #~ task_obj=self.env['project.task'].search([('id','=',self.job_id.id)])
        #~ if task_obj.date_end and self.end_date:
            #~ task_end_date=datetime.strptime(task_obj.date_end, ('%Y-%m-%d %H:%M:%S')).date()
            #~ ins_end_date=datetime.strptime(self.end_date, ('%Y-%m-%d'))
            #~ ins_end_date = ins_end_date.strftime("%Y-%m-%d")
            #~ ins_start_date=datetime.strptime(self.start_date, ('%Y-%m-%d'))
            #~ ins_start_date = ins_start_date.strftime("%Y-%m-%d")
            #~ instruction_end_date = parser.parse(ins_end_date).date()
            #~ instruction_start_date = parser.parse(ins_start_date).date()
            #~ val =''
            #~ if task_end_date < instruction_start_date:
                #~ val={'warning' : {
                    #~ 'title': _('Instruction date alert'),
                    #~ 'message':
                        #~ _("Start date of instruction exceeds the Job Order End Date ")}}
            #~ elif  task_end_date < instruction_end_date:
                #~ val={'warning' : {
                    #~ 'title': _('Instruction date alert'),
                    #~ 'message':
                        #~ _("End date of instruction exceeds the Job Order End Date ")}}
            #~ if val:
                #~ return val
            #~ else:
                #~ return None


