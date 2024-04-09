# -*- coding: utf-8 -*-
import operator
from odoo import api, fields, models, _, tools
from datetime import datetime

EJERCICIO_SELECT = [ (str(year), str(year)) for year in range(2018, 2031) ]
PERIODO_SELECT = [(str(periodo), str(periodo)) for periodo in range(1,13)]
TIPO_DOCUMENTO_SELECT = [
    ("ORIGINAL", "Original"),
    ("REDUCCION", "Reducción"),
    ("AMPLIACION", "Ampliación"),
    ("RECLASIFICACION", "Reclasificación"),
    ("COMPROMETIDO", "Comprometido"),
    ("DEVENGADO", "Devengado"),
    ("PAGADO", "Pagado"),
    ("EJERCIDO", "Ejercido"),
    ("REMANENTE", "Remanente"),
    ("AJUSTE", "Ajuste"),
    ("CANCELACION", "Cancelación"),
    ("DEDUCCION", "Deducción"),
    ("DEDUCCION_PAGO", "Pago deducción")
]
SIGNO_SELECT = [
    ("-","-"),
    ("+", "+")
]

class ClaseDocumento(models.Model):
    _name = 'presupuesto.clase_documento'
    _rec_name = 'nombre'
    _description = "Clase Documento"

    ops = { "+": operator.add, "-": operator.sub } # Diccionario de operadores

    nombre = fields.Char(string='Nombre', required=True)
    tipo_documento = fields.Selection(
        selection=TIPO_DOCUMENTO_SELECT,
        string="Tipo Documento",
        required=True)
    signo = fields.Selection(
        selection=SIGNO_SELECT,
        string='Signo',
        help='Indica el tipo de operacion que realizara sobre el prespuesto',
        required=True
    )

    
    @api.depends('nombre','signo',)
    def name_get(self):
        result = []
        for cls_doc in self:
            name = '%s %s' % (cls_doc.nombre, cls_doc.signo)
            result.append((cls_doc.id, name))
        return result

    def operator(self):
        return self.ops[self.signo]

    _sql_constraints = [
        ('prespuesto_clase_documento_uniq',
        'UNIQUE (nombre, tipo_documento, signo)',
        'Ya existe este registro!')]

class Version(models.Model):
    _name = 'presupuesto.version'
    _rec_name = 'version'
    _description = u'Versión'

    version = fields.Char(
        string='Versión',
        required=True
    )
    descripcion = fields.Text(
        string='Descripcion',
    )

    _sql_constraints = [
        ('prespuesto_version_uniq',
        'UNIQUE (version)',
        'La versión debe ser unica!')]



class ConfiAuxiliares(models.Model):
    _name = 'presupuesto.config_auxiliares'
    _rec_name='server'
    _description = "Configuracion de auxiliares"

    server=fields.Char(string='URL SERVER')
    status=fields.Boolean(string='Estado')

    
    
    @api.onchange('status')
    def put_satate(self):
        put_states_prea = "UPDATE presupuesto_config_auxiliares SET status='False'"
        self.env.cr.execute(put_states_prea)
        if(self.id):
            put_state_active = "UPDATE presupuesto_config_auxiliares SET status='True' WHERE id=%s" % (self.id)
            self.env.cr.execute(put_state_active)


    @api.model
    def create(self,values):
        record = super(ConfiAuxiliares, self).create(values)
        if(record.id):
            put_states_prea = "UPDATE presupuesto_config_auxiliares SET status='False'"
            self.env.cr.execute(put_states_prea)
            put_state_active = "UPDATE presupuesto_config_auxiliares SET status='True' WHERE id=%s" % (record.id)
            self.env.cr.execute(put_state_active)
        return record





    