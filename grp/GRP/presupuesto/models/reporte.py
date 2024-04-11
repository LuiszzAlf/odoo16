from odoo import models, fields, api
from odoo.osv import expression
import calendar
import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import float_round
from odoo.exceptions import ValidationError
def _get_month(periodo):
	month_name = calendar.month_name[periodo]
	return month_name.decode('utf-8').upper()

def _get_month_miniscula(periodo):
	month_name = calendar.month_name[periodo]
	return month_name.decode('utf-8')

def _get_month_capital(periodo):
	month_name = calendar.month_name[periodo]
	return month_name.decode('utf-8').capitalize()

def _get_last_day(periodo,anio):
	if periodo == 12:
		last_day = 31
		return last_day
	else:
		fecha = datetime.datetime(anio,periodo,1)
		dia = fecha.replace(day=1)+relativedelta(months=1)+datetime.timedelta(days=-1)
		return dia.day

class reporte_pedido_compra(models.AbstractModel):
    _name = 'presupuesto.report_pedido_compra'

    @api.model
    def render_html(self, docids, data=None):
        docs = self.env['purchase.order'].browse(docids)
        company = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        docargs = {
            'doc_model': 'purchase.order',
            'docs': docs,
            'company':company
        }
        return self.env['report'].render('presupuestos.report_pedido_compra', docargs)



class devengados_report(models.AbstractModel):
    _name = 'report.presupuestos.devengados_report'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
			'obtener_mes': _get_month,
			'obtener_mesmin': _get_month_miniscula,
			'ultimo_dia': _get_last_day,
            'data': data
        }
        return self.env['report'].render('presupuestos.devengados_report_template', docargs)


class KardexReport(models.AbstractModel):
    _name = 'report.presupuestos.kardex'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        docs = self.env['stock.move'].browse(docids)
        docargs = {
            'doc_ids': docids,
            'doc_model': 'stock.move',
            'docs': docs,
        }
        return report_obj.render('presupuestos.kardex', docargs)

class KardexReportProduct(models.AbstractModel):
    _name = 'report.presupuestos.kardex_product'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        docs = self.env['product.product'].browse(docids)
        docargs = {
            'obtener_mes': _get_month,
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
            'data': data
        }
        return report_obj.render('presupuestos.kardex_product', docargs)

class SpReport(models.AbstractModel):
    _name = 'report.presupuestos.sp_report'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        # docs = self.env['product.product'].browse(docids)
        docargs = {
            'obtener_mes': _get_month,
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': '',
            'data': data
        }
        return report_obj.render('presupuestos.sp_report_template', docargs)

class report_inventario_historial(models.AbstractModel):
    _name = 'report.presupuestos.report_inventario_historial'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        docs = self.env['product.product'].browse(docids)
        docargs = {
            'obtener_mes': _get_month,
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
            'data': data
        }
        return report_obj.render('presupuestos.report_inventario_historial_template', docargs)