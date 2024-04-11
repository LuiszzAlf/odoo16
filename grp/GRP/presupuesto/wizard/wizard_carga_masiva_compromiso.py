# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import base64 
import csv
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta

STATEFILE = [('success','Valido'),('error','Con errores')]

class CargaMasivaCompromiso(models.TransientModel):
    _name = 'carga_masiva_compromiso.wizard'

    state_file = fields.Selection(STATEFILE,default='error')
    file = fields.Binary(string='Archivo')

       