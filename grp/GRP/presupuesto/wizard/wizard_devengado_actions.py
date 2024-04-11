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

class momentos_presupuestales(models.TransientModel):
    _name = 'devengados_actions.wizard'

    @api.model
    def _get_remision(self):
        context = dict(self._context or {})
        remision = context.get('remision', False)
        if remision:
            data = remision
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
    def _get_momento(self):
        context = dict(self._context or {})
        momento = context.get('momento', False)
        if momento:
            data = momento
            return data
        return ''
    @api.model
    def _get_req_compra(self):
        context = dict(self._context or {})
        requisicion_compra = context.get('requisicion_compra', False)
        if requisicion_compra:
            data = requisicion_compra
            return data
        return ''
    @api.model
    def _get_devengado(self):
        context = dict(self._context or {})
        devengado = context.get('devengado', False)
        if devengado:
            data = devengado
            return data
        return ''

    fecha=fields.Date(required=True,default=_get_fecha)
    remision_ids=fields.Integer(default=_get_remision,readonly=True)
    momento=fields.Char(default=_get_momento,readonly=True)
    devengado = fields.Integer(defalt=_get_devengado,readonly=True)
    


    @api.multi
    def action_devengar(self):       
        ctrl_periodo = self.env['control.periodos.wizard']
        if(not ctrl_periodo.get_is_cerrado(self.fecha)):
            obj_documento = self.env['presupuesto.documento']
            fecha_orden = datetime.strptime(self.fecha, '%Y-%m-%d')
            ejercicio = fecha_orden.year
            periodo = fecha_orden.month
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','DEVENGADO')], limit=1)
            reqcom=self.env['presupuesto.requisicion.compras'].search([('id','=',self._get_req_compra())])
            dev_line=self.env['tjacdmx.devengados.line'].search([('id','=',self._get_devengado())])
            requisicion =  reqcom
            
            posicion_presupuestaria = requisicion.partida
            compras = []
            compra = [0, False,
                {
                    'centro_gestor': dev_line.centro_gestor.id,
                    'area_funcional': dev_line.area_funcional.id,
                    'fondo_economico': dev_line.fondo_economico.id,
                    'posicion_presupuestaria': posicion_presupuestaria.id,
                    'importe': dev_line.importe,
                    'momento_contable': 'DEVENGADO'
                }]
            compras.append(compra)
            documento = obj_documento.create({
                'clase_documento': cls_doc.id,
                'version': version.id,
                'ejercicio': ejercicio,
                'periodo': periodo,
                'periodo_origen': periodo,
                'fecha_contabilizacion': self.fecha,
                'fecha_documento': self.fecha,
                'detalle_documento_ids': compras,
                'concepto': dev_line.name,
                'remision_id':dev_line.remision_id
            })
            asiento_contable=self.env['account.move'].search([('documento_id', '=', documento.id)],limit=1)
            asiento_contable.write({
                'ref':dev_line.name
            })
            dev_line.write({
                'documento':documento.id,
                'asiento':asiento_contable.id,
                'state':'devengado'
            })
            if(documento):
                remision=self.env['tjacdmx.remisiones'].search([('id','=', dev_line.remision_id)])
                lista_devengados=self.env['tjacdmx.lista_devengados'].search([('devengado_doc','=', dev_line.id)])
                factura=self.env['account.invoice'].search([('id','=', remision.invoice_id.id)])
                factura.write({'state': 'draft_pre'})
                if(remision.is_list_devengado==True):
                    remision.write({'state': 'lista_devengado'})
                    lista_devengados.write({'state': 'devengado'})
                else:
                    remision.write({'state': 'devengado'})
                dev_line.write({'state': 'devengado'})
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")