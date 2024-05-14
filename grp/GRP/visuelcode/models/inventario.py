# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import calendar
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import dateutil.relativedelta
from calendar import monthrange
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)
import xlrd
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero
import base64
# import pandas

class AjusteInventario(models.Model):
    _name = 'visuelcode.ajuste.inventario'
    _description = "Ajuste de inventario"
    _rec_name='nombre'

    @api.depends('fecha')
    def _compute_date_planned(self):
        min_date = datetime.today()
        return min_date


    nombre=fields.Char(string="Nombre",required=True)		
    fecha=fields.Date(string="Fecha",required=True,default=_compute_date_planned)
    productos_put= fields.One2many('visuelcode.ajuste.inventario.linea', 'ajuste_inventario_id', string='remision Lines',copy=True,required=True)
    productos_put_file= fields.One2many('visuelcode.ajuste.inventario.linea.file', 'ajuste_inventario_file_id', string='remision',copy=True,required=True)
    state = fields.Selection([
            ('draft','Borrador'),
            ('open', 'Validado'),
            ('cancel', 'Cancelado'),
            ], string='Estado', index=True, readonly=False, default='draft')
    archivo=fields.Binary(string="Archivo",required=False)	

    # @api.onchange('archivo')
    # def _onchange_file(self):
    #     excel_data_df = pandas.read_excel('/stock_quant.xlsx', sheet_name='Sheet1')
    #     df2 = excel_data_df.to_json(orient = 'records')
    #     raise ValidationError("%s"%df2)
    #     pass

        

    def validate_in(self):
        warehouse = self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1)
        if(self.productos_put):
            sql="""select
                    vail.product_id,
                    (
                    select
                        case
                            when (
                            select
                                quantity
                            from
                                stock_quant sq
                            where
                                product_id = vail.product_id
                                and location_id = 8)>0 then (
                            select
                                quantity
                            from
                                stock_quant sq
                            where
                                product_id = vail.product_id
                                and location_id = 8)
                            else 0
                        end
                )+(case when count(vail.id)>0 then count(vail.id)
                    else 0
                end) as count
                from
                    visuelcode_ajuste_inventario_linea vail
                where
                    ajuste_inventario_id = %s
                group by
                    vail.product_id;"""
            self.env.cr.execute(sql % (self.id))
            total_product = self.env.cr.dictfetchall()
            products=[]
            for item in total_product:
                product={
                    'product_id': item['product_id'],
                    'inventory_quantity':item['count'],
                }
                products.append(product)
            # raise ValidationError("Debug: %s" % (products))
            for item in products:
                response=self.env['stock.quant'].with_context(inventory_mode=True).create({
                    'product_id': item['product_id'],
                    'location_id': warehouse.lot_stock_id.id,
                    'inventory_quantity': item['inventory_quantity'],
                })
                response.action_apply_inventory()
            self.write({'state': 'open'})


class AjusteInventarioLineasFile(models.Model):
    _name = 'visuelcode.ajuste.inventario.linea.file'
    _description = "Lineas ajuste de inventario file"
    _rec_name='product_id'

    ajuste_inventario_file_id = fields.Many2one('visuelcode.ajuste.inventario', string='Reference', index=True)
    product_id = fields.Many2one('product.product', string='Producto',required=True)
    name = fields.Char(string="Codigo de barra",required=False)
    qty_invoiced = fields.Float(string="Nueva cantidad")


            
class AjusteInventarioLineas(models.Model):
    _name = 'visuelcode.ajuste.inventario.linea'
    _description = "Lineas ajuste de inventario"
    _rec_name='product_id'

    ajuste_inventario_id = fields.Many2one('visuelcode.ajuste.inventario', string='Reference', index=True)
    product_id = fields.Many2one('product.product', string='Producto',required=True)
    codigo = fields.Char(string="Codigo de barra",required=False)
    qty_invoiced = fields.Float(string="Cantidad")


    @api.onchange('codigo')
    def _onchange_product_id(self):
        if(self.codigo):
            pp=self.env['product.product'].search([('barcode','=',self.codigo)],limit=1)
            if(pp):
                self.product_id=pp.id
            else:
                raise ValidationError("Este producto no esta registrado ")

    
    






    



