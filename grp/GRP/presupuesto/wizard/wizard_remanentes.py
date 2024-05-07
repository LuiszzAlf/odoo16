# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

EJERCICIO_SELECT = [ (str(year), str(year)) for year in range(2018, 2031) ]
PERIODO_SELECT = [(str(periodo), str(periodo)) for periodo in range(1,13)]
TIPO_UP = [('1', 'Periodo'),('2','Partida')]
STATUS = [('1', 'Abierto'),('2','Cerrado')]

class Remanentes(models.TransientModel):
    _name = 'remanentes.wizard'

    periodo_origen = fields.Selection(PERIODO_SELECT, required=True, default='1')
    periodo_destino = fields.Selection(PERIODO_SELECT, required=True)
    ejercicio = fields.Selection(EJERCICIO_SELECT, required=True)

    @api.onchange('periodo_origen')
    
    def _onchange_periodo_origen(self):
        periodo_destino=int(self.periodo_origen)+1
        self.update({'periodo_destino': str(periodo_destino)})

    
    def search_partidas_origen(self):
        search_periodo = self.env['presupuesto.view_cp'].search([
            ('ejercicio', '=', self.ejercicio),
            ('periodo', '=', self.periodo_origen)])
        periodo_val = self.periodo_destino
        documentos_rem = self.env['presupuesto.documento'].search([('clase_documento','=',10),('periodo','=', periodo_val),('ejercicio','=', self.ejercicio)])
        docs_as=int(len(documentos_rem))
        if (docs_as>0):
            raise ValidationError("Ya se registraron remanentes de este periodo: %s partidas registradas." % (len(documentos_rem)))
        else:
            for partidas_periodo in search_periodo:
                obj_documento = self.env['presupuesto.documento']
                ejercicio = self.ejercicio
                periodo = self.periodo_destino
                version = 1
                cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','REMANENTE')], limit=1)
                doc_detalle=partidas_periodo.detalle_documento_original_ids
                sql_md="""
                    SELECT ((SUM(CASE WHEN pd.clase_documento = 3 THEN importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN importe ELSE 0 END) + SUM(CASE WHEN pd.clase_documento = 10 THEN importe ELSE 0 END) ) -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN importe ELSE 0 END) ) - SUM(CASE WHEN pd.clase_documento = 7 THEN importe ELSE 0 END) disponible
                    FROM presupuesto_detalle_documento dd
                    INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                    INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                    WHERE posicion_presupuestaria=%s and periodo=%s and ejercicio='%s' and status='open'
                    GROUP BY dd.posicion_presupuestaria,pp.partida_presupuestal,pd.periodo
                    """
                self.env.cr.execute(sql_md % (doc_detalle.posicion_presupuestaria.id,self.periodo_origen,self.ejercicio))
                importe_disponible_origen = self.env.cr.fetchone()
                impor_validate=importe_disponible_origen[0]
                if (impor_validate>0):
                    impor_conv=importe_disponible_origen[0]
                else:
                    impor_conv=0
                control_destino = self.env['presupuesto.control_presupuesto'].search([
                    ('version', '=', version),
                    ('ejercicio', '=', self.ejercicio),
                    ('periodo', '=', self.periodo_destino),
                    ('posicion_presupuestaria', '=', doc_detalle.posicion_presupuestaria.id)]) 
                documentos_originales = []
                doc_origin = [0, False,{
                        'centro_gestor': doc_detalle.centro_gestor.id,
                        'area_funcional': doc_detalle.area_funcional.id,
                        'fondo_economico': doc_detalle.fondo_economico.id,
                        'posicion_presupuestaria': doc_detalle.posicion_presupuestaria.id,
                        'importe': impor_conv,
                        'control_presupuesto_id': control_destino.id
                        }]
                documentos_originales.append(doc_origin)
                
                fecha_conta=datetime(ejercicio,periodo,1).date()
                documento = obj_documento.create({
                    'clase_documento': cls_doc.id,
                    'version': version,
                    'ejercicio': ejercicio,
                    'periodo': periodo,
                    'periodo_origen': periodo,
                    'is_periodo_anterior': 5,
                    'fecha_contabilizacion': fecha_conta,
                    'fecha_documento': fecha_conta,
                    'partida_presupuestal': doc_detalle.posicion_presupuestaria.partida_presupuestal,
                    'detalle_documento_ids': documentos_originales
                },tipo='remanente')
                cp_destino_remanente = self.env['presupuesto.control_presupuesto'].search([
                        ('version', '=', version),
                        ('ejercicio', '=', self.ejercicio),
                        ('periodo', '=', self.periodo_destino),
                        ('posicion_presupuestaria', '=', doc_detalle.posicion_presupuestaria.id)])
                tjacdmx_update_field_remanente= "UPDATE presupuesto_control_presupuesto SET egreso_modificado_remanente=%s WHERE id=%s" % (impor_conv,cp_destino_remanente.id)
                self.env.cr.execute(tjacdmx_update_field_remanente)
            cp_origen_remanente = self.env['presupuesto.control_presupuesto'].search([
                        ('version', '=', version),
                        ('ejercicio', '=', self.ejercicio),
                        ('periodo', '=', self.periodo_origen),
                        ('posicion_presupuestaria', '=', doc_detalle.posicion_presupuestaria.id)])
            tjacdmx_update_field_remanente_status= "UPDATE presupuesto_control_presupuesto SET status='close' WHERE id=%s" % (cp_origen_remanente.id)
            self.env.cr.execute(tjacdmx_update_field_remanente_status)




