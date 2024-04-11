# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import base64 
import csv
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta

STATEFILE = [('success','Valido'),('error','Con errores')]

class CargaPresupuesto(models.TransientModel):
    _name = 'carga_presupuesto.wizard'

    state_file = fields.Selection(STATEFILE,default='error')
    file = fields.Binary(string='Archivo')

    @api.multi
    def validate_file(self):
        image_64_encode = self.file
        image_64_decode = base64.decodestring(image_64_encode) 
        csvReader = csv.DictReader(image_64_decode)
        control_presupuesto = self.env['presupuesto.control_presupuesto']
        obj_documento = self.env['presupuesto.documento']
        with open('/mnt/grp/GRP/presupuestos/static/src/carga_masiva.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            documentos_create = []
            for rows in reader:
                fecha = datetime.strptime(rows['fecha'], '%Y-%m-%d') if rows['fecha'] else datetime.today()
                partida = self.env['presupuesto.partida_presupuestal'].search([('partida_presupuestal', '=', rows['partida'])], limit=1)
                area_funcional = self.env['presupuesto.area_funcional'].search([('area_funcional', '=', rows['area_funcional'])], limit=1)
                ejercicio=fecha.year
                periodo=fecha.month
                cp = control_presupuesto.search([
                        ('ejercicio', '=', ejercicio),
                        ('periodo', '=', periodo),
                        ('version', '=', 1),
                        ('fondo_economico', '=', 1),
                        ('posicion_presupuestaria', '=', partida.id),
                        ('centro_gestor', '=', 1),
                        ('area_funcional', '=', area_funcional.id) ])
                if cp:
                    raise ValidationError('El documento original con la partida %s ya existe' % (rows['partida']))
                else:
                    if(partida and area_funcional):
                        self.write({'state_file': "success"})
                        documentos_originales = []
                        cp_create = control_presupuesto.create({
                            'ejercicio': ejercicio,
                            'periodo':periodo,
                            'version': 1,
                            'fondo_economico': 1,
                            'posicion_presupuestaria': partida.id,
                            'centro_gestor':1,
                            'area_funcional':area_funcional.id,
                            'egreso_aprobado': float(rows['importe'])
                        })
                        #raise ValidationError('debug: %s' % (cp_create))
                        doc_origin = [0, False,{
                                'centro_gestor':1,
                                'area_funcional': area_funcional.id,
                                'fondo_economico': 1,
                                'posicion_presupuestaria': partida.id,
                                'importe': float(rows['importe']),
                                'control_presupuesto_id':cp_create.id
                                }]
                        documentos_originales.append(doc_origin)
                        #raise ValidationError('debug: %s' % (documentos_originales))
                        documento ={
                            'clase_documento': 3,
                            'version': 1,
                            'ejercicio':ejercicio,
                            'periodo':periodo,
                            'periodo_origen':periodo,
                            'fecha_contabilizacion':rows['fecha'],
                            'fecha_documento': rows['fecha'],
                            'partida_presupuestal':partida.id,
                            'detalle_documento_ids': documentos_originales
                        }
                        documentos_create.append(documento)
                        # #raise ValidationError('debug: doc=%s' % (documento))
                    else:
                        self.write({'state_file': "error"})
                        raise ValidationError('Algunos datos son incorrectos.')
            for i in documentos_create:
                create=obj_documento.create(i)
                raise ValidationError('%s' %(create))
            self.write({'state_file': "success"})


    @api.multi
    def process_file(self):
        # image_64_encode = self.file
        # image_64_decode = base64.decodestring(image_64_encode) 
        # csvReader = csv.DictReader(image_64_decode)
        control_presupuesto = self.env['presupuesto.control_presupuesto']
        obj_documento = self.env['presupuesto.documento']
        documentos_create = []
        with open('/mnt/grp/GRP/presupuestos/static/src/carga_masiva.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            for rows in reader:
                fecha = datetime.strptime(rows['fecha'], '%Y-%m-%d') if rows['fecha'] else datetime.today()
                partida = self.env['presupuesto.partida_presupuestal'].search([('partida_presupuestal', '=', rows['partida'])], limit=1)
                area_funcional = self.env['presupuesto.area_funcional'].search([('area_funcional', '=', rows['area_funcional'])], limit=1)
                ejercicio=fecha.year
                periodo=fecha.month
                cp = control_presupuesto.search([
                        ('ejercicio', '=', ejercicio),
                        ('periodo', '=', periodo),
                        ('version', '=', 1),
                        ('fondo_economico', '=', 1),
                        ('posicion_presupuestaria', '=', partida.id),
                        ('centro_gestor', '=', 1),
                        ('area_funcional', '=', area_funcional.id) ])
                if cp:
                    raise ValidationError('El documento original con la partida %s ya existe' % (rows['partida']))
                else:
                    if(partida and area_funcional):
                        documentos_originales = []
                        cp_create = control_presupuesto.create({
                            'ejercicio': ejercicio,
                            'periodo':periodo,
                            'version': 1,
                            'fondo_economico': 1,
                            'posicion_presupuestaria': partida.id,
                            'centro_gestor':1,
                            'area_funcional':area_funcional.id,
                            'egreso_aprobado': float(rows['importe'])
                        })
                        doc_origin = [0, False,{
                                'centro_gestor':1,
                                'area_funcional': area_funcional.id,
                                'fondo_economico': 1,
                                'posicion_presupuestaria': partida.id,
                                'importe': float(rows['importe']),
                                'control_presupuesto_id':cp_create.id
                                }]
                        documentos_originales.append(doc_origin)
                        documento ={
                            'clase_documento': 3,
                            'version': 1,
                            'ejercicio':ejercicio,
                            'periodo':periodo,
                            'periodo_origen':periodo,
                            'fecha_contabilizacion':rows['fecha'],
                            'fecha_documento': rows['fecha'],
                            'partida_presupuestal':partida.id,
                            'detalle_documento_ids': documentos_originales
                        }
                        documentos_create.append(documento)
                        #raise ValidationError('debug: doc=%s' % (documento))
                    else:
                        raise ValidationError('Algunos datos son incorrectos.')
            for i in documentos_create:
                create=obj_documento.create(i)


class CargaPresupuestoCompromiso(models.TransientModel):
    _name = 'carga_presupuesto_compromiso.wizard'

    state_file = fields.Selection(STATEFILE,default='error')
    file = fields.Binary(string='Archivo')

       