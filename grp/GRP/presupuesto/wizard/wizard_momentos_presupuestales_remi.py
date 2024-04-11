# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from num2words import num2words
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

def check_exist_doc(lista, doc):
    exist = -1
    for idx, item in enumerate(lista):
        if item['clase_documento'] == doc['clase_documento'] and \
            item['version'] == doc['version'] and \
            item['ejercicio'] == doc['ejercicio'] and \
            item['periodo'] == doc['periodo']:
            exist = idx
            break
    return exist
def _check_exist_doc(lista, doc):
    exist = -1
    for idx, item in enumerate(lista):
        if item['clase_documento'] == doc['clase_documento'] and \
            item['version'] == doc['version'] and \
            item['ejercicio'] == doc['ejercicio'] and \
            item['periodo'] == doc['periodo']:
            exist = idx
            break
    return exist
def calcular_precio_total(subtotal, impuestos, presupuestal=True):
    suma_imp = 0
    for imp in impuestos:
        amount = (imp.amount, 0)[presupuestal]
        if imp.amount > 0:
            amount = imp.amount
        suma_imp = suma_imp + (subtotal*amount/100)
    # raise ValidationError("Debug: %s" % (tot))
    return round(suma_imp + subtotal, 2)
def calcular_precio_total2(subtotal, impuestos,presupuestal=True):
    if(subtotal>0):
        subtotal=subtotal
    else:
        subtotal=0

    suma_imp = 0
    for imp in impuestos:
        amount = (imp.amount, 0)[presupuestal]
        if imp.amount > 0:
            amount = imp.amount
        suma_imp = suma_imp + (subtotal*amount/100)
    # raise ValidationError("Debug: %s" % (tot))
    return round(suma_imp + subtotal, 2)

class momentos_presupuestales(models.TransientModel):
    _name = 'momentos_presupuestales_remi.wizard'

    @api.model
    def _get_remision(self):
        context = dict(self._context or {})
        remision = context.get('remision', False)
        if remision:
            data = remision
            return data
        return ''
    @api.model
    def _get_factura(self):
        context = dict(self._context or {})
        factura = context.get('factura', False)
        if factura:
            data = factura
            return data
        return ''
    @api.model
    def _get_fecha(self):
        context = dict(self._context or {})
        fecha = context.get('fecha', False)
        if fecha:
            data = fecha
            return data
        return ''
    @api.model
    def _get_provision(self):
        context = dict(self._context or {})
        provision = context.get('provision', False)
        if provision:
            data = provision
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
    def _get_is_devengado(self):
        context = dict(self._context or {})
        is_devengado = context.get('is_devengado', False)
        if is_devengado:
            data = is_devengado
            return data
        return False

        
    
    fecha=fields.Date(required=True,default=_get_fecha)
    remision_ids=fields.Integer(default=_get_remision,readonly=True)
    factura_ids=fields.Integer(default=_get_factura,readonly=True)
    momento=fields.Char(default=_get_momento,readonly=True)
    provision=fields.Boolean(default=_get_provision,readonly=True)
    is_devengado=fields.Boolean(default=_get_is_devengado,readonly=True)


    @api.multi
    def validate_pres_devengado(self):
        remision=self.env['tjacdmx.remisiones']
        remision_origin=remision.search([('id','=', self.remision_ids)])
        factura_model=self.env['account.invoice']
        #raise ValidationError("debug: %s"%(remision_origin))
        fecha = remision_origin.date_remision
        devengado=self.env['tjacdmx.devengados.line']
        detalle_dev={
                        'name': remision_origin.number,
                        'fecha': self.fecha,
                        'periodo': fecha.month,
                        'importe_origen': remision_origin.amount_total,
                        'importe': remision_origin.amount_total,
                        'state': 'send',
                        'area':remision_origin.origin.area,
                        'requisicion_compra':remision_origin.origin.requisicion_compra.id,
                        'partida':remision_origin.origin.requisicion_compra.partida.partida_presupuestal,
                    }
        if(remision_origin.sequence==1 or remision_origin.tipo_remision=='completa'):
            lines_factura=[]
            for it in  remision_origin.remision_line_ids:
                remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', it['id'])])
                lines_factura.append((0,0, {
                        'name': remision_line.name,
                        'sequence': remision_line.sequence,
                        'account_id': remision_line.account_id.id,
                        'price_unit': remision_line.price_unit,
                        'quantity': remision_line.product_qty,
                        'product_id': remision_line.product_id.id,
                        'line_remision_id': remision_line.id,
                        'uom_id': remision_line.product_uom.id,
                        'partner_id': remision_origin.partner_id.id,
                        'tax_line_ids': remision_line.taxes_id
                    }))
            factura_model_create=factura_model.create({
                        'partner_id': remision_origin.partner_id.id,
                        'origin': remision_origin.origin.name,
                        'remision': remision_origin.id,
                        'date_due': remision_origin.date_remision,
                        'date_invoice': remision_origin.date_remision,
                        'reference_provedor': remision_origin.no_factura,
                        'account_id': remision_origin.account_id.id,
                        'state': 'draft',
                        'stateinvoice': 'true',
                        'type':'in_invoice',
                        'journal_id':2,
                        'invoice_line_ids':lines_factura,
                        'requicision': remision_origin.origin.id,
                    })
             
            if(factura_model_create):
                for line_fac in factura_model_create.invoice_line_ids:
                    remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', line_fac.line_remision_id)])
                    for tax in remision_line.taxes_id:
                        query = "INSERT INTO account_invoice_line_tax values(%s,%s)" % (line_fac.id,tax.id)
                        self.env.cr.execute(query)
                taxes=self.env['account.invoice.tax']
                for line_fac in factura_model_create.invoice_line_ids:
                    remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', line_fac.line_remision_id)])
                    for tax in remision_line.taxes_id:
                        if(tax.amount<0):
                            pors='-0.%s'%(int(tax.amount)*-1)
                        else:
                            pors='0.%s'%(int(tax.amount))
                        total=line_fac.price_unit*float(pors)
                        vals = {
                            'invoice_id': factura_model_create.id,
                            'name': tax.name,
                            'tax_id': tax.id,
                            'amount': total,
                            'manual': False,
                            'sequence': 1,
                            'account_analytic_id': remision_line.account_analytic_id.id,
                            'account_id': tax.account_id.id
                        }
                        taxes_create=taxes.create(vals)
                if(self.is_devengado==False):
                    devengado_created=devengado.create(detalle_dev)
                    
                    
                remision_origin.write({'invoice_id': factura_model_create.id})
                remision_origin.write({'state': 'draft_pre'})
                if(remision_origin.tipo_remision=='completa'):
                    factura_model_create.write({'state': 'draft_pre'})
                elif(remision_origin.tipo_remision=='parcial'):
                    factura_model_create.write({'state': 'draft'})
                
        else:
            remision_origen=self.env['tjacdmx.remisiones'].search([('origin','=', remision_origin.origin.id),('sequence','=',1)])
            factura=self.env['account.invoice'].search([('id','=', remision_origen.invoice_id.id)])
            if(factura):
                if(remision_origin.tipo_remision=='parcial' and factura.state=='draft' or remision_origin.tipo_remision=='final_parcial'):
                    factura_lines_model=self.env['account.invoice.line']
                    lines_factura=[]
                    for it in  remision_origin.remision_line_ids:
                        order_line=self.env['tjacdmx.remisiones.line'].search([('id','=', it['id'])])
                        factura_model_create=factura_lines_model.create({
                                    'invoice_id': factura.id,
                                    'name': order_line.name,
                                    'sequence': order_line.sequence,
                                    'account_id': order_line.account_id.id,
                                    'price_unit': order_line.price_unit,
                                    'quantity': order_line.product_qty,
                                    'product_id': order_line.product_id.id,
                                    'line_remision_id': order_line.remision_id,
                                    'uom_id': order_line.product_uom.id,
                                    'partner_id': remision_origin.partner_id.id,
                                    'invoice_line_tax_ids': order_line.taxes_id
                                })
                    if(remision_origin.tipo_remision=='final_parcial'):
                        remision_related=self.env['tjacdmx.remisiones'].search([('origin','=', remision_origin.origin.id),('invoice_id','=',factura.id)])
                        if(self.is_devengado==False):
                            devengado_created=devengado.create(detalle_dev)
                            
                        remision_origin.write({'invoice_id': factura.id})
                        remision_origin.write({'state': 'draft_pre'})
                        remision_related.write({'state': 'draft_pre'})
                        factura.write({'state': 'draft_pre'})
                    elif(remision_origin.tipo_remision=='completa'):
                        remision_origin.write({'state': 'draft_pre'})
                        factura.write({'state': 'draft_pre'})
                    elif(remision_origin.tipo_remision=='parcial'):
                        remision_origin.write({'state': 'draft_pre'})
                        factura.write({'state': 'draft'})
                else:
                    raise ValidationError("La factura seleccionado para esta entrega ya esta en proceso, favor de verificar la información.")
            else:
                raise ValidationError("Aun no se ha validado la primera entrega, favor de revisar e internar de nuevo")
    @api.multi
    def print_clc_win(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('ejercido','=','open')])
        remision_precess = self.env['tjacdmx.remisiones'].search([('id','=',self.remision_ids)],limit=1)
        if(remision_precess):
            if(remision_precess.state == 'devengado' or remision_precess.state == 'lista_devengado'):
                search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.factura_ids)], limit=1)
                ctrl_periodo = self.env['control.periodos.wizard']
                if(self.provision==True):
                    fecha_ctrl = datetime.strptime(self.fecha, '%Y-%m-%d') if self.fecha else datetime.today()
                else:
                    fecha_ctrl = datetime.strptime(search_clc_active.fecha_expedicion, '%Y-%m-%d') if search_clc_active.fecha_expedicion else datetime.today()
                if(not ctrl_periodo.get_is_cerrado(fecha_ctrl)
                and permisos):
                    datas = {}
                    search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.factura_ids)], limit=1)
                    if (search_clc_active):
                        fecha_origen = datetime.strptime(remision_precess.date_remision, '%Y-%m-%d') if remision_precess.date_remision else datetime.today()
                        obj_date_remision = self.env['tjacdmx.remisiones'].search([('id','=',self.remision_ids)], limit=1)
                        lines_factura = self.env['account.invoice.line'].search([('invoice_id','=',self.factura_ids)])
                        factura_set = self.env['account.invoice'].search([('id','=',self.factura_ids)])
                        documentos = []
                        obj_documento = self.env['presupuesto.documento']
                        version = self.env['presupuesto.version'].search([], limit=1)
                        cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','EJERCIDO')], limit=1)
                        if(self.provision==True):
                            fecha = datetime.strptime(self.fecha, '%Y-%m-%d') if self.fecha else datetime.today()
                        else:
                            fecha = datetime.strptime(search_clc_active.fecha_expedicion, '%Y-%m-%d') if search_clc_active.fecha_expedicion else datetime.today()
                        if(remision_precess.origin):
                            fecha_origen = datetime.strptime(remision_precess.origin.fecha, '%Y-%m-%d')
                        # raise ValidationError("%s  ----%s" % (fecha_origen,fecha))
                        for invoice_item in lines_factura:
                            producto = invoice_item.product_id
                            name_purchase=remision_precess.number
                            concepto="""%s/Ejercido""" % (name_purchase)
                            documento = {
                                'clase_documento': cls_doc.id,
                                'version': version.id,
                                'ejercicio': fecha.year,
                                'periodo': fecha.month,
                                'fecha_contabilizacion': fecha.strftime("%Y-%m-%d"),
                                'fecha_documento': fecha.strftime("%Y-%m-%d"),
                                'periodo_origen': fecha_origen.month,
                                'detalle_documento_ids': [],
                                'referencia_factura': self.factura_ids,
                                'concepto': str(concepto),
                                'remision_id': obj_date_remision.id
                            }
                            detalle_doc = [0, False,
                                {
                                    'centro_gestor': factura_set.centro_gestor.id,
                                    'area_funcional': factura_set.area_funcional.id,
                                    'fondo_economico': factura_set.fondo_economico.id,
                                    'posicion_presupuestaria': producto.posicion_presupuestaria.id,
                                    'importe': calcular_precio_total2(invoice_item.price_subtotal, invoice_item.invoice_line_tax_ids),
                                    'momento_contable': 'EJERCIDO'
                                }
                            ]
                            doc_idx = check_exist_doc(documentos, documento)
                            if doc_idx > -1:
                                documentos[doc_idx]['detalle_documento_ids'].append(detalle_doc)
                            else:
                                documento['detalle_documento_ids'].append(detalle_doc)
                                documentos.append(documento)
                        for doc in documentos:
                            obj_documento.create(doc)
                        factura_set.write({'state': "clc"})
                    else:
                        raise ValidationError("No se genero CLC para esta factura")
                else:
                    raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
                
            else:
                raise ValidationError("La remisión origen aun no se encuentra devengada.")
        else:
            pass 

    @api.multi
    def pago_compra_win(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('pagado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        remision_precess = self.env['tjacdmx.remisiones'].search([('id','=',self.remision_ids)],limit=1)
        if(not ctrl_periodo.get_is_cerrado(self.fecha)and permisos):
            lines_factura = self.env['account.invoice.line'].search([('invoice_id','=',self.factura_ids)])
            factura_set = self.env['account.invoice'].search([('id','=',self.factura_ids)])
            obj_documento = self.env['presupuesto.documento']
            factura = lines_factura
            obj_date_remision = self.env['tjacdmx.remisiones'].search([('id','=',self.remision_ids)], limit=1)
            date_pay=obj_date_remision.date_remision
            documentos = []
            amount = 0
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','PAGADO')], limit=1)
            fecha = datetime.strptime(self.fecha, '%Y-%m-%d') if self.fecha else datetime.today()
            fecha_origen = datetime.strptime(date_pay, '%Y-%m-%d') if date_pay else datetime.today()
            if(remision_precess.origin):
                fecha_origen = datetime.strptime(remision_precess.origin.fecha, '%Y-%m-%d')
            for invoice_item in factura:
                producto = invoice_item.product_id
                importe_presupuestal = calcular_precio_total2(invoice_item.price_subtotal, invoice_item.invoice_line_tax_ids)
                importe_pagar = calcular_precio_total2(invoice_item.price_subtotal, invoice_item.invoice_line_tax_ids, False)
                name_purchase=remision_precess.origin.name
                concepto="""%s/Pagado""" % (name_purchase)
                documento = {
                    'clase_documento': cls_doc.id,
                    'version': version.id,
                    'ejercicio': fecha.year,
                    'periodo': fecha.month,
                    'periodo_origen': fecha_origen.month,
                    'fecha_contabilizacion': fecha.strftime('%Y-%m-%d'),
                    'fecha_documento': fecha.strftime('%Y-%m-%d'),
                    'detalle_documento_ids': [],
                    'concepto': str(concepto),
                    'remision_id': obj_date_remision.id
                }
                detalle_doc = [0, False,
                    {
                        'centro_gestor': factura_set.centro_gestor.id,
                        'area_funcional': factura_set.area_funcional.id,
                        'fondo_economico': factura_set.fondo_economico.id,
                        'posicion_presupuestaria': producto.posicion_presupuestaria.id,
                        'importe': importe_presupuestal,
                        'momento_contable': 'PAGADO'
                    }
                ]
                doc_idx = check_exist_doc(documentos, documento)
                if doc_idx > -1:
                    documentos[doc_idx]['detalle_documento_ids'].append(detalle_doc)
                else:
                    documento['detalle_documento_ids'].append(detalle_doc)
                    documentos.append(documento)   
                amount += importe_pagar
            tot=factura_set.amount_total
            for doc in documentos:
                obj_documento.create(doc)
            sale_search = self.env['tjacdmx.remisiones'].search([('id','=',self.remision_ids)], limit=1)
            sale_search.write({'state': "pagado"})
            factura_set.write({'state': "paid_all"})
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")