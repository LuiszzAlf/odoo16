# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.tools import float_round
from odoo.exceptions import ValidationError
import calendar
from dateutil.relativedelta import relativedelta

EJERCICIO_SELECT = [ (str(year), str(year)) for year in range(2018, 2031) ]
PERIODO_SELECT = [(str(periodo), str(periodo)) for periodo in range(1,13)]

def _get_month_capital(periodo):
	month_name = calendar.month_name[periodo]
	return month_name.decode('utf-8').capitalize()

class wizard_cp_acumulado(models.TransientModel):
    _name='tjacdmx.wizard_cp_acumulado'
    _description='Wizard CP Acumulado'

    @api.model
    def _select_anio(self):
        fecha = datetime.today()
        return  fecha.year

    @api.model
    def _select_periodo(self):
        fecha = datetime.today()
        return  int(fecha.month)

    periodo_inicial = fields.Selection(PERIODO_SELECT,default='1',required = True)
    periodo_final = fields.Selection(PERIODO_SELECT,default=_select_periodo,required = True)
    anio_fiscal = fields.Selection(EJERCICIO_SELECT,default=_select_anio,required = True)
    tipo_reporte = fields.Selection([('1','Control de presupuesto'),('2','Cuenta Publica')],default='1',required = True)
    posicion_presupuestaria = fields.Many2one('presupuesto.partida_presupuestal', string='Posicion presupuestaria', domain="[('control_contable_presupuestalc', '=', 0), ('capitulo', '>=', 1), ('capitulo', '<=', 5), ('concepto', '>', 0)]")

    
    def open_wizard(self):
        if (self.tipo_reporte==1):
            view_mode = 'tree'
            tree_view_id = self.env.ref('presupuestos.presupuesto_view_cp_acumulado_view_wizard_tree').id
            tree_search_id = self.env.ref('presupuestos.presupuesto_view_cp_acumulado_view_wizard_search').id
            if not self.posicion_presupuestaria:
                domain = [('periodo', '>=', self.periodo_inicial), ('periodo', '<=', self.periodo_final), ('ejercicio', '=', self.anio_fiscal)]
                name = 'De %s a %s del %s' % (_get_month_capital(self.periodo_inicial), _get_month_capital(self.periodo_final), self.anio_fiscal)
            else:
                domain = [('periodo', '>=', self.periodo_inicial), ('periodo', '<=', self.periodo_final), ('ejercicio', '=', self.anio_fiscal), ('partida_presupuestal', '=', self.posicion_presupuestaria.partida_presupuestal)]
                name = 'De %s a %s del %s/ %s - %s' % (_get_month_capital(self.periodo_inicial), _get_month_capital(self.periodo_final), self.anio_fiscal, self.posicion_presupuestaria.partida_presupuestal, self.posicion_presupuestaria.denominacion)

            return {
                'name': name,
                'type': 'ir.actions.act_window',
                'res_model': 'presupuestos.view_cp_acumulado',
                'view_mode': view_mode,
                'views' : [(tree_view_id, 'tree')],
                'res_id': False,
                'target': 'self',
                'domain': domain,
                'context': "{'group_by':['nom_capitulo', 'partida_presupuestal']}",
            }
        else:
            view_mode = 'tree'
            tree_view_id = self.env.ref('presupuestos.presupuesto_view_cp_acumulado_cp_view_wizard_tree').id
            tree_search_id = self.env.ref('presupuestos.presupuesto_view_cp_acumulado_cp_view_wizard_search').id
            if not self.posicion_presupuestaria:
                domain = [('periodo', '>=', self.periodo_inicial), ('periodo', '<=', self.periodo_final), ('ejercicio', '=', self.anio_fiscal)]
                name = 'De %s a %s del %s' % (_get_month_capital(self.periodo_inicial), _get_month_capital(self.periodo_final), self.anio_fiscal)
            else:
                domain = [('periodo', '>=', self.periodo_inicial), ('periodo', '<=', self.periodo_final), ('ejercicio', '=', self.anio_fiscal), ('partida_presupuestal', '=', self.posicion_presupuestaria.partida_presupuestal)]
                name = 'De %s a %s del %s/ %s - %s' % (_get_month_capital(self.periodo_inicial), _get_month_capital(self.periodo_final), self.anio_fiscal, self.posicion_presupuestaria.partida_presupuestal, self.posicion_presupuestaria.denominacion)

            return {
                'name': name,
                'type': 'ir.actions.act_window',
                'res_model': 'presupuestos.view_cp_acumulado_cp',
                'view_mode': view_mode,
                'views' : [(tree_view_id, 'tree')],
                'res_id': False,
                'target': 'self',
                'domain': domain,
                'context': "{'group_by':['nom_capitulo', 'partida_presupuestal']}",
            }
