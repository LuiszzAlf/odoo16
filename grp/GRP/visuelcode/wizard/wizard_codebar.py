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
import barcode
from barcode.writer import ImageWriter

barcode.PROVIDED_BARCODES

class CodeBar(models.TransientModel):
    _name = 'wizard.codebar'

    @api.model
    def _get_activo(self):
        context = dict(self._context or {})
        activo = context.get('activo', False)
        if activo:
            data = activo
            return data
        return ''
    @api.model
    def _get_no_inventario(self):
        context = dict(self._context or {})
        no_inventario = context.get('no_inventario', False)
        if no_inventario:
            data = no_inventario
            return data
        return ''
    @api.model
    def _get_codebar(self):
        context = dict(self._context or {})
        codebar_num = context.get('codebar_num', False)
        if codebar_num:
            data = codebar_num
            return data
        return ''

    @api.model
    def _get_codebar_img(self):
        context = dict(self._context or {})
        codebar_num = context.get('codebar_num', False)
        if codebar_num:
            data = codebar_num
            EAN = barcode.get_barcode_class('code128')
            ean = EAN(data, writer=ImageWriter())
            fullname = ean.save('/home/addons/GRP/temp/temp')
            with open(fullname, "rb") as imageFile:
                str_ime = base64.b64encode(imageFile.read())
            return str_ime
        return ''


    activo=fields.Char(default=_get_activo,readonly=True)
    no_inventario=fields.Char(default=_get_no_inventario,readonly=True)
    code_bar=fields.Char(default=_get_codebar,readonly=True)
    base64png = fields.Char(default=_get_codebar_img,readonly=True)

    