# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero

class InventarioInformatica(models.Model):
    _name = 'tjacdmax.inventario.informatica'
    _description = 'Inventario'
    _rec_name = 'activo'
    _inherit = ['mail.thread'] 

    activo=fields.Many2one('tjacdmax.activo.informatica',string='Activo')



class ActivoInformatica(models.Model):
    _name = 'tjacdmax.activo.informatica'
    _description = 'Activos Informatica'
    _rec_name = 'nombre'

    nombre= fields.Char(string='Nombre')
    detalle_archivo = fields.One2many('tjacdmax.activo.informatica.detalle', 'activo_id', string="Perifericos")



class ActivoDetalleInformatica(models.Model):
    _name = 'tjacdmax.activo.informatica.detalle'
    _description = 'Detalle de activo'
    _rec_name = 'nombre'

    activo_id=fields.Many2one('tjacdmax.activo.informatica',string='Activo')
    nombre= fields.Char(string='Periferico')

    
