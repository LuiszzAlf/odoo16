# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from num2words import num2words

class clc_model(models.Model):
    _name = 'presupuesto.clc'
    _rec_name = 'no_clc'
    _inherit = ['mail.thread']



    @api.model
    def _default_proveedor(self):
        if self._context.get('default_proveedor_c', False):
            return self.env['res.partner'].browse(self._context.get('default_proveedor_c'))

    @api.model
    def _default_factura(self):
        if self._context.get('default_proveedor_c_id_fac', False):
            return self.env['account.invoice'].browse(self._context.get('default_proveedor_c_id_fac'))


    id_factura = fields.Integer(string='ID_Factura',default=_default_factura)
    proveedor = fields.Many2one('res.partner', string='Proveedor',required=True, default=_default_proveedor)
    rfc = fields.Char(string='RFC', readonly=False)
    fecha_expedicion = fields.Date(string='Fecha de Expedición', readonly=False, default=datetime.today())
    banco = fields.Char(string='Banco', readonly=False)
    no_cuenta = fields.Char(string='No Cuenta', readonly=False)
    no_poliza = fields.Char(string='No Poliza', readonly=False)
    no_clc = fields.Char(string='No CLC', readonly=False)
    clave_presu = fields.Char(string='Clave presupuestaria', readonly=False)



    
    @api.onchange('proveedor')
    def _onchange_empleado(self):
        self.update({'rfc': self.proveedor.vat})
        # self.update({'banco': self.proveedor.banco})
        # self.update({'no_cuenta': self.proveedor.cuenta_banco})
    

    @api.model
    def create(self,values):
        record = super(clc_model, self).create(values)
        invoice = self.env['account.invoice'].search([('id', '=', record.id_factura)])
        am = self.env['account.move'].search([('name', '=', invoice.number)])
        aml = self.env['account.move.line'].search([('move_id', '=', am.id)])
        am.write({'ref': record.no_clc})
        for line in aml:
            line.write({'ref': record.no_clc})
        return record
    
    
    def write(self, values):
        record = super(clc_model, self).write(values)
        invoice = self.env['account.invoice'].search([('id', '=', self.id_factura)])
        am = self.env['account.move'].search([('name', '=', invoice.number)])
        aml = self.env['account.move.line'].search([('move_id', '=', am.id)])
        am.write({'ref': self.no_clc})
        for line in aml:
            line.write({'ref': self.no_clc})
        return record


    
        
        
