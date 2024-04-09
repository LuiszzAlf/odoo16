# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from bisect import bisect_left
from collections import defaultdict
import re
from datetime import datetime
from . import configuracion

EJERCICIO_SELECT = [ (str(year), str(year)) for year in range(2018, 2031) ]
PERIODO_SELECT = [(str(periodo), str(periodo)) for periodo in range(1,13)]

class PartidaPresupuestal(models.Model):
    _name = 'presupuesto.partida_presupuestal'
    _order = 'capitulo, concepto, partida_generica, partida_especifica, control_contable_presupuestal, control_contable_presupuestalc'
    _description = "Partida Presupuestal"

    capitulo = fields.Integer(string='Capitulo')
    concepto = fields.Integer(string='Concepto')
    partida_generica = fields.Integer(string='Partida Generica')
    partida_especifica = fields.Integer(string='Partida Especifica')
    control_contable_presupuestal = fields.Integer(string='Control Contable Presupuestal')
    control_contable_presupuestalc = fields.Integer(string='Control Contable Presupuestal C')
    denominacion = fields.Text(string='Denominacion')
    parent_id = fields.Many2one('presupuesto.partida_presupuestal', string="Partida Padre",  index=True,  ondelete='cascade')
    child_id = fields.One2many('presupuesto.partida_presupuestal', 'parent_id', string='Partidas hijo')
    parent_left = fields.Integer(string='Left Parent',  index=True)
    parent_right = fields.Integer(string='Right Parent',  index=True)
    partida_presupuestal = fields.Char(compute='_partida_presupuestal', store=True)

    @api.depends('capitulo', 'concepto', 'partida_generica', 'partida_especifica', 'control_contable_presupuestal','control_contable_presupuestalc')
    def _partida_presupuestal(self):
        for record in self:
            record.partida_presupuestal = '%s%s%s%s%s%s' % (record.capitulo, record.concepto,
                record.partida_generica, record.partida_especifica, record.control_contable_presupuestal,record.control_contable_presupuestalc)

    
    @api.depends('partida_presupuestal')
    def name_get(self):
        result = []
        for part_pres in self:
            name = '%s' % part_pres.partida_presupuestal
            result.append((part_pres.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('partida_presupuestal', '=ilike', name.split(' ')[0] + '%'), ('partida_presupuestal', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        partidas_ids = self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(partidas_ids).name_get()

    # _sql_constraints = [
    #     ('partida_presupuestal_uniq',
    #     'UNIQUE (capitulo, concepto, partida_generica, partida_especifica, control_contable_presupuestal)',
    #     'La partida presupuestal debe ser unica!')]

class AreaFuncional(models.Model):
    _name = 'presupuesto.area_funcional'
    _rec_name = 'concepto'
    _order = "rubro, tipo, subfuncion"
    _description = u'Área Funcional'
    

    rubro = fields.Char(string='Rubro', required=True, index=True)
    tipo = fields.Char(string='Tipo', required=True, index=True)
    subfuncion = fields.Char(string='Sub Funcion', required=True, index=True)
    concepto = fields.Char(string='Concepto', required=True)
    area_funcional = fields.Char(compute='_area_funcional', store=True)

    @api.depends('rubro', 'tipo', 'subfuncion')
    def _area_funcional(self):
        for record in self:
            record.area_funcional = '%s%s%s' % (record.rubro, record.tipo, record.subfuncion)

    
    @api.depends('rubro', 'tipo', 'subfuncion')
    def name_get(self):
        result = []
        for rubro_ingreso in self:
            name = '%s%s%s' % (rubro_ingreso.rubro, rubro_ingreso.tipo, rubro_ingreso.subfuncion)
            result.append((rubro_ingreso.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('area_funcional', '=ilike', name.split(' ')[0] + '%'), ('area_funcional', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        areas_ids = self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(areas_ids).name_get()

    _sql_constraints = [
        ('area_funcional_uniq',
        'UNIQUE (rubro, tipo, subfuncion)',
        'El programa de financiacion debe ser unico!')]

class FondoEconomico(models.Model):
    _name = 'presupuesto.fondo_economico'
    _rec_name = 'denominacion'
    _description = u"Fondo Económico"

    fuente_financiamiento = fields.Integer(string='Fuente financiamiento', required=True, index=True)
    denominacion = fields.Char(string='Denominacion', required=True)

    _sql_constraints = [
        ('fondo_economico_fuente_financiamiento_uniq',
        'UNIQUE (fuente_financiamiento)',
        'La fuente de financiamiento debe ser unico!')]

class CentroGestor(models.Model):
    _name = 'presupuesto.centro_gestor'
    _rec_name = 'centro_gestor'
    _description = "Centro Gestor"

    clave = fields.Char(string='Clave', required=True, index=True)
    fecha_inicio = fields.Date(string='De', required=True, default=datetime.today())
    fecha_final = fields.Date(string='A', required=True, default=datetime.today())
    centro_gestor = fields.Char(string='Centro Gestor', required=False)

    _sql_constraints = [
        ('centro_gestor_clave_uniq',
        'UNIQUE (clave)',
        'La clave del centro gestor debe ser unico!')]

class CuentaOrden(models.Model):
    _name = 'presupuesto.cuenta_orden'
    _rec_name = 'posicion_presupuestaria'
    _description = "Cuentas de orden"

    posicion_presupuestaria = fields.Many2one(
        'presupuesto.partida_presupuestal',
        string='Posición presupuestaria',
        required=True
    )
    cta_orden_original_egreso = fields.Many2one(
        'account.account',
        string='Original cargo',
        required=True
    )
    cta_orden_original_ingreso = fields.Many2one(
        'account.account',
        string='Original abono',
        required=True
    )
    cta_orden_modificado_egreso = fields.Many2one(
        'account.account',
        string='Modificado cargo',
        required=True
    )
    cta_orden_modificado_ingreso = fields.Many2one(
        'account.account',
        string='Modificado abono',
        required=True
    )
    cta_orden_comprometido_egreso = fields.Many2one(
        'account.account',
        string='Comprometido cargo',
        required=True
    )
    cta_orden_comprometido_ingreso = fields.Many2one(
        'account.account',
        string='Comprometido abono',
        required=True
    )
    cta_orden_devengado_egreso = fields.Many2one(
        'account.account',
        string='Devengado cargo',
        required=True
    )
    cta_orden_devengado_ingreso = fields.Many2one(
        'account.account',
        string='Devengado abono',
        required=True
    )
    cta_orden_ejercido_egreso = fields.Many2one(
        'account.account',
        string='Ejercido cargo',
        required=True
    )
    cta_orden_ejercido_ingreso = fields.Many2one(
        'account.account',
        string='Ejercido abono',
        required=True
    )
    cta_orden_pagado_egreso = fields.Many2one(
        'account.account',
        string='Pagado cargo',
        required=True
    )
    cta_orden_pagado_ingreso = fields.Many2one(
        'account.account',
        string='Pagado abono',
        required=True
    )

    _sql_constraints = [
        ('cuenta_orden_posicion_presupuestaria_uniq',
        'UNIQUE (posicion_presupuestaria)',
        'La posicion presupuestaria debe ser unico!')]




class AreasStok(models.Model):
    _name = 'presupuesto.areas.stok'
    _rec_name='nombre'

    nombre = fields.Char(string='Nombre del area')
    status= fields.Char(string='Status')


class ImportesCuentasAnuales(models.Model):
    _name = 'tjacdmx.contabilidad_saldos_anuales'
    _rec_name='cuenta'

    cuenta = fields.Many2one('account.account',string='Cuenta')
    cuenta_str = fields.Char(string='Cuenta')
    anio = fields.Selection(EJERCICIO_SELECT, required=True, default=2018)
    importe = fields.Float(string='Importe',default=0)
    cargo = fields.Float(string='Cargo',default=0)
    abono = fields.Float(string='Abono',default=0)
    id_reporte = fields.Many2one('reportes.clase_reportes',string='Tipo de Reporte',required=True)

    
    def name_get(self):
        cuenta= self.cuenta.name if self.cuenta.name else 0
        code= self.cuenta.code if self.cuenta.code else 0
        result = []
        for doc in self:
            name = '%s - %s  ' % (cuenta,code)
            result.append((doc.id, name))
        return result


class AreasDireccion(models.Model):
    _name = 'tjacdmx.contabilidad_saldos_anuales'
    _rec_name='cuenta'

    cuenta = fields.Many2one('account.account',string='Cuenta')
    cuenta_str = fields.Char(string='Cuenta')
    anio = fields.Selection(selection=EJERCICIO_SELECT, required=True, default=2018)
    importe = fields.Float(string='Importe',default=0)
    cargo = fields.Float(string='Cargo',default=0)
    abono = fields.Float(string='Abono',default=0)
    id_reporte = fields.Many2one('reportes.clase_reportes',string='Tipo de Reporte',required=True)

    
    def name_get(self):
        cuenta= self.cuenta.name if self.cuenta.name else 0
        code= self.cuenta.code if self.cuenta.code else 0
        result = []
        for doc in self:
            name = '%s - %s  ' % (cuenta,code)
            result.append((doc.id, name))
        return result