# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero

class ActivosArrendamiento(models.Model):
    _name = 'tjacdmax.arrendamiento'
    _description = 'Activos  arrendamiento'
    _rec_name = 'descripcion'
    _inherit = ['mail.thread'] 

    resguardo_id=fields.Many2one('tjacdmx.resguardos',string='Resguardo')
    id_tipo_articulo= fields.Integer(string='Tipo articulo id')
    descripcion= fields.Char(string='descripcion')
    observaciones= fields.Char(string='observaciones')
    marca= fields.Char(string='marca')
    modelo= fields.Char(string='modelo')
    progresivo= fields.Integer(string='progresivo')
    referencia= fields.Char(string='referencia')
    id_ubicacion= fields.Integer(string='id_ubicacion')
    state=fields.Selection([('open','Abierto'),('close','Cerrado')],default='open',string='State')
    status=fields.Selection([('open','Abierto'),('close','Cerrado')],default='open',string='Status')
    marca = fields.Char(string="Marca")
    no_serie = fields.Char(string="Numero de serie")
    modelo = fields.Char(string='Modelo')
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
         ('16', 'Almacén General')],string='Piso',default=1)
    edificio = fields.Selection([('', 'Indefinido'),('Insurgentes', 'Insurgentes'), ('Coyoacan', 'Coyoacan'), ('Nebraska', 'Nebraska'),('Estacionamiento 2','Estacionamiento 2')], string='Edificio')
    resguardante=fields.Many2one('tjacdmx.resguardantes',string='Resguardante')
    area=fields.Char(string='Area')
    id_empleado_linea = fields.Many2one('tjacdmx.resguardantes',string='Resguardante',compute='compute_name_resguardante')
    movimientos_reguardo_arrendamiento = fields.One2many('tjacdmx.mov_resguardante_arrendamiento', 'activo_arrendamiento', string='Movimientos arrendamiento')

    
    def update_state_off(self):
        self.write({'status': 'close'})
    
    
    def update_state_on(self):
        self.write({'status': 'open'})

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
                                ('descripcion', operator, name),
                            ] + args, limit=limit)
        return recs.name_get()
    @api.model
    def compute_name_resguardante(self):
        linea_resguardo = self.env['tjacdmx.resguardo_lineas_arrendamiento'].search([('id_activo','=',self.id)],limit=1)
        if(linea_resguardo):
            resguardo = self.env['tjacdmx.resguardos'].search([('id','=',linea_resguardo.resguardo_id)],limit=1)
            resguardante = self.env['tjacdmx.resguardantes'].search([('id','=',resguardo.resguardante.id)],limit=1)
            self.id_empleado_linea=resguardante.id
        
        

    # 
    # def actu_clave(self):
    #     activos = self.env['tjacdmax.arrendamiento'].search([])
    #     for i in activos:
    #         query = """select 
    #                     concat(
    #                         substring(no_inventario from 1 for 4),
    #                         substring(split_part(no_inventario::TEXT,'-',1) from length(split_part(no_inventario::TEXT,'-',1))-2),
    #                     	substring(split_part(no_inventario::TEXT,'-',2) from 1 for 5)
    #                     ) as clave
    #                 from tjacdmax_arrendamiento
    #                 where id=%s;""" % (i.id)
    #         self.env.cr.execute(query)
    #         code = self.env.cr.dictfetchall()
    #         code_barra=''
    #         if(code):
    #             code_barra=code[0]['clave']
    #         tjacdmx_update_asset_code = "UPDATE tjacdmax_arrendamiento SET clave='%s' WHERE id=%s" % (code_barra,i.id)
    #        self.env.cr.execute(tjacdmx_update_asset_code)


class mov_resguardante_arrendamiento(models.Model):
    _name = 'tjacdmx.mov_resguardante_arrendamiento'
    resguardante =fields.Many2one('tjacdmx.resguardantes',string='Resguardante')
    activo_arrendamiento = fields.Many2one('tjacdmax.arrendamiento',string='Arrendamiento')
    tipo=fields.Selection([('asignacion','Asignacion'),('reasignacion','Reasignacion'),('desasignacion','Desasignacion')],string='Tipo',default='asignacion')
    fecha = fields.Datetime(string='Scheduled Date',default=datetime.today())