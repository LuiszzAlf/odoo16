# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
# from odoo.tools.translate import _

class ProductoTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    # def _get_default_category_id(self):
    #     if self._context.get('categ_id') or self._context.get('default_categ_id'):
    #         return self._context.get('categ_id') or self._context.get('default_categ_id')
    #     category = self.env.ref('product.product_category_all', raise_if_not_found=False)
    #     return category and category.type == 'normal' and category.id or False

    name = fields.Char('Name', index=True, required=True, translate=True,track_visibility='onchange')
    posicion_presupuestaria = fields.Many2one('presupuesto.partida_presupuestal',track_visibility='onchange', string='Posición presupuestaria', required=True, domain="[('partida_presupuestal','!=','000000'),('partida_presupuestal','!=','800000'),('partida_presupuestal','!=','700000')]")
    remisiones_count=fields.Integer(compute="_compute_remisiones", string='Entregas',copy=False, default=0)
    purchase_count=fields.Integer(compute="_compute_purchase", string='Compras',copy=False, default=0)
    categ_id = fields.Many2one('product.category', 'Internal Category',change_default=True,
        required=True, help="Select category for the current product",track_visibility='onchange')
    account_stock=fields.Many2one('account.account',string='Cuenta inventario')
    tipo=fields.Selection([
        ('general', 'General'),
        ('orden_social', 'Orden Social'),
        ('viaticos', 'Viáticos'),
        ('alimentos', 'Alimentos'),
        ('informatica', 'Informatica')], string='Tipo', default="general", track_visibility='onchange')



    def open_kardex(self):
        product_product = self.env['product.product'].search([('product_tmpl_id','=',self.id)],limit=1)
        return {
                'name': _("Kardex %s" % self.name),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.kardex',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'product_id': product_product.id,'name': self.name,'uom': self.uom_id.name}
            } 


    
    @api.depends('qty_available','standard_price')
    def _compute_stock(self):
        self.qty_available_clone=self.qty_available
        self.standard_price_clone=self.standard_price
        
    qty_available_clone = fields.Float( digits=(15, 2), compute='_compute_stock', default=0, string='Stock',store=True)
    standard_price_clone = fields.Float( digits=(15, 2), compute='_compute_stock', default=0, string='Precio',store=True)

    def _compute_remisiones(self):
        product_product = self.env['product.product'].search([('product_tmpl_id','=',self.id)],limit=1)
        remisiones_line = self.env['tjacdmx.remisiones.line'].search([('product_id','=',product_product.id)])
        listids=[]
        for each in remisiones_line:
            listids.append(each.remision_id.id)
        remision_origen=self.env['tjacdmx.remisiones'].search([('id','in', listids)])
        self.remisiones_count = len(remision_origen)
    
    def _compute_purchase(self):
        product_product = self.env['product.product'].search([('product_tmpl_id','=',self.id)],limit=1)
        purchase_line = self.env['purchase.order.line'].search([('product_id','=',product_product.id)])
        listids=[]
        for each in purchase_line:
            listids.append(each.order_id.id)
        purchase_origen=self.env['purchase.order'].search([('id','in', listids)])
        self.purchase_count = len(purchase_origen)
    
    
    
    def view_remisiones(self):
        product_product = self.env['product.product'].search([('product_tmpl_id','=',self.id)],limit=1)
        remisiones_line = self.env['tjacdmx.remisiones.line'].search([('product_id','=',product_product.id)])
        listids=[]
        for each in remisiones_line:
            listids.append(each.remision_id.id)
        action = self.env.ref('presupuestos.action_remiciones')
        res = self.env.ref('presupuestos.action_tjacdmx_remisiones_form', False)
        search_remis_active = self.env['tjacdmx.remisiones'].search([('id','in',listids)])
        if (search_remis_active):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','in',%s)]" % (listids)
        else:
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','=','0')]"
        return result
    
    
    def view_purchase(self):
        purchase_origen_line = self.env['purchase.order.line'].search([('product_id','=',self.id)])
        listids=[]
        for each in purchase_origen_line:
            listids.append(each.order_id.id)
        action = self.env.ref('presupuestos.action_compras')
        res = self.env.ref('presupuestos.action_tjacdmx_purchase_form', False)
        search_remis_active = self.env['purchase.order'].search([('id','in',listids)])
        if (search_remis_active):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','in',%s)]" % (listids)
        else:
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','=','0')]"
        return result

    @api.onchange('type')
    
    def _change_type(self):
        if(self.type == 'consu'):
             raise ValidationError("Recuerda el tipo de producto Consumible no esta habilitado, selecciona 'CONSUMIBLE' o 'SERVICIO'.")

    @api.model
    def _partida_search(self, name, args=None, operator='ilike'):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('partida_presupuestal', '=ilike', name.split(' ')[0] + '%'), ('partida_presupuestal', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        partidas_ids = self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(partidas_ids).name_get()
    



# class ProductoCategory(models.Model):
#     _name = 'product.category'
#     _inherit = 'product.category'

#     numpp = fields.Char(string='Partida presupuestal', required=True)


class ProductoTemplateLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'

    tipo_contrato = fields.Many2one('purchase.requisition.type',string='Tipo de contrato')

class ProductoProducto(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'
    
    
    def view_remisiones(self):
        remisiones_line = self.env['tjacdmx.remisiones.line'].search([('product_id','=',self.id)])
        listids=[]
        for each in remisiones_line:
            listids.append(each.remision_id.id)
        action = self.env.ref('presupuestos.action_remiciones')
        res = self.env.ref('presupuestos.action_tjacdmx_remisiones_form', False)
        search_remis_active = self.env['tjacdmx.remisiones'].search([('id','in',listids)])
        if (search_remis_active):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','in',%s)]" % (listids)
        else:
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','=','0')]"
        return result
    
    
    def view_purchase(self):
        purchase_origen_line = self.env['purchase.order.line'].search([('product_id','=',self.id)])
        listids=[]
        for each in purchase_origen_line:
            listids.append(each.order_id.id)
        action = self.env.ref('presupuestos.action_compras')
        res = self.env.ref('presupuestos.action_tjacdmx_purchase_form', False)
        search_remis_active = self.env['purchase.order'].search([('id','in',listids)])
        if (search_remis_active):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','in',%s)]" % (listids)
        else:
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','=','0')]"
        return result


class ProductoCategoria(models.Model):
    _name = 'product.category'
    _inherit = 'product.category'

    account_stock=fields.Many2one('account.account',string='Cuenta inventario')
