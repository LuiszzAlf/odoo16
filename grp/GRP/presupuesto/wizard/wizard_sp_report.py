# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import calendar
import base64 
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]    
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]
MOVE_SELECT = [('all','Todo'),('move_exist','Con movimientos')]


class wizard_sp_report(models.TransientModel):
    _name = 'wizard.sp_report'

    @api.model
    def _select_anio(self):
        fecha = datetime.today()
        return  fecha.year
    
    @api.model
    def _select_periodo(self):
        fecha = datetime.today()
        return  int(fecha.month)

    state = fields.Selection([('send','Enviado'),('received','Recibido')])
    periodo = fields.Selection(PERIODO_SELECT,required = True, default=_select_periodo)
    anio_fiscal = fields.Selection(EJERCICIO_SELECT,required = True, default=_select_anio)
    fecha_inicio = fields.Date(string='Fecha inicio')
    fecha_fin = fields.Date(string='Fecha del fin')
    tipo_contrato = fields.Many2many('presupuesto.tipo.contrato', string='Tipo de contratos',relation='tipo_contrato', required=True)
    
    @api.multi
    @api.onchange('fecha_inicio')
    def _onchange_date(self):
        date_fin=self.fecha_inicio
        self.update({'fecha_fin': date_fin})
    
    @api.multi
    def search_sps(self):
        datas = {}
        anio=self.anio_fiscal
        periodo=self.periodo
        last_day = calendar.monthrange(anio,periodo)[1]
        periodo_inicio=datetime(anio,periodo,01).date()
        periodo_fin = datetime(anio,periodo,last_day).date()

        tipo_contrato_ids=[]
        tipo_contrato_str=[]
        show_ds='yes'
        for clase in self.tipo_contrato:
            tipo_contrato_ids.append(clase.id)
            tipo_contrato_str.append(clase.code)

        if(len(tipo_contrato_ids)>1):
            tipo_contrato=tuple(tipo_contrato_ids)
            tipos_contrato_str=tuple(tipo_contrato_str)
        else:
            tipo_contrato='('+str(tipo_contrato_ids[0])+')'
            tipos_contrato_str='('+str(tipo_contrato_str[0])+')'
            if(tipo_contrato_ids[0]==20):
                show_ds='no'
        sql_all="""select
                        	psp.id,psp.vb,psp.otra_info,psp.recibio,psp.autorizo,psp.caas,psp.no_procedimiento,
                            psp.contrato,psp.justificacion,psp.adjunta,psp.fecha,psp."name" no_sp,
                            psp.state,psp.elaboro,psp.fecha_pago,psp.fecha_recibido,psp.afavor,
                            pspl.factura,rp.name proveedor,ppp.partida_presupuestal,pspl.adjudicacion,ptc.code tipo_adjudicacion,pspl.tipo_adjudicacion tipo_adjudicacion_id,
                            pspl.descripcion,pspl.importe,pspl.importe_si,pspl.compromiso
                        from
                            presupuesto_solicitud_pago_line pspl
                        join presupuesto_solicitud_pago psp on
                            psp.id = pspl.solicitud_pago_id
                        join res_partner rp on rp.id=pspl.proveedor
                        join presupuesto_partida_presupuestal ppp on ppp.id=pspl.partida
                        join presupuesto_tipo_contrato ptc on ptc.id=pspl.tipo_adjudicacion
                    where
                        psp.state in ('send', 'received')
                        and pspl.tipo_adjudicacion in %s
                        and psp.fecha between '%s' and '%s';"""
        self.env.cr.execute(sql_all % (tipo_contrato,periodo_inicio, periodo_fin))
        rows_sql = self.env.cr.dictfetchall()
        array_mov=[] 
        for i in rows_sql:
            mov = {
                'partida': i['partida_presupuestal'],
                'no_contrato': i['contrato'],
                'caas': i['caas'],
                'no_procedimiento': i['no_procedimiento'],
                'proveedor': i['proveedor'],
                'descripcion': i['descripcion'],
                'importe': i['importe_si'],
                'obcervaciones': i['justificacion'],
                'no_sp': i['no_sp'],
                'tipo_adjudicacion': i['tipo_adjudicacion'],
                'exepcion': i['adjunta']
           }
            array_mov.append(mov)
        

        fechas=datetime.today()
        datas['periodo'] = self.periodo
        datas['anio'] = self.anio_fiscal
        datas['show_ds'] =show_ds
        datas['fecha_reporte'] = str(datetime.strftime(fechas,"%Y-%m-%d"))
        datas['movimientos'] = array_mov
        # raise ValidationError('%s'%datas)
        return self.env['report'].get_action([], 'presupuestos.sp_report', data=datas)
    
    