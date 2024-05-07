# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

EJERCICIO_SELECT = [ (str(year), str(year)) for year in range(2018, 2031) ]
PERIODO_SELECT = [(str(periodo), str(periodo)) for periodo in range(1,13)]
TIPO_UP = [('1', 'Periodo'),('2','Partida')]
STATUS = [('1', 'Abierto'),('2','Cerrado')]

class ControlPeriodos(models.TransientModel):
    _name = 'control.periodos.wizard'

    tipo_up = fields.Selection(TIPO_UP, required=True, default='1')
    
    ejercicio = fields.Selection(EJERCICIO_SELECT, required=True)
    periodo = fields.Selection(PERIODO_SELECT, required=True)
    version = fields.Many2one('presupuesto.version', string='Version', required=True)
    partida_presupuestal = fields.Many2one('presupuesto.partida_presupuestal', string='Posición presupuestaria')

    status = fields.Selection(STATUS, required=True, default='1')

    
    def search_periodo(self):
        search_periodos = self.env['presupuesto.control_presupuesto'].search([
            ('version', '=', self.version.version),
            ('ejercicio', '=', self.ejercicio),
            ('periodo', '=', self.periodo)])
        
        if self.status=='1':
            status='open'
        else:
            status='close'
        indice = 0
        while indice < len(search_periodos):
            ids_cp=(search_periodos[indice][0])
            #raise ValidationError("Debug %s" % (ids_cp.id))
            update_status_cp = "update presupuesto_control_presupuesto set status='%s' where id=%s" % (status,ids_cp.id) 
            self.env.cr.execute(update_status_cp)
            indice += 1
            self.env.cr.commit()
        #raise ValidationError("Partidas actualizadas  %s" % (indice))
       


    
    def search_periodo_partida(self):
        search_periodos = self.env['presupuesto.control_presupuesto'].search([
            ('version', '=', self.version.version),
            ('ejercicio', '=', self.ejercicio),
            ('periodo', '=', self.periodo),
            ('posicion_presupuestaria', '=', self.partida_presupuestal.id)], limit=1)
        if self.status=='1':
            status='open'
        else:
            status='close'
        partida_up=search_periodos.posicion_presupuestaria.partida_presupuestal
        id_up=search_periodos.id
        update_status_cp = "update presupuesto_control_presupuesto set status='%s' where id=%s" % (status,id_up) 
        self.env.cr.execute(update_status_cp)
        self.env.cr.commit()
        #raise ValidationError("Partida %s actualizada  %s" % (partida_up,id_up))


    
    def get_is_cerrado(self, fecha):

        fecha = str(fecha)
        fecha = fecha[:10]
        
        status = False

        periodo = datetime.strptime(fecha, '%Y-%m-%d').month
        ejercicio = datetime.strptime(fecha, '%Y-%m-%d').year

        search_periodos = self.env['presupuesto.control_presupuesto'].search([
            ('ejercicio', '=', ejercicio),
            ('periodo', '=', periodo)], limit=1)

        
        if search_periodos.status == 'open':
            status = False
        else:
            status = True
            raise ValidationError("El periodo %s/%s ya ha sido cerrado presupuestalmente.\n \
                 Por favor verifique la fecha."  % (str(periodo),str(ejercicio)) )
            
        return status
        





