# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
from num2words import num2words
import xlwt
import json
from odoo import api, fields, models, _


class SalidadeProductos(models.Model):
    _inherit = 'stock.move'

    devolucion = fields.Boolean(default=False)

    
    def action_cancelar_entrada(self):
        if(self.env['tjacdmx.cierre.inventario'].get_is_periodo_cerrado(
            datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').month,
            datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').year) == False):           

            self.quant_ids.update( { 'location_id': 4})
            self.update({'state':'cancel'})

            for picking in self.picking_id:
                
                namepkg = self.name.lstrip().rstrip()

                tjacdmx_select_id_move_lines = "SELECT am.id FROM account_move am \
                                                    INNER JOIN account_move_line aml ON am.id = aml.move_id \
                                                    WHERE aml.ref = '"+picking.name+"' \
                                                    AND aml.name like '%"+namepkg+"%' \
                                                    GROUP BY am.id;"

                self.env.cr.execute(tjacdmx_select_id_move_lines)
                results = self.env.cr.fetchall()

                print(tjacdmx_select_id_move_lines.encode('utf-8', 'ignore')) 

                if(len(results)>=1):
                    for ids in results:
                        tjacdmx_update_status_account_move = "UPDATE account_move SET state = 'draft' WHERE id =%s" % (ids[0])
                        self.env.cr.execute(tjacdmx_update_status_account_move)
                        #self.env['account.move'].search([('id','=',ids[0])], limit=1).unlink()
                else:
                      raise UserError(_('Contacte a su personal de sistemas. No se encuentra una coincidencia para el asiento contable -account_move_line.name- para el nombre del movovimiento de stock stock_move.name:.'))  


# solicitud.suministro.lineas
class SolicitudSuministroLinea(models.Model):
    _name = 'solicitud.suministro.lineas'
    _rec_name='producto_solicit'

    producto_solicit = fields.Char(string="Producto solicitado")
    cantidad_solicit = fields.Char(string="Cantidad solicitada")
    uom_solicit = fields.Char(string="Medida solicitada")
    producto_id = fields.Integer(string='producto_id')
    producto_uom_id = fields.Integer(string='producto_uom_id')

    producto_entre = fields.Char(compute="_get_entrega", string="Producto entregado")
    cantidad_entre = fields.Char(compute="_get_entrega", string="Cantidad entregada")
    uom_entre = fields.Char(compute="_get_entrega", string="Medida entregada")

    codigo = fields.Char(compute="_get_entrega", string="Código")

    salida_masiva_id = fields.Many2one('tjacdmx.salida.inventario.masiva', string='S.S.')
    entregado = fields.Boolean(string='Entregado')

    estado_ss = fields.Char(string="Edo. S.S.", compute="_get_entrega")

    # @api.one
    def _get_entrega(self):
        scrap = self.env['stock.scrap'].search([('linea_suministro','=',self.id)])
        self.producto_entre = scrap.product_id.name
        self.cantidad_entre = scrap.scrap_qty
        self.uom_entre = scrap.product_uom_id.name
        self.estado_ss = self.salida_masiva_id.state

class ManualesUsuario(models.Model):
    _name = 'manuales.usuario'

    nombre = fields.Char(string="Nombre",required=True)
    area = fields.Many2one('presupuesto.areas.stok', string='Area',required=True)
    fecha = fields.Date(string='Fecha',required=True)
    version = fields.Char(string="Version")
    descripcion = fields.Text(string=u'Descripción') 

    archivo = fields.Binary('File', required=True)
    archivo_filename = fields.Char("Image Filename")

    status = fields.Selection([
        ('borrador', 'Borrador'),
        ('publicado', 'Públicado'),
        ('oculto', 'Oculto')], string='Estado', default="borrador")


#################################################stock_remisiones


class StockPickingRemei(models.Model):
    _inherit = 'stock.picking'

    remision_id = fields.Many2one('tjacdmx.remisiones',string="remision", readonly=True)

    @api.model
    def _prepare_values_extra_move(self, op, product, remaining_qty):
        res = super(StockPickingRemei, self)._prepare_values_extra_move(op, product, remaining_qty)
        for m in op.linked_move_operation_ids:
            if m.move_id.remisiones_line_id and m.move_id.product_id == product:
                res['remisiones_line_id'] = m.move_id.remisiones_line_id.id
                break
        return res

    @api.model
    def _create_backorder(self, backorder_moves=[]):
        res = super(StockPickingRemei, self)._create_backorder(backorder_moves)
        for picking in self:
            if picking.picking_type_id.code == 'incoming':
                for backorder in self.search([('backorder_id', '=', picking.id)]):
                    backorder.message_post_with_view('mail.message_origin_link',
                        values={'self': backorder, 'origin': backorder.remision_id},
                        subtype_id=self.env.ref('mail.mt_note').id)
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    remisiones_line_id = fields.Many2one('tjacdmx.remisiones.line','Remision Line', ondelete='set null', index=True, readonly=True)
    

    
    def get_price_unit(self):
        """ Returns the unit price to store on the quant """
        if self.remisiones_line_id:
            order = self.remisiones_line_id.remision_id
            #if the currency of the PO is different than the company one, the price_unit on the move must be reevaluated
            #(was created at the rate of the PO confirmation, but must be valuated at the rate of stock move execution)
            if order.currency_id != self.company_id.currency_id:
                #we don't pass the move.date in the compute() for the currency rate on purpose because
                # 1) get_price_unit() is supposed to be called only through move.action_done(),
                # 2) the move hasn't yet the correct date (currently it is the expected date, after
                #    completion of action_done() it will be now() )
                price_unit = self.purchase_line_id._get_stock_move_price_unit()
                self.write({'price_unit': price_unit})
                return price_unit
            return self.price_unit
        return super(StockMove, self).get_price_unit()

    
    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        if not default.get('split_from'):
            #we don't want to propagate the link to the purchase order line except in case of move split
            default['purchase_line_id'] = False
        return super(StockMove, self).copy(default)


class StockWarehouseRemision(models.Model):
    _inherit = 'stock.warehouse'

    buy_to_resupply = fields.Boolean('Purchase to resupply this warehouse', default=True,
                                     help="When products are bought, they can be delivered to this warehouse")
    buy_pull_id = fields.Many2one('procurement.rule', 'Buy rule')

    
    def _get_buy_pull_rule(self):
        try:
            buy_route_id = self.env['ir.model.data'].get_object_reference('purchase', 'route_warehouse0_buy')[1]
        except:
            buy_route_id = self.env['stock.location.route'].search([('name', 'like', _('Buy'))])
            buy_route_id = buy_route_id[0].id if buy_route_id else False
        if not buy_route_id:
            raise UserError(_("Can't find any generic Buy route."))

        return {
            'name': self._format_routename(_(' Buy')),
            'location_id': self.in_type_id.default_location_dest_id.id,
            'route_id': buy_route_id,
            'action': 'buy',
            'picking_type_id': self.in_type_id.id,
            'warehouse_id': self.id,
            'group_propagation_option': 'none',
        }

    
    def create_routes(self):
        res = super(StockWarehouseRemision, self).create_routes() # super applies ensure_one()
        if self.buy_to_resupply:
            buy_pull_vals = self._get_buy_pull_rule()
            buy_pull = self.env['procurement.rule'].create(buy_pull_vals)
            res['buy_pull_id'] = buy_pull.id
        return res

    
    def write(self, vals):
        if 'buy_to_resupply' in vals:
            if vals.get("buy_to_resupply"):
                for warehouse in self:
                    if not warehouse.buy_pull_id:
                        buy_pull_vals = self._get_buy_pull_rule()
                        buy_pull = self.env['procurement.rule'].create(buy_pull_vals)
                        vals['buy_pull_id'] = buy_pull.id
            else:
                for warehouse in self:
                    if warehouse.buy_pull_id:
                        warehouse.buy_pull_id.unlink()
        return super(StockWarehouseRemision, self).write(vals)

    
    def _get_all_routes(self):
        routes = super(StockWarehouseRemision, self).get_all_routes_for_wh()
        routes |= self.filtered(lambda self: self.buy_to_resupply and self.buy_pull_id and self.buy_pull_id.route_id).mapped('buy_pull_id').mapped('route_id')
        return routes

    
    def _update_name_and_code(self, name=False, code=False):
        res = super(StockWarehouseRemision, self)._update_name_and_code(name, code)
        warehouse = self[0]
        #change the buy procurement rule name
        if warehouse.buy_pull_id and name:
            warehouse.buy_pull_id.write({'name': warehouse.buy_pull_id.name.replace(warehouse.name, name, 1)})
        return res

    
    def _update_routes(self):
        res = super(StockWarehouseRemision, self)._update_routes()
        for warehouse in self:
            if warehouse.in_type_id.default_location_dest_id != warehouse.buy_pull_id.location_id:
                warehouse.buy_pull_id.write({'location_id': warehouse.in_type_id.default_location_dest_id.id})
        return res



class Remisiones(models.Model):
    _name = 'tjacdmx.devoluciones_almacen'
    _description = "Devoluciones Almacen"
    _inherit = ['mail.thread']

    number=fields.Char(string='Numero')
    move_origin=fields.Many2one('stock.quant',string='Origen',required=True)
    move_destination=fields.Many2one('stock.quant',string='Destino',required=True)
    date=fields.Date(string='Fecha', index=True, copy=False,track_visibility='always',required=True)
    amount_origin=fields.Float(string='Valor antes', readonly=True, compute='_amount_move')
    amount_destination=fields.Float(string='Valor despues', readonly=True, compute='_amount_move')

    # @api.one
    def _amount_move(self):
        self.amount_origin=self.move_origin.inventory_value if self.move_origin.inventory_value else 0
        self.amount_destination=self.move_destination.inventory_value if self.move_destination.inventory_value else 0




class ValoracionInventario(models.Model):
    _inherit = 'stock.quant'

    devolucion = fields.Boolean(default=False)


    
    def action_devoluciones(self):
        return {
                'name': _("Crear devolucion"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.devoluciones_almacen',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'origin': self.id}
            } 




    