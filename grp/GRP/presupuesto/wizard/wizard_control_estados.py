# -*- coding: utf-8 -*-
from datetime import datetime
from collections import Counter
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
# import csv, sys
import collections
import datetime
from dateutil.relativedelta import relativedelta
from datetime import date

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]


class wizard_control_estados(models.TransientModel):
    _name = 'wizard.control.estados'

    modulo=fields.Selection([
        ('tjacdmx_remisiones','Remision'),
        ('account_invoice','Factura'),
        ('purchase_order','Compra'),
        ('presupuesto_solicitud_pago','Solicitud de pago'),
        ('presupuesto_requisicion_compras','Requisiciones')
        ],required=True)
    estado=fields.Selection([
        ('open','open'),
        ('cancel','cancel'),
        ('close','close'),
        ('draft','draft'),
        ('draft_pre','draft_pre'),
        ('paid','paid'),
        ('paid_all','paid_all'),
        ('clc','clc'),
        ('send','send'),
        ('received','received'),
        ('in_payment','in_payment'),
        ('comprometido','comprometido'),
        ('devengado','devengado'),
        ('ejercido','ejercido'),
        ('pagado','pagado'),
        ('lista_devengado','lista_devengado'),
        ('sent','sent'),
        ('to approve','to approve'),
        ('purchase','purchase'),
        ('done','done')
        ],string='Estados')
    fecha = fields.Date(string='Fecha')
    remisiones = fields.Many2one('tjacdmx.remisiones',string='Remisiones')
    facturas = fields.Many2one('account.invoice',string='Facturas')
    compras = fields.Many2one('purchase.order',string='Compras')
    solicitud_pago = fields.Many2one('presupuesto.solicitud.pago',string='Solicitud pago')
    requisiciones = fields.Many2one('presupuesto.requisicion.compras',string='Requisiciones')
    result_html=fields.Html(string='Vista previa',compute='vista_previa')

    @api.multi
    @api.onchange('modulo')
    def clear(self):
        self.result_html=""""""

    @api.multi
    @api.onchange('remisiones','facturas','compras','solicitud_pago','requisiciones')
    def vista_previa(self):
        html=""" """
        if(self.modulo=='tjacdmx_remisiones'):
            remision_model=self.env['tjacdmx.remisiones']
            opciones_campo_selection = remision_model._fields['state'].selection
            html="""
                    <div><h3>Remision: %s</h3></div>
                    <h5>Estado: %s</h5>
                    <h5>Fecha: %s</h5>
                    <h5>Total: %s</h5>
                    <h5>Opciones de estado: %s</h5>
                """ % (str(self.remisiones.number),str(self.remisiones.state),str(self.remisiones.date_remision),str(self.remisiones.amount_total),str(opciones_campo_selection))
            self.result_html=html
        elif(self.modulo=='account_invoice'):
            account_invoice=self.env['account.invoice']
            opciones_campo_selection = account_invoice._fields['state'].selection
            html="""
                    <div><h3>Factura: %s</h3></div>
                    <h5>Estado: %s</h5>
                    <h5>Fecha: %s</h5>
                    <h5>Fecha de factura: %s</h5>
                    <h5>Total: %s</h5>
                    <h5>Opciones de estado: %s</h5>
                """ % (str(self.facturas.number),str(self.facturas.state),str(self.facturas.date_invoice),str(self.facturas.date_due),str(self.facturas.amount_total),str(opciones_campo_selection))
            self.result_html=html
        elif(self.modulo=='purchase_order'):
            purchase_order=self.env['purchase.order']
            opciones_campo_selection = purchase_order._fields['state'].selection
            html="""
                    <div><h3>Compra: %s</h3></div>
                    <h5>Estado: %s</h5>
                    <h5>Fecha: %s</h5>
                    <h5>Total: %s</h5>
                    <h5>Opciones de estado: %s</h5>
                """ % (str(self.compras.name),str(self.compras.state),str(self.compras.date_order),str(self.compras.amount_total),str(opciones_campo_selection))
            self.result_html=html
        elif(self.modulo=='presupuesto_solicitud_pago'):
            presupuesto_solicitud_pago=self.env['presupuesto.solicitud.pago']
            opciones_campo_selection = presupuesto_solicitud_pago._fields['state'].selection
            html="""
                    <div><h3>Remision: %s</h3></div>
                    <h5>Estado: %s</h5>
                    <h5>Fecha: %s</h5>
                    <h5>Total: %s</h5>
                    <h5>Opciones de estado: %s</h5>
                """ % (str(self.solicitud_pago.name),str(self.solicitud_pago.state),str(self.solicitud_pago.fecha),str(self.solicitud_pago.importe),str(opciones_campo_selection))
            self.result_html=html
        elif(self.modulo=='presupuesto_requisicion_compras'):
            presupuesto_requisicion_compras=self.env['presupuesto.requisicion.compras']
            opciones_campo_selection = presupuesto_requisicion_compras._fields['state'].selection
            html="""
                    <div><h3>Requisiciones: %s</h3></div>
                    <h5>Estado: %s</h5>
                    <h5>Fecha: %s</h5>
                    <h5>Total: %s</h5>
                    <h5>Opciones de estado: %s</h5>
                """ % (str(self.requisiciones.name),str(self.requisiciones.state),str(self.requisiciones.fecha),str(self.requisiciones.importe),str(opciones_campo_selection))
            self.result_html=html



    @api.multi
    def guarda_cambios(self):
        id_element=0
        if(self.modulo=='tjacdmx_remisiones'):
            id_element=self.remisiones.id
        elif(self.modulo=='account_invoice'):
            id_element=self.facturas.id
        elif(self.modulo=='purchase_order'):
            id_element=self.compras.id
        elif(self.modulo=='presupuesto_solicitud_pago'):
            id_element=self.solicitud_pago.id
        elif(self.modulo=='presupuesto_requisicion_compras'):
            id_element=self.requisiciones.id
        qry_dinamic = """
                UPDATE %s
                SET state='%s'
                WHERE id =%s""" %(str(self.modulo),self.estado,id_element)
        self.env.cr.execute(qry_dinamic)

    

