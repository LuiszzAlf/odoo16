# -*- coding: utf-8 -*-
from datetime import datetime
from collections import Counter
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
# import csv, sys
import collections
from dateutil.relativedelta import relativedelta

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]


class wizard_entregas_suministro(models.TransientModel):
    _name = 'wizard.entregas.suministro'
 
    date_expected_gral = fields.Date("Fecha de salida", default=datetime.today())
    empleado_delivered = fields.Many2one('tjacdmx.resguardantes', string="Entrega", create="false", edit="false", track_visibility='onchange', domain=[('ubicacion','=','Almacén General')])
    solicitudes_suministro = fields.One2many('tjacdmx.salida.inventario.masiva', 'id', string="Solicitudes de suministro")
    result_html=fields.Html(string='Resultados', compute='search_button')    
    count_sol = fields.Integer("Solicitudes",  compute='search_button')

    def search_orders(self):
        if(self.date_expected_gral):
            t_date= datetime.strptime(self.date_expected_gral, "%Y-%m-%d")
            d1 = str(datetime(t_date.year, t_date.month, t_date.day, 0,0,0))
            d2 = str(datetime(t_date.year, t_date.month, t_date.day, 23,59,59))

        if self.empleado_delivered and self.date_expected_gral:
            sql_all="""SELECT * FROM tjacdmx_salida_inventario_masiva
                        WHERE date_expected_gral >= '%s' 
                        AND date_expected_gral <= '%s'
                        AND empleado_delivered = %s
                        AND state in ('done', 'delivered');"""
            self.env.cr.execute(sql_all % (d1,d2,self.empleado_delivered.id))
            
        if self.date_expected_gral and not self.empleado_delivered:
            sql_all="""SELECT * FROM tjacdmx_salida_inventario_masiva
                        WHERE date_expected_gral >= '%s' 
                        AND date_expected_gral <= '%s'
                        AND state in ('done', 'delivered');"""
            self.env.cr.execute(sql_all % (d1,d2))
            
        if not self.date_expected_gral and self.empleado_delivered:
            sql_all="""SELECT * FROM tjacdmx_salida_inventario_masiva
                        WHERE empleado_delivered>= '%s'
                        AND state in ('done', 'delivered');"""
            self.env.cr.execute(sql_all % (self.empleado_delivered.id))

        if not self.date_expected_gral and not self.empleado_delivered:
            return []

        rows_sql = self.env.cr.dictfetchall()
        sol_ids = []
        for i in rows_sql:
            sol_ids.append(i['id'])

        orders = self.env['tjacdmx.salida.inventario.masiva'].search([('id','in',sol_ids)])
        self.count_sol = len(orders)

        if(self.count_sol == 0):
            return []

        return orders

    @api.multi
    @api.onchange('empleado_delivered','date_expected_gral')
    def search_button(self):

        html_items=""
           
        for items in self.search_orders():
            name=items.name
            fecha_estimada= str(items.fecha_estimada)[:16]
            state=''
            date_expected_gral= str(items.date_expected_gral)[:16]
            empleado_delivered= items.empleado_delivered.nombre

            if(items.state == 'draft'):
                state='Solicitado'
            if(items.state == 'autorized'):
                state='En trámite'
            if(items.state == 'done'):
                state='Para envio'
            if(items.state == 'delivered'):
                state='Entregado'

            
            html_items2="""
            <tr><td><p>%s</p></td> 
            <td><p>%s</p></td>
            <td><p>%s</p></td> 
            <td><p>%s</p></td> 
             <td><p>%s</p></td> 
            </tr>""" % (name,fecha_estimada,date_expected_gral,empleado_delivered, state)
            html_items+=html_items2.encode('ascii', 'ignore')

        html="""
        <div><h3></h3></div>
            <table id="ss_table" class="table table-striped">
                    <thead class="thead-dark">
                    <tr>
                    <th>Folio</th>
                    <th>Fecha estimada de entrega</th>
                    <th>Fecha de salida</th>
                    <th>Repartidor</th>
                    <th>Estatus</th>
                    </tr>
                    </thead>
                    %s
            </table>""" % (html_items)

        self.result_html=html.encode('ascii', 'ignore')
           
    @api.multi
    def print_sp(self):
        ordenes = self.search_orders()
        return self.env['report'].get_action(ordenes, 'reportes.solicitud_suministro_bloque_template')
        
    
    


