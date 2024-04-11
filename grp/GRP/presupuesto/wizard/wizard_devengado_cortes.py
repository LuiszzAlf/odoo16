# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
# import csv, sys
PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]

class devengados_corte_wizard(models.TransientModel):
    _name = 'devengados_corte.wizard'
    
    @api.model
    def _select_anio(self):
        fecha = datetime.today()
        return  fecha.year
    
    @api.model
    def _select_periodo(self):
        fecha = datetime.today()
        return  int(fecha.month)
    
    anio=fields.Selection(EJERCICIO_SELECT, default=_select_anio)
    periodo = fields.Selection(PERIODO_SELECT, default=_select_periodo)

    @api.multi
    def report_devengados_corte(self):
        datas={}
        partida=[]
        sql_compromisos="""select sum(importe) as total,partida from presupuesto_requisicion_compras_compromisos_line prccl
        where EXTRACT(YEAR FROM DATE (fecha))=%s and  periodo=%s and state ='comprometido' and documento>0 and asiento >0 group  by 2 order by partida;"""
        self.env.cr.execute(sql_compromisos % (self.anio,self.periodo))
        row_compromisos = self.env.cr.dictfetchall()
        for i in row_compromisos:
            devengados_mov=[]
            total_devengado=0
            sql_mov_dev="""select a."name" ,b."name" as req ,a.partida ,a.fecha , a.area ,a.importe from tjacdmx_devengados_line a
                            inner join presupuesto_requisicion_compras b on  b.id = a.requisicion_compra 
                            where  EXTRACT(YEAR FROM DATE (a.fecha))=%s 
                            and periodo =%s 
                            and a.state ='devengado' 
                            and documento>0 
                            and asiento >0
                            and a.partida ='%s';"""
            self.env.cr.execute(sql_mov_dev % (self.anio,self.periodo,i['partida']))
            row_mov_dev = self.env.cr.dictfetchall()
            for m in row_mov_dev:
                total_devengado=total_devengado+m['importe']
                partidas_dev = {
                    'name': m['name'],
                    'req': m['req'],
                    'partida': m['partida'],
                    'fecha': m['fecha'],
                    'area': m['area'],
                    'importe': m['importe'],
                    }
                devengados_mov.append(partidas_dev)
            partidas = {
                    'partida': i['partida'],
                    'total': i['total'],
                    'total_devengado': total_devengado,
                    'movimientos': devengados_mov
                    }
            partida.append(partidas)
        datas['partidas']=partida
        #raise ValidationError("%s" % (datas))
        return self.env['report'].get_action([], 'presupuestos.devengados_report', data=datas)
