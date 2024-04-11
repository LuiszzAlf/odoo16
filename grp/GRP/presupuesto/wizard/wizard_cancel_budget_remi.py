# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class cancel_budget_remi(models.TransientModel):
    _name = 'cancel_budget_remi.wizard'

    @api.model
    def _get_documentos(self):
        listids=[]
        doc_ids=[]
        context = dict(self._context or {})
        requi_id = context.get('requi_id', False)
        momento = context.get('momento', False)
        compromisos = self.env['presupuesto.requisicion.compras.compromisos.line'].search([('id','=',requi_id)])
        # devengados = self.env['tjacdmx.devengados.line'].search([('requisicion_compra','=',requi_id)])
        for each in compromisos:
            listids.append(each.id)
        remisiones_req=self.env['tjacdmx.remisiones'].search([('origin','in', listids)])
        if(momento=='pagado'):
            for i in remisiones_req.documentos:
                if(i.id and i.clase_documento.id==8):
                    doc_ids.append(i.id)
        if(momento=='ejercido'):
            for i in remisiones_req.documentos:
                if(i.id and i.clase_documento.id==9):
                    doc_ids.append(i.id)
        # for i in compromisos:
        #     if(i.documento.id):
        #         doc_ids.append(i.documento.id)
        # for i in devengados:
        #     if(i.documento.id):
        #         doc_ids.append(i.documento.id)

        
        #raise ValidationError("debug: %s"  % (doc_ids))
        if doc_ids:
            data = doc_ids
            return data
        return ''
    @api.model
    def _get_momento(self):
        context = dict(self._context or {})
        momento = context.get('momento', False)
        if momento:
            data = momento
            return data
        return ''

    @api.model
    def _get_remi(self):
        context = dict(self._context or {})
        remision = context.get('remision', False)
        if remision:
            data = remision
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
    
    requi_ids=fields.Integer(default=_get_remi,readonly=True)
    invoice_id=fields.Integer(default=_get_factura,readonly=True)
    tipo=fields.Char(string='Clave', default=_get_momento, readonly=True)

    momento_documento=fields.Many2one('presupuesto.documento',string='Documento')
    momento_contable=fields.Many2one('account.move',string='Momento contable')

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
    @api.onchange('requi_ids')
    def _onchange_periodo(self):
        if self.requi_ids:
            return {'domain': {'momento_documento': [('id', 'in', self._get_documentos())]}}

    @api.multi
    @api.onchange('momento_documento')
    def _onchange_asiento(self):
        documento = self.momento_documento
        self.momento_contable=documento.move_id.id
        documento_detalle = self.momento_documento.detalle_documento_ids
        asiento_c = self.env['account.move'].search([('id','=',documento.move_id.id)],limit=1)
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
        if(not ctrl_periodo.get_is_cerrado(self.momento_documento.fecha_documento)):
            if(self.tipo=='pagado'):
                self.momento_documento.button_state_off()
                self.momento_documento.unlink()
                query_put = "update tjacdmx_remisiones set state ='ejercido' where invoice_id=%s and tipo_remision in ('completa','final_parcial'); " % (self.invoice_id)
                self.env.cr.execute(query_put)
                query_put_state_invoice = "UPDATE account_invoice SET state='paid' WHERE id = %s;" % (self.invoice_id)
                self.env.cr.execute(query_put_state_invoice)
            elif(self.tipo=='ejercido'):
                self.momento_documento.button_state_off()
                self.momento_documento.unlink()
                query_put = "update tjacdmx_remisiones set state ='open' where invoice_id=%s and tipo_remision in ('completa','final_parcial'); " % (self.invoice_id)
                self.env.cr.execute(query_put)
                query_put_state_invoice = "UPDATE account_invoice SET state='open' WHERE id = %s;" % (self.invoice_id)
                self.env.cr.execute(query_put_state_invoice)
            elif(self.tipo=='COPD'):
                purchase = self.env['purchase.order'].search([('id','=',self.requi_ids)])
                purchase_order_line = self.env['purchase.order.line'].search([('order_id','=',self.requi_ids)])
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
                put_state_line_purchase= "UPDATE purchase_order SET state='purchase', status_account_move='COMPROMETIDO' WHERE id=%s" % (self.requi_ids)
                self.env.cr.execute(put_state_line_purchase) 

            elif(self.tipo=='COPC'):
                purchase = self.env['purchase.order'].search([('id','=',self.requi_ids)])
                purchase_order_line = self.env['purchase.order.line'].search([('order_id','=',self.requi_ids)])
                documento=self.env['presupuesto.documento'].search([('compra_id', '=', self.requi_ids)],limit=1)
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
                put_state_line_purchase= "UPDATE purchase_order SET state='draft', status_account_move='ORIGINAL' WHERE id=%s" % (self.requi_ids)
                self.env.cr.execute(put_state_line_purchase) 





