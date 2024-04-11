# -*- coding: UTF-8 -*-
from odoo import api, fields, models

class log_resguardo_lineas(models.Model):
    _name = 'tjacdmx.log_resguardo_lineas'
    resguardo_id = fields.Integer(string='resguardo')
    id_activo = fields.Many2one('account.asset.asset',string='Nombre de activo')
    status=fields.Char(string='Status',default='draft')
    tipo_mov=fields.Char(string='Tipo de movimiento',default='Asignacion')
    comment_activo = fields.Text(string="Comentario")
    comentarios = fields.Text(string="comentarios", compute="_def_tooltip")

    def _def_tooltip(self):
        self.comentarios = self.comment_activo if self.comment_activo else 'Sin comentarios'
