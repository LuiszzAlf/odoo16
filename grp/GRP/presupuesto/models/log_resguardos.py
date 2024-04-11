# -*- coding: UTF-8 -*-
from odoo import api, fields, models

class log_resguardos(models.Model):
    _name = 'tjacdmx.log_resguardos'
    _rec_name = 'nombre_empleado'

    no_empleado = fields.Char(string='Numero de empleado')
    id_empleado=fields.Integer(string='ID empleado')
    nombre_empleado = fields.Char(string='Nombre de empleado')
    puesto=fields.Char(string='Puesto')
    departamento = fields.Char(string='Departamento')
    area = fields.Char(string='Area')
    ubicacion = fields.Char(string='Ubicación')
    status = fields.Char(string='status')
    lineas_resguardo = fields.One2many('tjacdmx.log_resguardo_lineas', 'resguardo_id', string='Lineas resguardo', copy=True)
    folio = fields.Char(string="Folio")
    _status = fields.Char(compute="_put_status", string="status")

    def _put_status(self):
        self._status = 'Activo' if self.status == '1' else 'Inactivo'
