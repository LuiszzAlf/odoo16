# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
# import csv, sys
PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]

class situacion_financiera_wizard(models.TransientModel):
    _name = 'situacion_financiera.wizard'
    
    @api.model
    def _select_anio(self):
        fecha = datetime.today()
        return  fecha.year
    
    @api.model
    def _select_periodo(self):
        fecha = datetime.today()
        return  int(fecha.month)
    
    anio=fields.Selection(EJERCICIO_SELECT, default=_select_anio)
    periodo = fields.Selection(PERIODO_SELECT, default=_select_periodo)

    @api.multi
    def report_situacion_financiera(self):
        datas={}
        arr_activo=[]
        #####activo circulante#####
        sql_activo_circulante="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (38,45,52,62,72,98,105,108,127,137,143,147,151,161,164,167,170)  order by code asc"""
        self.env.cr.execute(sql_activo_circulante % (self.anio,self.periodo))
        row_activo_efectivo = self.env.cr.dictfetchall()
        
        sql_activo_circulante_banco="""SELECT code,account_id,saldo_inicial AS saldo_inicial,saldo_final AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (45,52)  order by code asc"""
        self.env.cr.execute(sql_activo_circulante_banco % (self.anio,self.periodo))
        row_activo_efectivo_banco = self.env.cr.dictfetchall()
        
        datas['efectivo_saldo']= row_activo_efectivo[0]['saldo_final'] if row_activo_efectivo[0]['saldo_final'] else 0 
        datas['efectivo_saldo_inicial']= row_activo_efectivo[0]['saldo_inicial']
        datas['bancos_tesoreria_saldo']= row_activo_efectivo_banco[0]['saldo_final']
        datas['bancos_tesoreria_saldo_inicial']= row_activo_efectivo_banco[0]['saldo_inicial']
        datas['inversiones_tesoreria_saldo']= row_activo_efectivo_banco[1]['saldo_final']
        datas['inversiones_tesoreria_saldo_inicial']= row_activo_efectivo[2]['saldo_inicial']
        suma_efectivo_bancos= row_activo_efectivo[0]['saldo_final']+row_activo_efectivo_banco[0]['saldo_final']+row_activo_efectivo[2]['saldo_final']
        suma_efectivo_bancos_si= row_activo_efectivo[0]['saldo_inicial']+row_activo_efectivo_banco[0]['saldo_inicial']+row_activo_efectivo[2]['saldo_inicial']
        datas['suma_efectivo_bancos']= suma_efectivo_bancos
        datas['suma_efectivo_bancos_si']= suma_efectivo_bancos_si
        ####
        datas['cuentas_pccp_saldo']= row_activo_efectivo[3]['saldo_final']
        datas['cuentas_pccp_saldo_inicial']= row_activo_efectivo[3]['saldo_inicial']
        datas['deudores_diversos_saldo']= row_activo_efectivo[4]['saldo_final']
        datas['deudores_diversos_saldo_inicial']= row_activo_efectivo[4]['saldo_inicial']
        datas['ingreso_recuperar_cp_saldo']= row_activo_efectivo[5]['saldo_final']
        datas['ingreso_recuperar_cp_saldo_inicial']= row_activo_efectivo[5]['saldo_inicial']
        suma_derechos_recibir= row_activo_efectivo[3]['saldo_final']+row_activo_efectivo[4]['saldo_final']+row_activo_efectivo[5]['saldo_final']
        suma_derechos_recibir_si= row_activo_efectivo[3]['saldo_inicial']+row_activo_efectivo[4]['saldo_inicial']+row_activo_efectivo[5]['saldo_inicial']
        datas['suma_derechos_recibir']= suma_derechos_recibir
        datas['suma_derechos_recibir_si']=suma_derechos_recibir_si
        ####
        datas['inventario_saldo']= row_activo_efectivo[6]['saldo_final']
        datas['inventario_saldo_inicial']= row_activo_efectivo[6]['saldo_inicial']
        datas['almacen_saldo']= row_activo_efectivo[7]['saldo_final']
        datas['almacen_saldo_inicial']= row_activo_efectivo[7]['saldo_inicial']
        suma_activos_inventario= row_activo_efectivo[6]['saldo_final']+row_activo_efectivo[7]['saldo_final']
        suma_activos_inventario_si= row_activo_efectivo[6]['saldo_inicial']+row_activo_efectivo[7]['saldo_inicial']
        datas['suma_activos_circulantes']= suma_efectivo_bancos+suma_derechos_recibir+suma_activos_inventario
        datas['suma_activos_circulantes_si']= suma_efectivo_bancos_si+suma_derechos_recibir_si+suma_activos_inventario_si
        ####activo no circulante
        datas['mobiliario_equipo_saldo']= row_activo_efectivo[8]['saldo_final']
        datas['mobiliario_equipo_saldo_inicial']= row_activo_efectivo[8]['saldo_inicial']
        datas['mobiliario_recreativo_saldo']= row_activo_efectivo[9]['saldo_final']
        datas['mobiliario_recreativo_saldo_inicial']= row_activo_efectivo[9]['saldo_inicial']
        datas['equipo_instrumental_saldo']= row_activo_efectivo[10]['saldo_final']
        datas['equipo_instrumental_saldo_inicial']= row_activo_efectivo[10]['saldo_inicial']
        datas['equipo_trasporte_saldo']= row_activo_efectivo[11]['saldo_final']
        datas['equipo_trasporte_saldo_inicial']= row_activo_efectivo[11]['saldo_inicial']
        datas['maquinaria_otros_saldo']= row_activo_efectivo[12]['saldo_final']
        datas['maquinaria_otros_saldo_inicial']= row_activo_efectivo[12]['saldo_inicial']
        datas['coleciones_arte_saldo']= row_activo_efectivo[13]['saldo_final']
        datas['coleciones_arte_saldo_inicial']= row_activo_efectivo[13]['saldo_inicial']
        suma_bienes_inmuebles= row_activo_efectivo[8]['saldo_final']+row_activo_efectivo[9]['saldo_final']+row_activo_efectivo[10]['saldo_final']+row_activo_efectivo[11]['saldo_final']+row_activo_efectivo[12]['saldo_final']+row_activo_efectivo[13]['saldo_final']
        suma_bienes_inmuebles_si= row_activo_efectivo[8]['saldo_inicial']+row_activo_efectivo[9]['saldo_inicial']+row_activo_efectivo[10]['saldo_inicial']+row_activo_efectivo[11]['saldo_inicial']+row_activo_efectivo[12]['saldo_inicial']+row_activo_efectivo[13]['saldo_inicial']
        datas['suma_bienes_inmuebles']= suma_bienes_inmuebles
        datas['suma_bienes_inmuebles_si']= suma_bienes_inmuebles_si
        ####
        datas['software_saldo']= row_activo_efectivo[14]['saldo_final']
        datas['software_saldo_inicial']= row_activo_efectivo[14]['saldo_inicial']
        datas['licencias_info_saldo']= row_activo_efectivo[15]['saldo_final']
        datas['licencias_info_saldo_inicial']= row_activo_efectivo[15]['saldo_inicial']
        suma_activos_intangibles= row_activo_efectivo[14]['saldo_final']+row_activo_efectivo[15]['saldo_final']
        suma_activos_intangibles_si= row_activo_efectivo[14]['saldo_inicial']+row_activo_efectivo[15]['saldo_inicial']
        datas['suma_activos_intangibles']= suma_activos_intangibles
        datas['suma_activos_intangibles_si']= suma_activos_intangibles_si
        ####
        suma_depreciaciones= row_activo_efectivo[16]['saldo_final']*-1
        suma_depreciaciones_si= row_activo_efectivo[16]['saldo_inicial']*-1
        datas['suma_depreciaciones']= suma_depreciaciones
        datas['suma_depreciaciones_si']= suma_depreciaciones_si

        datas['suma_activos_no_circulantes']= suma_bienes_inmuebles+suma_activos_intangibles+suma_depreciaciones
        datas['suma_activos_no_circulantes_si']= suma_bienes_inmuebles_si+suma_activos_intangibles_si+suma_depreciaciones_si

        datas['suma_activos']= suma_efectivo_bancos+suma_derechos_recibir+suma_activos_inventario+suma_bienes_inmuebles+suma_activos_intangibles+suma_depreciaciones
        datas['suma_activos_si']= suma_efectivo_bancos_si+suma_derechos_recibir_si+suma_activos_inventario_si+suma_bienes_inmuebles_si+suma_activos_intangibles_si+suma_depreciaciones_si
        #####pasivo circulante#####
        sql_pasivo="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (186,226,253,275,277,283,291,312,318,2635)"""
        self.env.cr.execute(sql_pasivo % (self.anio,self.periodo))
        row_pasivo = self.env.cr.dictfetchall()

        datas['servicios_per_saldo']=row_pasivo[0]['saldo_final']
        datas['servicios_per_saldo_inicial']= row_pasivo[0]['saldo_inicial']
        datas['proveedor_saldo']= row_pasivo[1]['saldo_final']
        datas['proveedor_saldo_inicial']= row_pasivo[1]['saldo_inicial']
        datas['retenciones_contri']= row_pasivo[2]['saldo_final']
        datas['retenciones_contri_inicial']= row_pasivo[2]['saldo_inicial']
        datas['acreedores_dicersos_saldo']= row_pasivo[3]['saldo_final']
        datas['acreedores_dicersos_saldo_inicial']= row_pasivo[3]['saldo_inicial']
        datas['contingencias_saldo']= row_pasivo[4]['saldo_final']
        datas['contingencias_saldo_inicial']= row_pasivo[4]['saldo_inicial']
        suma_cuenta_pagar= row_pasivo[0]['saldo_final']+row_pasivo[1]['saldo_final']+row_pasivo[2]['saldo_final']+row_pasivo[3]['saldo_final']+row_pasivo[4]['saldo_final']
        suma_cuenta_pagar_si= row_pasivo[0]['saldo_inicial']+row_pasivo[1]['saldo_inicial']+row_pasivo[2]['saldo_inicial']+row_pasivo[3]['saldo_inicial']+row_pasivo[4]['saldo_inicial']
        datas['suma_cuenta_pagar']= suma_cuenta_pagar
        datas['suma_cuenta_pagar_si']= suma_cuenta_pagar_si

        datas['suma_pasivo_circulante']= suma_cuenta_pagar
        datas['suma_pasivo_circulante_si']= suma_cuenta_pagar_si

        ####pasivo no circulante
        datas['otras_provisiones_saldo']= row_pasivo[5]['saldo_final']
        datas['otras_provisiones_saldo_inicial']= row_pasivo[5]['saldo_inicial']
        suma_proviciones_lp=row_pasivo[5]['saldo_final']
        suma_proviciones_lp_si=row_pasivo[5]['saldo_inicial']
        datas['suma_proviciones_lp']= suma_proviciones_lp
        datas['suma_proviciones_lp_si']= suma_proviciones_lp_si
        ####
        suma_pasivo_no_cir=row_pasivo[5]['saldo_final']
        suma_pasivo_no_cir_si=row_pasivo[5]['saldo_inicial']
        datas['suma_pasivo_no_cir']= suma_pasivo_no_cir
        datas['suma_pasivo_no_cir_si']= suma_pasivo_no_cir_si
        suma_pasivos=suma_cuenta_pagar+suma_pasivo_no_cir
        suma_pasivos_si=suma_cuenta_pagar_si+suma_pasivo_no_cir_si
        datas['suma_pasivos']= suma_cuenta_pagar+suma_pasivo_no_cir
        datas['suma_pasivos_si']= suma_cuenta_pagar_si+suma_pasivo_no_cir_si

        ####hacienda publica
        datas['aportaciones_saldo']= row_pasivo[6]['saldo_final']
        datas['aportaciones_saldo_inicial']= row_pasivo[6]['saldo_inicial']
        datas['donaciones_capital_saldo']= row_pasivo[7]['saldo_final']
        datas['donaciones_capital_saldo_inicial']= row_pasivo[7]['saldo_inicial']
        suma_hacienda_publica_dona=row_pasivo[6]['saldo_final']+row_pasivo[7]['saldo_final']
        suma_hacienda_publica_dona_si=row_pasivo[6]['saldo_inicial']+row_pasivo[7]['saldo_inicial']
        datas['suma_hacienda_publica_dona']= suma_hacienda_publica_dona
        datas['suma_hacienda_publica_dona_si']= suma_hacienda_publica_dona_si
        ######
        sql_pasivo_ahorro="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in ('333','338','356','472','558','684')"""
        self.env.cr.execute(sql_pasivo_ahorro % (self.anio,self.periodo))
        row_pasivo_ahorro = self.env.cr.dictfetchall()
        sql_pasivo_ahorro_2019="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in ('333','338','356','472','558','684');"""
        self.env.cr.execute(sql_pasivo_ahorro_2019 % (self.anio-1,self.periodo))
        row_pasivo_ahorro_2019 = self.env.cr.dictfetchall()
        
        datas['trans_asig_saldo']= row_pasivo_ahorro[0]['saldo_final']
        datas['trans_asig_saldo_inicial']= row_pasivo_ahorro[0]['saldo_inicial']
        datas['otros_ingresos_saldo']= row_pasivo_ahorro[1]['saldo_final']
        datas['otros_ingresos_saldo_inicial']= row_pasivo_ahorro[1]['saldo_inicial']
        datas['servi_personales_saldo']= row_pasivo_ahorro[2]['saldo_final']
        datas['servi_personales_saldo_inicial']= row_pasivo_ahorro[2]['saldo_inicial']
        datas['materiales_sumi_saldo']= row_pasivo_ahorro[3]['saldo_final']
        datas['materiales_sumi_saldo_inicial']= row_pasivo_ahorro[3]['saldo_inicial']
        datas['servicios_general_saldo']= row_pasivo_ahorro[4]['saldo_final']
        datas['servicios_general_saldo_inicial']= row_pasivo_ahorro[4]['saldo_inicial']
        datas['otros_gastos_p_saldo']= row_pasivo_ahorro[5]['saldo_final']
        datas['otros_gastos_p_saldo_inicial']= row_pasivo_ahorro[5]['saldo_inicial']
        suma_a=row_pasivo_ahorro[0]['saldo_final']+ row_pasivo_ahorro[1]['saldo_final']
        suma_a_inicial=row_pasivo_ahorro[0]['saldo_inicial']+ row_pasivo_ahorro[1]['saldo_inicial']
        suma_b=row_pasivo_ahorro[2]['saldo_final']+ row_pasivo_ahorro[3]['saldo_final']+ row_pasivo_ahorro[4]['saldo_final']+ row_pasivo_ahorro[5]['saldo_final']
        suma_b_inicial=row_pasivo_ahorro[2]['saldo_inicial']+ row_pasivo_ahorro[3]['saldo_inicial']+ row_pasivo_ahorro[4]['saldo_inicial']+ row_pasivo_ahorro[5]['saldo_inicial']
        suma_re=suma_a-suma_b
        suma_re_saldo=suma_a_inicial-suma_b_inicial
        datas['suma_resultado_ejercicio']= suma_re
        datas['suma_resultado_ejercicio_si']=suma_re_saldo
        ###
        datas['resultado_del_ejerci_saldo']= row_pasivo[8]['saldo_final']
        datas['resultado_del_ejerci_saldo_inicial']= row_pasivo[8]['saldo_inicial']
        datas['resultado_ejer_anteriores']= row_pasivo[9]['saldo_final']*-1
        datas['resultado_ejer_anteriores_inicial']= row_pasivo[9]['saldo_inicial']*-1
        suma_hacienda_publica=suma_re+row_pasivo[9]['saldo_final']*-1
        suma_hacienda_publica_si=suma_re_saldo+row_pasivo[9]['saldo_inicial']*-1
        datas['suma_hacienda_publica']= suma_hacienda_publica
        datas['suma_hacienda_publica_si']= suma_hacienda_publica_si
        ###
        suma_hacienda_patrimonio=suma_hacienda_publica_dona+suma_hacienda_publica
        suma_hacienda_patrimonio_si=suma_hacienda_publica_dona_si+suma_hacienda_publica_si
        datas['suma_hacienda_patrimonio']= suma_hacienda_patrimonio
        datas['suma_hacienda_patrimonio_si']= suma_hacienda_patrimonio_si
        ###
        datas['suma_pasivo_hacienda']= suma_pasivos+suma_hacienda_patrimonio
        datas['suma_pasivo_hacienda_si']= suma_pasivos_si+suma_hacienda_patrimonio_si
        datas['anio_fiscal']= self.anio
        datas['periodo_fiscal']= self.periodo

        ####
        
        ##raise ValidationError("%s" % (datas))
        return self.env['report'].get_action([], 'reportes.report_situacion_financiera', data=datas)
