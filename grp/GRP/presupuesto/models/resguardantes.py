# -*- coding: UTF-8 -*-
from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError

class resguardantes(models.Model):
    _name = 'tjacdmx.resguardantes'
    _rec_name = 'num_empleado'
    _rec_name='nombre'
    
    num_empleado = fields.Integer(string='Numero de empleado')
    nombre = fields.Char(string='Nombre')
    puesto = fields.Char(string='Puesto')
    departamento=fields.Char(string='Departamento')
    area = fields.Char(string='Area')
    ubicacion = fields.Char(string='Ubicación')
    activo = fields.Char(string='status')
    edificio = fields.Char(string='Edificio')
    piso =fields.Char(string='Piso')
    resguardo =fields.Integer(string='resguardo',default=0)
    correo =fields.Char(string='correo')

    @api.model
    def create(self,values):
        record = super(resguardantes, self).create(values)
        return record 

    # activos_count = fields.Integer(compute='count_activos', string='Numero de activos')



    # @api.multi
    # def count_activos(self):
    #     ActivosResguardo = self.env['tjacdmx.resguardo_lineas'].search([('no_empleado', '=', self.num_empleado)])
    #     numeros=len(ActivosResguardo)
    #     raise ValidationError("Debug: %s" % (numeros))
    #     return numeros

class formato_movimiento(models.Model):
    _name = 'tjacdmx.formato.movimiento'
    
    num_empleado = fields.Integer(string='Numero de empleado')
    num_movimiento = fields.Integer(string='Numero de movimiento')
    formato = fields.Text(string='Puesto')
  

    

    

    
    
