# -*- coding: utf-8 -*-
from datetime import datetime
from collections import Counter
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
# import csv, sys
import collections
import datetime
from dateutil.relativedelta import relativedelta
from datetime import date

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]


class wizard_cierre_inventario(models.TransientModel):
    _name = 'wizard.cierre.inventario'

    @api.model
    def get_year(self):
        return date.today().year

    @api.model
    def get_month(self):
        periodo=int(date.today().month)
        return periodo
 
    anio=fields.Selection(EJERCICIO_SELECT, default=get_year)
    periodo = fields.Selection(PERIODO_SELECT, default=get_month)
    

    def crea_movimientos(self):
        obj_ci = self.env['tjacdmx.cierre.inventario']   
        qry_devs = """
                    select
                    product_id,
                    0 stock_actual,
                    price_unit impo_exist_final
                    from stock_move
                    where 
                        devolucion = true
                        AND EXTRACT(YEAR FROM date)='%s';"""
        self.env.cr.execute(qry_devs % (self.anio))
        rows_sql_devs = self.env.cr.dictfetchall()
        
        for ite in rows_sql_devs:
            produc = obj_ci.search([('anio', '=',self.periodo),('periodo', '=',self.periodo),('product_id', '=',ite['product_id'])])
            # raise ValidationError("debug %s"  % (len(produc)))
            if(produc):
                obj_ci.update({'importe_existencias':  produc.impo_exist_final-ite['impo_exist_final']})
            else:
                obj_ci.create(
                        {
                        'anio': self.anio, 
                        'periodo': self.periodo, 
                        'existencias': ite['stock_actual'],
                        'importe_existencias':  ite['impo_exist_final']*-1,
                        'product_id':  ite['product_id'],
                        'devolucion': True
                        })
                


    @api.multi
    def cierre_periodo(self):
        if(not self.env['tjacdmx.cierre.inventario'].get_is_periodo_cerrado(self.periodo, self.anio)):
            fecha_inicio = str(self.anio)+"-"
            fecha_fin = str(self.anio)+"-"

            if(self.periodo<=9):
                fecha_inicio += "0" + str(self.periodo) + '-01 00:00:01'
            else:
                fecha_inicio += str(self.periodo) + '-01 00:00:01'
                
            fecha_fin=datetime.datetime(self.anio,self.periodo,10)
            fecha_fin=fecha_fin.replace(day=1)+relativedelta(months=1)+datetime.timedelta(minutes=-1)

            qry_select_val_inv =  "SELECT product_id, sum(qty) as stock_actual, sum(qty*cost) as impo_exist_final FROM stock_quant sq\
                                    WHERE location_id = 15\
                                    GROUP BY product_id"

            self.env.cr.execute(qry_select_val_inv)
            rows_sql = self.env.cr.dictfetchall()
            obj_ci = self.env['tjacdmx.cierre.inventario']   
            for i in rows_sql:
                obj_ci.create(
                            {
                            'anio': self.anio, 
                            'periodo': self.periodo, 
                            'existencias': i['stock_actual'],
                            'importe_existencias':  i['impo_exist_final'],
                            'product_id':  i['product_id']
                            })
            
            self.crea_movimientos()
        else:
            raise ValidationError("El periodo %s/%s ya ha sido cerrado."  % (str(self.periodo),str(self.anio)) )
    
    


