# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]
PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
TIPO_UP = [(1, 'Periodo'),(2,'Partida')]
STATUS = [(1, 'Abierto'),(2,'Cerrado')]

class Remanentes(models.TransientModel):
    _name = 'remanentes.wizard'

    periodo_origen = fields.Selection(PERIODO_SELECT, required=True, default=1)
    periodo_destino = fields.Selection(PERIODO_SELECT, required=True)
    ejercicio = fields.Selection(EJERCICIO_SELECT, required=True)
    version = fields.Many2one('presupuesto.version', string='Version', required=True)
    
    @api.onchange('periodo_origen')
    @api.multi
    def _onchange_periodo_origen(self):
        periodo_destino=self.periodo_origen+1
        self.update({'periodo_destino': periodo_destino})

    @api.multi
    def search_partidas_origen(self):
        search_periodo = self.env['presupuesto.documento'].search([
            ('version', '=', self.version.version),
            ('ejercicio', '=', self.ejercicio),
            ('periodo', '=', self.periodo_origen)],limit=7)
        #proceso de crear documento
        for partidas_periodo in search_periodo:
            search_periodo_destino = self.env['presupuesto.documento'].search([
            ('version', '=', self.version.version),
            ('ejercicio', '=', self.ejercicio),
            ('periodo', '=', self.periodo_destino)])
            obj_documento = self.env['presupuesto.documento']
            ejercicio = self.ejercicio
            periodo = self.periodo_destino
            version = self.version
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','REMANENTE')], limit=1)
            sql_md="""
                SELECT ((SUM(CASE WHEN pd.clase_documento = 3 THEN importe ELSE 0 END) + SUM(CASE WHEN pd.clase_documento = 1 THEN importe ELSE 0 END) ) -  SUM(CASE WHEN pd.clase_documento = 2 THEN importe ELSE 0 END) ) - SUM(CASE WHEN pd.clase_documento = 7 THEN importe ELSE 0 END) as disponible
                FROM presupuesto_detalle_documento dd
                INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                WHERE posicion_presupuestaria=%s and periodo=%s					
                GROUP BY dd.posicion_presupuestaria,pp.partida_presupuestal,pd.periodo
                """
            self.env.cr.execute(sql_md % (partidas_periodo.detalle_documento_ids[0].posicion_presupuestaria.id,self.periodo_origen))
            importe_disponible_origen = self.env.cr.fetchone()
            impor_conv=importe_disponible_origen[0]
            documentos_originales = []
            for item in search_periodo[0].detalle_documento_ids:
                control_destino = self.env['presupuesto.control_presupuesto'].search([
                    ('version', '=', self.version.version),
                    ('ejercicio', '=', self.ejercicio),
                    ('periodo', '=', self.periodo_destino),
                    ('posicion_presupuestaria', '=', partidas_periodo.detalle_documento_ids[0].posicion_presupuestaria.id)])
                doc_origin = [0, False,
                    {
                        'centro_gestor': item.centro_gestor.id,
                        'area_funcional': item.area_funcional.id,
                        'fondo_economico': item.fondo_economico.id,
                        'posicion_presupuestaria': partidas_periodo.detalle_documento_ids[0].posicion_presupuestaria.id,
                        'importe': impor_conv,
                        'control_presupuesto_id': control_destino.id,
                    }
                ]
                documentos_originales.append(doc_origin)
            if (search_periodo[0].status_rem=='open'):
                documento = obj_documento.create({
                    'clase_documento': cls_doc.id,
                    'version': version.id,
                    'ejercicio': ejercicio,
                    'periodo': periodo,
                    'fecha_contabilizacion': datetime.today(),
                    'fecha_documento': datetime.today(),
                    'detalle_documento_ids': documentos_originales,
                })
                cp_destino_remanente = self.env['presupuesto.control_presupuesto'].search([
                        ('version', '=', self.version.version),
                        ('ejercicio', '=', self.ejercicio),
                        ('periodo', '=', self.periodo_destino),
                        ('posicion_presupuestaria', '=', partidas_periodo.detalle_documento_ids[0].posicion_presupuestaria.id)])
                tjacdmx_update_field_remanente= "UPDATE presupuesto_control_presupuesto SET egreso_modificado_remanente=%s WHERE id=%s" % (impor_conv,control_destino.id)
                self.env.cr.execute(tjacdmx_update_field_remanente)
                tjacdmx_update_field_remanente_status= "UPDATE presupuesto_documento SET status_rem='close' WHERE id=%s" % (partidas_periodo.id)
                self.env.cr.execute(tjacdmx_update_field_remanente_status)
        #raise ValidationError("Saldos transferidos  %s" % (len(search_periodo)))




