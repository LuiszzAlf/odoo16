# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _, SUPERUSER_ID,tools
from odoo.exceptions import ValidationError,UserError
# from odoo.tools.translate import _
from num2words import num2words
import xlwt
import json
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_compare
import collections
from . import configuracion, catalogos
import calendar
from . import permisos



class PresupuestoSolicitudPago(models.Model):
    _name = 'presupuesto.solicitud.pago'
    _inherit = ['mail.thread']
    _description = u'SP Splicitud de pago compras'
    _order = 'name desc'


    @api.model
    def _default_origen(self):
        context = dict(self._context or {})
        origen = context.get('origen', False)
        if origen==True:
            return True
        return False

    @api.model
    def _get_requi(self):
        context = dict(self._context or {})
        compromiso = context.get('requi_id', False)
        if compromiso:
            data = compromiso
            return data
        return ''

    @api.model
    def _get_lines_sp(self):
        context = dict(self._context or {})
        lineas_solicitud_pago = context.get('lineas_solicitud_pago', False)
        if lineas_solicitud_pago:
            data = lineas_solicitud_pago
            return data
        return ''
    
    @api.model
    def _get_requi_m2m(self):
        context = dict(self._context or {})
        compromiso = context.get('requi_id', False)
        idsreq=[]
        idsreq.append(compromiso)
        return self.env['presupuesto.requisicion.compras.compromisos.line'].search([('id', 'in', idsreq)]).ids
        


    state = fields.Selection([('draft','Borrador'),
                            ('send','Enviado'),
                            ('received','Rebibido'),
                            ('cancel','Cancelado')],
                            default="draft",  track_visibility='onchange')    
    name = fields.Char(string="name")
    fecha = fields.Date(string="Fecha", required=True)
    fecha_recibido = fields.Datetime(string="Fecha recibido")
    tipo_pago =fields.Selection([('transferencia', 'Transferencia'),
                                     ('cheque', 'Cheque')], string='Solicitud de pago vía', required=True)
    afavor = fields.Char(string="A favor de")
    solicitante = fields.Many2one('presupuesto.areas.stok', string="Trámite solicitado por")
    responsabe_area = fields.Many2one('tjacdmx.resguardantes', string="Nombre del responsabe del área")
    area_solicitante = fields.Many2one('presupuesto.areas.stok',string="Área solicitante del bien o servicio")
    proveedor = fields.Many2one('res.partner', string="Proveedor")
    proveedor_tipo = fields.Selection([('existente', 'Existente'),
                                ('nuevo', 'Nuevo')], 
                                default="existente", string='Proveedor', required=True)
    proveedor_nvo = fields.Char(string="Nuevo proveedor")
    fecha_pago = fields.Char(string="Fecha de pago")
    adjunta = fields.Text(string="Documentacion adjunta")
    contrato = fields.Char(string="Contrato/No.Pedido", help="Contrato o número de pedido.", required=True)
    elaboro = fields.Text(string="Elaboró")
    vb = fields.Text(string="Vo. Bo.", default="""MTRA. CECILIA SOTO GALLARDO DIRECTORA DE RECURSOS MATERIALES Y SERVICIOS GENERALES""")
    autorizo = fields.Text(string="Autorizó", default="""LIC. ANDREA DEL CARMEN ROSER GALVÁN
DIRECTORA GENERAL DE ADMINISTRACIÓN""")
    recibio = fields.Text(string="Recibió", default="""L. C. JUANA SALAZAR VÁZQUEZ
    DIRECTORA DE RECURSOS FINANCIEROS""")
    justificacion = fields.Text(string="Justificación", default="""A efecto de que el expediente relativo al trámite del presente asunto se encuentre debidamente integrado,
    le solicito atentamente su apoyo para que en su oportunidad nos informe la fecha en que ésa Área Financiera
    haya realizado el pago solicitado.""")
    otra_info = fields.Char("Información adicional", default="Consta de Solicitud de pago y factura original")
    lineas_solicitud_pago =  fields.One2many('presupuesto.solicitud.pago.line', 'solicitud_pago_id', string="Lineas pago",default=_get_lines_sp)
    compras =  fields.Many2one('purchase.order', string="Compras")
    requisiciones =  fields.Many2one('presupuesto.requisicion.compras.compromisos.line', string="Requisiciones",default=_get_requi)
    origen_compra =  fields.Boolean(default=_default_origen)
    archivo = fields.Binary(string='Archivo')
    archivo_filename = fields.Char("Image Filename")
    importe = fields.Float(string="SUMA",compute='_amount_all')
    invisible_enviar =  fields.Boolean(compute='_compute_visible')      
    invisible_recibir =  fields.Boolean(compute='_compute_visible')
    invisible_regresar =  fields.Boolean(compute='_compute_visible')
    invisible_rechazar =  fields.Boolean(compute='_compute_visible')
    compromisos = fields.Many2many('presupuesto.requisicion.compras.compromisos.line','compromisos_sp','sp_id','compromiso_id', string='Requisiciones',default=_get_requi_m2m)
    compras_many = fields.Many2many('purchase.order','compras_sp','spc_id','compras_id', string='Compras')
    caas = fields.Char(string="CAAS")
    no_procedimiento = fields.Char(string="No. Procedimiento")

    
    def _amount_all(self):
        amount_total = 0.0
        for line in self.lineas_solicitud_pago:
            amount_total +=line.importe
        self.importe = amount_total
    # @api.model
    # def get_compras(self):
    #     print(self.lineas_solicitud_pago)
    #     return self.env['purchase.order'].search([('sp_ids','=',1)])

    # compras = fields.One2many('purchase.order',  default='get_compras', string='Compras')
   
    
    @api.onchange('requi_ids')
    def _onchange_periodo(self):
        if self.requi_ids:
            return {'domain': {'requisiciones': [('id', 'in', self._get_requi())]}}

    
    @api.onchange('requisiciones')
    def _onchange_prov(self):
        proves=[]
        remisiones = self.env['tjacdmx.remisiones'].search([('origin','=',self.requisiciones.id)])
        for f in remisiones:
            proves.append(f.partner_id.id)
        if proves:
            return {'domain': {'proveedor': [('id', 'in',proves)]}}

    
    def _compute_visible(self):
        self.invisible_enviar = permisos.PermisosManager(self.env,self.env.uid).getVisible('sp_enviar')
        self.invisible_recibir = permisos.PermisosManager(self.env,self.env.uid).getVisible('sp_recibir')
        self.invisible_regresar = permisos.PermisosManager(self.env,self.env.uid).getVisible('sp_regresar_borrador')
        self.invisible_rechazar = permisos.PermisosManager(self.env,self.env.uid).getVisible('sp_reversar')




    def generar_name(self):
        last_id = 0
        self.env.cr.execute('SELECT id FROM "presupuesto_solicitud_pago" ORDER BY id DESC LIMIT 1')
        ids_data = self.env.cr.fetchone()
        #ids_data = self.id
        if ids_data>=0:
            last_id = ids_data[0]
        else:
            last_id = 0
        
        year = datetime.now().year
        prefijo = 'SP/'+str(year)+'/'
        serie = last_id+1
        consecutivo = prefijo + str(serie).rjust(4, '0')
        return consecutivo

    @api.model
    def create(self, values):
        res = super(PresupuestoSolicitudPago, self).create(values)
        res.update({'name': self.generar_name(),
                    'importe': self.calcula_importe()})                  
        return res

    
    def write(self, values):
        values.update({'importe': self.calcula_importe()})
        super(PresupuestoSolicitudPago, self).write(values)
        return True

    @api.onchange('lineas_solicitud_pago')
    
    def onchange_lineas_solicitud_pago(self):
        self.update({'importe': self.calcula_importe()})

    def calcula_importe(self):
        importe = 0
        for linea in self.lineas_solicitud_pago: 
            importe = importe + linea.importe
        return float(importe)

    
    def action_enviar(self):
        for devengado in self.lineas_solicitud_pago:
            if(devengado.state != 'devengado'):
                devengado.write({'state': 'send',
                                'name': self.name+'-'+str(devengado.id),
                                'proveedor': self.proveedor.id})
        self.update({'state': 'send'})             

    
    def action_aprobar(self):
        for devengado in self.lineas_solicitud_pago:
            if(devengado.state != 'devengado'):
                devengado.write({'state': 'received'})
        self.update({'state': 'received','fecha_recibido': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    
    def action_regresar(self):
        for devengado in self.lineas_solicitud_pago:
            if(devengado.state != 'devengado'):
                devengado.write({'state': 'draft'})
        self.update({'state':'draft'})

    
    def action_rechazar(self):
        for devengado in self.lineas_solicitud_pago:
            if(devengado.state == 'devengado'):
                raise ValidationError("No se puede reversar una Solicitud de pago que ha sido devengada.")
        if(self.env['purchase.order'].search([('sp_ids','=',self.id)])):
            raise ValidationError("No se puede reversar una Solicitud de pago que se ha asignado una Compra.")
        self.update({'state':'draft'})
        for devengado in self.lineas_solicitud_pago:
            if(devengado.state != 'devengado'):
                devengado.write({'state': 'draft'})
       
    
    def unlink(self):    
        if(self.state == 'received'):
            raise ValidationError("No se puede eliminar una Solicitud de pago recibida.")
        if(self.env['purchase.order'].search([('sp_ids','=',self.id)])):
            raise ValidationError("No se puede eliminar una Solicitud de pago que se ha asignado una Compra.")
        #if(self.requisicion_compra):
            #raise ValidationError("No se puede eliminar un compromiso de una requisicion activa")
        if(self.state == 'cancel'):
            return models.Model.unlink(self)
        else:   
            raise ValidationError("No se puede eliminar una Solicitud de pago que no encuentre cancelada.")
    
    
    def print_sp(self):
        return self.env['report'].get_action(self, 'reportes.solicitud_pago')



class TipoContrato(models.Model):
    _name = 'presupuesto.tipo.contrato'
    _description = u'Tipo de contrato'
    _rec_name = 'code'
    _inherit = ['mail.thread']

    code = fields.Char(strig="code")
    name = fields.Char(strig="Nombre")
    state = fields.Selection([('draft','Borrador'),
                            ('open','Abierto'),
                            ('cancel','Cancelado')],
                            default="draft")
    
class PresupuestoSolicitudPagoLinea(models.Model):
    _name = 'presupuesto.solicitud.pago.line'
    _description = u'SP Splicitud de pago compras linea'
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
    
    fondo_economico = fields.Many2one('presupuesto.fondo_economico', string='Fondo',required=True,readonly=1,  default=get_fondo)
    centro_gestor = fields.Many2one('presupuesto.centro_gestor', string='Centro gestor',required=True,readonly=1, default=get_centro_g)
    area_funcional = fields.Many2one('presupuesto.area_funcional',string='Área funcional', required=True, default=get_area_funci)

    state = fields.Selection([('draft','Borrador'),
                            ('send','Enviado'),
                            ('received','Con suficiecia presupuestal'),
                            ('devengado','Devengado'),
                            ('cancel','Cancelado')],
                            default="draft")
    name = fields.Char(strig="name")
    partida=fields.Many2one('presupuesto.partida_presupuestal', track_visibility='onchange', string='Partida presupuestaria', required=True)
    factura = fields.Char(string="Factura", required=True)
    fecha = fields.Date(string="Fecha", required=True)
    descripcion = fields.Char(string="Descripción", required=True)
    importe =  fields.Float(select="Importe", required=True)
    importe_si = fields.Float(string="Importe sin impuestos")
    tipo_adjudicacion = fields.Many2one('presupuesto.tipo.contrato',string="Tipo Adjudicación")
    #adjudicacion = fields.Many2one('purchase.requisition.type', string="Adjudicación", required=True)
    adjudicacion = fields.Char( string="Adjudicación", required=False)
    compromiso = fields.Many2one('presupuesto.requisicion.compras.compromisos.line',string="Requisición")
    
    solicitud_pago_id =  fields.Many2one('presupuesto.solicitud.pago', string="S.P.")
    documento = fields.Many2one('presupuesto.documento', string='Documento', required=False)
    asiento = fields.Many2one('account.move', string='Asiento', required=False)
    proveedor = fields.Many2one('res.partner', string="Proveedor")
    line_asientos_contables = fields.One2many('account.move', string='Asientos contables', compute="_computed_asientos")

    
    def _computed_asientos(self):
        #doc = self.env['presupuesto.documento'].search([('concepto','=',self.name)])
        self.line_asientos_contables = self.env['account.move'].search([('ref','=',self.name)])
    
    @api.onchange('compromiso')
    
    def onchange_compromiso(self):
        self.update({'partida':self.compromiso.requisicion_compra.partida})
    
    @api.model
    def create(self, values):
        res = super(PresupuestoSolicitudPagoLinea, self).create(values)          
        return res

    
    def action_devengar(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(not ctrl_periodo.get_is_cerrado(self.fecha)
            and permisos):
            obj_documento = self.env['presupuesto.documento']
            fecha_orden = datetime.strptime(self.fecha, '%Y-%m-%d')
            ejercicio = fecha_orden.year
            periodo = fecha_orden.month
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','DEVENGADO')], limit=1)
            #self.write({'status_account_move': "COMPROMETIDO"})
            posicion_presupuestaria = self.partida
            compras = []
            compra = [0, False,
                {
                    'centro_gestor': self.centro_gestor.id,
                    'area_funcional': self.area_funcional.id,
                    'fondo_economico': self.fondo_economico.id,
                    'posicion_presupuestaria': posicion_presupuestaria.id,
                    'importe': self.importe,
                    'momento_contable': 'ORIGINAL'
                }]
            compras.append(compra)
            # Si, el compromiso de la compra viene referenciado no realizar asiento de compromido
            documento = obj_documento.create({
                'clase_documento': cls_doc.id,
                'version': version.id,
                'ejercicio': ejercicio,
                'periodo': periodo,
                'periodo_origen': periodo,
                'fecha_contabilizacion': self.fecha,
                'fecha_documento': self.fecha,
                'detalle_documento_ids': compras,
                'concepto': self.name
            })
            asiento_contable=self.env['account.move'].search([('documento_id', '=', documento.id)],limit=1)
            asiento_contable.write({
                'ref':self.name
            })
            self.write({
                'documento':documento.id,
                'asiento':asiento_contable.id,
                'state':'devengado'
            })
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    
    
    def action_crear_compra(self):
        sp = self.env['presupuesto.solicitud.pago.line'].search([('id','=',self.id)])
        listids=[]
        listids.append(sp.id)
        return {
                    'name': _("Crear compra"),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'purchase.order',
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                    'context': {
                        'default_state': 'draft',
                        'default_status_account_move':'ORIGINAL',
                        'default_type_purchacee':'compra',
                        'default_compromiso':self.compromiso.id,
                        'default_date_order':self.compromiso.fecha,
                        'default_fecha_devengado': self.fecha,
                        'default_sp_ids': listids ,
                        'default_partner_id': self.proveedor.id
                        }
                } 

    
    def action_cancelar(self):
        permisos.PermisosManager(self.env,self.env.uid).getPermiss('sp_cancelar_devengado')            
        user_session = self.env['res.users'].browse(self.env.uid)
        ctrl_periodo = self.env['control.periodos.wizard']
        # if(self.env['purchase.order'].search([('sp_ids','=',self.solicitud_pago_id.id)])):
        #     raise ValidationError("No se puede modificar un devengadi que se ha asignado una Compra.")

        if(not ctrl_periodo.get_is_cerrado(self.fecha)):

            documento= self.documento
            asiento_contable= self.asiento
                        
            documento_id= documento.id if documento.id else 0
            asiento_contable_id= asiento_contable.id if asiento_contable.id else 0
                        
            posicion_presupuestaria = self.partida

            cp = self.env['presupuesto.control_presupuesto'].search([
            ('version', '=', documento.version.id),
            ('ejercicio', '=', documento.ejercicio),
            ('periodo', '=', documento.periodo),
            ('posicion_presupuestaria', '=', posicion_presupuestaria.id)])
            
            total_dev= cp.egreso_devengado - self.importe
            total_com=cp.egreso_comprometido + self.importe
            
            put_state_line= "UPDATE presupuesto_control_presupuesto SET egreso_comprometido='%s', egreso_devengado='%s' WHERE id=%s" % (total_com,total_dev,cp.id)
            self.env.cr.execute(put_state_line)
            

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
        if(self.state == 'received'):
            raise ValidationError("No se puede eliminar una Solicitud de pago recibida.")

        if(self.env['purchase.order'].search([('sp_ids','=',self.id)])):
            raise ValidationError("No se puede eliminar una Solicitud de pago que se ha asignado una Compra.")
       
        #if(self.requisicion_compra):
            #raise ValidationError("No se puede eliminar un compromiso de una requisicion activa")

        return models.Model.unlink(self)

  

