from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
from num2words import num2words

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2019, 2031)]
REPORTE = [
(1, 'CLASIFICADOR POR RUBRO DE INGRESOS'),
(2, 'CLASIFICADOR POR OBJETO DEL GASTO'),
(3, 'CLASIFICADOR ECONOMICO (POR TIPO DE GASTO)'),
(4, 'CLASIFICADOR FUNCIONAL ARMONIZADO'),
(5, 'CLASIFICADOR PROGRAMATICO ARMONIZADO'),
(6, 'CLASIFICADOR ADMINISTRATIVO ARMONIZADO'),
(7, 'CLASIFICADOR POR FUENTE DE FINANCIAMIENTO ARMONIZADO')]

class wizard_reportes_financieros_clasificador(models.TransientModel):
    _name='tjacdmx.wizard_reportes_financieros_clasificador'
    _description='Reportes financieros clasificados'
    
    @api.model
    def _select_anio(self):
        fecha = datetime.today()
        return  fecha.year
    
    reporte_select = fields.Selection(REPORTE, required=True)
    anio_fiscal = fields.Selection(EJERCICIO_SELECT,required = True, default=_select_anio)
    
    @api.multi
    def action_reportes_financieros_clasi(self, values):
        if self.reporte_select == 1:
            datas = {}
            res = self.read(['anio_fiscal'])
            res = res and res[0] or {}
            datas['form']= res
            return self.env['report'].get_action([], 'reportes.report_b1', data=datas)
        elif self.reporte_select == 2:
            datas = {}
            res = self.read(['anio_fiscal'])
            res = res and res[0] or {}
            datas['form']= res
            return self.env['report'].get_action([], 'reportes.report_b2', data=datas)
        elif self.reporte_select == 3:
            datas = {}
            res = self.read(['anio_fiscal'])
            res = res and res[0] or {}
            datas['form']= res
            return self.env['report'].get_action([], 'reportes.report_b3', data=datas)
        elif self.reporte_select == 4:
            datas = {}
            res = self.read(['anio_fiscal'])
            res = res and res[0] or {}
            datas['form']= res
            return self.env['report'].get_action([], 'reportes.report_b4', data=datas)
        elif self.reporte_select == 5:
            datas = {}
            res = self.read(['anio_fiscal'])
            res = res and res[0] or {}
            datas['form']= res
            return self.env['report'].get_action([], 'reportes.report_b5', data=datas)
        elif self.reporte_select == 6:
            datas = {}
            res = self.read(['anio_fiscal'])
            res = res and res[0] or {}
            datas['form']= res
            return self.env['report'].get_action([], 'reportes.report_b6', data=datas)
        elif self.reporte_select == 7:
            datas = {}
            res = self.read(['anio_fiscal'])
            res = res and res[0] or {}
            datas['form']= res
            return self.env['report'].get_action([], 'reportes.report_b7', data=datas)