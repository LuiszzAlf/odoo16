#-*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
from datetime import datetime
import calendar
from odoo import models, fields, api
from odoo.tools.translate import _
import collections
import json
import xlwt 
import xlsxwriter 
from PIL import Image
import base64 
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta
ALLOWED_HOSTS = "*"
def get_logo():
     with open ("/home/addons/GRP/presupuestos/static/src/img/logo.png", "r") as bmpfile:
        bmpdata = bmpfile.read()
        logo=base64.b64encode(bytes(str(bmpdata)))
        image_base64 = str(logo).decode('base64')
        image_data = StringIO(image_base64)
        img = Image.open(image_data).convert('RGB')
        img.save('/home/addons/GRP/presupuestos/static/src/img/tjacdmx2.bmp') 

class Funciones_internas(http.Controller):

    # Ruta para descargar Resguardo impreso por clave de empleado
    # desde Portal del empleado
    @http.route('/api/resguardo/pdf/<string:no_empleado>', auth='public', methods=['GET'], website=True)
    def get_resguardo_pdf(self, **kwargs):
        values = dict(kwargs)
        report = request.env['report'].sudo()
        solmodel = request.env['tjacdmx.resguardos'].sudo()
        solicitud = solmodel.search([('no_empleado','=',values['no_empleado'])])
        if(solicitud):
            pdf = report.get_pdf([solicitud.id],'reportes.resguardos_impre', data=solicitud.get_data_for_report_resguardo())
            filename = 'resguardo.pdf'
            pdfhttpheaders = [ ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)), ('Content-Disposition', 'attachment; filename="'+filename+'"'), ]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return http.request.render('business.no-resguardo')
    
    @http.route('/balanza_conta/<string:fecha_inicio>/<string:fecha_fin>/', type='http',auth='public',methods=['GET'])
    def balanza(self, **kwargs):
        values = dict(kwargs)
        sql_all_ht="""select
                            aa.id,
                            aa.code,
                            concat(aa.code, ' ', aa."name") as "name",
                            coalesce(sum(mp.debit), 0) as debe,
                            coalesce(sum(mp.credit), 0) as haber,
                            coalesce(sum(mp.debit), 0)-coalesce(sum(mp.credit), 0) as saldo
                        from
                            account_account aa
                        left join movimientos_polizas_presupuestal mp on
                            mp.account_id = aa.id
                            and mp.date between '%s' and '%s'
                        where aa.code like '%s'
                        group by 1,2,3
                        order by
                            aa.code;"""
        request.cr.execute(sql_all_ht % (values['fecha_inicio'],values['fecha_fin'],str('8%')))
        rows_sqlht = request.cr.dictfetchall()
        excel_encode = self.get_decode_excel(rows_sqlht)
        archivo_base64 = "data:application/octet-stream;charset=utf-16le;base64,"+excel_encode
        datas={'b64_data': archivo_base64,'items': rows_sqlht}
        
        return request.make_response(json.dumps(datas),
                [('Content-Type', 'application/json'),])

    @http.route('/balanza_contable/<int:periodo>/<int:periodo_fin>/<int:anio>/<int:radio_nivel_valanza>/', type='http',auth='public',methods=['GET'])
    def balanza_contable(self, **kwargs):
        values = dict(kwargs)
        anio=values['anio']
        periodo=values['periodo']
        periodo_f=values['periodo_fin']
        radio_nivel_valanza=values['radio_nivel_valanza']
        periodo_inicio=datetime(anio,periodo,01).date()
        periodo_fin=datetime(anio,periodo_f,01).date()
        sql_all_ht="""SELECT * from v_balanza where periodo=%s and anio='%s' and code not like '%s' order by code;"""
        sql_bal_nivel_mayor="""SELECT * from v_balanza
                                where periodo = %s
                                and anio='%s' 
                                and substring(split_part(code::TEXT,'.', 1),3,3)!='0'
                                and split_part(code::TEXT,'.', 1) not in ('114','123') 
                                and split_part(code::TEXT,'.', 2)='0'
                                and split_part(code::TEXT,'.', 3)='0000'
                                and split_part(code::TEXT,'.', 4)='00'
                                and code not like '%s'
                                order by code;"""
        sql_bal_nivel_mayor_rango="""SELECT  concat(b.code, ' ', b."name")  as cuentas,
                                b.code as code,
                                account_id,
                                sum(a.debe) debe,
                                sum(a.haber) haber
                                from tjacdmx_balanza_comprobacion a
                                inner join account_account b on b.id=a.account_id
                                where periodo between '%s' and  '%s'
                                and substring(split_part(b.code::TEXT,'.', 1),3,3)!='0'
                                and split_part(b.code::TEXT,'.', 1) not in ('114','123') 
                                and split_part(code::TEXT,'.', 2)='0'
                                and split_part(code::TEXT,'.', 3)='0000'
                                and split_part(code::TEXT,'.', 4)='00'
                                and b.code not like '%s'
                                group by 1,2,3
                                order by b.code;"""
        sql_bal_ultimo_nivel="""SELECT distinct b."name" as cuentas,b.code,account_id,a.periodo,a.saldo_inicial,a.debe,a.haber,a.saldo_final 
                                from tjacdmx_balanza_comprobacion a
                                inner join account_account b on b.id=a.account_id  and b.code not like '%s'
                                where 
                                split_part(code::TEXT,'.', 1)='322' and account_id not in (2635,320) and periodo='%s'
                                or split_part(code::TEXT,'.', 1)='126' and account_id not in (170,171,172,173,2635,320,180)  and periodo='%s'
                                or split_part(code::TEXT,'.', 1)='115' and periodo='%s'
                                or split_part(code::TEXT,'.', 4)>='01' and periodo='%s'
                                or account_id in (165,162,181,182,174,175,176,177,178,179,141,142,146,158,705,754,877)
                                and periodo='%s'
                                order by b.code;
                                        """
        sql_bal_ultimo_nivel_rango="""(select b.name as cuentas,
                                            a.code,
                                            a.account_id,
                                            c.saldo_inicial as saldo_inicial,
                                            sum(a.debe) as debe,
                                            sum(a.haber) as haber,
                                            c.saldo_inicial + sum(a.debe) - sum(a.haber) as saldo_final
                                        from
                                            v_balanza a
                                            inner join account_account b on b.id = a.account_id
                                            inner join v_balanza c on c.account_id = a.account_id and c.periodo = '%s' and c.anio = '%s'
                                        where
                                            a.code not like '%s'
                                            and split_part(a.code :: text, '.', 4) >= '01'
                                            and a.anio = '%s'
                                            and a.periodo between '%s' and '%s'
                                        group by 1,2,3,4 order by code)
                                        union
                                        (select
                                            b.name as cuentas,
                                            a.code,
                                            a.account_id,
                                            c.saldo_inicial as saldo_inicial,
                                            sum(a.debe) as debe,
                                            sum(a.haber) as haber,
                                            c.saldo_inicial + sum(a.debe) - sum(a.haber) as saldo_final
                                        from
                                            v_balanza a
                                            inner join account_account b on b.id = a.account_id
                                            inner join v_balanza c on c.account_id = a.account_id and c.periodo = '%s' and c.anio = '%s'
                                        where
                                            a.code not like '%s'
                                            and a.code not like '%s'
                                            and a.account_id in (110,111,112,113,114,115,125,141,142,146,158,162,165,174,175,176,177,178,179,181,182,226,321,322,323,324,325,326,327,328,329,330,705,2927)
                                            and a.anio = '%s'
                                            and a.periodo between '%s' and '%s'
                                        group by 1,2,3,4
                                        order by code) order by code;"""
        sql_bal_todo_rango="""select
                                b.name as cuentas,
                                a.code,
                                a.account_id,
                                coalesce(c.saldo_inicial, 0) as saldo_inicial,
                                sum(a.debe) as debe,
                                sum(a.haber) as haber,
                                coalesce(c.saldo_inicial, 0) + sum(a.debe)-sum(a.haber) as saldo_final
                            from
                                v_balanza a
                            inner join account_account b on
                                b.id = a.account_id
                            left join v_balanza c on
                                c.account_id = a.account_id
                                and c.periodo = '%s'
                                and c.anio = '%s'
                            where
                                a.anio = '%s'
                                and a.periodo between '%s' and '%s'
                            and a.code not like '%s'
                            group by 1,2,3,4
                            order by
                                code;"""
        if(radio_nivel_valanza==1):
            request.cr.execute(sql_all_ht % (periodo,anio,str('8%')))
        elif (radio_nivel_valanza==2):
            request.cr.execute(sql_bal_nivel_mayor % (periodo,anio,str('8%')))
        elif (radio_nivel_valanza==3):
            request.cr.execute(sql_bal_nivel_mayor_rango % (str(periodo_inicio),str(periodo_fin),str('8%')))
        elif (radio_nivel_valanza==4):
            request.cr.execute(sql_bal_ultimo_nivel % (str('8%'),periodo_inicio,periodo_inicio,periodo_inicio,periodo_inicio,periodo_inicio))
        elif (radio_nivel_valanza==5):
            request.cr.execute(sql_bal_ultimo_nivel_rango % (periodo,anio,str('8%'),anio,periodo,periodo_f,periodo,anio,str('8%'),str('211.2.0000.00%'),anio,periodo,periodo_f))
        elif (radio_nivel_valanza==6):
            request.cr.execute(sql_bal_todo_rango % (periodo,anio,anio,periodo,periodo_f,str('8%')))
        rows_sqlht = request.cr.dictfetchall()
        ids=[]
        if (radio_nivel_valanza==1 or radio_nivel_valanza==2 or radio_nivel_valanza==4 ):
            for i in rows_sqlht:
                debe='$'+'{:0,.2f}'.format(i['debe'])
                haber='$'+'{:0,.2f}'.format(i['haber'])
                saldo_inicial='$'+'{:0,.2f}'.format(i['saldo_inicial'])
                saldo_final='$'+'{:0,.2f}'.format(i['saldo_final'])
                cuentas = {
                    'cuenta': i['cuentas'],
                    'code': i['code'],
                    'periodo': i['periodo'],
                    'anio': anio,
                    'saldo_inicial': saldo_inicial,
                    'debe': debe,
                    'haber': haber,
                    'saldo_final': saldo_final}
                ids.append(cuentas)
        elif (radio_nivel_valanza==3):
            for i in rows_sqlht:
                sql_si_sf="""SELECT saldo_inicial,saldo_final from v_balanza where periodo in (%s,%s) and account_id=%s limit 1;"""
                request.cr.execute(sql_si_sf % (periodo,periodo_f,i['account_id']))
                rows_code = request.cr.dictfetchall()
                debe='$'+'{:0,.2f}'.format(i['debe'])
                haber='$'+'{:0,.2f}'.format(i['haber'])
                if(rows_code):
                    saldo_inicial='$'+'{:0,.2f}'.format(rows_code[0]['saldo_inicial'])
                    saldo_fi=rows_code[0]['saldo_inicial']+i['debe']-i['haber']
                    saldo_final='$'+'{:0,.2f}'.format(saldo_fi)
                else:
                    saldo_inicial='$'+'{:0,.2f}'.format(0)
                    saldo_final='$'+'{:0,.2f}'.format(0)
               
                cuentas = {
                    'cuenta': i['cuentas'],
                    'code': i['code'],
                    'saldo_inicial': saldo_inicial,
                    'debe': debe,
                    'haber': haber,
                    'saldo_final': saldo_final}
                ids.append(cuentas)
        elif (radio_nivel_valanza==6 or radio_nivel_valanza==5):
            for i in rows_sqlht:
                cuentas = {
                    'cuenta': i['cuentas'],
                    'code': i['code'],
                    'saldo_inicial': i['saldo_inicial'],
                    'periodo_fecha': periodo,
                    'debe': i['debe'],
                    'haber': i['haber'],
                    'saldo_final': i['saldo_final']}
                ids.append(cuentas)
       
        excel_encode = self.get_decode_excel_bc(ids,radio_nivel_valanza)
        archivo_base64 = "data:application/octet-stream;charset=utf-16le;base64,"+excel_encode
        datas={'b64_data': archivo_base64,'items': ids}
        
        return request.make_response(json.dumps(datas),
                [('Content-Type', 'application/json'),])

    @api.multi
    def get_decode_excel_bc(self, ids,name):
        if(name==1):
            nombre_balanza='Balanza'
        elif (name==2):
            nombre_balanza='Nivel Mayor'
        elif (name==3):
            nombre_balanza='Nivel Mayor (Rango)'
        elif (name==4):
            nombre_balanza='Ultimo Nivel'
        elif (name==5):
            nombre_balanza='Ultimo Nivel (Rango)'
        elif (name==6):
            nombre_balanza='(Rango)'

        style0 = xlwt.easyxf('font: name Arial, bold on;\
                                pattern: pattern solid, fore_colour white;\
                                borders: top_color black, bottom_color black, right_color black, left_color black,\
                                left thin, right thin, top thin, bottom thin;'
                                , num_format_str='#,##0.00')
        style00 = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            align: vert centre, horiz centre;', num_format_str='#,##0.00')

        style1 = xlwt.easyxf('font: name Arial, bold 1,height 250;\
                            pattern: pattern solid, fore_colour aqua; \
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item_money = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        style_item_money_bold = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Balanza contable')
        # build_img=get_logo()
        sheet.insert_bitmap('/home/addons/GRP/presupuestos/static/src/img/tjacdmx2.bmp', 0, 0, x=1, y=1, scale_x=0.23, scale_y=0.18)
        sheet.write_merge(0, 0, 2, 5, 'TRIBUNAL DE JUSTICIA ADMINISTRATIVA.', style00)
        sheet.write_merge(1, 1, 2, 5, 'DE LA CIUDAD DE MEXICO.', style00)
        sheet.write_merge(2, 2, 2, 5, 'Sistema Contable Integrador Odoo', style00)
        sheet.write_merge(3, 3, 2, 5, nombre_balanza, style00)
        sheet.write_merge(4, 4, 2, 5, u'Balanza general de comprobación', style00)
        sheet.write_merge(6, 6, 0, 0, 'Codigo', style1)
        sheet.write_merge(6, 6, 1, 1, 'Cuenta', style1)
        sheet.write_merge(6, 6, 2, 2,'Saldo inicial', style1)
        sheet.write_merge(6, 6, 3, 3,'Debe', style1)
        sheet.write_merge(6, 6, 4, 4, 'Haber', style1)
        sheet.write_merge(6, 6, 5, 5, 'Saldo', style1)
        n = 7
        for item in ids:               
            sheet.write_merge(n, n, 0, 0, item['code'], style_item)
            sheet.write_merge(n, n, 1, 1, item['cuenta'], style_item)
            sheet.write_merge(n, n, 2, 2, item['saldo_inicial'], style_item_money)
            sheet.write_merge(n, n, 3, 3, item['debe'], style_item_money)
            sheet.write_merge(n, n, 4, 4, item['haber'], style_item_money)
            sheet.write_merge(n, n, 5, 5, item['saldo_final'], style_item_money)
            n += 1
        output = StringIO()
        workbook.save(output)
        out = base64.encodestring(output.getvalue())
        return out

    @api.multi
    def get_decode_excel(self, ids):
        style0 = xlwt.easyxf('font: name Arial, bold on;\
                                pattern: pattern solid, fore_colour white;\
                                borders: top_color black, bottom_color black, right_color black, left_color black,\
                                left thin, right thin, top thin, bottom thin;'
                                , num_format_str='#,##0.00')
        style00 = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            align: vert centre, horiz centre;', num_format_str='#,##0.00')

        style1 = xlwt.easyxf('font: name Arial, bold 1,height 250;\
                            pattern: pattern solid, fore_colour aqua; \
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item_money = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        style_item_money_bold = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Balanza contable')
        # build_img=get_logo()
        sheet.insert_bitmap('/home/addons/GRP/presupuestos/static/src/img/tjacdmx2.bmp', 0, 0, x=1, y=1, scale_x=0.23, scale_y=0.18)
        #sheet.insert_bitmap('/mnt/grp/GRP.git/presupuestos/static/src/img/tjacdmx2.bmp', 0, 0, x=1, y=1, scale_x=0.23, scale_y=0.18)
        sheet.write_merge(0, 0, 2, 5, 'TRIBUNAL DE JUSTICIA ADMINISTRATIVA.', style00)
        sheet.write_merge(1, 1, 2, 5, 'DE LA CIUDAD DE MEXICO.', style00)
        sheet.write_merge(2, 2, 2, 5, 'Sistema Contable Integrador Odoo', style00)
        sheet.write_merge(3, 3, 2, 5, 'Presupuesto', style00)
        sheet.write_merge(4, 5, 2, 5, u'Balanza de comprobación presupuestal', style00)
        sheet.write_merge(6, 6, 0, 0, 'Codigo', style1)
        sheet.write_merge(6, 6, 1, 1, 'Cuenta', style1)
        sheet.write_merge(6, 6, 2, 2,'Debe', style1)
        sheet.write_merge(6, 6, 3, 3, 'Haber', style1)
        sheet.write_merge(6, 6, 4, 4, 'Saldo', style1)
        n = 7
        for item in ids:               
            sheet.write_merge(n, n, 0, 0, item['code'], style_item)
            sheet.write_merge(n, n, 1, 1, item['name'], style_item)
            sheet.write_merge(n, n, 2, 2, item['debe'], style_item_money)
            sheet.write_merge(n, n, 3, 3, item['haber'], style_item_money)
            sheet.write_merge(n, n, 4, 4, item['saldo'], style_item_money)
            n += 1
        output = StringIO()
        workbook.save(output)
        out = base64.encodestring(output.getvalue())
        return out
    
    @http.route('/carga_masiva/',auth='user',website=True)
    def home(self, **kwargs):
        return http.request.render('presupuestos.carga_masiva')

    @http.route('/carga_masiva_comprometido/',auth='user',website=True)
    def carga_masiva_comprimiso_home(self, **kwargs):
        return http.request.render('presupuestos.carga_masiva_compromiso')
    
    @http.route('/api/carga_masiva_validate/',cors=ALLOWED_HOSTS,auth='public',type='http',methods=['GET'])
    def valida_documentos_masivos(self, **kwargs):
        values = dict(kwargs)
        if(values['documentos']!=''):
            obj=json.loads(values['documentos'])
            lista=[]
            documentos_create = []
            obj_documento = request.env['presupuesto.documento'].sudo()
            for i in obj:
                control_presupuesto = request.env['presupuesto.control_presupuesto'].sudo()
                fecha = datetime.strptime(i['fecha'], '%Y-%m-%d') if i['fecha'] else datetime.today()
                partida = request.env['presupuesto.partida_presupuestal'].sudo().search([('partida_presupuestal', '=', i['partida'])], limit=1)
                area_funcional = request.env['presupuesto.area_funcional'].sudo().search([('area_funcional', '=', i['area_funcional'])], limit=1)
                ejercicio=fecha.year
                periodo=fecha.month
                if(partida and area_funcional):
                    cp = control_presupuesto.search([
                            ('ejercicio', '=', ejercicio),
                            ('periodo', '=', periodo),
                            ('version', '=', 1),
                            ('fondo_economico', '=', 1),
                            ('posicion_presupuestaria', '=', partida.id),
                            ('centro_gestor', '=', 1),
                            ('area_funcional', '=', area_funcional.id) ])
                    if cp:
                        detalle="""El documento original con la partida %s ya existe""" % i['partida']
                        datas={'state':'error','detalle':detalle}
                    else:
                        doc_origin = {
                                    'centro_gestor':1,
                                    'area_funcional': area_funcional.id,
                                    'fondo_economico': 1,
                                    'posicion_presupuestaria': partida.id,
                                    'importe': float(i['importe']),
                                    }
                        lista.append(doc_origin)
                else:
                    datas={'state':'error','data':'error'}
            if(len(obj)!=len(lista)):
                datas={'state':'error','data':'error',
                        'detalle':'Algunos elementos son incorrectos.'}
            else:
                datas={'state':'success','data':list(lista)}
        else:
            datas={'state':'error','data':'error'}
        return request.make_response(json.dumps(datas),
                [('Content-Type', 'application/json'),])
    
    @http.route('/api/carga_masiva_create/',type='http', auth='public', website=True, cors='*')
    def crea_documentos_masivos(self, **kwargs):
        values = dict(kwargs)
        if(values['documentos']!=''):
            obj=json.loads(values['documentos'])
            lista=[]
            documentos_create = []
            obj_documento = request.env['presupuesto.documento'].sudo()
            for i in obj:
                control_presupuesto = request.env['presupuesto.control_presupuesto'].sudo()
                fecha = datetime.strptime(i['fecha'], '%Y-%m-%d') if i['fecha'] else datetime.today()
                partida = request.env['presupuesto.partida_presupuestal'].sudo().search([('partida_presupuestal', '=', i['partida'])], limit=1)
                area_funcional = request.env['presupuesto.area_funcional'].sudo().search([('area_funcional', '=', i['area_funcional'])], limit=1)
                ejercicio=fecha.year
                periodo=fecha.month
                if(partida and area_funcional):
                    cp = control_presupuesto.search([
                            ('ejercicio', '=', ejercicio),
                            ('periodo', '=', periodo),
                            ('version', '=', 1),
                            ('fondo_economico', '=', 1),
                            ('posicion_presupuestaria', '=', partida.id),
                            ('centro_gestor', '=', 1),
                            ('area_funcional', '=', area_funcional.id) ])
                    if cp:
                        detalle="""El documento original con la partida %s ya existe""" % i['partida']
                        datas={'state':'success','detalle':detalle}
                    else:
                        lineas_documento = []
                        line = [0, False,{
                                'centro_gestor':1,
                                'area_funcional': area_funcional.id,
                                'fondo_economico': 1,
                                'posicion_presupuestaria': partida.id,
                                'importe': float(i['importe'])
                                }]
                        lineas_documento.append(line)
                        obj_doc={ 
                            'concepto': str(i['concepto']),
                            'clase_documento': 3,
                            'version': 1,
                            'ejercicio':ejercicio,
                            'periodo': int(periodo),
                            'periodo_origen':int(periodo),
                            'is_periodo_anterior':1,
                            'fecha_contabilizacion':i['fecha'],
                            'fecha_documento': i['fecha'],
                            'partida_presupuestal':partida.id,
                            'detalle_documento_ids': lineas_documento
                        }
                        documento =obj_documento.create({ 
                            'concepto': str(i['concepto']),
                            'clase_documento': 3,
                            'version': 1,
                            'ejercicio':ejercicio,
                            'periodo': int(periodo),
                            'periodo_origen':int(periodo),
                            'is_periodo_anterior':1,
                            'fecha_contabilizacion':i['fecha'],
                            'fecha_documento': i['fecha'],
                            'partida_presupuestal':partida.id,
                            'detalle_documento_ids': lineas_documento
                        })
                        documentos_create.append(obj_doc)
                        lista.append(obj_doc)
                else:
                    datas={'state':'error','data':'error'}
            if(len(obj)!=len(lista)):
                detallerror="""Algunos elementos son incorrectos. %s de """ % len(obj),len(lista)
                datas={'state':'error','data':list(lista),
                        'detalle':detallerror}
            else:
                datas={'state':'success','data':list(lista)}  
        else:
            datas={'state':'error','data':'error'}
        
        return request.make_response(json.dumps(datas),
                [('Content-Type', 'application/json'),])



    @http.route('/api/carga_masiva_comprometido_validate/',type='http', auth='public', website=True, cors='*')
    def valida_documentos_comprometido_masivos(self, **kwargs):
        values = dict(kwargs)
        if(values['documentos']!=''):
            obj=json.loads(values['documentos'])
            lista=[]
            errores=[]
            documentos_create = []
            obj_documento = request.env['presupuesto.documento'].sudo()
            obj_documento_detalle = request.env['presupuesto.detalle_documento'].sudo()
            for i in obj:
                control_presupuesto = request.env['presupuesto.control_presupuesto'].sudo()
                fecha = datetime.strptime(i['fecha'], '%Y-%m-%d') if i['fecha'] else datetime.today()
                partida = request.env['presupuesto.partida_presupuestal'].sudo().search([('partida_presupuestal', '=', i['partida'])], limit=1)
                area_funcional = request.env['presupuesto.area_funcional'].sudo().search([('area_funcional', '=', i['area_funcional'])], limit=1)
                ejercicio=fecha.year
                periodo=fecha.month
                if(partida and area_funcional):
                    cp = control_presupuesto.search([
                            ('ejercicio', '=', ejercicio),
                            ('periodo', '=', periodo),
                            ('version', '=', 1),
                            ('fondo_economico', '=', 1),
                            ('posicion_presupuestaria', '=', partida.id),
                            ('centro_gestor', '=', 1),
                            ('area_funcional', '=', area_funcional.id) ])
                    if cp:
                        pass
                    else:
                        detalle="""No se tiene presupuesto para la partida %s""" % i['partida']
                        datas={'detalle':detalle}
                        errores.append(datas)
                else:
                    detalle="""La informacion proporcionada es incorrecta"""
                    datas={'error':detalle}
                    errores.append(datas)
            if(errores):
                datas={'state':'error','data':list(errores),'detalle':'Algunos elementos son incorrectos.'}
            else:
                datas={'state':'succes','detalle':'Documentos listos para cargar'}
        else:
            datas={'state':'error','data':'error'}     

        return request.make_response(json.dumps(datas),
                [('Content-Type', 'application/json'),])

    @http.route('/api/carga_masiva_comprometido_create/',type='http', auth='public', website=True, cors='*')
    def crea_documentos_comprometido_masivos(self, **kwargs):
        values = dict(kwargs)
        if(values['documentos']!=''):
            obj=json.loads(values['documentos'])
            lista=[]
            errores=[]
            documentos_create = []
            documentos_error = []
            obj_documento = request.env['presupuesto.documento'].sudo()
            for i in obj:
                control_presupuesto = request.env['presupuesto.control_presupuesto'].sudo()
                fecha = datetime.strptime(i['fecha'], '%Y-%m-%d') if i['fecha'] else datetime.today()
                partida = request.env['presupuesto.partida_presupuestal'].sudo().search([('partida_presupuestal', '=', i['partida'])], limit=1)
                area_funcional = request.env['presupuesto.area_funcional'].sudo().search([('area_funcional', '=', i['area_funcional'])], limit=1)
                ejercicio=fecha.year
                periodo=fecha.month
                if(i['clase']=='comprometido'):
                    clase_docuemento=6
                elif(i['clase']=='devengado'):
                    clase_docuemento=7
                elif(i['clase']=='ejercido'):
                    clase_docuemento=9
                elif(i['clase']=='pagado'):
                    clase_docuemento=8

                if(partida and area_funcional and clase_docuemento):
                    cp = control_presupuesto.search([
                            ('ejercicio', '=', ejercicio),
                            ('periodo', '=', periodo),
                            ('version', '=', 1),
                            ('fondo_economico', '=', 1),
                            ('posicion_presupuestaria', '=', partida.id),
                            ('centro_gestor', '=', 1),
                            ('area_funcional', '=', area_funcional.id) ])
                    if cp:
                        lineas_documento = []
                        line = [0, False,{
                                'centro_gestor':1,
                                'area_funcional': area_funcional.id,
                                'fondo_economico': 1,
                                'posicion_presupuestaria': partida.id,
                                'importe': float(i['importe'])
                                }]
                        lineas_documento.append(line)
                        obj_doc={ 
                            'concepto': str(i['concepto']),
                            'clase_documento': clase_docuemento,
                            'version': 1,
                            'ejercicio':ejercicio,
                            'periodo': int(periodo),
                            'periodo_origen':int(periodo),
                            'fecha_contabilizacion':i['fecha'],
                            'fecha_documento': i['fecha'],
                            'partida_presupuestal':partida.id,
                            'detalle_documento_ids': lineas_documento
                        }
                        documento =obj_documento.create({ 
                            'concepto': str(i['concepto']),
                            'clase_documento': clase_docuemento,
                            'version': 1,
                            'ejercicio':ejercicio,
                            'periodo': int(periodo),
                            'periodo_origen':int(periodo),
                            'fecha_contabilizacion':i['fecha'],
                            'fecha_documento': i['fecha'],
                            'partida_presupuestal':partida.id,
                            'detalle_documento_ids': lineas_documento
                        })
                        if(documento):
                            lista.append(obj_doc)
                    else:
                        detalle="""No se tiene presupuesto para la partida %s""" % i['partida']
                        datas={'detalle':detalle}
                        errores.append(datas)

                else:
                    error={'state':'error','data':'error'}
            if(len(obj)!=len(lista)):
                detallerror="""Algunos elementos son incorrectos. %s de %s""" % (len(obj),len(lista))
                datas={'state':'error','data':documentos_error,
                        'detalle':detallerror}
            else:
                datas={'state':'success','data':list(lista)}  
        else:
            datas={'state':'error','data':'error'}
        
        return request.make_response(json.dumps(datas),
                [('Content-Type', 'application/json'),])

    @http.route('/balanza_contablev2/<int:periodo>/<int:periodo_fin>/<int:anio>/<int:radio_nivel_valanza>/', type='http',auth='public',methods=['GET'])
    def balanza_contablev2(self, **kwargs):
        values = dict(kwargs)
        anio=values['anio']
        periodo=values['periodo']
        periodo_f=values['periodo_fin']
        radio_nivel_valanza=values['radio_nivel_valanza']
        periodo_inicio=datetime(anio,periodo,01).date()#obtiene el primer dia del mes 
        if(periodo==1):
            periodo_inicio_anterior=12
            anio_inicio_anterior=anio-1
        else:
            periodo_inicio_anterior=periodo-1
            anio_inicio_anterior=anio
        last_day = calendar.monthrange(anio,periodo)[1] #obtine el ultimo dia del mes
        last_dayf = calendar.monthrange(anio,periodo_f)[1] 
        periodo_inicio_dia_fin = datetime(anio,periodo,last_day).date()#obtiene el ultimo dia del mes 
        periodo_fin_dia_fin = datetime(anio,periodo_f,last_dayf).date()
        saldos=[]
        filter=""""""
        if(radio_nivel_valanza==1):
            filter="""where aa.code not like '8%'"""
        
        elif(radio_nivel_valanza==2):
            filter="""where substring(split_part(aa.code::TEXT,'.', 1),3,3)!='0'
                            and split_part(aa.code::TEXT,'.', 1) not in ('114','123') 
                            and split_part(aa.code::TEXT,'.', 2)='0'
                            and split_part(aa.code::TEXT,'.', 3)='0000'
                            and split_part(aa.code::TEXT,'.', 4)='00'"""
        elif(radio_nivel_valanza==3):
            filter="""where substring(split_part(aa.code::TEXT,'.', 1),3,3)!='0'
                            and split_part(aa.code::TEXT,'.', 1) not in ('114','123') 
                            and split_part(aa.code::TEXT,'.', 2)='0'
                            and split_part(aa.code::TEXT,'.', 3)='0000'
                            and split_part(aa.code::TEXT,'.', 4)='00'"""
        elif(radio_nivel_valanza==4):
            filter="""where split_part(code::TEXT,'.', 1)='322' and account_id not in (2635,320)
                                or account_id not in (180,170,171,172,173,2635,320) and split_part(code::TEXT,'.', 1)='126' 
                                or split_part(code::TEXT,'.', 1)='115'
                                or split_part(code::TEXT,'.', 4)>='01'
                                or account_id in (165,162,181,182,174,175,176,177,178,179,141,142,146,158,705,754,877)"""
        elif(radio_nivel_valanza==5):
            filter="""where split_part(code::TEXT,'.', 1)='322' and account_id not in (2635,320)
                                or account_id not in (180,170,171,172,173,2635,320) and split_part(code::TEXT,'.', 1)='126' 
                                or split_part(code::TEXT,'.', 1)='115'
                                or split_part(code::TEXT,'.', 4)>='01'
                                or account_id in (165,162,181,182,174,175,176,177,178,179,141,142,146,158,705,754,877)"""
        if(periodo==1 and radio_nivel_valanza==1):
            plan_contable="""select 
                                    aa.id,
                                    aa.code,
                                    concat(aa.code, ' ', aa."name") nombre,
                                    coalesce(vb.saldo_inicial, 0) saldo_inicial,
                                    coalesce(sum(vb.debe),0)  AS cargo,
                                    coalesce(sum(vb.haber),0) AS abono,
                                    coalesce(vb.saldo_inicial, 0)+coalesce(sum(vb.debe),0)-coalesce(sum(vb.haber),0) AS saldo_final,
                                    coalesce(vb.saldo_inicial, 0)-coalesce(sum(vb.haber),0)+coalesce(sum(vb.debe),0) AS saldo_final_deudora
                                from account_account aa
                                    left join v_balanza vb on  vb.account_id=aa.id and vb.periodo=%s and vb.anio='%s'
                                %s
                                GROUP by 1,2,3,4
                                order by aa.code;"""
        else:
            plan_contable="""select 
                        aa.id,
                        aa.code,
                        concat(aa.code, ' ', aa."name") nombre,
                        (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END) saldo_inicial,
                        coalesce(sum(mp.debit),0)  AS cargo,
                        coalesce(sum(mp.credit),0) AS abono,
                        (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END)+coalesce(sum(mp.debit),0)-coalesce(sum(mp.credit),0) AS saldo_final,
                        (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END)-coalesce(sum(mp.credit),0)+coalesce(sum(mp.debit),0) AS saldo_final_deudora
                    from account_account aa
                        left join movimientos_polizas mp on mp.account_id = aa.id and mp.date between '%s' and '%s'
                        left join v_balanza vb on  vb.account_id=aa.id and vb.periodo=%s and vb.anio='%s'
                    %s
                    GROUP by 1,2,3,4
                    order by aa.code;"""
        if(radio_nivel_valanza==1):
            if(periodo==1):
                request.cr.execute(plan_contable%(periodo,anio,filter))
            else:
                request.cr.execute(plan_contable%(str('8%'),str('8%'),str('8%'),periodo_inicio,periodo_inicio_dia_fin,periodo_inicio_anterior,anio_inicio_anterior,filter))
        elif(radio_nivel_valanza==3):
            request.cr.execute(plan_contable%(str('8%'),str('8%'),str('8%'),periodo_inicio,periodo_fin_dia_fin,periodo_inicio_anterior,anio_inicio_anterior,filter))
        elif(radio_nivel_valanza==4):
            request.cr.execute(plan_contable%(str('8%'),str('8%'),str('8%'),periodo_inicio,periodo_fin_dia_fin,periodo_inicio_anterior,anio_inicio_anterior,filter))
        elif(radio_nivel_valanza==6):
            filter="""where aa.code not like '8%'"""
            request.cr.execute(plan_contable%(str('8%'),str('8%'),str('8%'),periodo_inicio,periodo_fin_dia_fin,periodo_inicio_anterior,anio_inicio_anterior,filter))

        rows_sql_plan_contable = request.cr.dictfetchall()
        for i in rows_sql_plan_contable:
            cuenta = {
                     'code': i['code'],
                     'cuenta':  i['nombre'],
                     'saldo_inicial': '$'+'{:0,.2f}'.format(i['saldo_inicial']),
                     'debe': '$'+'{:0,.2f}'.format(i['cargo']),
                     'haber':  '$'+'{:0,.2f}'.format(i['abono']),
                     'saldo_final':  '$'+'{:0,.2f}'.format(i['saldo_final']),
                     }
            saldos.append(cuenta)
        excel_encode = self.get_decode_excel_bc(saldos,radio_nivel_valanza)
        archivo_base64 = "data:application/octet-stream;charset=utf-16le;base64,"+excel_encode
        datas={'b64_data': archivo_base64,'items': saldos}
        
        return request.make_response(json.dumps(datas),
                [('Content-Type', 'application/json'),])


    @http.route('/activos_depreciacion/<int:tipo>/<string:fecha_fin_cal>/<string:categorias_cal>', type='http',auth='public',methods=['GET'])
    def activos_depreciacion(self, **kwargs):
        values = dict(kwargs)
        fecha_fin_cal=values['fecha_fin_cal']
        categorias_cal=values['categorias_cal']
        tipo_cal=values['tipo']
        if(tipo_cal==1):
            ids_categ=[]
            for cat in categorias_cal:
                ids_categ.append(cat)
            cats=str(ids_categ).replace(']', '').replace('[', '')
            sql_all="""with saldo_anterior as (
                        (
                            select aadl.asset_id id_activo,
                                coalesce(sum(aadl.amount), 0) valor_anterior2018
                            from account_asset_depreciation_line aadl
                            where extract(
                                    year
                                    from DATE (aadl.depreciation_date)
                                ) <= '2018'
                            group by 1
                        )
                    )
                    select aaa."name" nombre_activo,
                        aaa.code referencia,
                        aaa."date" fecha_activo,
                        aaa.value valor_bruto,
                        coalesce(
                            (
                                select valor_anterior2018
                                from saldo_anterior
                                where id_activo = aaa.id
                            ),
                            0
                        ) valor_anterior2018,
                        (
                            sum(aadl.amount) + coalesce(
                                (
                                    select valor_anterior2018
                                    from saldo_anterior
                                    where id_activo = aaa.id
                                ),
                                0
                            )
                        ) total_depreciado,
                        aaa.value -(
                            sum(aadl.amount) + coalesce(
                                (
                                    select valor_anterior2018
                                    from saldo_anterior
                                    where id_activo = aaa.id
                                ),
                                0
                            )
                        ) residual
                    from account_asset_asset aaa
                        inner join account_asset_depreciation_line aadl on
                        aaa.id = aadl.asset_id
                        and aadl.depreciation_date <= '%s'
                    where aadl.move_id > 0
                        and category_id in (%s)
                        and state = 'open'
                    group by 1,2,3,4,5;"""
            request.cr.execute(sql_all % (fecha_fin_cal,categorias_cal))
            rows_sql = request.cr.dictfetchall()
            activos_rows=[]
            for i in rows_sql:
                activos = {
                    'nombre_activo': i['nombre_activo'],
                    'referencia': i['referencia'],
                    'fecha_activo': i['fecha_activo'],
                    'valor_bruto': i['valor_bruto'],
                    'valor_anterior2018': i['valor_anterior2018'],
                    'total_depreciado': i['total_depreciado'],
                    'residual': i['residual']}
                activos_rows.append(activos)
            excel_encode = self.get_decode_excel_reporte_resgurardo(activos_rows)
        elif(tipo_cal==2):
            ids_categ=[]
            for cat in categorias_cal:
                ids_categ.append(cat)
            cats=str(ids_categ).replace(']', '').replace('[', '')
            sql_all="""select
                            aaa.id asset_id,
                            aaa."name" nombre_activo,
                            aaa.code referencia,
                            aaa."date" fecha_activo,
                            aaa.value valor_bruto
                        from
                            account_asset_asset aaa
                        where
                            aaa.state = 'open'
                            and aaa.category_id in (%s)
                        order by
                            aaa."code";"""
            request.cr.execute(sql_all % (categorias_cal))
            rows_sql = request.cr.dictfetchall()
            activos_rows=[]
            
            for i in rows_sql:
                sql_all_depres="""select
                                aadl."name" numero_depreciacion,
                                aadl.move_id poliza,
                                aadl.depreciation_date fecha_depreciacion, 
                                aadl.amount importe
                            from
                                account_asset_depreciation_line aadl
                            where
                                aadl.asset_id = %s
                            order by
                                aadl."name", aadl.depreciation_date;"""
                request.cr.execute(sql_all_depres % (i['asset_id']))
                rows_depres_sql = request.cr.dictfetchall()
                activos_depreciacion=[]
                for linea in rows_depres_sql:
                    lineas = {
                        'numero_depreciacion': linea['numero_depreciacion'],
                        'poliza': linea['poliza'],
                        'fecha_depreciacion': linea['fecha_depreciacion'],
                        'importe': linea['importe']}
                    activos_depreciacion.append(lineas)

                activos = {
                    'nombre_activo': i['nombre_activo'],
                    'referencia': i['referencia'],
                    'fecha_activo': i['fecha_activo'],
                    'valor_bruto': i['valor_bruto'],
                    'no_depreciaciones': len(activos_depreciacion),
                    'depreciaciones': activos_depreciacion}
                activos_rows.append(activos)
            excel_encode = self.get_decode_excel_reporte_activos(activos_rows)

        archivo_base64 = "data:application/octet-stream;charset=utf-16le;base64,"+excel_encode
        datas={'b64_data': archivo_base64,'items': activos_rows}
        return request.make_response(json.dumps(datas),
                [('Content-Type', 'application/json'),])

    @api.multi
    def get_decode_excel_reporte_resgurardo(self, ids):
        style0 = xlwt.easyxf('font: name Arial, bold on;\
                                pattern: pattern solid, fore_colour white;\
                                borders: top_color black, bottom_color black, right_color black, left_color black,\
                                left thin, right thin, top thin, bottom thin;'
                                , num_format_str='#,##0.00')
        style00 = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            align: vert centre, horiz centre;', num_format_str='#,##0.00')

        style1 = xlwt.easyxf('font: name Arial, bold 1,height 250;\
                            pattern: pattern solid, fore_colour aqua; \
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item_money = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        style_item_money_bold = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Activos')
        # build_img=get_logo()
        #sheet.insert_bitmap('/home/addons/GRP/presupuestos/static/src/img/tjacdmx2.bmp', 0, 0, x=1, y=1, scale_x=0.23, scale_y=0.18)
        sheet.write_merge(0, 0, 1, 4, 'TRIBUNAL DE JUSTICIA ADMINISTRATIVA.', style00)
        sheet.write_merge(1, 1, 1, 4, 'DE LA CIUDAD DE MEXICO.', style00)
        sheet.write_merge(2, 2, 1, 4, 'Sistema Contable Integrador Odoo', style00)
        sheet.write_merge(3, 3, 1, 4, 'Activo Fijo', style00)
        sheet.write_merge(4, 4, 1, 4, u'Depreciaciones por categoria', style00)
        sheet.write_merge(6, 6, 0, 0, 'Activo', style1)
        sheet.write_merge(6, 6, 1, 1, 'Refrerencia', style1)
        sheet.write_merge(6, 6, 2, 2,'Valor bruto', style1)
        sheet.write_merge(6, 6, 3, 3,'Total depreciado', style1)
        sheet.write_merge(6, 6, 4, 4, 'Residual', style1)
        n = 7
        for item in ids:            
            sheet.write_merge(n, n, 0, 0, item['nombre_activo'], style_item)
            sheet.write_merge(n, n, 1, 1, item['referencia'], style_item)
            sheet.write_merge(n, n, 2, 2, item['valor_bruto'], style_item_money)
            sheet.write_merge(n, n, 3, 3, item['total_depreciado'], style_item_money)
            sheet.write_merge(n, n, 4, 4, item['residual'], style_item_money)
            n += 1
        output = StringIO()
        workbook.save(output)
        out = base64.encodestring(output.getvalue())
        return out

    @api.multi
    def get_decode_excel_reporte_activos(self, ids):
        style0 = xlwt.easyxf('font: name Arial, bold on;\
                                pattern: pattern solid, fore_colour white;\
                                borders: top_color black, bottom_color black, right_color black, left_color black,\
                                left thin, right thin, top thin, bottom thin;'
                                , num_format_str='#,##0.00')
        style00 = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            align: vert centre, horiz centre;', num_format_str='#,##0.00')

        style1 = xlwt.easyxf('font: name Arial, bold 1,height 250;\
                            pattern: pattern solid, fore_colour aqua; \
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item_money = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        style_item_money_bold = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        workbook = xlwt.Workbook()
        
        sheet = workbook.add_sheet('Depreciaciones')
        sheet.write_merge(0, 0, 1, 4, 'TRIBUNAL DE JUSTICIA ADMINISTRATIVA.', style00)
        sheet.write_merge(1, 1, 1, 4, 'DE LA CIUDAD DE MEXICO.', style00)
        sheet.write_merge(2, 2, 1, 4, 'Sistema Contable Integrador Odoo', style00)
        sheet.write_merge(3, 3, 1, 4, 'Activo Fijo', style00)
        sheet.write_merge(4, 4, 1, 4, u'Activos y depreciaciones por categoria', style00)
        sheet.write_merge(6, 6, 0, 0, 'Activo', style1)
        sheet.write_merge(6, 6, 1, 1, 'Refrerencia', style1)
        sheet.write_merge(6, 6, 2, 2,'Valor bruto', style1)
        sheet.write_merge(6, 6, 3, 3,'Numero depreciaciones', style1)
        sheet.write_merge(6, 6, 4, 4, 'Fecha activo', style1)
        sheet.write_merge(6, 6, 5, 5, 'Numero depreciacion', style1)
        sheet.write_merge(6, 6, 6, 6, 'Poliza', style1)
        sheet.write_merge(6, 6, 7, 7, 'Fecha depreciacion', style1)
        sheet.write_merge(6, 6, 8, 8, 'Importe', style1)

        n = 7
        for item in ids:            
            sheet.write_merge(n, n, 0, 0, item['nombre_activo'], style_item)
            sheet.write_merge(n, n, 1, 1, item['referencia'], style_item)
            sheet.write_merge(n, n, 2, 2, item['valor_bruto'], style_item_money)
            sheet.write_merge(n, n, 3, 3, item['no_depreciaciones'], style_item)
            sheet.write_merge(n, n, 4, 4, item['fecha_activo'], style_item)
            if(item['depreciaciones']):
                for item_line in item['depreciaciones']:            
                    sheet.write_merge(n, n, 5, 5, item_line['numero_depreciacion'], style_item)
                    sheet.write_merge(n, n, 6, 6, item_line['poliza'], style_item)
                    sheet.write_merge(n, n, 7, 7, item_line['fecha_depreciacion'], style_item_money)
                    sheet.write_merge(n, n, 8, 8, item_line['importe'], style_item)
                    n += 1
            else:
                n += 1

        output = StringIO()
        workbook.save(output)
        out = base64.encodestring(output.getvalue())
        return out



    @http.route('/web/session/authenticate', type='http', cors='*',auth="none")
    def authenticate(self, db, login, password, base_location=None):
        request.session.authenticate(db, login, password)
        response =request.env['ir.http'].session_info()
        cuenta = {
                    'solicitudes':response,
                }
        return request.make_response(json.dumps(cuenta),
                [('Content-Type', 'application/json'),])

    @http.route('/api/tablero/',type='json', auth='user', cors='*',methods=['GET'])
    def apiTablero(self):
        obj_documento = request.env['presupuesto.partida_presupuestal'].search([])
        print(obj_documento)
        solicitudes=[]
        for item in obj_documento:
            it={
                'denominacion':item.denominacion,
                'partida_presupuestal':item.partida_presupuestal
            }
            solicitudes.append(it)

        cuenta = {
                    'solicitudes':solicitudes,
                }
        return cuenta