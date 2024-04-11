# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class cancel_budget(models.TransientModel):
    _name = 'cancel_budget.wizard'

    @api.model
    def _get_tipo(self):
        context = dict(self._context or {})
        momento_con = context.get('tipo', False)
        if momento_con:
            data = momento_con
            return data
        return ''

    @api.model
    def _get_compra(self):
        context = dict(self._context or {})
        compra_id = context.get('compra_id', False)
        if compra_id:
            data = compra_id
            return data
        return ''

    @api.model
    def _get_factura(self):
        context = dict(self._context or {})
        invoice_id = context.get('invoice_id', False)
        if invoice_id:
            data = invoice_id
            return data
        return ''
    
    compra_ids=fields.Integer(default=_get_compra,readonly=True)
    invoice_id=fields.Integer(default=_get_factura,readonly=True)
    tipo=fields.Char(string='Clave', default=_get_tipo, readonly=True)
    momento_contable=fields.Many2one ('account.move',string='Momento contable', domain="[('compra_id','=', compra_ids),('state','=','posted'),('name','like', tipo)]")
    ejercicio=fields.Char(string='Ejercicio', readonly=True)
    periodo=fields.Char(string='Periodo', readonly=True)
    fecha_documento=fields.Char(string='Fecha', readonly=True)
    centro_gestor=fields.Char(string='Centro gestor', readonly=True)
    area_funcional=fields.Char(string='Area funcional', readonly=True)
    partida_presupuestal=fields.Char(string='Partida', readonly=True)  
    partida_presupuestal_id=fields.Char(string='Partida id', readonly=True)    
    str_momento=fields.Char(string='Tipo', readonly=True)
    amount_total=fields.Float(string='Monto',readonly=True)
    diario=fields.Char(string='Diario',readonly=True)
    fecha_contable=fields.Char(string='Fecha contable',readonly=True)
    html_apuntes_contables=fields.Html(string='Apuntes contables',readonly=True)

    @api.multi
    @api.onchange('momento_contable')
    def _onchange_asiento(self):
        documento = self.env['presupuesto.documento'].search([('id','=',self.momento_contable.documento_id.id)],limit=1)
        documento_detalle = self.env['presupuesto.detalle_documento'].search([('documento_id','=',documento.id)],limit=1)
        asiento_c = self.env['account.move'].search([('id','=',self.momento_contable.id)],limit=1)
        asiento_c_det = self.env['account.move.line'].search([('move_id','=',asiento_c.id)])
        html_items=""
        for items in asiento_c_det:
            code=str(items.account_id.code)
            debe=str(items.debit)
            haber=str(items.credit)
            html_items2="<tr><td><p>"+code+"</p></td> <td><p>"+debe+"</p></td><td><p>"+haber+"</p></td></tr>"
            html_items+=html_items2.encode('ascii', 'ignore')
        html="""<table class="table table-striped">
                <tr><td>Cuenta</td><td>Debe</td><td>Haber</td></tr>
                %s
            </table>""" % (html_items)
        self.update({
            'ejercicio': documento.ejercicio,
            'periodo': documento.periodo,
            'fecha_documento': documento.fecha_documento,
            'centro_gestor': documento_detalle.centro_gestor.centro_gestor,
            'area_funcional': documento_detalle.area_funcional.concepto,
            'partida_presupuestal': documento_detalle.posicion_presupuestaria.partida_presupuestal,
            'partida_presupuestal_id': documento_detalle.posicion_presupuestaria,
            'str_momento': documento_detalle.momento_contable,
            'amount_total': documento_detalle.importe,
            'diario': asiento_c.journal_id.name,
            'fecha_contable': asiento_c.date,
            'html_apuntes_contables': html,
            })

    def cancel_pago_compra_fuction(self):
        ctrl_periodo = self.env['control.periodos.wizard']

        documento = self.env['presupuesto.documento'].search([('id','=',self.momento_contable.documento_id.id)],limit=1)
        
        if(not ctrl_periodo.get_is_cerrado(documento.fecha_documento)):
            if(self.tipo=='COPP'):
                purchase = self.env['purchase.order'].search([('id','=',self.compra_ids)], limit=1)
                documento_pagado=self.env['presupuesto.documento'].search([('id', '=',self.momento_contable.documento_id.id)],limit=1)
                documento=self.env['presupuesto.documento'].search([('compra_id', '=',purchase.id)],limit=1)
                asiento_contable=self.momento_contable
                purc_ids= purchase.id if purchase.id else 0
                asiento_contable_ids= asiento_contable.id if asiento_contable.id else 0
                documento_ids= documento.id if documento.id else 0
                fecha=datetime.strptime(purchase.date_order, '%Y-%m-%d %H:%M:%S') if purchase.date_order else datetime.today()
                factura = self.env['account.invoice'].search([('id','=',self.invoice_id)])
                line_factura = self.env['account.invoice.line'].search([('invoice_id','=',self.invoice_id)])
                for item in line_factura:
                    posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
                    cp = self.env['presupuesto.control_presupuesto'].search([
                    ('version', '=', documento.version.id),
                    ('ejercicio', '=', documento.ejercicio),
                    ('periodo', '=', fecha.month),
                    ('posicion_presupuestaria', '=', posicion_presupuestaria.id)])
                    if(item.uom_id.id==31):
                        importe=item.price_subtotal+factura.amount_tax
                        cp.write({ 'egreso_pagado': cp.egreso_pagado - importe })
                        cp.write({ 'egreso_ejercido': cp.egreso_ejercido + importe })
                    else:
                        cp.write({ 'egreso_pagado': cp.egreso_pagado - item.price_subtotal })
                        cp.write({ 'egreso_ejercido': cp.egreso_ejercido + item.price_subtotal })
                if(documento_pagado.clase_documento.id):
                    query1 = "DELETE FROM presupuesto_detalle_documento WHERE documento_id=%s" % (documento_ids)
                    query2 = "DELETE FROM presupuesto_documento WHERE id=%s" % (documento_ids)
                    self.env.cr.execute(query1)
                    self.env.cr.execute(query2)
                query_put = "UPDATE purchase_order SET status_account_move='EJERCIDO' WHERE id = %s;" % (purc_ids)
                query_delete = "DELETE FROM account_move WHERE id=%s" % (asiento_contable_ids)
                query_delete2 = "DELETE FROM account_move_line WHERE move_id=%s" % (asiento_contable_ids)
                self.env.cr.execute(query_delete2)
                self.env.cr.execute(query_delete)
                self.env.cr.execute(query_put)
                query_put_state_invoice = "UPDATE account_invoice SET state='paid' WHERE id = %s;" % (self.invoice_id)
                self.env.cr.execute(query_put_state_invoice)

            elif(self.tipo=='COPE'):
                purchase = self.env['purchase.order'].search([('id','=',self.compra_ids)], limit=1)
                documento_ejercido=self.env['presupuesto.documento'].search([('compra_id', '=',purchase.id),('clase_documento', '=',9)],limit=1)
                documento_dev=self.env['presupuesto.documento'].search([('compra_id', '=',purchase.id),('clase_documento', '=',7)],limit=1)
                asiento_contable=self.env['account.move'].search([('compra_id', '=', purchase.id),('journal_id', '=', 71)],limit=1)
                purc_ids= purchase.id if purchase.id else 0
                asiento_contable_ids= asiento_contable.id if asiento_contable.id else 0
                documento_ids= documento_ejercido.id if documento_ejercido.id else 0
                fecha=datetime.strptime(purchase.date_order, '%Y-%m-%d %H:%M:%S') if purchase.date_order else datetime.today()
                factura = self.env['account.invoice'].search([('id','=',self.invoice_id)])
                line_factura = self.env['account.invoice.line'].search([('invoice_id','=',self.invoice_id)])
                if(documento_ejercido):
                    documento_version=documento_ejercido.version.id
                    documento_ejercicio=documento_ejercido.ejercicio
                else:
                    documento_version=documento_dev.version.id
                    documento_ejercicio=documento_dev.ejercicio
                for item in line_factura:
                    posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
                    cp = self.env['presupuesto.control_presupuesto'].search([
                    ('version', '=', documento_version),
                    ('ejercicio', '=', documento_ejercicio),
                    ('periodo', '=', fecha.month),
                    ('posicion_presupuestaria', '=', posicion_presupuestaria.id)])
                    cp_ids= cp.id if cp.id else 0
                    importe=item.price_subtotal+factura.amount_tax
                    if(item.uom_id.id==31):
                        query_put_invoice1 = "UPDATE presupuesto_control_presupuesto SET egreso_ejercido=%s WHERE id= %s;" % (cp.egreso_ejercido - importe,cp.id)
                        query_put_invoice2 = "UPDATE presupuesto_control_presupuesto SET egreso_devengado=%s WHERE id= %s;" % (cp.egreso_devengado + importe,cp.id)
                        self.env.cr.execute(query_put_invoice1)
                        self.env.cr.execute(query_put_invoice2)
                    else:
                        query_put_invoice1 = "UPDATE presupuesto_control_presupuesto SET egreso_ejercido=%s WHERE id= %s;" % (cp.egreso_ejercido - importe,cp.id)
                        query_put_invoice2 = "UPDATE presupuesto_control_presupuesto SET egreso_devengado=%s WHERE id= %s;" % (cp.egreso_devengado + importe,cp.id)
                        self.env.cr.execute(query_put_invoice1)
                        self.env.cr.execute(query_put_invoice2)
                if(documento_ejercido.clase_documento.id):
                    query1 = "DELETE FROM presupuesto_detalle_documento WHERE documento_id=%s" % (documento_ids)
                    query2 = "DELETE FROM presupuesto_documento WHERE id=%s" % (documento_ids)
                    self.env.cr.execute(query1)
                    self.env.cr.execute(query2)
                query_put = "UPDATE purchase_order SET status_account_move='DEVENGADO' WHERE id = %s;" % (purc_ids)
                query_put_invoice = "UPDATE account_invoice SET state='open' WHERE id = %s;" % (factura.id)
                query_delete = "DELETE FROM account_move WHERE id=%s" % (asiento_contable_ids)
                query_delete2 = "DELETE FROM account_move_line WHERE move_id=%s" % (asiento_contable_ids)
                self.env.cr.execute(query_delete2)
                self.env.cr.execute(query_delete)
                self.env.cr.execute(query_put)
                self.env.cr.execute(query_put_invoice)

            elif(self.tipo=='COPD'):
                purchase = self.env['purchase.order'].search([('id','=',self.compra_ids)])
                purchase_order_line = self.env['purchase.order.line'].search([('order_id','=',self.compra_ids)])
                documento=self.env['presupuesto.documento'].search([('compra_id', '=', purchase.id)],limit=1)
                asiento_contable=self.env['account.move'].search([('documento_id', '=', documento.id)],limit=1)
                stock=self.env['stock.picking'].search([('origin', '=', purchase.name)],limit=1)
                documento_id= documento.id if documento.id else 0
                asiento_contable_id= asiento_contable.id if asiento_contable.id else 0
                stick_ids= stock.id if stock.id else 0
                for item in purchase_order_line:
                    posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
                    cp = self.env['presupuesto.control_presupuesto'].search([
                    ('version', '=', documento.version.id),
                    ('ejercicio', '=', documento.ejercicio),
                    ('periodo', '=', documento.periodo),
                    ('posicion_presupuestaria', '=', posicion_presupuestaria.id)])
                    total_dev=cp.egreso_devengado - item.price_subtotal
                    total_com=cp.egreso_comprometido + item.price_subtotal
                    put_state_line= "UPDATE presupuesto_control_presupuesto SET egreso_comprometido='%s', egreso_devengado='%s' WHERE id=%s" % (total_com,total_dev,cp.id)
                    self.env.cr.execute(put_state_line)
                    put_state_line= "UPDATE purchase_order_line SET state_devengado='comprometido', check_items='True' WHERE id=%s" % (item.id)
                    self.env.cr.execute(put_state_line)
                query1 = "DELETE FROM presupuesto_detalle_documento WHERE documento_id=%s" % (documento_id)
                query2 = "DELETE FROM presupuesto_documento WHERE id=%s" % (documento_id)
                query3 = "DELETE FROM account_move_line WHERE move_id=%s" % (asiento_contable_id)
                query4 = "DELETE FROM account_move WHERE id=%s" % (asiento_contable_id)
                query5 = "DELETE FROM stock_pack_operation WHERE picking_id=%s" % (stick_ids)
                query6 = "DELETE FROM stock_move WHERE picking_id=%s" % (stick_ids)
                query7 = "DELETE FROM stock_picking WHERE id=%s" % (stick_ids)
                self.env.cr.execute(query1)
                self.env.cr.execute(query2)
                self.env.cr.execute(query3)
                self.env.cr.execute(query4)
                self.env.cr.execute(query5)
                self.env.cr.execute(query6)
                self.env.cr.execute(query7)
                put_state_line_purchase= "UPDATE purchase_order SET state='purchase', status_account_move='COMPROMETIDO' WHERE id=%s" % (self.compra_ids)
                self.env.cr.execute(put_state_line_purchase) 

            elif(self.tipo=='COPC'):
                purchase = self.env['purchase.order'].search([('id','=',self.compra_ids)])
                purchase_order_line = self.env['purchase.order.line'].search([('order_id','=',self.compra_ids)])
                documento=self.env['presupuesto.documento'].search([('compra_id', '=', self.compra_ids)],limit=1)
                asiento_contable=self.env['account.move'].search([('documento_id', '=', documento.id)],limit=1)
                stock=self.env['stock.picking'].search([('origin', '=', purchase.name)],limit=1)
                documento_id= documento.id if documento.id else 0
                asiento_contable_id= asiento_contable.id if asiento_contable.id else 0
                stick_ids= stock.id if stock.id else 0
                if(purchase.type_purchase=='compra'):
                    posicion_presupuestaria = self.partida_presupuestal_id
                    cp = self.env['presupuesto.control_presupuesto'].search([
                    ('version', '=', documento.version.id),
                    ('ejercicio', '=', documento.ejercicio),
                    ('periodo', '=', documento.periodo),
                    ('posicion_presupuestaria', '=', posicion_presupuestaria)])
                    cp.write({ 'egreso_comprometido': cp.egreso_comprometido - purchase.importe_comprometido })
                else:
                    for item in purchase_order_line:
                        posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
                        cp = self.env['presupuesto.control_presupuesto'].search([
                        ('version', '=', documento.version.id),
                        ('ejercicio', '=', documento.ejercicio),
                        ('periodo', '=', documento.periodo),
                        ('posicion_presupuestaria', '=', posicion_presupuestaria.id)])
                        res_comp=cp.egreso_comprometido - item.price_subtotal
                        if(cp.egreso_comprometido==0 or cp.egreso_comprometido<0):
                            cp.write({ 'egreso_comprometido': 0 })
                        else:
                            cp.write({ 'egreso_comprometido': res_comp })
                query1 = "DELETE FROM presupuesto_detalle_documento WHERE documento_id=%s" % (documento_id)
                query2 = "DELETE FROM presupuesto_documento WHERE id=%s" % (documento_id)
                query3 = "DELETE FROM account_move_line WHERE move_id=%s" % (asiento_contable_id)
                query4 = "DELETE FROM account_move WHERE id=%s" % (asiento_contable_id)
                query5 = "DELETE FROM stock_pack_operation WHERE picking_id=%s" % (stick_ids)
                query6 = "DELETE FROM stock_move WHERE picking_id=%s" % (stick_ids)
                query7 = "DELETE FROM stock_picking WHERE id=%s" % (stick_ids)
                self.env.cr.execute(query1)
                self.env.cr.execute(query2)
                self.env.cr.execute(query3)
                self.env.cr.execute(query4)
                self.env.cr.execute(query5)
                self.env.cr.execute(query6)
                self.env.cr.execute(query7)
                put_state_line_purchase= "UPDATE purchase_order SET state='sent', status_account_move='ORIGINAL' WHERE id=%s" % (self.compra_ids)
                self.env.cr.execute(put_state_line_purchase) 





