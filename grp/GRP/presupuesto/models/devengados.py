# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
from num2words import num2words
import xlwt
import json
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_compare
import collections
from . import configuracion, catalogos
from . import permisos
import os

class DevengadosLine(models.Model):
    _name = 'tjacdmx.devengados.line'
    _description = u'Requisición devengados'
    _rec_name = 'name'
    _inherit = ['mail.thread']

    @api.model
    def get_fondo(self):
        return self.env['presupuesto.fondo_economico'].search([('fuente_financiamiento','=','11')])
    @api.model
    def get_centro_g(self):
        return self.env['presupuesto.centro_gestor'].search([('clave','=','21A000')])
    @api.model
    def get_area_funci(self):
        return self.env['presupuesto.area_funcional'].search([('area_funcional','=','020400')])

    name = fields.Char(strig="name")
    fecha = fields.Date(string="Fecha",)
    periodo = fields.Selection(
       [(str(1),'Enero'),
        (str(2),'Febrero'),
        (str(3),'Marzo'),
        (str(4),'Abril'),
        (str(5),'Mayo'),
        (str(6),'Junio'),
        (str(7),'Julio'),
        (str(8),'Agosto'),
        (str(9),'Septiembre'),
        (str(10),'Octubre'),
        (str(11),'Noviembre'),
        (str(12),'Diciembre')], required=True)
    disponible =  fields.Float(select="Disponible")
    importe_origen =  fields.Float(select="Importe origen")
    importe =  fields.Float(select="Importe")
    state = fields.Selection([('draft','Borrador'),
                            ('send','Enviado'),
                            ('received','Con suficiecia presupuestal'),
                            ('devengado','Devengado'),
                            ('cancel','Cancelado')],
                            default="draft")
    fondo_economico = fields.Many2one('presupuesto.fondo_economico', string='Fondo',required=True,readonly=1,  default=get_fondo)
    centro_gestor = fields.Many2one('presupuesto.centro_gestor', string='Centro gestor',required=True,readonly=1, default=get_centro_g)
    area_funcional = fields.Many2one('presupuesto.area_funcional',string='Área funcional', required=True, default=get_area_funci)
    requisicion_compra = fields.Many2one('presupuesto.requisicion.compras', string='Requisición')
    remision_id = fields.Integer(string='remision')
    documento = fields.Many2one('presupuesto.documento', string='Documento', required=False)
    asiento = fields.Many2one('account.move', string='Asiento', required=False)
    line_asientos_contables = fields.One2many('account.move', string='Asientos contables', compute="_computed_asientos")
    invisible_devengado =  fields.Boolean(compute='_compute_visible')
    invisible_cancelar =  fields.Boolean(compute='_compute_visible')
    
    
    def _compute_visible(self):
        self.invisible_devengado = permisos.PermisosManager(self.env,self.env.uid).getVisible('req_devengar')
        self.invisible_cancelar = permisos.PermisosManager(self.env,self.env.uid).getVisible('req_cancelar_compromiso')
        

    
    def _computed_asientos(self):
        #doc = self.env['presupuesto.documento'].search([('concepto','=',self.name)])
        self.line_asientos_contables = self.env['account.move'].search([('ref','=',self.name.encode('utf-8'))])

    area = fields.Char(string="Área")
    partida = fields.Char(string="Partida")
    descripcion = fields.Char(string=u"Descripción")


    
    def button_open_devengado_window(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(permisos):
            if(self.state=='send' or self.state=='cancel'):
                return {
                    'name': _("Validar devengado"),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'devengados_actions.wizard',
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                    'context': {'remision': self.id,'momento': str('devengado'),'requisicion_compra':self.requisicion_compra.id,'devengado': self.id}
                } 
            else:
                raise ValidationError("El documento no se encuentra enel estatus Enviado para poder devengar.")
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def action_devengar(self):
        permisos.PermisosManager(self.env,self.env.uid).getPermiss('req_devengar')            
        ctrl_periodo = self.env['control.periodos.wizard']
        if(not ctrl_periodo.get_is_cerrado(self.fecha)):
            obj_documento = self.env['presupuesto.documento']
            fecha_orden = datetime.strptime(self.fecha, '%Y-%m-%d')
            ejercicio = fecha_orden.year
            periodo = fecha_orden.month
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','DEVENGADO')], limit=1)
            requisicion =  self.requisicion_compra
            posicion_presupuestaria = requisicion.partida
            compras = []
            compra = [0, False,
                {
                    'centro_gestor': self.centro_gestor.id,
                    'area_funcional': self.area_funcional.id,
                    'fondo_economico': self.fondo_economico.id,
                    'posicion_presupuestaria': posicion_presupuestaria.id,
                    'importe': self.importe,
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
                'concepto': self.name.encode('utf-8'),
                'remision_id':self.remision_id
            })
           
            asiento_contable=self.env['account.move'].search([('documento_id', '=', documento.id)],limit=1)
            asiento_contable.write({
                'ref':self.name.encode('utf-8')
            })
            self.write({
                'documento':documento.id,
                'asiento':asiento_contable.id,
                'state':'devengado'
            })
            if(documento):
                remision=self.env['tjacdmx.remisiones'].search([('id','=', self.remision_id)])
                lista_devengados=self.env['tjacdmx.lista_devengados'].search([('devengado_doc','=', self.id)])
                factura=self.env['account.invoice'].search([('id','=', remision.invoice_id.id)])
                factura.write({'state': 'devengado'})
                if(remision.is_list_devengado==True):
                    remision.write({'state': 'lista_devengado'})
                    lista_devengados.write({'state': 'devengado'})
                else:
                    remision.write({'state': 'devengado'})
                self.write({'state': 'devengado'})
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    
    

    
    def action_ajuste_cancelacion(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('registro_cancelaciones','=','open')])
        if(permisos):
            return {
                'name': _("Cancelación o Ajuste"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cancelacion_ajuste.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'compra_id':self.id, 
                'default_momento_contable': self.asiento.id,
                'default_ref_compra': self.name.encode('utf-8')}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")



    
    def action_cancelar(self):
        permisos.PermisosManager(self.env,self.env.uid).getPermiss('req_cancelar_compromiso')            
        ctrl_periodo = self.env['control.periodos.wizard']

        # if(self.env['presupuesto.solicitud.pago.line'].search([('compromiso','=',self.id)])):
        #     raise ValidationError("No se puede modificar un compromiso que se ha asignado una Solicitud de pago.")
        
        # if(self.env['purchase.order'].search([('compromiso','=',self.id)])):
        #     raise ValidationError("No se puede modificar un compromiso que se ha asignado una Compra.")

        if(not ctrl_periodo.get_is_cerrado(self.fecha)):
            
            documento=self.documento
            asiento_contable=self.env['account.move'].search([('documento_id', '=', documento.id)],limit=1)
            documento_id= documento.id if documento.id else 0
            asiento_contable_id= asiento_contable.id if asiento_contable.id else 0
            
            requisicion = self.requisicion_compra
            posicion_presupuestaria = requisicion.partida.id
            
            cp = self.env['presupuesto.control_presupuesto'].search([
            ('version', '=', documento.version.id),
            ('ejercicio', '=', documento.ejercicio),
            ('periodo', '=', documento.periodo),
            ('posicion_presupuestaria', '=', posicion_presupuestaria)])
            
            cp.write({ 'egreso_comprometido': cp.egreso_comprometido - self.importe })
            
            query1 = "DELETE FROM presupuesto_detalle_documento WHERE documento_id=%s" % (documento_id)
            query2 = "DELETE FROM presupuesto_documento WHERE id=%s" % (documento_id)
            query3 = "DELETE FROM account_move_line WHERE move_id=%s" % (asiento_contable_id)
            query4 = "DELETE FROM account_move WHERE id=%s" % (asiento_contable_id)
            
            self.env.cr.execute(query1)
            self.env.cr.execute(query2)
            self.env.cr.execute(query3)
            self.env.cr.execute(query4)

            self.update({'state':'cancel'})
        
        
    
    def unlink(self):
        if(self.state == 'devengado'):
            raise ValidationError("No se puede rechazar una requisión con asientos devengados.")        
        # if(self.env['presupuesto.solicitud.pago.line'].search([('devengado','=',self.id)])):
        #     raise ValidationError("No se puede eliminar un devengado que se ha asignado una Solicitud de pago.")
        return models.Model.unlink(self)


class ListaDevengados(models.Model):
    _name = 'tjacdmx.lista_devengados'
    _description = "Devengados Lista"
    _rec_name = 'remision'
    _inherit = ['mail.thread']

    remision = fields.Many2one('tjacdmx.remisiones', string='Entrega',required=True)
    devengado_doc = fields.Many2one('tjacdmx.devengados.line', string='Devengado',required=True)
    fecha = fields.Date(string="Fecha")
    
    importe_total=fields.Float(string='Importe', digits=(15, 2), compute='_compute_total', default=0)
    state = fields.Selection([('draft','Borrador'),
                            ('send','Enviado'),
                            ('devengado','Devengado'),
                            ('cancel','Cancelado')],
                            default="draft")
    
    
    def _compute_total(self):
        self.importe_total=self.devengado_doc.importe


    
    def action_devengar(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(permisos):
            if(self.devengado_doc):
                self.devengado_doc.action_devengar()
                self.write({'state': 'devengado'}) 
            else:
                raise ValidationError("Campos faltantes (Concepto y/o importe)")
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")