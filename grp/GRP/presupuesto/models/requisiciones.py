# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _, SUPERUSER_ID,tools
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
import calendar
# from calendar import calendar.TimeEncoding, month_name
from . import permisos 
import os


class PresupuestoRequisicionCompras(models.Model):
    _name = 'presupuesto.requisicion.compras'
    _rec_name='name'
    _inherit = ['mail.thread']
    _description = u'Requisición compras v2'
    _order = 'numero desc'


    justificacion=fields.Text(strig='Justificación')
    observaciones=fields.Text(strig='Observaciones')
    solicitante=fields.Text(string='Área solicitante')
    #cargo_solicitante=fields.Char(string=u"Área",store=True, compute="_getAreaSolicitante")
    elaboro=fields.Text(string=u'Elabora')
    #cargo_elaboro=fields.Char(string=u"Área",store=True, compute="_getAreaElaboro")
    reviso=fields.Text(string=u'Revisa')
    #cargo_reviso=fields.Char(string=u"Área",store=True, compute="_getAreaReviso")
    autorizo=fields.Text(string=u'Autorizó', default="""LIC. ANDREA DEL CARMEN ROSER GALVÁN DIRECTORA GENERAL DE ADMINISTRACIÓN """)
    #cargo_autorizo=fields.Char(string=u"Área",store=True ,compute="_getAreaAutorizo")
    lugar_entrega = fields.Text(string=u'Los bienes serán entregados en:', default=u'TRIBUNAL DE JUSTICIA ADMINISTRATIVA DE LA CIUDAD DE MÉXICO')
    numero=fields.Integer(strig='Número', required=True)
    indice=fields.Char(strig='Índice')
    area=fields.Selection([('SG', 'SG'), ('RM', 'RM')],strig='Area', required=True)
    partida=fields.Many2one('presupuesto.partida_presupuestal', track_visibility='onchange', string='Partida presupuestaria', required=True)
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT)
    fecha = fields.Date(string="Fecha", required=True)
    fecha_recibido = fields.Datetime(string="Fecha recibido",)
    tipo = fields.Selection([
                            ('mensual','Mes corriente'),
                            ('anual','Anual'),
                            ('complemento','Complemento')], string="Periodicidad", 
                            default="mensual", required=True)
    importe =  fields.Float(string="Total",readonly=True, compute='_amount_all')
    state = fields.Selection([('draft','Borrador'),
                            ('send','Enviado'),
                            ('received','Con suficiecia presupuestal'),
                            ('comprometido','Comprometido'),
                            ('devengado','Devengado'),
                            ('cancel','Cancelado')],
                            default="draft",  track_visibility='onchange')
    name = fields.Char(strig="name")
    descripcion=fields.Char(strig='Descripción', required=True)
    lineas_requisicion_compras  = fields.One2many('presupuesto.requisicion.compras.line', 'requisicion_compra', string='Lineas requisicion',required=False)
    lineas_compromisos  = fields.One2many('presupuesto.requisicion.compras.compromisos.line', 'requisicion_compra', string='Lineas compromisos',required=False)
    lineas_devengados  = fields.One2many('tjacdmx.devengados.line', 'requisicion_compra', string='Lineas compromisos',required=False)
    archivo = fields.Binary(string='Archivo')
    archivo_filename = fields.Char("Image Filename")    
    invisible_enviar =  fields.Boolean(compute='_compute_visible')
    invisible_aprobar =  fields.Boolean(compute='_compute_visible')
    invisible_comprometer =  fields.Boolean(compute='_compute_visible')
    invisible_regresar =  fields.Boolean(compute='_compute_visible')
    invisible_rechazar =  fields.Boolean(compute='_compute_visible')
    remisiones_count = fields.Integer(compute="_compute_remisiones", string=' ',default=0)
    facturas_count = fields.Integer(compute="_compute_facturas", string=' ',copy=False, default=0)
    sp_count = fields.Integer(compute="_compute_sp", string=' ',default=0)
    documentacion=fields.Many2one('tjacdmx.documentacion', track_visibility='onchange', string='Documentacion')



    
    def _amount_all(self):
        amount_total = 0.0
        for line in self.lineas_requisicion_compras:
            amount_total +=line.precio_unitario*line.cantidad
        self.importe = amount_total

    
    def _compute_movimientos(self):
        listids=[]
        docs=[]
        for each in self.lineas_compromisos:
            for d in each.documento:
                docs.append(d.id)
            listids.append(each.id)
        for eachd in self.lineas_devengados:
            for de in eachd.documento:
                docs.append(de.id)
        remision_origen=self.env['tjacdmx.remisiones'].search([('origin','in', listids)])
        for i in remision_origen:
            for e in i.documentos:
                docs.append(e.id)
        self.movimientos=docs
        
    movimientos= fields.One2many('presupuesto.documento', 'remision_id', string='Documentos',compute='_compute_movimientos')
    
    
    def _compute_visible(self):
        self.invisible_enviar = permisos.PermisosManager(self.env,self.env.uid).getVisible('req_enviar')
        self.invisible_aprobar = permisos.PermisosManager(self.env,self.env.uid).getVisible('req_aprobar')
        self.invisible_comprometer = permisos.PermisosManager(self.env,self.env.uid).getVisible('req_comprometer')
        self.invisible_regresar = permisos.PermisosManager(self.env,self.env.uid).getVisible('req_regresar_borrador')
        self.invisible_rechazar = permisos.PermisosManager(self.env,self.env.uid).getVisible('req_reversar')
    

    def _compute_remisiones(self):
        listids=[]
        for each in self.lineas_compromisos:
            listids.append(each.id)
        remision_origen=self.env['tjacdmx.remisiones'].search([('origin','in', listids)])
        self.remisiones_count = len(remision_origen)

    
    def _compute_facturas(self):
        listids=[]
        for each in self.lineas_compromisos:
            listids.append(each.id)
        facturas=self.env['account.invoice'].search([('requicision','in', listids)])
        self.facturas_count = len(facturas)
    
    def _compute_sp(self):
        listids=[]
        for each in self.lineas_compromisos:
            listids.append(each.id)
        sps=self.env['presupuesto.solicitud.pago'].search(['|',('requisiciones','in', listids),('compromisos','in', listids)])
        self.sp_count = len(sps)
    

    
    def new_factura(self):
        action = self.env.ref('presupuestos.action_facturas')
        res = self.env.ref('presupuestos.action_facturas_form', False)
        listids=[]
        for each in self.lineas_compromisos:
            listids.append(each.id)
        facturas=self.env['account.invoice'].search([('requicision','in', listids)])
        search_remis_active = self.env['account.invoice'].search([('requicision','=',self.id)], limit=1)
        if (listids):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('requicision','in', %s)]" % (listids)
        else:
            result = res.read()[0]
            result['context'] = {}
            result['context']['default_id_purchase'] = self.id
            result['context']['name_requi'] = str(self.numero)
            result['context']['origin'] = str(self.id)
            result['context']['requicision'] = str(self.id)
            result['context']['reference_provedor'] = str(self.numero)
            result['context']['account_id'] = 248
            result['context']['state'] = 'draft'
            result['context']['type'] ='in_invoice'
            result['context']['journal_id'] = 2
        return result

    
    def sp_new(self):
        action = self.env.ref('presupuestos.action_sps')
        res = self.env.ref('presupuestos.action_sps_form', False)
        listids=[]
        for each in self.lineas_compromisos:
            listids.append(each.id)
        sps=self.env['presupuesto.solicitud.pago'].search(['|',('requisiciones','in', listids),('compromisos','in', listids)])
        search_remis_active = self.env['presupuesto.solicitud.pago'].search([('requisiciones','=',self.id)], limit=1)
        if (listids):
            result = action.read()[0]
            result['context'] = {
                        'origen': True,
                        }
            result['domain'] = "['|',('requisiciones','in', %s),('compromisos','in', %s)]" % (listids,listids)
        else:
            result = action.read()[0]
            result['context'] = {
                        'origen': True,
                        }
            result['domain'] = "[('requisiciones','in', '')]"
        return result



    
    def list_remision(self):
        action = self.env.ref('presupuestos.action_remiciones')
        listids=[]
        for each in self.lineas_compromisos:
            listids.append(each.id)
        remision_origen=self.env['tjacdmx.remisiones'].search([('origin','in', listids)])
        if (remision_origen):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('origin','in', %s)]" % (listids)
        else:
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('origin','in', '')]" 

        return result



    
    def button_wizard_cancel(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('registro_cancelaciones','=','open')])
        if(permisos):
            return {
                'name': _("Cancelación o Ajuste"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cancelacion_ajuste_req.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'requi_id':self.id,}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")


    @api.model
    def create(self, values):
        res = super(PresupuestoRequisicionCompras, self).create(values)
        ejercicio =  datetime.strptime(res.fecha, "%Y-%m-%d")
        res.update({'ejercicio':ejercicio.year})     
        
        indice_s= res.indice if res.indice else ''
        nombre = "REQ/"+str(res.ejercicio)+"/"+str(res.numero)+str(indice_s)+str(res.area)

        res.update({'ejercicio':ejercicio.year,
                'name': nombre})     
        return res

    
    def write(self, values):
        res = super(PresupuestoRequisicionCompras, self).write(values)
        if(self.state=='draft'):    
            ejercicio =  datetime.strptime(self.fecha, "%Y-%m-%d")
            indice_s= self.indice if self.indice else ''
            nombre = "REQ/"+str(ejercicio.year)+"/"+str(self.numero)+str(indice_s)+str(self.area)
            put_folio="UPDATE presupuesto_requisicion_compras SET name='%s' WHERE id=%s" % (nombre,self.id)
            self.env.cr.execute(put_folio)
        return res

    # @api.onchange('lineas_requisicion_compras')
    # 
    # def onchange_lineas_requisicion_compras(self):
    #     self.update({'importe': self.calcula_importe()})

    def calcula_importe(self):
        importe = 0
        for linea in self.lineas_requisicion_compras: 
            linea_importe = linea.precio_unitario*linea.cantidad
            linea.write({'importe':linea_importe})
            importe = importe + linea_importe
        
        return float(importe)
        
    
    def importe_con_letra(self, cantidad):
        cantidad = '{0:.2f}'.format(float(cantidad))
        importe = cantidad.split('.')[0]
        centavos = cantidad.split('.')[1]
        importe = (num2words(importe, lang='es').split(' punto ')[0]).upper()
        moneda = ' pesos '.upper()
        leyenda = '/100 m.n.'.upper()
        return importe + moneda + centavos + leyenda

    
    def generar_name(self):
        indice_s= self.indice if self.indice else ''
        nombre = "REQ/"+str(self.ejercicio)+"/"+str(self.numero)+str(indice_s)+str(self.area)
        self.name = nombre
        return nombre

    
    
    def action_enviar(self):
        permisos.PermisosManager(self.env,self.env.uid).getPermiss('req_enviar')
            
        #self.generar_name()
        #self.update({'name': self.generar_name()})   
        self.update({'state': 'send'})

            
        periodos = [] 
        
        for linea in self.lineas_requisicion_compras: 
            periodos.append(linea.periodo)

        periodos = [x for x, y in collections.Counter(periodos).items() if y >= 1]
        periodos.sort() 
        
        for periodo in periodos:
            total_compromiso = 0
            fecha = ''
            for linea in self.lineas_requisicion_compras: 
                if(linea.periodo == periodo):
                    total_compromiso = total_compromiso + linea.importe
                    fecha = linea.fecha
            
            compromisos = self.env['presupuesto.requisicion.compras.compromisos.line']
            mes = self.get_month_name(periodo, "es_MX.UTF-8")
            #fecha = str(self.ejercicio)+"-"+str(periodo)+"-01"
                    
            compromisos.create({
                        'state': 'send',
                        'name': self.name+'('+mes+')',
                        'fecha': fecha,
                        'periodo': periodo,
                        'disponible': total_compromiso,
                        'importe':total_compromiso,
                        'requisicion_compra':self.id,
                        'area':self.area,
                        'partida':self.partida.partida_presupuestal,
                        'descripcion':self.descripcion,
                        }
                    )

    def get_month_name(self, month_no, locale):
        with calendar.TimeEncoding(locale) as encoding:
            s = calendar.month_name[month_no]
            if encoding is not None:
                s = s.decode(encoding)
            return s

    
    def action_aprobar(self):
        permisos.PermisosManager(self.env,self.env.uid).getPermiss('req_aprobar')

        self.update({'state': 'received','fecha_recibido': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        for linea in self.lineas_compromisos:                     
            linea.update({
                        'state': 'received',
                        }
                    )
                
        self.env['wizard.popup'].create_notificacion_url(self.name,'Con sificiencia, recuerda comprometer el mes corriente.', self.create_uid.id, 
        '/web#id='+str(self.id)+'&view_type=form&model=presupuesto.requisicion.compras&menu_id=389&action=543'
        ,'presupuesto.requisicion.compras')

        # html = u"""
        #     <p>
        #         </p><table border="0" width="100%%" cellpadding="0" bgcolor="#ededed" style="padding: 20px; background-color: #ededed">
        #             <tbody>
        #               <tr>
        #                 <td align="center" style="min-width: 590px;">
        #                   <table width="590" border="0" cellpadding="0" bgcolor="#fff" style="min-width: 590px; background-color: #fff; padding: 20px;">
        #                     <tbody>
        #                         <tr>
        #                             <td valign="middle">
        #                                 <span style="font-size:20px; color:#875A7B; font-weight: bold;">%s</span><br><br>
        #                                 <span style="font-size:20px; color:#875A7B; font-weight: bold;">Con sufuciencia presupuestal.</span>
        #                             </td>
        #                             <td valign="middle" align="right">
        #                                 <img src="http://scio.tjacdmx.gob.mx/logo.png?company=1" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="1">
        #                             </td>
        #                         </tr>
        #                     </tbody>
        #                   </table>
        #                 </td>
        #               </tr>
        #               <tr>
        #                 <td align="center" style="min-width: 590px;">
        #                   <table width="590" border="0" cellpadding="0" bgcolor="#ffffff" style="min-width: 590px; background-color: rgb(255, 255, 255); padding: 20px;">
        #                     <tbody>
        #                       <tr><td valign="top" style="font-family:Arial,Helvetica,sans-serif; color: #555; font-size: 14px;"><br></td>
        #                     </tr><tr>
        #                     <td valign="top" style="font-family:Arial,Helvetica,sans-serif; color: #555; font-size: 14px;">
        #                         Buen día. <br><br>
        #                         La requisicón cuenta con suficiencia presupuestal, no olvide comprometer el mes corriente.
        #                         <br><br>
        #                         <br><br>
        #                         <br><br><a href="http://%s//web#id=%s&view_type=form&model=presupuesto.requisicion.compras&action=543"><h4>Da click aquí para revisar.</h4></a>
        #                     </td>
        #                     </tr><tr><td valign="top" style="font-family:Arial,Helvetica,sans-serif; color: #555; font-size: 14px;"><br></td>
        #                     </tr></tbody>
        #                   </table>
        #                 </td>
        #               </tr>
        #               <tr>
        #                 <td align="center" style="min-width: 590px;"> 
        #                   <table width="590" border="0" cellpadding="0" bgcolor="#875A7B" style="min-width: 590px; background-color: rgb(135,90,123); padding: 20px;">
        #                     <tbody><tr>
        #                       <td valign="middle" align="left" style="color: #fff; padding-top: 10px; padding-bottom: 10px; font-size: 12px;">
        #                         Tribunal de Justicia Administrativa de la Ciudad de México<br>
        #                         SCIO Solicitud de suministro v.1.0
        #                       </td>
        #                       <td valign="middle" align="right" style="color: #fff; padding-top: 10px; padding-bottom: 10px; font-size: 12px;">
                             
        #                      </td>
        #                     </tr>
        #                   </tbody></table>
        #                 </td>
        #               </tr>
        #               <tr>
        #                 <td align="center">
                            
        #                 </td>
        #               </tr>
        #             </tbody>
        #         </table>""" % (self.name, 'scio.tjacdmx.gob.mx', self.id)

        # correo = self.env['mail.mail'].create({
        #     'subject': self.name,
        #     'email_from':'<odoogrp@tjacdmx.gob.mx>',
        #     'autor_id': 1,
        #     'email_to':'<'+self.create_uid.login+'>',
        #     'body_html': html,
        # })
        # correo.send()
        

    
    def action_comprometer(self):
        permisos.PermisosManager(self.env,self.env.uid).getPermiss('req_comprometer')
       
        for linea in self.lineas_compromisos:                     
            if(linea.state == 'received'):
                linea.action_comprometer()

        self.update({'state': 'comprometido'})

    
    def action_regresar(self):
        permisos.PermisosManager(self.env,self.env.uid).getPermiss('req_regresar_borrador')
        
        self.update({'state':'draft',
                    'fecha_recibido':''})
        for linea in self.lineas_compromisos:                     
            linea.unlink() 

    
    def action_rechazar(self):
        permisos.PermisosManager(self.env,self.env.uid).getPermiss('req_reversar')
        
        for compromiso in self.lineas_compromisos:
            if(compromiso.state == 'comprometido'):
                raise ValidationError("No se puede revertir una requisión con asientos comprometidos.")
        
        self.update({'state':'send',
                    'fecha_recibido':''})
        
    @api.model
    def _get_fecha(self):
        return self.fecha
    
    
    def unlink(self):
        if(self.state!='draft'):
            raise ValidationError("No se puede eliminar una requisición enviada.")
        if(self.lineas_compromisos):
            raise ValidationError("No se puede eliminar una requisión con asientos comprometidos.")
        
        
        #if(self.requisicion_compra):
            #raise ValidationError("No se puede eliminar un compromiso de una requisicion activa")

        return models.Model.unlink(self)
    
    
    def print_req(self):
        return self.env['report'].get_action(self, 'reportes.requisicion_compras')
   

    # 
    # @api.depends('solicitante')
    # def _getAreaSolicitante(self):
    #     for rec in self:
    #         if rec.solicitante:
    #             rec.cargo_solicitante =  rec.solicitante.puesto + '\n' + rec.solicitante.departamento
    
    # 
    # @api.depends('elaboro')
    # def _getAreaElaboro(self):
    #     for rec in self:
    #         if rec.elaboro:
    #             rec.cargo_elaboro =  rec.elaboro.puesto + '\n' + rec.elaboro.departamento
    
    # 
    # @api.depends('reviso')
    # def _getAreaReviso(self):
    #     for rec in self:
    #         if rec.reviso:
    #             rec.cargo_reviso =  rec.reviso.puesto + '\n' + rec.reviso.departamento
    
    # 
    # @api.depends('autorizo')
    # def _getAreaAutorizo(self):
    #     for rec in self:
    #         if rec.autorizo:
    #             rec.cargo_autorizo =  rec.autorizo.puesto + '\n' + rec.autorizo.departamento
        


class PresupuestoRequisicionComprasLine(models.Model):
    _name = 'presupuesto.requisicion.compras.line'
    _description = u'Requisición compras lineas v2'

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

    requisicion_compra = fields.Integer(string='requisicion_compra')
    
    
    def default_unitario(self):       
        if(self.env.context.get("tipo")=='anual'):
            lineas = self.env.context.get("lineas_requisicion_compras")
            
            if(len(lineas) > 0 ):
                if(lineas[len(lineas)-1][0] != 0):
                    ultima_linea = self.env['presupuesto.requisicion.compras.line'].search([('id','=',lineas[len(lineas)-1][1])])
                    return ultima_linea.precio_unitario
                else:
                    ultima_linea = lineas[len(lineas)-1][2]
                    return ultima_linea['precio_unitario']
            else:
                return 0 
        else:
            return 0

    precio_unitario =  fields.Float(select="Unitario", default=default_unitario, digits=dp.get_precision('Product Price'))
    cantidad =  fields.Integer(select="Cantidad", default=1)
    
    def default_unidad(self):       
        if(self.env.context.get("tipo")=='anual'):
            lineas = self.env.context.get("lineas_requisicion_compras")
            if(len(lineas) > 0 ):
                if(lineas[len(lineas)-1][0] != 0):
                    ultima_linea = self.env['presupuesto.requisicion.compras.line'].search([('id','=',lineas[len(lineas)-1][1])])
                    return ultima_linea.unidad
                else:
                    ultima_linea = lineas[len(lineas)-1][2]
                    return ultima_linea['unidad']
            else:
                return 30
        
    unidad =  fields.Many2one('product.uom', default=default_unidad, string="Unidad de medida", options="{'no_create': True, 'no_create_edit':True")
    importe =  fields.Float(select="Importe")

    
    def default_fecha(self):       
        if(self.env.context.get("tipo")=='anual'):
            lineas = self.env.context.get("lineas_requisicion_compras")
            if(len(lineas) > 0 ):
                
                if(lineas[len(lineas)-1][0] != 0):
                    ultima_linea = self.env['presupuesto.requisicion.compras.line'].search([('id','=',lineas[len(lineas)-1][1])])
                    date = datetime.strptime(ultima_linea.fecha, "%Y-%m-%d")
                else:
                    ultima_linea = lineas[len(lineas)-1][2]
                    date = datetime.strptime(ultima_linea['fecha'], "%Y-%m-%d")
                
                
                if(date.month <12):
                    mes_ante = date.month+1 
                else:
                    mes_ante = 1

                if (mes_ante < 10):
                    mes = "0"+str(mes_ante)
                else:
                    mes = str(mes_ante)

                return str(date.year)+"-"+mes+"-01"
            else:
                return self.env.context.get("fecha")
        else:
            return self.env.context.get("fecha")

            
    fecha = fields.Date(string='Fecha', default=default_fecha)

    
    def default_descripcion(self):
        if(self.env.context.get("tipo")=='anual'):
            return self.env.context.get("descripcion")

    descripcion=fields.Char(strig='Descripcion', default=default_descripcion)
    
    

    
    @api.onchange('fecha')
    
    def onchange_fecha(self):
        if(self.fecha):
            date = datetime.strptime(self.fecha, "%Y-%m-%d")
            self.periodo = date.month
    
    @api.onchange('precio_unitario')
    
    def onchange_precio_unitario(self):
        self.update_importe()
    
    @api.onchange('cantidad')
    
    def onchange_cantidad(self):
        self.update_importe()

    
    def update_importe(self):
        self.importe = self.precio_unitario*self.cantidad
        self.update({'importe':self.precio_unitario*self.cantidad})

class PresupuestoRequisicionComprasCompromisosLine(models.Model):
    _name = 'presupuesto.requisicion.compras.compromisos.line'
    _description = u'Requisición compromisos'
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
    importe =  fields.Float(select="Importe")
    state = fields.Selection([('draft','Borrador'),
                            ('send','Enviado'),
                            ('received','Con suficiecia presupuestal'),
                            ('comprometido','Comprometido'),
                            ('devengado','Devengado'),
                            ('cancel','Cancelado')],
                            default="draft")

    fondo_economico = fields.Many2one('presupuesto.fondo_economico', string='Fondo',required=True,readonly=1,  default=get_fondo)
    centro_gestor = fields.Many2one('presupuesto.centro_gestor', string='Centro gestor',required=True,readonly=1, default=get_centro_g)
    area_funcional = fields.Many2one('presupuesto.area_funcional',string='Área funcional', required=True, default=get_area_funci)

    requisicion_compra = fields.Many2one('presupuesto.requisicion.compras', string='Requisición')

    documento = fields.Many2one('presupuesto.documento', string='Documento', required=False)
    asiento = fields.Many2one('account.move', string='Asiento', required=False)
    
    line_asientos_contables = fields.One2many('account.move', string='Asientos contables', compute="_computed_asientos")
    
    invisible_comprometer =  fields.Boolean(compute='_compute_visible')
    invisible_cancelar =  fields.Boolean(compute='_compute_visible')

    remisiones_count = fields.Integer(compute="_compute_remisiones", string=' ',default=0)
    facturas_count = fields.Integer(compute="_compute_facturas", string=' ',copy=False, default=0)


    def _compute_remisiones(self):
        remisiones = self.env['tjacdmx.remisiones'].search([('origin','=',self.id)])
        self.remisiones_count = len(remisiones)

    
    def _compute_facturas(self):
        facturas = self.env['account.invoice'].search([('requicision','=',self.id)])
        self.facturas_count = len(facturas)

    
    def new_remision(self):
        action = self.env.ref('presupuestos.action_remiciones')
        res = self.env.ref('presupuestos.action_tjacdmx_remisiones_form', False)
        result = res.read()[0]
        result['context'] = {}
        result['context']['requisicion_id'] = int(self.id)
        result['context']['name_requi'] = str(self.name)
        result['context']['requicision'] = str(self.id)
        return result



    
    def new_factura(self):
        action = self.env.ref('presupuestos.action_facturas')
        res = self.env.ref('presupuestos.action_facturas_form', False)
        search_remis_active = self.env['account.invoice'].search([('requicision','=',self.id)], limit=1)
        if (search_remis_active):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('requicision','=', %s)]" % (self.id)
        else:
            result = res.read()[0]
            result['context'] = {}
            result['context']['default_id_purchase'] = self.id
            result['context']['name_requi'] = str(self.numero)
            result['context']['origin'] = str(self.id)
            result['context']['requicision'] = str(self.id)
            result['context']['reference_provedor'] = str(self.numero)
            result['context']['account_id'] = 248
            result['context']['state'] = 'draft'
            result['context']['type'] ='in_invoice'
            result['context']['journal_id'] = 2
        return result


    
    def list_remision(self):
        action = self.env.ref('presupuestos.action_remiciones')
        res = self.env.ref('presupuestos.action_tjacdmx_remisiones_form', False)
        search_remis_active = self.env['tjacdmx.remisiones'].search([('origin','=',self.id)], limit=1)
        if (search_remis_active):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('origin','=', %s)]" % (self.id)
        else:
            result = res.read()[0]
            result['context'] = {}
            result['context']['requicision_id'] = self.id
            result['context']['name_requi'] = str(self.name)
        return result
    
    
    def _compute_visible(self):
        self.invisible_comprometer = permisos.PermisosManager(self.env,self.env.uid).getVisible('req_comprometer')
        self.invisible_cancelar = permisos.PermisosManager(self.env,self.env.uid).getVisible('req_cancelar_compromiso')
        

    
    def _computed_asientos(self):
        #doc = self.env['presupuesto.documento'].search([('concepto','=',self.name)])
        self.line_asientos_contables = self.env['account.move'].search([('ref','=',self.name)])

    area = fields.Char(string="Área")
    partida = fields.Char(string="Partida")
    descripcion = fields.Char(string=u"Descripción")

    compras = fields.One2many('purchase.order','compromiso', string='compras')
    compras_count = fields.Integer(compute="_compute_compras", string='Compras', copy=False, default=0)
    def _compute_compras(self):
        self.compras_count = len(self.compras)

    
    def action_crear_sp(self):
        lineas_sp = []
        facturas = self.env['account.invoice'].search([('requicision','=',self.id)])
        for each in facturas:
            total=0
            if(each.invoice_line_ids):
                partida_p=self.env['presupuesto.partida_presupuestal'].search([('partida_presupuestal','=',self.partida)])
                lineas_sp.append({
                                'proveedor': each.remision.partner_id.id,
                                'fecha': each.date_due,
                                'importe': each.amount_total,
                                'partida': partida_p.id,
                                'descripcion': each.invoice_line_ids[0].name,
                                'factura': each.reference_provedor,
                                'adjudicacion': '',
                                'compromiso': self.id,
                                })
                
            

        return {
                    'name': _("Crear compra"),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'presupuesto.solicitud.pago',
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                    'context': {
                        'origen': True,
                        'requi_id': self.id,
                        'lineas_solicitud_pago':lineas_sp
                        }
                } 

    
    def action_comprometer(self):
        permisos.PermisosManager(self.env,self.env.uid).getPermiss('req_comprometer')            
        ctrl_periodo = self.env['control.periodos.wizard']
        if(not ctrl_periodo.get_is_cerrado(self.fecha)):
            obj_documento = self.env['presupuesto.documento']
            fecha_orden = datetime.strptime(self.fecha, '%Y-%m-%d')
            ejercicio = fecha_orden.year
            periodo = fecha_orden.month
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','COMPROMETIDO')], limit=1)
            
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
                'state':'comprometido'
            })
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    
    
    def action_crear_compra(self):
        search_purchase_active = self.env['purchase.order'].search([('compromiso','=',self.id)], limit=1)
        if (search_purchase_active):
            action = self.env.ref('presupuestos.action_presupuesto_compras_tree')
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('compromiso','=', %s)]" % (self.id)
            result['context']['default_type_purchacee'] = 'compra'
            result['context']['default_compromiso'] = self.id
            result['context']['default_date_order'] = self.fecha
        else:
            res = self.env.ref('presupuestos.action_presupuesto_compras')
            result = res.read()[0]
            result['context'] = {}
            result['context']['default_type_purchacee'] = 'compra'
            result['context']['default_compromiso'] = self.id
            result['context']['default_date_order'] = self.fecha
            # result['views'] = [(res and res.id or False, 'form')]
        return result
    

    
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
                'default_ref_compra': self.name}
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
        

        if(self.state == 'comprometido'):
            raise ValidationError("No se puede rechazar una requisión con asientos comprometidos.")
        
        if(self.env['presupuesto.solicitud.pago.line'].search([('compromiso','=',self.id)])):
            raise ValidationError("No se puede eliminar un compromiso que se ha asignado una Solicitud de pago.")

        if(self.env['purchase.order'].search([('compromiso','=',self.id)])):
            raise ValidationError("No se puede modificar un compromiso que se ha asignado una Compra.")
       
        #if(self.requisicion_compra):
            #raise ValidationError("No se puede eliminar un compromiso de una requisicion activa")

        return models.Model.unlink(self)
