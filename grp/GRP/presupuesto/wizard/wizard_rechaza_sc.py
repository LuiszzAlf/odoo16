# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from num2words import num2words
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class rechaza_solicitud_compra(models.TransientModel):
    _name = 'rechaza_solicitud_compra.wizard'

    @api.model
    def _get_sc(self):
        context = dict(self._context or {})
        solicitud_compra = context.get('solicitud_compra', False)
        if solicitud_compra:
            data = solicitud_compra
            return data
        return ''
        
    sc_id=fields.Integer(default=_get_sc,readonly=True)
    comentarios=fields.Char(string='Comentarios',required=True)


    @api.multi
    def rechaza(self):
        solicitud_compra = self.env['tjacdmx.solicitud.compra.materiales'].search([('id','=',self.sc_id)])
        solicitud_compra.write({'state': 'cancel'}) 
        solicitud_compra.write({'observaciones': self.comentarios}) 
        # raise ValidationError("%s" % (solicitud_compra))

    