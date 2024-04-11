# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from num2words import num2words

class documentacion(models.Model):
    _name = 'tjacdmx.documentacion'
    _rec_name = 'number'
    _inherit = ['mail.thread']

    @api.model
    def _default_number(self):
        fecha = datetime.today()
        num_sm=self.env['tjacdmx.documentacion'].search([], order='number DESC', limit=1)
        if(num_sm):
            numero=num_sm.number.split('/')[2]
        else:
            numero=0
        identifi=int(numero)+1
        consecutivo = str(identifi).rjust(4, '0')
        number_char="""DOC/%s/%s""" % (str(fecha.year),consecutivo)
        return number_char
        
    number = fields.Char(default=_default_number)
    descripcion = fields.Char(string=u'Descripción')
    tipo = fields.Selection([
        ('adjudicacion_directa','Adjudicación directa'),
        ('invitacion_proveedores','Invitación a cuando menos tres proveedores'),
        ('licitacion_publica','Licitación Pública')],required=True)
    fecha = fields.Date(string='Fecha', default=datetime.today())
    documentacion_line= fields.One2many('tjacdmx.documentacion.line', 'documento_id', string='Documentos Lines',copy=True)
    req_count = fields.Integer(compute="_compute_req", string=' ',default=0)

    def _compute_req(self):
        requis=self.env['presupuesto.requisicion.compras'].search([('documentacion','=', self.id)])
        self.req_count = len(requis)

    
    def list_requis(self):
        action = self.env.ref('presupuestos.action_requis')
        requis=self.env['presupuesto.requisicion.compras'].search([('documentacion','=', self.id)])
        if (requis):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('documentacion','=', %s)]" % (self.id)
        else:
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('documentacion','=', '')]"

        return result

    @api.onchange('tipo')
    def change_tipo(self):
        default_values=[]
        documentos=self.env['tjacdmx.documentos'].search([('tipo', '=', self.tipo)])
        for doc in documentos:
            elem=(0, 0, {'documento_id': self.id, 'documento': doc.id})
            default_values.append(elem)
        self.documentacion_line=default_values


class RemisionesLine(models.Model):
    _name = "tjacdmx.documentacion.line"
    _description = "Documentacion Line"
    _order = 'id'

    documento_id = fields.Many2one('tjacdmx.documentacion', string='Reference', index=True)
    documento = fields.Many2one('tjacdmx.documentos', string='Documento')
    archivo = fields.Binary(string='Archivo')
    archivo_html = fields.Html(string='Archivo Binario (HTML)')

    
    
    def open_pdf_viewer(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        pdf_url = base_url + '/web/image?model=tjacdmx.documentacion.line&id=' + str(self.id) + '&field=archivo'
        return {
           'type': 'ir.actions.act_url',
            'url': pdf_url,
            'target': 'new',
        }


class documentos(models.Model):
    _name = 'tjacdmx.documentos'
    _rec_name = 'name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Nombre')
    tipo= fields.Selection([
        ('adjudicacion_directa','Adjudicación directa'),
        ('invitacion_proveedores','Invitación a cuando menos tres proveedores'),
        ('licitacion_publica','Licitación Pública')],required=True)