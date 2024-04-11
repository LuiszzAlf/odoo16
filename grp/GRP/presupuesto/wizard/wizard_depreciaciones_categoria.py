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


class ReportDepre(models.TransientModel):
    _name = 'depreciaciones_categoria.wizard'

    @api.model
    def get_categs(self):
        return self.env['account.asset.category'].search([('id', 'in', ['54','43','45','47','50','52','40','49','51','41','44','39','46','37','56','42','38','48','53'])]).ids
    tipo=fields.Selection([(1,'Depreciaciones por categoria'),(2,'Lista de depreciaciones de activos')], string='Reporte', default=1)
    fecha_fin = fields.Date(string='Fecha de corte',default=datetime.today())
    categorias = fields.Many2many('account.asset.category',default=get_categs,string='Categorias')
    result_pc_html=fields.Html(string='Resultados',compute='search_pc_button_va')
    csv_urls = fields.Char(compute='search_pc_button_va')

    tipo_cal = fields.Char(string='Tipo',compute='_onchange_date_cal')
    fecha_fin_cal = fields.Char(string='Fecha de corte',compute='_onchange_date_cal')
    categorias_cal = fields.Char(string='Categorias cal',compute='_onchange_date_cal')

    @api.multi
    @api.onchange('tipo','fecha_fin','categorias')
    def _onchange_date_cal(self):
        self.tipo_cal=self.tipo
        self.fecha_fin_cal=self.fecha_fin
        ids_categ=[]
        for cat in self.categorias:
            ids_categ.append(cat.id)
        cats=str(ids_categ).replace(']', '').replace('[', '')
        self.categorias_cal=cats


       







