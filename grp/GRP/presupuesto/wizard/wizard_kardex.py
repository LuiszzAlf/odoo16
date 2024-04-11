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


class wizard_kardex(models.TransientModel):
    _name = 'wizard.kardex'

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
    fecha_inicio = fields.Date(string='Fecha inicio')
    fecha_fin = fields.Date(string='Fecha del fin')
    result_pc_html=fields.Html(string='Resultados',compute='search_kardex_xls')
    csv_urls = fields.Char(compute='search_kardex_xls')
    
    @api.multi
    @api.onchange('fecha_inicio')
    def _onchange_date(self):
        date_fin=self.fecha_inicio
        self.update({'fecha_fin': date_fin})
    
    @api.multi
    def search_kardex(self):
        datas = {}
        sql_all="""(
                    select
                        'Entrada' tipo,
                        'WH/IN' referencia,
                        date_expected fecha,
                        product_qty cantidad
                    from
                        stock_move sm
                    where
                        date_expected between '%s 00:00:00' and '%s 23:59:00'
                        and product_id = %s
                        and scrapped = false
                    )
                    union
                    (
                    select
                        'Salida' tipo,
                    "name" referencia,
                    date_expected fecha,
                    scrap_qty cantidad
                    from
                        stock_scrap sq
                    where
                        date_expected between '%s 00:00:00' and '%s 23:59:00'
                    and product_id = %s
                    and state = 'done')
                    order by
                    fecha desc;"""
        self.env.cr.execute(sql_all % (self.fecha_inicio, self.fecha_fin,self.product_id,self.fecha_inicio, self.fecha_fin,self.product_id))
        rows_sql = self.env.cr.dictfetchall()
        array_mov=[] 
        for i in rows_sql:
            mov = {
                'tipo': i['tipo'],
                'referencia': i['referencia'],
                'fecha': i['fecha'],
                'cantidad': i['cantidad']
           }
            array_mov.append(mov)
        fecha = datetime.strptime(self.fecha_inicio, '%Y-%m-%d') if self.fecha_inicio else datetime.today()
        fechas=datetime.today()
        datas['periodo'] = fecha.month
        datas['anio'] = fecha.year
        datas['fecha_reporte'] = str(datetime.strftime(fechas,"%Y-%m-%d"))
        datas['name'] = self.producto
        datas['uom'] = self.uom
        datas['movimientos'] = array_mov
        return self.env['report'].get_action([], 'presupuestos.kardex_product', data=datas)
    
    
    @api.multi
    def search_kardex_xls(self):
        sql_all="""(
                    select
                        'Entrada' tipo,
                        'WH/IN' referencia,
                        date_expected fecha,
                        product_qty cantidad
                    from
                        stock_move sm
                    where
                        date_expected between '%s 00:00:00' and '%s 23:59:00'
                        and product_id = %s
                        and scrapped = false
                    )
                    union
                    (
                    select
                        'Salida' tipo,
                    "name" referencia,
                    date_expected fecha,
                    scrap_qty cantidad
                    from
                        stock_scrap sq
                    where
                        date_expected between '%s 00:00:00' and '%s 23:59:00'
                    and product_id = %s
                    and state = 'done')
                    order by
                    fecha desc;"""
        self.env.cr.execute(sql_all % (self.fecha_inicio, self.fecha_fin,self.product_id,self.fecha_inicio, self.fecha_fin,self.product_id))
        rows_sql = self.env.cr.dictfetchall()
        array_mov=[] 
        for i in rows_sql:
            mov = {
                'tipo': i['tipo'],
                'referencia': i['referencia'],
                'fecha': i['fecha'],
                'cantidad': i['cantidad']
           }
            array_mov.append(mov)
        fecha = datetime.strptime(self.fecha_inicio, '%Y-%m-%d') if self.fecha_inicio else datetime.today()
        fechas=datetime.today()
        fecha_reporte=str(fecha.month)+' '+str(fecha.year)
        excel_encode = self.get_decode_excel(array_mov,self.producto,self.uom,str(fecha.month),str(fecha.year))
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
        sheet.write_merge(2, 2, 0, 4, 'Periodo %s del %s' % (periodo,anio), style00)
        sheet.write_merge(3, 3, 0, 4, 'Kardex: %s %s' % (name,uom), style00)
        sheet.write_merge(6, 6, 0, 0, 'Tipo', style1)
        sheet.write_merge(6, 6, 1, 1, 'Referencia', style1)
        sheet.write_merge(6, 6, 2, 2,'Fecha', style1)
        sheet.write_merge(6, 6, 3, 3,'Cantidad', style1)
        n = 7
        n_ini=n+1
        for item in ids:               
            sheet.write_merge(n, n, 0, 0, item['tipo'], style_item)
            sheet.write_merge(n, n, 1, 1, item['referencia'], style_item)
            sheet.write_merge(n, n, 2, 2, item['fecha'], style_item)
            sheet.write_merge(n, n, 3, 3, item['cantidad'], style_item)
            n += 1
        n_fin=n
        # sum_tot = "SUM(D"+str(n_ini)+":D"+str(n_fin)+")"
        # sheet.write_merge(n, n, 3, 3, xlwt.Formula(sum_tot), style_item) 
        output = StringIO()
        workbook.save(output)
        out = base64.encodestring(output.getvalue())
        return out

     




       







