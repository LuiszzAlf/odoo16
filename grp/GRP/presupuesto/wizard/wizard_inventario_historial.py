# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import base64 
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]    
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]
MOVE_SELECT = [('all','Todo'),('move_exist','Con movimientos')]


class wizard_inventario_historial(models.TransientModel):
    _name = 'wizard.inventario.historial'

    @api.model
    def _get_product_name(self):
        context = dict(self._context or {})
        name = context.get('name', False)
        if name:
            data = name
            return data
        return ''
    
    @api.model
    def _get_product_uom(self):
        context = dict(self._context or {})
        uom = context.get('uom', False)
        if uom:
            data = uom
            return data
        return ''
        
    @api.model
    def _get_product(self):
        context = dict(self._context or {})
        product_id = context.get('product_id', False)
        if product_id:
            data = product_id
            return data
        return ''

    producto=fields.Char(string='Clave', default=_get_product_name, readonly=True)
    uom=fields.Char(string='Clave', default=_get_product_uom, readonly=True)
    product_id=fields.Integer(default=_get_product,readonly=True)
    fecha_inicio = fields.Date(string='Fecha inicio',default=datetime.today())
    fecha_fin = fields.Date(string='Fecha del fin',default=datetime.today())
    result_pc_html=fields.Html(string='Resultados',compute='search_kardex_xls')
    csv_urls = fields.Char(compute='search_kardex_xls')
    
    @api.multi
    @api.onchange('fecha_inicio')
    def _onchange_date(self):
        date_fin=self.fecha_inicio
        # self.update({'fecha_fin': date_fin})
    
    @api.multi
    def search_kardex(self):
        datas = {}
        sql_all="""with  entradas_producto as(select
                    product_qty cantidad_entradas,
                    product_id
                from
                    stock_move sm
                where
                    date_expected between '%s 00:00:00' and '%s 23:59:00'
                    and scrapped = false),
                salidas_producto as(select
                scrap_qty cantidad_salidas,
                product_id
                from
                stock_scrap sq
                where
                date_expected between '%s 00:00:00' and '%s 23:59:00'
                and state = 'done'),
                stock_producto as(
                select product_id,qty  
                from stock_quant  
                where location_id =15 and in_date between '%s' and '%s'
                )
                select  
                pt."name" as "producto",
                coalesce((select sum(cantidad_entradas) from  entradas_producto where  product_id =pp.id),0) "entradas",
                coalesce((select sum(cantidad_salidas) from  salidas_producto where  product_id =pp.id),0) "salidas",
                coalesce((select sum(qty) from  stock_producto where  product_id =pp.id),0) "stock_fisico"
                from stock_scrap ss
                inner join product_product pp on pp.id=ss.product_id
                inner join product_template pt on pt.id = pp.product_tmpl_id
                inner join product_uom pu on pu.id=pt.uom_id
                join presupuesto_partida_presupuestal ppp on ppp.id=pt.posicion_presupuestaria 
                where ss.date_expected between '%s' and '%s'
                group by 1,2,3,4
                order by 2,3;"""
        self.env.cr.execute(sql_all % (self.fecha_inicio, self.fecha_fin,self.fecha_inicio, self.fecha_fin,self.fecha_inicio, self.fecha_fin,self.fecha_inicio, self.fecha_fin))
        rows_sql = self.env.cr.dictfetchall()
        array_mov=[] 
        for i in rows_sql:
            mov = {
                'producto': i['producto'],
                'entradas': i['entradas'],
                'salidas': i['salidas'],
                'stock_fisico': i['stock_fisico']
           }
            array_mov.append(mov)
        fecha = datetime.strptime(self.fecha_inicio, '%Y-%m-%d') if self.fecha_inicio else datetime.today()
        fechas=datetime.today()
        datas['periodo'] = fecha.month
        datas['anio'] = fecha.year
        datas['fecha_reporte'] = str(datetime.strftime(fechas,"%Y-%m-%d"))
        datas['fecha_inicio'] = self.fecha_inicio
        datas['fecha_fin'] = self.fecha_fin
        datas['movimientos'] = array_mov
        return self.env['report'].get_action([], 'presupuestos.report_inventario_historial', data=datas)
    
    
    @api.multi
    def search_kardex_xls(self):
        sql_all="""with  entradas_producto as(select
                    product_qty cantidad_entradas,
                    product_id
                from
                    stock_move sm
                where
                    date_expected between '%s 00:00:00' and '%s 23:59:00'
                    and scrapped = false),
                salidas_producto as(select
                scrap_qty cantidad_salidas,
                product_id
                from
                stock_scrap sq
                where
                date_expected between '%s 00:00:00' and '%s 23:59:00'
                and state = 'done'),
                stock_producto as(
                select product_id,qty  
                from stock_quant  
                where location_id =15 and in_date between '%s' and '%s'
                )
                select  
                pt."name" as "producto",
                coalesce((select sum(cantidad_entradas) from  entradas_producto where  product_id =pp.id),0) "entradas",
                coalesce((select sum(cantidad_salidas) from  salidas_producto where  product_id =pp.id),0) "salidas",
                coalesce((select sum(qty) from  stock_producto where  product_id =pp.id),0) "stock_fisico"
                from stock_scrap ss
                inner join product_product pp on pp.id=ss.product_id
                inner join product_template pt on pt.id = pp.product_tmpl_id
                inner join product_uom pu on pu.id=pt.uom_id
                join presupuesto_partida_presupuestal ppp on ppp.id=pt.posicion_presupuestaria 
                where ss.date_expected between '%s' and '%s'
                group by 1,2,3,4
                order by 2,3;"""
        self.env.cr.execute(sql_all % (self.fecha_inicio, self.fecha_fin,self.fecha_inicio, self.fecha_fin,self.fecha_inicio, self.fecha_fin,self.fecha_inicio, self.fecha_fin))
        rows_sql = self.env.cr.dictfetchall()
        array_mov=[] 
        for i in rows_sql:
            mov = {
                'producto': i['producto'],
                'entradas': i['entradas'],
                'salidas': i['salidas'],
                'stock_fisico': i['stock_fisico']
           }
            array_mov.append(mov)
        fecha = datetime.strptime(self.fecha_inicio, '%Y-%m-%d') if self.fecha_inicio else datetime.today()
        fechas=datetime.today()
        fecha_reporte='Del '+str(self.fecha_inicio)+' al'+str(self.fecha_fin)
        excel_encode = self.get_decode_excel(array_mov,'','',str(self.fecha_inicio),str(self.fecha_fin))
        self.csv_urls = "data:application/octet-stream;charset=utf-16le;base64,"+excel_encode
        
    @api.multi
    def get_decode_excel(self, ids,name,uom,periodo,anio):

        style00 = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            align: vert centre, horiz centre;', num_format_str='#,##0.00')

        style1 = xlwt.easyxf('font: name Arial, bold 1,height 250;\
                            pattern: pattern solid, fore_colour aqua; \
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')

        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Kardex')
        sheet.write_merge(0, 0, 0, 4, 'TRIBUNAL DE JUSTICIA ADMINISTRATIVA.', style00)
        sheet.write_merge(1, 1, 0, 4, 'DE LA CIUDAD DE MEXICO.', style00)
        sheet.write_merge(2, 2, 0, 4, 'Del %s al %s' % (periodo,anio), style00)
        sheet.write_merge(3, 3, 0, 4, 'Inventario historial %s %s' % (name,uom), style00)
        sheet.write_merge(6, 6, 0, 0, 'Producto', style1)
        sheet.write_merge(6, 6, 1, 1, 'Entradas', style1)
        sheet.write_merge(6, 6, 2, 2,'Salidas', style1)
        sheet.write_merge(6, 6, 3, 3,'Stock fisico', style1)
        n = 7
        n_ini=n+1
        for item in ids:               
            sheet.write_merge(n, n, 0, 0, item['producto'], style_item)
            sheet.write_merge(n, n, 1, 1, item['entradas'], style_item)
            sheet.write_merge(n, n, 2, 2, item['salidas'], style_item)
            sheet.write_merge(n, n, 3, 3, item['stock_fisico'], style_item)
            n += 1
        n_fin=n
        # sum_tot = "SUM(D"+str(n_ini)+":D"+str(n_fin)+")"
        # sheet.write_merge(n, n, 3, 3, xlwt.Formula(sum_tot), style_item) 
        output = StringIO()
        workbook.save(output)
        out = base64.encodestring(output.getvalue())
        return out

     




       







