# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import pytz
import base64 
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta




class wizard_devoluciones(models.TransientModel):
    _name = 'wizard.devoluciones_almacen'

    @api.model
    def _get_origin(self):
        context = dict(self._context or {})
        origin = context.get('origin', False)
        if origin:
            data = origin
            return data
        return ''

    move_origin=fields.Many2one('stock.quant',string='Origen',required=True,default=_get_origin)
    qty=fields.Float(string='Cantidad',required=True)
    date= fields.Date(string='Fecha',required=True)
    
    @api.multi
    def create_devolucion(self):
        tz_NY = pytz.timezone('America/Mexico_City') 
        datetime_CDMX = datetime.now(tz_NY)
        fecha=datetime_CDMX.strftime('%Y-%m-%d')
        devoluciones=self.env['tjacdmx.devoluciones_almacen']
        stock_quant=self.env['stock.quant'].search([('id','=', self.move_origin.id)])
        cantidad=stock_quant.qty-self.qty
        #stock_move=self.env['stock.move'].search([('id','=', stock_quant.history_ids.id)])
        move_orig_ids=[]
        quant_ids=[]
        reserved_quant_ids=[]
        linked_move_operation_ids=[]
        route_ids=[]
        location=0
        if(cantidad>0):
            location=15
        else:
            location=4
        detalle_sm={
                    'name':str('DEV/'+str(stock_quant.product_id.name.encode('utf-8'))),
                    'sequence':10,
                    'priority': '1',
                    'create_date':self.date,
                    'date':self.date,
                    'company_id':1,
                    'date_expected':self.date,
                    'product_id':stock_quant.product_id.id,
                    'ordered_qty':self.qty,
                    'product_uom_qty':self.qty,
                    'product_uom':stock_quant.product_id.uom_id.id,
                    'product_tmpl_id':stock_quant.product_id.product_tmpl_id.id,
                    'product_packaging':'',
                    'location_id':15,
                    'location_dest_id':4,
                    'partner_id':'',
                    'move_dest_id':'',
                    'move_orig_ids':move_orig_ids,
                    'picking_id':'',
                    'picking_partner_id':'',
                    'note':'',
                    'state':'done',
                    'partially_available':False,
                    'price_unit':stock_quant.cost,
                    'split_from':'',
                    'backorder_id':'',
                    'origin':'',
                    'procure_method':'make_to_stock',
                    'scrapped':True,
                    'quant_ids':quant_ids,
                    'reserved_quant_ids':reserved_quant_ids,
                    'linked_move_operation_ids':linked_move_operation_ids,
                    'procurement_id':'',
                    'group_id':'',
                    'rule_id':'',
                    'push_rule_id':'',
                    'propagate':True,
                    'picking_type_id':'',
                    'inventory_id':'',
                    'origin_returned_move_id':'',
                    'availability':'',
                    'restrict_lot_id':'',
                    'restrict_partner_id':'',
                    'route_ids':route_ids,
                    'warehouse_id':'',
                    'devolucion': True
                }
        stock_move_created=self.env['stock.move'].create(detalle_sm)
        history_ids=[]
        for e in stock_move_created:
            history_ids.append(e.id)
        detalle_sc={
                    'product_id': stock_quant.product_id.id,
                    'location_id': location,
                    'qty': cantidad,
                    'product_uom_id': stock_quant.product_uom_id.id,
                    'package_id': stock_quant.package_id.id,
                    'packaging_type_id':stock_quant.packaging_type_id.id,
                    'reservation_id':stock_quant.reservation_id.id,
                    'lot_id':stock_quant.lot_id.id,
                    'cost':stock_quant.cost,
                    'owner_id':stock_quant.owner_id.id,
                    'create_date':self.date,
                    'in_date':stock_quant.in_date,
                    'history_ids':history_ids,
                    'company_id':stock_quant.company_id.id,
                    'propagated_from_id':stock_quant.propagated_from_id.id,
                    'negative_move_id':stock_quant.negative_move_id.id,
                    'negative_dest_location_id':stock_quant.negative_dest_location_id.id,
                    'devolucion': True
                }

        stock_quant_created=self.env['stock.quant'].create(detalle_sc)
        query = "INSERT INTO stock_quant_move_rel values(%s,%s)" % (stock_move_created.id,stock_quant_created.id)
        self.env.cr.execute(query)

        
        detalle_dev={
                        'number': stock_quant.product_id.name,
                        'move_origin': stock_quant.id,
                        'move_destination': stock_quant_created.id,
                        'date': self.date
                    }

                    
        devoluciones_create=devoluciones.create(detalle_dev)
        stock_quant.write({'qty': self.qty})
        stock_quant.write({'location_id': 4})




       