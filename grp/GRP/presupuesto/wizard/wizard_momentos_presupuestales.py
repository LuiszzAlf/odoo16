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
def calcular_precio_total(subtotal, impuestos,tipo_contrato,presupuestal=True):
    if(tipo_contrato==2):
        if(subtotal>0):
            subtotal=subtotal
        else:
            subtotal=0
    else:
        if(subtotal>0):
            subtotal=subtotal
        else:
            subtotal=subtotal*-1
    suma_imp = 0
    for imp in impuestos:
        amount = (imp.amount, 0)[presupuestal]
        if imp.amount > 0:
            amount = imp.amount
        suma_imp = suma_imp + (subtotal*amount/100)
    # raise ValidationError("Debug: %s" % (tot))
    return round(suma_imp + subtotal, 2)

class momentos_presupuestales(models.TransientModel):
    _name = 'momentos_presupuestales.wizard'

    @api.model
    def _get_compra(self):
        context = dict(self._context or {})
        compra = context.get('compra', False)
        if compra:
            data = compra
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
    def _get_tipo_contrato(self):
        context = dict(self._context or {})
        tipo_contrato = context.get('tipo_contrato', False)
        if tipo_contrato:
            data = tipo_contrato
            return data
        return ''
    
    fecha=fields.Date(required=True,default=_get_fecha)
    compra_ids=fields.Integer(default=_get_compra,readonly=True)
    factura_ids=fields.Integer(default=_get_factura,readonly=True)
    momento=fields.Char(default=_get_momento,readonly=True)
    provision=fields.Boolean(default=_get_provision,readonly=True)
    tipo_contrato=fields.Integer(default=_get_tipo_contrato,readonly=True)


    @api.multi
    def do_new_transfer_dev_wiz(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        compra_precess = self.env['purchase.order'].search([('id','=',self.compra_ids)],limit=1)
        ctrl_periodo = self.env['control.periodos.wizard']    
        if(not ctrl_periodo.get_is_cerrado(self.fecha)
            and permisos):
            documentos = []
            obj_documento = self.env['presupuesto.documento']
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','DEVENGADO')], limit=1)
            fecha_origen = datetime.strptime(compra_precess.date_order, '%Y-%m-%d %H:%M:%S') if compra_precess.date_order else datetime.today()
            if(compra_precess.compromiso 
                and compra_precess.type_purchase == 'compra'):
                fecha_origen = datetime.strptime(compra_precess.compromiso.fecha, '%Y-%m-%d')
            fecha = datetime.strptime(self.fecha, '%Y-%m-%d') if self.fecha else datetime.today()
            purchase_order = compra_precess
            items = self.env['purchase.order.line'].search([('order_id', '=', purchase_order.id),('check_items', '=', True)])
            items_deven = self.env['purchase.order.line'].search([('order_id', '=', purchase_order.id),('state_devengado', '=', 'devengado')])
            items_validate = self.env['purchase.order.line'].search([('order_id', '=', purchase_order.id)])
            items_deve_con = self.env['account.move'].search([('compra_id', '=', purchase_order.id), ('journal_id','=',70)])
            rowo=len(items)
            rowv=len(items_validate)
            rowas=len(items_deve_con)
            rowdeven=len(items_deven)
            if(rowo==rowdeven):
                put_states_purchase="UPDATE purchase_order SET status_account_move='DEVENGADO' WHERE id=%s" % (compra_precess.id)
                self.env.cr.execute(put_states_purchase)
            if(rowo==rowv or rowas>=rowv):
                put_states_purchase="UPDATE purchase_order SET status_account_move='DEVENGADO' WHERE id=%s" % (compra_precess.id)
                self.env.cr.execute(put_states_purchase)
            if (rowas>=rowv):
                put_states_purchase="UPDATE purchase_order SET status_account_move='DEVENGADO' WHERE id=%s" % (compra_precess.id)
                self.env.cr.execute(put_states_purchase)
            else:
                if(rowo<=0):
                    raise ValidationError("No se han seleccionado productos o servicios para recibir.")
                elif(rowdeven>=rowv):
                    raise ValidationError("No hay registros para devengar.")
                else:
                    for item in items:
                        put_states="UPDATE purchase_order_line SET state_devengado='devengado',check_items='False' WHERE id=%s" % (item.id)
                        self.env.cr.execute(put_states)
                        posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
                        if(compra_precess.type_purchase=='compra'):
                            name_purchase=compra_precess.compromiso.name
                        else:
                            name_purchase=compra_precess.folio
                        concepto="""%s/Devengado""" % (name_purchase)
                        documento={'clase_documento': cls_doc.id,'version': version.id,
                                    'ejercicio': fecha.year,'periodo': fecha.month,'periodo_origen': fecha_origen.month,
                                    'fecha_contabilizacion': fecha.strftime("%Y-%m-%d"),'fecha_documento': fecha.strftime("%Y-%m-%d"),
                                    'detalle_documento_ids': [],'compra_id': purchase_order.id,'concepto': str(concepto)}
                        detalle_doc = [0, False,{
                            'centro_gestor': purchase_order.centro_gestor.id,'area_funcional': purchase_order.area_funcional.id,
                            'fondo_economico': purchase_order.fondo_economico.id,'posicion_presupuestaria': posicion_presupuestaria.id,
                            'importe': item.price_total,'momento_contable': 'DEVENGADO','periodo_origen': fecha_origen.month }]
                        doc_idx = _check_exist_doc(documentos, documento)
                        if doc_idx > -1:
                            documentos[doc_idx]['detalle_documento_ids'].append(detalle_doc)
                        else:
                            documento['detalle_documento_ids'].append(detalle_doc)
                            documentos.append(documento)
                    for doc in documentos:
                        obj_documento.create(doc)
                        asientos=rowas+1
                        if(asientos==rowv):
                            put_states_dev="UPDATE purchase_order SET status_account_move='DEVENGADO' WHERE id=%s" % (compra_precess.id)
                            self.env.cr.execute(put_states_dev)
                            compra_precess.write({'status_account_move': "DEVENGADO"})
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")




    @api.multi
    def print_clc_win(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('ejercido','=','open')])
        compra_precess = self.env['purchase.order'].search([('id','=',self.compra_ids)],limit=1)
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
                fecha_origen = datetime.strptime(compra_precess.date_order, '%Y-%m-%d %H:%M:%S') if compra_precess.date_order else datetime.today()
                obj_date_purchase = self.env['purchase.order'].search([('id','=',self.compra_ids)], limit=1)
                lines_factura = self.env['account.invoice.line'].search([('invoice_id','=',self.factura_ids)])
                factura_set = self.env['account.invoice'].search([('id','=',self.factura_ids)])
                date_pay=obj_date_purchase.compromiso.fecha
                documentos = []
                obj_documento = self.env['presupuesto.documento']
                version = self.env['presupuesto.version'].search([], limit=1)
                cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','EJERCIDO')], limit=1)
                if(self.provision==True):
                    fecha = datetime.strptime(self.fecha, '%Y-%m-%d') if self.fecha else datetime.today()
                else:
                    fecha = datetime.strptime(search_clc_active.fecha_expedicion, '%Y-%m-%d') if search_clc_active.fecha_expedicion else datetime.today()
                if(compra_precess.compromiso and compra_precess.type_purchase == 'compra'):
                    fecha_origen = datetime.strptime(compra_precess.compromiso.fecha, '%Y-%m-%d')
                # raise ValidationError("%s  ----%s" % (fecha_origen,fecha))
                for invoice_item in lines_factura:
                    producto = invoice_item.product_id
                    if(compra_precess.type_purchase=='compra'):
                        name_purchase=compra_precess.compromiso.name
                    else:
                        name_purchase=compra_precess.folio
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
                        'compra_id': obj_date_purchase.id
                    }
                    detalle_doc = [0, False,
                        {
                            'centro_gestor': factura_set.centro_gestor.id,
                            'area_funcional': factura_set.area_funcional.id,
                            'fondo_economico': factura_set.fondo_economico.id,
                            'posicion_presupuestaria': producto.posicion_presupuestaria.id,
                            'importe': calcular_precio_total(invoice_item.price_subtotal, invoice_item.invoice_line_tax_ids,self.tipo_contrato),
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
                sale_search = self.env['purchase.order'].search([('id','=',self.compra_ids)], limit=1)
                tjacdmx_update_status_mc = "UPDATE purchase_order SET status_account_move='EJERCIDO' WHERE id=%s" % (sale_search.id)
                self.env.cr.execute(tjacdmx_update_status_mc)
                cantidad = factura_set.amount_total
                cantidad = '{0:.2f}'.format(float(cantidad))
                importe = cantidad.split('.')[0]
                centavos = cantidad.split('.')[1]
                importe = (num2words(importe, lang='es').split(' punto ')[0]).upper()
                moneda = ' pesos '.upper()
                leyenda = '/100 m.n.'.upper()
                total_letra = importe + moneda + centavos + leyenda
                asiento_contable=obj_date_purchase.line_asientos_contables[0].id
                obj_line_ac = self.env['account.move.line'].search([('move_id','=',asiento_contable)], limit=2)
                datas['prov_nombre'] = search_clc_active.proveedor.name
                datas['prov_rfc'] = search_clc_active.rfc
                datas['prov_fecha_expedicion'] = search_clc_active.fecha_expedicion
                datas['prov_banco'] = search_clc_active.banco
                datas['prov_no_cuenta'] = search_clc_active.no_cuenta
                datas['prov_no_poliza'] = search_clc_active.no_poliza
                datas['prov_no_clc'] = search_clc_active.no_clc
                datas['prov_clave_presu'] = search_clc_active.clave_presu
                datas['prov_importe_letra'] = total_letra
                datas['reference_provedor'] = factura_set.reference_provedor
                #linea de momento contable abono
                cuentas = []
                suma_cargo = 0
                suma_abono = 0
                count = 0
                get_move= self.env['account.move'].search([('name', '=', factura_set.number)])
                docs = self.env['account.move.line'].search([('move_id', '=', get_move.id)])
                #obtener las cuentas
                for el in docs:
                    #obtener el id de la cuenta
                    account = el.account_id
                    i = account.code.split('.')
                    #buscar los nombres de las cuentas
                    cuenta_nombre = self.env['account.account'].search([('code', '=ilike', i[0] + '.' + '%')])[0].name
                    subcuenta_nombre = self.env['account.account'].search([('code', '=like', i[0] + '.' + i[1] + '.' + '%')])[0].name
                    suma_cargo = suma_cargo + el.debit
                    suma_abono = suma_abono + el.credit
                    cuenta = {
                        'cuenta': i[0],             #cuenta               [0]
                        'subcuenta': i[1],          #sub cuenta           [1]
                        'cargo': '{0:,.2f}'.format(float(el.debit)),          #cargo                [5]
                        'abono': '{0:,.2f}'.format(float(el.credit)),         #abono                [6]
                    }
                    if len(i) > 2:
                        subsubcuenta_nombre = self.env['account.account'].search(
                            [('code', '=like', i[0] + '.' + i[1] + '.' + i[2] + '%')]
                            )[0].name
                        cuenta.update({'subsubcuenta': i[2], 'subsubcuenta_nombre': subsubcuenta_nombre})
                    if len(i) >= 3:
                        subsubsubcuenta_nombre = self.env['account.account'].search(
                            [('code', '=', account.code)]
                            )[0].name
                    if len(i) <= 3:
                        cuenta.update({'subsubsubcuenta': i[2], 'subsubsubcuenta_nombre': subsubsubcuenta_nombre})
                    else:
                        cuenta.update({'subsubsubcuenta': i[3], 'subsubsubcuenta_nombre': subsubsubcuenta_nombre})
                    cuentas.append(cuenta)
                    lineas = []
                    for cuenta in cuentas:
                        for count in range(1,5):
                            if count == 1:
                                insert = {
                                'nombre': cuenta_nombre,
                                'cuenta': cuenta.get('cuenta'),
                                'subcuenta': '',
                                'subsubcuenta': '',
                                'subsubsubcuenta': '',
                                'parcial': '',
                                'cargo': cuenta.get('cargo'),
                                'abono': cuenta.get('abono'),
                                }
                                lineas.append(insert)
                            if count == 2:
                                insert = {
                                'nombre': subcuenta_nombre,
                                'cuenta': '',
                                'subcuenta': cuenta.get('subcuenta'),
                                'subsubcuenta': '',
                                'subsubsubcuenta': '',
                                'parcial': cuenta.get('abono') if (cuenta.get('abono') != 0.0) else cuenta.get('cargo'),
                                'cargo': '',
                                'abono': '',
                                }
                                lineas.append(insert)
                            if count == 3:
                                insert = {
                                'nombre': cuenta.get('subsubcuenta_nombre'),
                                'cuenta': '',
                                'subcuenta': '',
                                'subsubcuenta': cuenta.get('subsubcuenta'),
                                'subsubsubcuenta': '',
                                'parcial': '',
                                'cargo': '',
                                'abono': '',
                                }
                                lineas.append(insert)
                            if count == 4:
                                insert = {
                                'nombre': cuenta.get('subsubsubcuenta_nombre'),
                                'cuenta': '',
                                'subcuenta': '',
                                'subsubcuenta': '',
                                'subsubsubcuenta': cuenta.get('subsubsubcuenta'),
                                'parcial': cuenta.get('abono') if (cuenta.get('abono') != 0.0) else cuenta.get('cargo'),
                                'cargo': '',
                                'abono': '',
                                }
                                lineas.append(insert)
                                count += 1
                datas['lineas_cuenta'] = lineas
                datas['suma_abono'] = suma_abono
                datas['suma_cargo'] = suma_cargo
            else:
                raise ValidationError("No se genero CLC para esta factura")
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")


    @api.multi
    def pago_compra_win(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('pagado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        compra_precess = self.env['purchase.order'].search([('id','=',self.compra_ids)],limit=1)
        if(not ctrl_periodo.get_is_cerrado(self.fecha)and permisos):
            lines_factura = self.env['account.invoice.line'].search([('invoice_id','=',self.factura_ids)])
            factura_set = self.env['account.invoice'].search([('id','=',self.factura_ids)])
            obj_documento = self.env['presupuesto.documento']
            factura = lines_factura
            obj_date_purchase = self.env['purchase.order'].search([('id','=',self.compra_ids)], limit=1)
            date_pay=obj_date_purchase.date_order
            documentos = []
            amount = 0
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','PAGADO')], limit=1)
            fecha = datetime.strptime(self.fecha, '%Y-%m-%d') if self.fecha else datetime.today()
            fecha_origen = datetime.strptime(date_pay, '%Y-%m-%d %H:%M:%S') if date_pay else datetime.today()
            if(compra_precess.compromiso and compra_precess.type_purchase == 'compra'):
                fecha_origen = datetime.strptime(compra_precess.compromiso.fecha, '%Y-%m-%d')
            for invoice_item in factura:
                producto = invoice_item.product_id
                importe_presupuestal = calcular_precio_total(invoice_item.price_subtotal, invoice_item.invoice_line_tax_ids,self.tipo_contrato)
                importe_pagar = calcular_precio_total(invoice_item.price_subtotal, invoice_item.invoice_line_tax_ids,self.tipo_contrato,False)
                if(compra_precess.type_purchase=='compra'):
                    name_purchase=compra_precess.compromiso.name
                else:
                    name_purchase=compra_precess.folio
                concepto="""%s/Pagado""" % (name_purchase)
                documento = {
                    'clase_documento': cls_doc.id,
                    'version': version.id,
                    'ejercicio': fecha.year,
                    'periodo': fecha.month,
                    'periodo_origen': fecha_origen.month,
                    'fecha_contabilizacion': fecha.strftime('%Y-%m-%d %H:%M:%S'),
                    'fecha_documento': fecha.strftime('%Y-%m-%d %H:%M:%S'),
                    'detalle_documento_ids': [],
                    'concepto': str(concepto),
                    'compra_id': obj_date_purchase.id
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
            sale_search = self.env['purchase.order'].search([('id','=',self.compra_ids)], limit=1)
            tjacdmx_update_status_mc = "UPDATE purchase_order SET status_account_move='PAGADO' WHERE id=%s" % (sale_search.id)
            self.env.cr.execute(tjacdmx_update_status_mc)
            factura_set.write({'state': "paid_all"})
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")




    