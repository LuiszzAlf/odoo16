# -*- coding: UTF-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime

class PresupuestoSalidaActivos(models.Model):
    _name = 'presupuesto.salida_activos'
    _rec_name = 'account_salida'

    account_salida = fields.Many2one('account.asset.asset', string='Activo fijo', required=True, domain=[('state', '!=', 'close')])
    date_salida = fields.Date(string='Fecha de salida', required=True)
    descripcion = fields.Text(string='Descripcion')


    @api.model
    def create(self, values):
        record = super(PresupuestoSalidaActivos, self).create(values)
        activo = values['account_salida']
        account_move = self.env['account.move']
        # raise ValidationError("%s" % (activo))
        line_ids=[]
        poliza = account_move.create({
                    'journal_id': 80,
                    'date': record.fecha_contabilizacion,
                    'ref': 'Baja de activo ',
                    'documento_id':record.id,
                    'narration':False,
                    'line_ids':line_ids,
                    'compra_id':''
                })
        poliza.post()
        update_asset = "UPDATE account_asset_asset SET state='close' WHERE id=%s" % (activo)
        self.env.cr.execute(update_asset)
        self.env.cr.commit()
        return record
        
