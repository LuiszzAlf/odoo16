# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from num2words import num2words


MOMENTOS= [
    ('COMPROMETIDO','Comprometido'),
    ('DEVENGADO','Devengado'),
    ('EJERCIDO','Ejercido'),
    ('PAGADO','Pagado')]

class PresupuestoMomentos(models.Model):
    _name = 'presupuesto.momentos.presupuestales'

    id_momento=fields.Integer(string='ID momento')
    momento=fields.Selection([('COMPROMETIDO','Comprometido'),('DEVENGADO','Devengado'),('EJERCIDO','Ejercido'),('PAGADO','Pagado')],required=True)
    status=fields.Selection([('open','Abierto'),('close','Cerrado')],required=True)
    

class PresupuestoPermisos(models.Model):
    _name = 'presupuesto.permisos.presupuestales'
    _rec_name='usuario_id'
    usuario_id=fields.Many2one(comodel_name='res.users', string='Usuario',required=True)
    comprometido=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    devengado=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    ejercido=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    pagado=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    cancelar_compra=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    cancelar_devengado=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    cancelar_ejercido_presupuestal=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    cancelar_pago_presupuestal=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    registro_cancelaciones=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    validar_factura_presupuestal=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    validar_factura_contable=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    control_periodos=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    nomina_get=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    nomina_post=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    nomina_pago_presu=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')
    nomina_pago_contable=fields.Selection([('open','Abierto'),('close','Cerrado')],default='close')

    
    # Requisiciones V2
    req_enviar=fields.Boolean(default=False)
    req_regresar_borrador=fields.Boolean(default=False)
    req_aprobar=fields.Boolean(default=False)
    req_reversar=fields.Boolean(default=False)
    req_comprometer=fields.Boolean(default=False)
    req_devengar=fields.Boolean(default=False)
    req_cancelar_compromiso=fields.Boolean(default=False)

    # Solicitudes de pago
    sp_enviar=fields.Boolean(default=False)
    sp_regresar_borrador=fields.Boolean(default=False)
    sp_recibir=fields.Boolean(default=False)
    sp_reversar=fields.Boolean(default=False)
    sp_devengar=fields.Boolean(default=False)
    sp_cancelar_devengado = fields.Boolean(default=False)

    # Solicitud de suministro
    ss_crear=fields.Boolean(default=False, string="Crear SS")
    ss_entregar=fields.Boolean(default=False, string="Entregar SS")
    ss_salida=fields.Boolean(default=False, string="Realizar salida de stock SS")


    # Admin usuarios
    # area = fields.Many2one(comodel_name='presupuesto.areas.stok', string='Área')
    is_titular_area = fields.Boolean(default=False, string="Es titular")
    titular_area = fields.Many2one(comodel_name='res.users', string='Titular de área')
    empleado = fields.Many2one(comodel_name='tjacdmx.resguardantes', string='Empleado')
    


    momentos_presupuestales = fields.One2many('presupuesto.momentos.presupuestales', 'id_momento', string='Permisos')


    @api.model
    def create(self,values):
        result = super(PresupuestoPermisos, self).create(values)
        usuario = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',values['usuario_id'])])
        if(len(usuario)>=2):
            raise ValidationError("Ya existe un registro con este usuario")
        return result

class DocumentoManager():
    usr_id = None
    env = None 

    def __init__(self, env=None,  usr_id=-1):
        self.usr_id = usr_id
        self.env = env

    def getUserId(self):
        return self.usr_id


    def deleteDocComprometidoById(self, id_documento):
        ctrl_periodo = self.env['control.periodos.wizard']
        
        permiss = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',self.usr_id)])

        if(permiss.registro_cancelaciones == 'close'):
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")  

        documento=self.env['presupuesto.documento'].search([('id', '=',id_documento)],limit=1)

        if(documento):
            if(documento.clase_documento.tipo_documento == 'COMPROMETIDO'):
                if(not ctrl_periodo.get_is_cerrado(documento.fecha_documento)):
                
                    if(len(documento.detalle_documento_ids) > 1):
                        raise ValidationError("Este documento contiene más de una linea id_doc: %s" % id_documento)  

                    asiento_contable=self.env['account.move'].search([('documento_id', '=', documento.id)],limit=1)
                    documento_id= documento.id if documento.id else 0
                    asiento_contable_id= asiento_contable.id if asiento_contable.id else 0
                    
                    partida = 0
                    importe = 0
                    for detalle_doc in documento.detalle_documento_ids:
                        partida = detalle_doc.posicion_presupuestaria.id
                        importe = importe + detalle_doc.importe
                    
                    posicion_presupuestaria = partida
                    
                    cp = self.env['presupuesto.control_presupuesto'].search([
                    ('version', '=', documento.version.id),
                    ('ejercicio', '=', documento.ejercicio),
                    ('periodo', '=', documento.periodo),
                    ('posicion_presupuestaria', '=', posicion_presupuestaria)])
                    
                    cp.write({ 'egreso_comprometido': cp.egreso_comprometido - importe })
                    
                    query1 = "DELETE FROM presupuesto_detalle_documento WHERE documento_id=%s" % (documento_id)
                    query2 = "DELETE FROM presupuesto_documento WHERE id=%s" % (documento_id)
                    query3 = "DELETE FROM account_move_line WHERE move_id=%s" % (asiento_contable_id)
                    query4 = "DELETE FROM account_move WHERE id=%s" % (asiento_contable_id)
                
                    # query2 = "UPDATE presupuesto_documento SET status = 'close' WHERE id=%s" % (documento_id)
                    # query4 = "UPDATE account_move SET state = 'draft' WHERE id=%s" % (asiento_contable_id)
                    
                    self.env.cr.execute(query1)
                    self.env.cr.execute(query2)
                    self.env.cr.execute(query3)
                    self.env.cr.execute(query4)
            else:
                raise ValidationError("El documento no es de tipo Comprometido id_cocumento: %s" % (id_documento) )
        else:
            raise ValidationError("No se encuentra el id del documento %s" % (id_documento) )
    
            
class PermisosManager():
    usr_id = None
    env = None 

    def __init__(self, env=None,  usr_id=-1):
        self.usr_id = usr_id
        self.env = env

    def getUserId(self):
        return self.usr_id

    def getModel(self):
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',self.usr_id)])
        return  permisos[0]
    
    #Si es True o False
    def getPermiss(self, campo):
        permiss = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',self.usr_id),(campo,'=',True)])
        if(not permiss):
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")  

    def getVisible(self, campo):
        permiss = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',self.usr_id),(campo,'=',True)])
        if(permiss):
            return True
        else:
            return False
    
    # Si es Open o Close
    def getPermissStatus(self, campo):
        permiss = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',self.usr_id),(campo,'=','open')])
        if(not permiss):
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    def getVisibleStatus(self, campo):
        permiss = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',self.usr_id),(campo,'=','open')])
        if(permiss):
            return True
        else:
            return False