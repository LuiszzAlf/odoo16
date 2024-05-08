# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import base64 
import pandas as pd
import json
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta


class polizas_presupuestales_wizard(models.TransientModel):
    _name = 'polizas_presupuestales.wizard'

    partidas = fields.Many2many('presupuesto.partida_presupuestal', string='Posición presupuestaria',relation='partidas_polizas')
    capitulo = fields.Selection([('1000','1000'),('2000','2000'),('3000','3000'),('5000','5000')],string='Capitulo')
    clase_documento = fields.Many2many('presupuesto.clase_documento', string='Clase documento',relation='clase_documento', required=True)
    fecha_inicio =fields.Date(string='Fecha inicio', default=datetime.today())
    fecha_fin =fields.Date(string='Fecha fin', default=datetime.today())
    no_poliza = fields.Char(string='Poliza')
    concepto = fields.Char(string='concepto')
    elaboro = fields.Char(string='elaboro',default='SJGH')
    reviso = fields.Char(string='reviso',default='MPYM')
    vobo = fields.Char(string='vobo',default='JSV')
    autorizo = fields.Char(string='autorizo',default='ACRG')
    result_pc_html=fields.Html(string='Resultados',compute='search_pc_button')    
    csv_urls = fields.Char(compute='search_pc_button')

    
    
    def moves_poliza(self):
        
        pass


    
    def pdf_poliza(self):
        obj_poliza = self.env['polizas_presupuestales']
        ids_pareg=[]
        for par in self.partidas:
            ids_pareg.append(par.id)
        if(len(ids_pareg)>1):
            partidas=tuple(ids_pareg)
        else:
            if(self.partidas):
                partidas='('+str(ids_pareg[0])+')'
        clase_ids=[]
        for clase in self.clase_documento:
            clase_ids.append(clase.id)
        if(len(clase_ids)>1):
            clas_doc=tuple(clase_ids)
        else:
            clas_doc='('+str(clase_ids[0])+')'
        if(self.capitulo):
            capitulo=self.capitulo[:-3]
            sql_lineas = """(select
                            concat(SUBSTRING(code, 1, 3 ), '.0.0000.00') code, cuenta,capitulo sub_cta,
                            0 partida_id,clase_documento,'' "ref",sum(credit) credit,sum(debit) debit
                        from
                            presupuesto_view_polizas_documento
                        where
                            clase_documento in %s
                            and capitulo=%s
                            and fecha_documento between '%s' and '%s'
                        group by 1,2,3,4,5)                 
                        union all
                        (select code,cuenta,capitulo sub_cta,partida_id,
                            clase_documento,ref,credit,debit
                        from
                            presupuesto_view_polizas_documento
                        where
                            clase_documento in %s
                            and capitulo=%s
                            and fecha_documento between '%s' and '%s')
            order by code asc""" % (clas_doc,capitulo,self.fecha_inicio,self.fecha_fin,clas_doc,capitulo,self.fecha_inicio,self.fecha_fin)
        else:
            sql_lineas = """(select
                                 concat(SUBSTRING(code, 1, 3 ), '.0.0000.00') code,
                            cuenta,capitulo sub_cta,0 partida_id,clase_documento,
                            '' "ref",sum(credit) credit,sum(debit) debit
                            from
                                presupuesto_view_polizas_documento
                            where
                                clase_documento in %s
                                and partida_id in %s
                                and fecha_documento between '%s' and '%s'
                            group by 1,2,3,4,5)                 
                            union all
                            (select
                                code,cuenta,capitulo sub_cta,partida_id,
                                clase_documento,ref,credit,debit
                            from
                                presupuesto_view_polizas_documento
                            where
                                clase_documento in %s
                                and partida_id in %s
                                and fecha_documento between '%s' and '%s') 
            order by code asc;""" %(clas_doc,partidas,self.fecha_inicio,self.fecha_fin,clas_doc,partidas,self.fecha_inicio,self.fecha_fin)

        self.env.cr.execute(sql_lineas)
        results = self.env.cr.dictfetchall()
        
        datas = {}
        suma_cargo = 0
        suma_abono = 0
        lineas = []
        count = 0
        if(results):
            datas['lineas_cuenta'] = lineas
        else:
            raise ValidationError('No se encontraron resultados')
        df=pd.DataFrame.from_dict(results)
        cts_padre=df[df.code.str.contains('.0.0000.00')].filter(items=['code','ref','cuenta','sub_cta','credit','debit']).to_json(orient="records")
        cts_padre_parsed = json.loads(cts_padre)
        for item in cts_padre_parsed:
            filt=item['code'].split('.')
            ct_hijo=df[df.cuenta.str.contains(filt[0])].filter(items=['code','ref','cuenta','sub_cta','credit','debit']).to_json(orient="records")
            cuenta_nombre = self.env['account.account'].search([('code', '=', str(item['code']))])[0].name
            insert_padre = {
                            'nombre': cuenta_nombre,
                            'cuenta': filt[0],
                            'subcuenta': '',
                            'subsubcuenta': '',
                            'subsubsubcuenta': '',
                            'parcial': '',
                            'cargo': '{0:,.2f}'.format(float(item['debit'])),
                            'abono': '{0:,.2f}'.format(float(item['credit'])),
                            }
            suma_cargo+=item['debit']
            suma_abono+=item['credit']
            lineas.append(insert_padre)
            capitulos = []
            cts_sub_cta_parsed = json.loads(ct_hijo)
            for subc in cts_sub_cta_parsed:
                capitulos.append(subc['sub_cta'])
            for sub_cta in list(set(capitulos)):
                tot_sub_cta=0
                sub_cta_filter=filt[0]+'.'+str(sub_cta)
                sub_cta_nombre = self.env['account.account'].search([('code', '=', str(sub_cta_filter+'.0000.00'))])[0].name
                cts_sub_cta=df[df.code.str.contains(sub_cta_filter)].filter(items=['code','ref','cuenta','sub_cta','credit','debit']).to_json(orient="records")
                cts_sub_cta_parsed = json.loads(cts_sub_cta)
                for it in cts_sub_cta_parsed:
                    if(it['debit']==0):
                        parcial=it['credit']
                    else:
                        parcial=it['debit']
                    tot_sub_cta=tot_sub_cta+parcial
                insert_padre = {
                                'nombre': sub_cta_nombre,
                                'cuenta': '',
                                'subcuenta': sub_cta,
                                'subsubcuenta': '',
                                'subsubsubcuenta': '',
                                'parcial': '',
                                'cargo': '',
                                'abono': '',
                                }
                lineas.append(insert_padre)
                for it_part in cts_sub_cta_parsed:
                    subc = it_part['code'].split('.')
                    subsubcuenta_nombre = self.env['account.account'].search([('code', '=like', subc[0] + '.' + subc[1] + '.' + subc[2] + '%')])[0].name
                    subsubsubcuenta_nombre = self.env['account.account'].search([('code', '=', str(it_part['code']))])[0].name
                    if(it_part['debit']==0):
                        parcial=it_part['credit']
                    else:
                        parcial=it_part['debit']
                    for count in range(1,5):
                        if count == 1:
                            pass
                        if count == 2:
                            pass
                        if count == 3:
                            insert = {
                            'nombre':subsubcuenta_nombre,
                            'cuenta': '',
                            'subcuenta': '',
                            'subsubcuenta': subc[2],
                            'subsubsubcuenta': '',
                            'parcial': '',
                            'cargo': '',
                            'abono': '',
                            }
                            lineas.append(insert)
                        if count == 4:
                            insert = {
                            'nombre': subsubsubcuenta_nombre,
                            'cuenta': '',
                            'subcuenta': '',
                            'subsubcuenta': '',
                            'subsubsubcuenta': subc[3],
                            'parcial': '{0:,.2f}'.format(float(parcial)),
                            'cargo': '',
                            'abono': '',
                            }
                            lineas.append(insert)
                            count += 1
        
        datas['suma_abono'] = suma_abono
        datas['suma_cargo'] = suma_cargo
        
        create_poliza=obj_poliza.create({
                    'partidas': [(6, 0, ids_pareg)],
                    'capitulo':self.capitulo,
                    'clase_documento':[(6, 0, clase_ids)],
                    'fecha_inicio':self.fecha_inicio,
                    'fecha_fin':self.fecha_fin,
                    'no_poliza':self.no_poliza,
                    'concepto':self.concepto,
                    'elaboro':self.elaboro,
                    'reviso':self.reviso,
                    'vobo':self.vobo,
                    'autorizo':self.autorizo,
                    })
        id_poliza=0
        if(create_poliza):
            id_poliza=create_poliza.id

        form={
            'date':'De %s a %s'%(self.fecha_inicio,self.fecha_fin),
            'name':'CP-'+str(self.no_poliza),
            'concepto':self.concepto,
            'elaboro':self.elaboro,
            'reviso':self.reviso,
            'vobo':self.vobo,
            'autorizo':self.autorizo
        }
        datas['form'] = form



        return self.env['report'].get_action([], 'reportes.poliza_presupuestal', data=datas)
        

