# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
from num2words import num2words
import xlwt
import json
from odoo import api, fields, models, _, tools


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




# class viewSalidasInventarioDetalle(models.Model):
#     _name = 'tjacdmx.view_salidas_inventario_detalle'
#     _auto = False
#     _order = "partida_presupuestal asc"
    
#     id = fields.Integer(string='id')
#     mes = fields.Integer(string='mes')
#     anio = fields.Char(string='anio')
#     partida_presupuestal = fields.Char(string='partida_presupuestal')
#     area = fields.Char(string='areas')
#     departamento = fields.Char(string='departamento')
#     denominacion = fields.Char(string='denominacion')
#     salidas = fields.Float(string='salidas')
#     importe_salida = fields.Float(string='importe_salida')

#     def _select(self):
#         select_str = """
#         select  row_number() OVER () AS id,
#                 EXTRACT(MONTH FROM ss.date_expected) mes, 
#                 cast(EXTRACT(YEAR FROM ss.date_expected) as varchar) anio,
#                 ppp.partida_presupuestal as "partida_presupuestal",
#                 COALESCE(ss.areas, 'Sin especificar'::character varying) AS area,
#                 COALESCE(ss.departamento, 'Sin especificar'::character varying) AS departamento,
#                 ppp.denominacion,
#                 sum(ss.scrap_qty) as "salidas", 
#                 COALESCE(sum(ss.importe_salida_clone), 0) importe_salida
#         """
#         return select_str

#     def _group_by(self):
#         group_by_str = """
#             group by 2,3,4,5,6,7
#         """
#         return group_by_str

#     def _order_by(self):
#         order_by_str = """
#             order by anio
#         """
#         return order_by_str

#     def init(self):
#         tools.drop_view_if_exists(self._cr, self._table)
#         self._cr.execute("""
#             CREATE view %s as
#                 %s
#                from stock_scrap ss
#                 inner join product_product pp on pp.id=ss.product_id
#                 inner join product_template pt on pt.id = pp.product_tmpl_id
#                 inner join product_uom pu on pu.id=pt.uom_id
#                 join presupuesto_partida_presupuestal ppp on ppp.id=pt.posicion_presupuestaria 
#                 where  ppp.partida_presupuestal  in ('211100','214100','215100','216100','217100','221100','223100','233100','243100','244100','245100','246100',
#                 '247100','248100','249100','253100','254100','256100','261100','271100','272100','274100','291100','292100','293100','294100','296100','299100')
#                 %s
#                 %s
#         """ % (self._table, self._select(), self._group_by(), self._order_by()))


# class viewSalidasInventario(models.Model):
#     _name = 'tjacdmx.view_salidas_inventario'
#     _auto = False
#     _order = "partida_presupuestal asc"
    
#     id = fields.Integer(string='id')
#     mes = fields.Integer(string='mes')
#     anio = fields.Char(string='anio')
#     partida_presupuestal = fields.Char(string='partida_presupuestal')
#     denominacion = fields.Char(string='denominacion')
#     salidas = fields.Float(string='salidas')
#     importe_salida = fields.Float(string='importe_salida')

#     def _select(self):
#         select_str = """
#         select  row_number() OVER () AS id,
#                 EXTRACT(MONTH FROM ss.date_expected) mes, 
#                 cast(EXTRACT(YEAR FROM ss.date_expected) as varchar) anio,
#                 ppp.partida_presupuestal as "partida_presupuestal",
#                 ppp.denominacion,
#                 sum(ss.scrap_qty) as "salidas", 
#                 COALESCE(sum(ss.importe_salida_clone), 0) importe_salida
#         """
#         return select_str

#     def _group_by(self):
#         group_by_str = """
#             group by 2,3,4,5
#         """
#         return group_by_str

#     def _order_by(self):
#         order_by_str = """
#             order by anio
#         """
#         return order_by_str

#     def init(self):
#         tools.drop_view_if_exists(self._cr, self._table)
#         self._cr.execute("""
#             CREATE view %s as
#                 %s
#                from stock_scrap ss
#                 inner join product_product pp on pp.id=ss.product_id
#                 inner join product_template pt on pt.id = pp.product_tmpl_id
#                 inner join product_uom pu on pu.id=pt.uom_id
#                 join presupuesto_partida_presupuestal ppp on ppp.id=pt.posicion_presupuestaria 
#                 where  ppp.partida_presupuestal  in ('211100','214100','215100','216100','217100','221100','223100','233100','243100','244100','245100','246100',
#                 '247100','248100','249100','253100','254100','256100','261100','271100','272100','274100','291100','292100','293100','294100','296100','299100')
#                 %s
#                 %s
#         """ % (self._table, self._select(), self._group_by(), self._order_by()))

# class viewSalidasProductoArea(models.Model):
#     _name = 'tjacdmx.view_salidas_producto_area'
#     _description = "salidas propucto Almacen"
#     _auto = False
#     _order = "mes"
    
#     id = fields.Integer(string='id')
#     mes = fields.Integer(string='mes')
#     anio = fields.Char(string='anio')
#     producto_id = fields.Integer(string='producto_id')
#     partida_presupuestal = fields.Char(string='partida_presupuestal')
#     producto = fields.Char(string='producto')
#     area = fields.Char(string='area')
#     departamento = fields.Char(string='departamento')
#     salidas = fields.Float(string='salidas')
#     importe_salida = fields.Float(string='importe_salida')

#     def _select(self):
#         select_str = """
#         select
#             row_number() OVER () AS id,
#             EXTRACT(MONTH FROM ss.date_expected) mes, 
# 	        cast(EXTRACT(YEAR FROM ss.date_expected) as varchar)  anio,
#             pt.id as producto_id,
#             ppp.partida_presupuestal,
#             pt."name" as "producto",
#             coalesce(tsim.area, 'Sin especificar') area,
#             coalesce(tsim.departamento, 'Sin especificar') departamento,
#             sum(ss.scrap_qty) as "salidas",
#             sum(ss.importe_salida_clone) importe_salida
#         """
#         return select_str

#     def _group_by(self):
#         group_by_str = """
#             group by 2,3,4,5,6,7,8
#         """
#         return group_by_str

#     def _order_by(self):
#         order_by_str = """
#             order by 2
#         """
#         return order_by_str

#     def init(self):
#         tools.drop_view_if_exists(self._cr, self._table)
#         self._cr.execute("""
#             CREATE view %s as
#                 %s
#                from
#                 stock_scrap ss
#                 inner join product_product pp on
#                     pp.id = ss.product_id
#                 inner join product_template pt on
#                     pt.id = pp.product_tmpl_id
#                 inner join product_uom pu on
#                     pu.id = pt.uom_id
#                 join presupuesto_partida_presupuestal ppp on
#                     ppp.id = pt.posicion_presupuestaria
#                 join tjacdmx_salida_inventario_masiva tsim on tsim.id=ss.salida_masiva_id
#                 where ppp.capitulo = 2
#                 %s
#                 %s
#         """ % (self._table, self._select(), self._group_by(), self._order_by()))




# class view_servicio_electrico(models.Model):
#     _name = 'tjacdmx.view_servicio_electrico'
#     _description = "salidas propucto Almacen"
#     _auto = False
    
#     id = fields.Integer(string='id')
#     producto_id = fields.Integer(string='producto_id')
#     servicio = fields.Char(string='servicio')
#     edificio = fields.Char(string='edificio')
#     proveedor = fields.Char(string='proveedor')
#     categoria_id = fields.Integer(string='categoria_id')
#     categoria = fields.Char(string='categoria')
#     partida = fields.Char(string='partida')
#     no_factura = fields.Char(string='no_factura')
#     requisicion = fields.Char(string='requisicion')
#     descripcion = fields.Char(string='descripcion')
#     fecha = fields.Date(string='fecha')
#     total = fields.Float(string='total')
#     total_unitario = fields.Float(string='total_unitario')

#     def _select(self):
#         select_str = """
#        select
#         row_number() OVER () AS id,
#         pt.id producto_id,
#         pt."name" servicio,
#         (CASE WHEN pt.id=1181 THEN 'COYOACAN' 
# 	      WHEN pt.id=1182 THEN 'INSURGENTES' 
# 	      WHEN pt.id=1183 THEN 'NEBRASKA'
# 	      WHEN pt.id=1121 THEN 'COYOACAN'
# 	      WHEN pt.id=1122 THEN 'INSURGENTES'
# 	      WHEN pt.id=1123 THEN 'NEBRASKA' ELSE 'Indefinido' END) edificio,
#         rp."name" proveedor,
#         pc.id categoria_id,
#         pc."name" categoria,
#         ppp.partida_presupuestal partida,
#         tr.no_factura,
#         prccl."name" requisicion,
#         prccl.descripcion,
#         trl.date_planned fecha,
#         trl.price_total total,
#         trl.price_unit total_unitario
#         """
#         return select_str

#     def _group_by(self):
#         group_by_str = """
            
#         """
#         return group_by_str

#     def _order_by(self):
#         order_by_str = """
#             order by 10 desc
#         """
#         return order_by_str

#     def init(self):
#         tools.drop_view_if_exists(self._cr, self._table)
#         self._cr.execute("""
#             CREATE view %s as
#                 %s
#                from product_template pt 
#                 join product_product pp on pp.product_tmpl_id =pt.id
#                 join tjacdmx_remisiones_line trl on trl.product_id =pp.id
#                 join tjacdmx_remisiones tr on tr.id=trl.remision_id
#                 join res_partner rp on rp.id=tr.partner_id
#                 join product_category pc on pc.id=pt.categ_id
#                 join presupuesto_partida_presupuestal ppp on ppp.id=pt.posicion_presupuestaria
#                 join  presupuesto_requisicion_compras_compromisos_line prccl on prccl.id=tr.origin
#                 where pt.id in (1181, 1182, 1183, 1121, 1122, 1123,1231,1248,1384,1212) and trl.state='pagado'
#                 %s
#                 %s
#         """ % (self._table, self._select(), self._group_by(), self._order_by()))


class view_servicios_normatividad(models.Model):
    _name = 'tjacdmx.view_servicios_normatividad'
    _description = "Normatividad"
    _auto = False
    
    id = fields.Integer(string='id')
    account_id = fields.Integer(string='account_id')
    nombre_cuenta = fields.Char(string='nombre_cuenta')
    cuenta = fields.Char(string='cuenta')
    fecha = fields.Date(string='fecha')
    periodo = fields.Integer(string='periodo')
    anio = fields.Char(string='anio')
    saldo_inicial = fields.Float(string='saldo_inicial')
    debe = fields.Float(string='debe')
    haber = fields.Float(string='haber')
    saldo_final = fields.Float(string='saldo_final')

    def _select(self):
        select_str = """
       select
        row_number() over () as id,
        vb.account_id,
        vb.nombre_c nombre_cuenta,
        vb.code cuenta,
        vb.periodo_fecha fecha,
        vb.periodo,
        vb.anio,
        vb.saldo_inicial,
        vb.debe,
        vb.haber,
        vb.saldo_final
        """
        return select_str

    def _group_by(self):
        group_by_str = """
            
        """
        return group_by_str

    def _order_by(self):
        order_by_str = """
            order by 5 desc
        """
        return order_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
                %s
            from v_balanza vb
            where
                vb.account_id in (562, 247, 495, 475, 581, 601, 578, 663, 647,233,651)
                %s
                %s
        """ % (self._table, self._select(), self._group_by(), self._order_by()))



# class view_servicios_factura(models.Model):
#     _name = 'tjacdmx.view_servicios_factura'
#     _description = "Servicios factura"
#     _auto = False
    
#     id = fields.Integer(string='id')
#     producto = fields.Char(string='producto')
#     description = fields.Char(string='description')
#     categoria = fields.Char(string='categoria')
#     partida_presupuestal = fields.Char(string='partida_presupuestal')
#     vatios = fields.Float(string='vatios')
#     litros = fields.Float(string='litros')
#     periodo_inicio = fields.Date(string='periodo_inicio')
#     periodo_fin = fields.Date(string='periodo_fin')
#     price_subtotal = fields.Float(string='price_subtotal')
#     amount_total = fields.Float(string='amount_total')
#     date_invoice = fields.Date(string='date_invoice')
#     date_due = fields.Date(string='date_due')
#     proveedor = fields.Char(string='proveedor')
#     area_direccion = fields.Char(string='area_direccion')
#     edificio = fields.Char(string='edificio')

#     def _select(self):
#         select_str = """
#         select
#             row_number() OVER () AS id,
#             pt."name" producto,
#             ail."name" description,
#             pc."name" categoria,
#             ppp.partida_presupuestal,
#             ai.vatios,
#             ai.litros,
#             ai.periodo_inicio,
#             ai.periodo_fin,
#             ail.price_subtotal,
#             ai.amount_total,
#             ai.date_invoice,
#             ai.date_due,
#             rp."name" proveedor,
#             ad.nombre area_direccion,
#             (CASE WHEN pt.id=1181 THEN 'COYOACÁN' 
#                 WHEN pt.id=1182 THEN 'INSURGENTES' 
#                 WHEN pt.id=1183 THEN 'NEBRASKA'
#                 WHEN pt.id=1121 THEN 'COYOACÁN'
#                 WHEN pt.id=1122 THEN 'INSURGENTES'
#                 WHEN pt.id=1123 THEN 'NEBRASKA' ELSE 'Indefinido' END) edificio
#         """
#         return select_str

#     def _group_by(self):
#         group_by_str = """
            
#         """
#         return group_by_str

#     def _order_by(self):
#         order_by_str = """
#             order by 10 desc
#         """
#         return order_by_str

#     def init(self):
#         tools.drop_view_if_exists(self._cr, self._table)
#         self._cr.execute("""
#             CREATE view %s as
#                 %s
#               from
#                     account_invoice_line ail
#                 join account_invoice ai on
#                     ai.id = ail.invoice_id
#                 join product_product pp on
#                     pp.id = ail.product_id
#                 join product_template pt on
#                     pt.id = pp.product_tmpl_id
#                 join res_partner rp on
#                     rp.id = ai.partner_id
#                 join product_category pc on
#                     pc.id = pt.categ_id
#                 join presupuesto_partida_presupuestal ppp on
#                     ppp.id=pt.posicion_presupuestaria
#                 left join areas_direccion ad on
#                     ad.id=ai.area_tb 
#                 where
#                     ail.product_id in (1176,1175,1177,1116,1117,1115,1225,1241,1335,1206,1129,1130,1131,1277,1337,1338,1612,1629,1638,1665)
#                     and ai.state = 'paid_all'
#                 %s
#                 %s
#         """ % (self._table, self._select(), self._group_by(), self._order_by()))




    