# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import base64 
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]
MOVE_SELECT = [('all','Todo'),('move_exist','Con movimientos')]


class wizard_suministros(models.TransientModel):
    _name = 'wizard.suministros'

    fecha_inicio = fields.Date(string='Fecha inicio',required=True)
    fecha_fin = fields.Date(string='Fecha fin',required=True)
    fecha_inicio_cal = fields.Date(string='Fecha inicio cla',compute='_onchange_date_cal')
    fecha_fin_cal = fields.Date(string='Fecha fin cal', compute='_onchange_date_cal')

    
    @api.multi
    @api.onchange('fecha_inicio')
    def _onchange_date(self):
        date_fin=self.fecha_inicio
        self.update({'fecha_fin': date_fin})
    
    @api.multi
    @api.onchange('fecha_inicio','fecha_fin')
    def _onchange_date_cal(self):
        self.fecha_inicio_cal=self.fecha_inicio
        self.fecha_fin_cal=self.fecha_fin




       