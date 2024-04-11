# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import base64 
import pytz
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]
MOVE_SELECT = [('all','Todo'),('move_exist','Con movimientos')]


class Remanentes(models.TransientModel):
    _name = 'balanza_presupuestal.wizard'

    fecha_inicio = fields.Date(string='Fecha inicio',required=True)
    fecha_fin = fields.Date(string='Fecha fin',required=True)
    fecha_inicio_cal = fields.Date(string='Fecha inicio cla',compute='_onchange_date_cal')
    fecha_fin_cal = fields.Date(string='Fecha fin cal', compute='_onchange_date_cal')
    select_move=fields.Selection(MOVE_SELECT,default='all')

    
    @api.multi
    @api.onchange('fecha_inicio')
    def _onchange_date(self):
        date_fin=self.fecha_inicio
        self.update({'fecha_fin': date_fin})
    
    @api.multi
    @api.onchange('fecha_inicio','fecha_fin')
    def _onchange_date_cal(self):
        self.fecha_inicio_cal=self.fecha_inicio
        self.fecha_fin_cal=self.fecha_fin
    


    @api.multi
    def search_cuentas_origen(self):
        datas = {}
        sql_all_ht="""select
                            aa.id,
                            aa.code,
                            concat(aa.code, ' ', aa."name") as "name",
                            coalesce(sum(mp.debit), 0) as debe,
                            coalesce(sum(mp.credit), 0) as haber,
                            coalesce(sum(mp.debit), 0)-coalesce(sum(mp.credit), 0) as saldo
                        from
                            account_account aa
                        left join movimientos_polizas_presupuestal mp on
                            mp.account_id = aa.id
                            and mp.date between '%s' and '%s'
                        where aa.code like '%s'
                        group by 1,2,3
                        order by
                            aa.code;"""
        self.env.cr.execute(sql_all_ht % (self.fecha_inicio,self.fecha_fin,'8%'))
        rows_sql = self.env.cr.dictfetchall()
        tz_MX = pytz.timezone('America/Mexico_City') 
        datetime_CDMX = datetime.now(tz_MX)
        fechas=datetime_CDMX.strftime("%Y-%m-%d %H:%M:%S")
        datas['periodo_inicio'] = self.fecha_inicio
        datas['periodo_fin'] = self.fecha_fin
        datas['fecha_reporte'] = str(fechas)
        datas['cuentas'] = rows_sql
        return self.env['report'].get_action([], 'reportes.report_balanza_presupuestal', data=datas)
    
    
    @api.multi
    def sincronizar_balanza(self):
        fecha= datetime.strptime(self.fecha_inicio, '%Y-%m-%d')
        anio=fecha.year
        periodo=fecha.month
        fecha_balanza_up=datetime(anio,periodo,01).date()
        sql="""
        WITH periodos_registrados AS (
        SELECT 
                DATE(generate_series(MIN(date_trunc('month', a.date)), MAX(a.date), '1 month')) periodo
        FROM account_move_line a)
        SELECT 
        a."id" account_id,
        b.periodo,
        calcular_balanza_2019(a."id", b.periodo)
        FROM account_account a
        CROSS JOIN periodos_registrados b 
        WHERE periodo = '%s'"""
        self.env.cr.execute(sql % (fecha_balanza_up))
        rows_sql = self.env.cr.dictfetchall()




       