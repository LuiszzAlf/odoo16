# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class cancelacion_ajuste(models.TransientModel):
    _name = 'cancelacion_ajuste.wizard'

    @api.model
    def _get_tipo(self):
        context = dict(self._context or {})
        momento_con = context.get('tipo', False)
        if momento_con:
            data = momento_con
            return data
        return ''

    @api.model
    def _get_tipo_compra(self):
        context = dict(self._context or {})
        tipo_compra = context.get('tipo_compra', False)
        if tipo_compra:
            data = tipo_compra
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
    def _get_ref(self):
        context = dict(self._context or {})
        compra_id = context.get('compra_id', False)
        compra = self.env['purchase.order'].search([('id',"=",compra_id)])
        if (compra.type_purchase == 'compra' and compra.compromiso):
            data = compra.compromiso.name
            return data
        return ''
    
    @api.model
    def _get_documentos_ids(self):
        context = dict(self._context or {})
        documentos_ids = context.get('documentos_ids', False)
        if documentos_ids:
            data = documentos_ids
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
    documentos_ids=fields.Integer(default=_get_documentos_ids,readonly=True)
    ref_compra=fields.Char(default=_get_ref, readonly=True)
    invoice_id=fields.Integer(default=_get_factura,readonly=True)
    tipo=fields.Char(string='Clave', default=_get_tipo, readonly=True)
    tipo_compra=fields.Char(string='tipo compra', default=_get_tipo_compra, readonly=True)
      
    momento_documento=fields.Many2one('presupuesto.documento',string='Documento', domain="['|',('compra_id','=', compra_ids),('id','=',documentos_ids)]")
    momento_contable=fields.Many2one('account.move',string='Momento contable', domain="[('compra_id','=', compra_ids)]")
    
   

    ejercicio=fields.Char(string='Ejercicio', readonly=True)
    periodo=fields.Char(string='Periodo', readonly=True)
    fecha_documento=fields.Char(string='Fecha', readonly=True)
    partida_presupuestal=fields.Char(string='Partida', readonly=True)   
    partida_pf=fields.Many2one('presupuesto.partida_presupuestal', string='Partida presupuestaria', required=True) 
    str_momento=fields.Char(string='Tipo', readonly=True)
    amount_total=fields.Float(string='Monto',readonly=True)
    diario=fields.Char(string='Diario',readonly=True)
    fecha_contable=fields.Char(string='Fecha contable',readonly=True)
    fecha_ajuste=fields.Date(string='Fecha')
    monto_cancel=fields.Float(string='Importe')
    tipo_ajuste=fields.Selection([('cancel',u'Cancelación'),('ajust','Ajuste')],sting='Tipo')
    html_apuntes_contables=fields.Html(string='Apuntes contables',readonly=True)

    
    @api.onchange('partida_pf')
    def onchange_partidas_doc(self):
        documento_detalle_partida = self.env['presupuesto.detalle_documento'].search([('documento_id','=',self.momento_documento.id),('posicion_presupuestaria','=',self.partida_pf.id)])
        asiento_c = self.env['account.move'].search([('documento_id','=',self.momento_documento.id)],limit=1)
        asiento_c_det = self.env['account.move.line'].search([('move_id','=',asiento_c.id)])
        asiento = self.env['account.move'].search([('id','=',self.momento_contable.id)],limit=1)
        saldo_partida=0
        for saldos in documento_detalle_partida:
            saldo_partida=saldo_partida+saldos.importe
        self.update({
            'monto_cancel': saldo_partida
            })
    
    @api.onchange('momento_documento')
    def _onchange_documento(self):
        documento_detalle = self.env['presupuesto.detalle_documento'].search([('documento_id','=',self.momento_documento.id)],limit=1)
        documento_detalle_partida = self.env['presupuesto.detalle_documento'].search([('documento_id','=',self.momento_documento.id),('posicion_presupuestaria','=',self.partida_pf.id)])
        asiento_c = self.env['account.move'].search([('documento_id','=',self.momento_documento.id)],limit=1)
        asiento_c_det = self.env['account.move.line'].search([('move_id','=',asiento_c.id)])
        asiento = self.env['account.move'].search([('id','=',self.momento_contable.id)],limit=1)
        saldo_partida=0
        for saldos in documento_detalle_partida:
            saldo_partida=saldo_partida+saldos.importe
        if(self.tipo_compra=='fondo'):
            dif=saldo_partida
        else:
            dif=asiento.amount-self.amount_total
        html_items=""
        for items in asiento_c_det:
            code=str(items.account_id.code)
            debe=str(items.debit)
            haber=str(items.credit)
            html_items2="<tr><td><p>"+code+"</p></td> <td><p>"+debe+"</p></td><td><p>"+haber+"</p></td></tr>"
            html_items+=html_items2.encode('ascii', 'ignore')
        html=""""""
        if(self.momento_documento):
            html="""<table class="table table-striped">
                    <tr><td>Cuenta</td><td>Debe</td><td>Haber</td></tr>
                    %s
                </table>""" % (html_items)
        
        self.update({
            'ejercicio': self.momento_documento.ejercicio,
            'periodo': self.momento_documento.periodo,
            'fecha_documento': self.momento_documento.fecha_documento,
            'partida_presupuestal': documento_detalle.posicion_presupuestaria.partida_presupuestal,
            'partida_pf': documento_detalle.posicion_presupuestaria.id,
            'str_momento': documento_detalle.momento_contable,
            'amount_total': documento_detalle.importe,
            'diario': asiento_c.journal_id.name,
            'fecha_contable': asiento_c.date,
            'monto_cancel': dif,
            'html_apuntes_contables': html,
            })

    @api.multi
    @api.onchange('momento_documento')
    def _onchange_documento_partidas(self):
        documento_detalle = self.env['presupuesto.detalle_documento'].search([('documento_id','=',self.momento_documento.id)])
        partidas=[]
        for it in documento_detalle:
            partidas.append(it.posicion_presupuestaria.id)
        if self.momento_documento:
            return {'domain': {'partida_pf': [('id', 'in', partidas)]}}

    @api.multi
    def cancela_ajuste_fuction(self):
        ctrl_periodo = self.env['control.periodos.wizard']
        if(not ctrl_periodo.get_is_cerrado(self.fecha_ajuste)):
            documentos = []
            purchase = self.env['purchase.order'].search([('id','=',self.compra_ids)], limit=1)
            obj_documento = self.env['presupuesto.documento']
            if (self.tipo_ajuste=='cancel'):
                cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','CANCELACION')], limit=1)
            elif (self.tipo_ajuste=='ajust'):
                cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','AJUSTE')], limit=1)
            fecha = datetime.strptime(self.fecha_ajuste, '%Y-%m-%d') if self.fecha_ajuste else datetime.today()
            fecha_origen = datetime.strptime(purchase.date_order , '%Y-%m-%d %H:%M:%S') if purchase.date_order else datetime.today()
            if(purchase.referencia_compra 
                and purchase.type_purchase == 'compra' 
                and purchase.importe_comprometido == 0):
                fecha_origen = datetime.strptime(purchase.referencia_compra.date_order, '%Y-%m-%d %H:%M:%S')
            documento = self.momento_documento
            if(self.tipo_ajuste=='cancel'):
                importe_doc=float(self.monto_cancel)*-1
            else:
                importe_doc=float(self.monto_cancel)
            if(self.tipo_compra=='fondo'):
                partida_doc_cancel=self.partida_pf.id
            else:
                partida_doc_cancel=documento.detalle_documento_ids[0].posicion_presupuestaria.id
            control_destino = self.env['presupuesto.control_presupuesto'].search([
                ('version', '=', documento.version.id),
                ('ejercicio', '=', fecha.year),
                ('periodo', '=', fecha.month),
                ('posicion_presupuestaria', '=', partida_doc_cancel)])
            documentos_originales = []
            detalle_doc = [0, False,
                {
                'centro_gestor': documento.detalle_documento_ids[0].centro_gestor.id,
                'area_funcional': documento.detalle_documento_ids[0].area_funcional.id,
                'fondo_economico': documento.detalle_documento_ids[0].fondo_economico.id,
                'posicion_presupuestaria': partida_doc_cancel,
                'importe': importe_doc,
                'importe_val':importe_doc,
                'control_presupuesto_id': control_destino.id
                }]
            documentos_originales.append(detalle_doc)
            if(self.tipo_ajuste=='cancel'):
                concepto_t='Cancelacion'
            else:
                concepto_t='Ajuste'
            if(purchase.type_purchase=='compra'):
                name_purchase=purchase.compromiso.name
            else:
                name_purchase=purchase.folio
            concepto="""%s/%s""" % (name_purchase,concepto_t)
            documento_create = obj_documento.create({
                'clase_documento': documento.clase_documento.id,
                'clase_documento_ajuste': cls_doc.id,
                'version': documento.version.id,
                'ejercicio': fecha.year,
                'periodo': fecha.month,
                'periodo_origen': fecha_origen.month,
                'fecha_contabilizacion': fecha.strftime("%Y-%m-%d"),
                'fecha_documento': fecha.strftime("%Y-%m-%d"),
                'detalle_documento_ids': documentos_originales,
                'compra_id': self.compra_ids,
                'tipo':  documento.clase_documento.tipo_documento,
                'account_move_id': self.momento_contable.id,
                'concepto': str(concepto),
            },tipo=self.tipo_ajuste)
            if(self.ref_compra 
            and documento_create.clase_documento.tipo_documento == 'COMPROMETIDO'):
                compra = self.env['purchase.order'].search([('id',"=",self.compra_ids)])
                if (compra.type_purchase == 'compra' and compra.compromiso):
                    asiento_contable=self.env['account.move'].search([('documento_id', '=', documento_create.id)],limit=1)
                    asiento_contable.write({
                        'ref':self.ref_compra
                    })

 



