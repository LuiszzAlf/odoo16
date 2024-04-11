from odoo import api, models
from odoo.tools import float_round


class reports(models.AbstractModel):
    _name = 'report.resguardos.print_resguardo'

    def render_html(self):
        return self.env['report'].get_action([], 'resguardos.print_resguardo')


class report_resguardo_arrendamiento(models.AbstractModel):
    _name = 'report.resguardos.print_resguardo_arrendamiento'

    @api.model
    def render_html(self, docids, data=None):
        data = data if data is not None else {}
        docargs = {
            'data': dict(
                data
            )
        }
        return self.env['report'].render('resguardos.print_resguardo_arrendamiento_template', docargs)
