# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero

class ActivosNoCapitalizables(models.Model):
    _name = 'tjacdmax.activos_no_capitalizables'
    _description = 'Activos no capitalizables'
    _rec_name = 'descripcion'
    _inherit = ['mail.thread'] 

    resguardo_id=fields.Many2one('tjacdmx.resguardos',string='Resguardo')
    tipo_articulo= fields.Many2one('tjacdmax.tipo_articulo_ac',string='Tipo articulo')
    id_tipo_articulo= fields.Integer(string='Tipo articulo id')
    descripcion= fields.Char(string='descripcion',track_visibility='onchange')
    observaciones= fields.Char(string='observaciones',track_visibility='onchange')
    marca= fields.Char(string='marca',track_visibility='onchange')
    modelo= fields.Char(string='modelo',track_visibility='onchange')
    no_serie= fields.Char(string='no_serie',track_visibility='onchange')
    progresivo= fields.Integer(string='progresivo')
    no_inventario= fields.Char(string='no_inventario')
    fecha_baja= fields.Date(string='fecha_baja')
    id_ubicacion= fields.Integer(string='id_ubicacion')
    clave= fields.Char(string='Clave')
    state=fields.Selection([('open','Abierto'),('close','Cerrado')],default='open',string='State')
    status=fields.Selection([('open','Abierto'),('close','Cerrado')],default='open',string='Status',track_visibility='onchange')
    marca = fields.Char(string="Marca")
    no_serie = fields.Char(string="Numero de serie")
    modelo = fields.Char(string='Modelo')
    estado_fisico = fields.Char(string='Estado Fisico')
    piso =  fields.Selection(
        [('1', '1'), 
         ('2', '2'), 
         ('3', '3'), 
         ('4', '4'),
         ('5', '5'), 
         ('6', '6'), 
         ('7', '7'), 
         ('8', '8'),
         ('9', '9'), 
         ('10', '10'), 
         ('11', '11'), 
         ('12', '12'), 
         ('13', 'PB'), 
         ('14', 'E1'), 
         ('15', 'E2'), 
         ('16', 'Almacén General')],string='Piso',default=1,track_visibility='onchange')
    edificio = fields.Selection([('', 'Indefinido'),('Insurgentes', 'Insurgentes'), ('Coyoacan', 'Coyoacan'), ('Nebraska', 'Nebraska'),('Estacionamiento 2','Estacionamiento 2')], string='Edificio',track_visibility='onchange')
    resguardante=fields.Many2one('tjacdmx.resguardantes',string='Resguardante')
    area=fields.Char(string='Area',track_visibility='onchange')
    id_empleado_linea = fields.Integer(string='Empleado')
    fecha_compra = fields.Date(string='Fecha de compra')
    precio= fields.Float(string='Precio',track_visibility='onchange')
    movimientos_reguardo= fields.One2many('tjacdmx.mov_activos_no_capitalizables', 'activo_no_capitalizable', string='Movimientos')

    
    def update_state_off(self):
        self.write({'status': 'close'})
    
    
    def update_state_on(self):
        self.write({'status': 'open'})


    
    def wizard_codebar(self):
        if(self.clave):
            return {
                'name': _("Genera codigo de barras del activo"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.codebar',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'codebar_num':self.clave,'activo':self.descripcion,'no_inventario':self.no_inventario}
            } 

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|',
                                ('no_serie', operator, name),
                                ('descripcion', operator, name),
                            ] + args, limit=limit)
            if(not recs.name_get()):
                recs = self.search(['|',
                                ('clave', operator, name),
                                ('no_inventario', operator, name),
                            ] + args, limit=limit)
        return recs.name_get()

    
    def actu_clave(self):
        activos = self.env['tjacdmax.activos_no_capitalizables'].search([])
        for i in activos:
            query = """select 
                        concat(
                            substring(no_inventario from 1 for 4),
                            substring(split_part(no_inventario::TEXT,'-',1) from length(split_part(no_inventario::TEXT,'-',1))-2),
                        	substring(split_part(no_inventario::TEXT,'-',2) from 1 for 5)
                        ) as clave
                    from tjacdmax_activos_no_capitalizables
                    where id=%s;""" % (i.id)
            self.env.cr.execute(query)
            code = self.env.cr.dictfetchall()
            code_barra=''
            if(code):
                code_barra=code[0]['clave']
            tjacdmx_update_asset_code = "UPDATE tjacdmax_activos_no_capitalizables SET clave='%s' WHERE id=%s" % (code_barra,i.id)
            self.env.cr.execute(tjacdmx_update_asset_code)





class TipoArticulo(models.Model):
    _name = 'tjacdmax.tipo_articulo_ac'
    _description = 'Tipo Articulo'
    _rec_name = 'nombre'
    _inherit = ['mail.thread']
    
    nombre= fields.Char(string='Nombre')
    clave= fields.Char(string='Clave')


class mov_activos_no_capitalizables(models.Model):
    _name = 'tjacdmx.mov_activos_no_capitalizables'
    resguardante =fields.Many2one('tjacdmx.resguardantes',string='Resguardante')
    activo_no_capitalizable = fields.Many2one('tjacdmax.activos_no_capitalizables',string='No capitalizable')
    tipo=fields.Selection([('asignacion','Asignacion'),('reasignacion','Reasignacion'),('desasignacion','Desasignacion')],string='Tipo',default='asignacion')
    fecha = fields.Datetime(string='Scheduled Date',default=datetime.today())