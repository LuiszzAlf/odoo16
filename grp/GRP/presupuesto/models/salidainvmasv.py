# -*- coding: UTF-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID,tools
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.parser import parse
import json
from dateutil.relativedelta import relativedelta
import odoo.addons.decimal_precision as dp
import collections
from . import permisos

import os

# tjacdmx.salida.inventario.masiva
class salidainvmasv(models.Model):
    _name = 'tjacdmx.salida.inventario.masiva'
    _order = 'create_date desc'
    _inherit = ['mail.thread']


 
    state = fields.Selection([
        ('pre_order', 'Nueva'),
        ('draft', 'Solicitado'),
        ('autorized', 'Recibida'),
        ('done', 'Procesando entrega'),
        ('delivered', 'Entregado')], string='Status', default="pre_order", track_visibility='onchange')


    area_gral = fields.Many2one('presupuesto.areas.stok', string='General', track_visibility='onchange')
    area = fields.Selection(selection='_get_areas', string='*Areas', track_visibility='onchange')
    departamento = fields.Selection(selection='_get_departamentos', string='*Departamentos', track_visibility='onchange')
    ubicacion =fields.Selection(selection='_get_ubicaciones', string=u'*Ubicaciónes', track_visibility='onchange')

    str_area = fields.Char(string=u'Área solicitante', track_visibility='onchange')
    str_departamento = fields.Char(string='Departamento solicitante', track_visibility='onchange')
    str_ubicacion =fields.Char(string=u'Ubicación', track_visibility='onchange')
    
    def _get_areas(self):
        choise = []
        ql_all_ht="""SELECT distinct(area) FROM tjacdmx_resguardantes;"""
        self.env.cr.execute(ql_all_ht)
        result = self.env.cr.dictfetchall()
        for item in result:
            if (item['area']):
                choise.append((item['area'], item['area'].encode('UTF-8', 'ignore')))
            else:
                pass
        return choise
    def _get_departamentos(self):
        choise = []
        ql_all_ht="""SELECT distinct(departamento) FROM tjacdmx_resguardantes;"""
        self.env.cr.execute(ql_all_ht)
        result = self.env.cr.dictfetchall()
        for item in result:
            if (item['departamento']):
                choise.append((item['departamento'], item['departamento'].encode('UTF-8', 'ignore')))
            else:
                pass
        return choise
    def _get_ubicaciones(self):
        choise = []
        ql_all_ht="""SELECT distinct(ubicacion) FROM tjacdmx_resguardantes;"""
        self.env.cr.execute(ql_all_ht)
        result = self.env.cr.dictfetchall()
        for item in result:
            if(item['ubicacion']):
                choise.append((item['ubicacion'], item['ubicacion'].encode('UTF-8', 'ignore')))
        return choise
        
        

    fecha_solicitud = fields.Datetime('Fecha de solicitud', required=True, default=fields.Datetime.now, track_visibility='onchange')
    fecha_estimada = fields.Datetime('Fecha estimada de entrega', required=True, track_visibility='onchange')
    date_expected_gral = fields.Datetime('Fecha de salida', default=fields.Datetime.now, track_visibility='onchange') # Fecha de salida
    date_delivered = fields.Datetime('Fecha de entregado', track_visibility='onchange') # Fecha de recibido por el solicitante
    comment_delivered = fields.One2many('tjacdmx.commentarios.solicitud.suministro', 'id_suministro','Cometarios de entrega', track_visibility='onchange')

    lineas_productos = fields.One2many('stock.scrap', 'salida_masiva_id', string='Lineas salidas',required=False, default=False, eval="False", track_visibility='onchange')
    lineas_solicitud_suministro  = fields.One2many('solicitud.suministro.lineas', 'salida_masiva_id', string='Lineas suministro',required=False, track_visibility='onchange')
    
    justificacion_gral = fields.Text(string=u'Justificación', track_visibility='onchange') 
    name = fields.Char(string="Folio", track_visibility='onchange')
    solicitante = fields.Char(string="Solicitante", track_visibility='onchange')
    tipo = fields.Selection([
        ('papeleria', 'Papelería'),
        ('electrico', 'Eléctrico'),
        ('mantenimiento', 'Mantenimineto'),
        ('computo', 'Computo'),
        ('otros', 'Otros')], string='Tipo', default="papeleria", track_visibility='onchange')
    productos_json = fields.Char(string="productos_json", required=False, track_visibility='onchange')
    titular_area_sol = fields.Char(string="Titular área solicitante", track_visibility='onchange')

    productos_json_suministro = fields.Char(compute="_get_json_products_suministro", track_visibility='onchange')

    reviso =fields.Char(string=u'Revisó', default="ALEPH ARANA MANZANO", track_visibility='onchange')
    vb =fields.Char(string=u'Autorizó', default=u"MTRA. CECILIA SOTO GALLARDO", track_visibility='onchange')
    recibio =fields.Char(string=u'Recibió', track_visibility='onchange')

    edificio =fields.Char(string=u'Edificio', track_visibility='onchange')
    piso =fields.Char(string=u'Piso', track_visibility='onchange')

    area_destino =  fields.Selection([
        ('almacen', u'Almacén'),
        ('informatica', u'Dirección de informática'),
        ('servicios', u'Dirección de Servicios Generales')], string='Área destino', default="almacen", track_visibility='onchange')
    
    empleado_delivered = fields.Many2one('tjacdmx.resguardantes', string="Entrega", create="false", track_visibility='onchange', domain=[('ubicacion','=','Almacén General')])
    pendiente = fields.Boolean(string=u'Pendiente', default=False, track_visibility='onchange')

    invisible_entregar =  fields.Boolean(compute='_compute_visible')      
    invisible_salida =  fields.Boolean(compute='_compute_visible')

    
    def _compute_visible(self):
        self.invisible_entregar = permisos.PermisosManager(self.env,self.env.uid).getVisible('ss_entregar')
        self.invisible_salida = permisos.PermisosManager(self.env,self.env.uid).getVisible('ss_salida')

    
    def _get_json_products_suministro(self):
        prods = []
        cont = 1
        for linea in self.lineas_solicitud_suministro:
            scrap = self.env['stock.scrap'].search([('linea_suministro', '=',linea.id)])
         
            pr = {
                "no.":cont,
                "descripcion":linea.producto_solicit,
                "producto_id":'',
                "medida":linea.uom_solicit,
                "solicitada":linea.cantidad_solicit,
                "producto_entre":linea.producto_entre,
                "entregada":linea.cantidad_entre,
                "entregado":linea.entregado,
                "scrap_id": scrap.id,
                "codigo":''
                }
            prods.append(pr)
            cont = cont +1
        

        self.productos_json_suministro = json.dumps(prods)

    @api.onchange('area')
    
    def onchange_are(self):
        self.str_area = self.area
    
    @api.onchange('departamento')
    
    def onchange_depa(self):
        self.str_departamento = self.departamento
    
    @api.onchange('ubicacion')
    
    def onchange_ubi(self):
        self.str_ubicacion = self.ubicacion

    # Si el área, fecha, o jsutificacion cambia, la cambiamos para cada una de las lineas
    @api.onchange('area_gral')
    
    def onchange_area_gral(self):
        self.update_lineas()
    
    @api.onchange('date_expected_gral')
    
    def onchange_date_expected_gral(self):
        self.update_lineas()

    @api.onchange('justificacion_gral')
    
    def onchange_justificacion_gral(self):
        self.update_lineas()
    # -----------------------------------------------------------------------------------------

   
    @api.model
    def create(self, values):
        self.update_lineas()

        res = super(salidainvmasv, self).create(values)
        res.update({'name': self.generar_name()})      



        s_date_expected_gral =  values['date_expected_gral']
        s_justificacion_gral =  values['justificacion_gral']
        s_area_gral =  values['area_gral']

        # Recorremos las lineas para asignarles el total del importe de salida, partida y fecha
        for product_line in values['lineas_productos']:
            date_expected2 = product_line[2]['date_expected']          
            
        return res
    
    
    def action_realiza_salidas(self):
        self.update_lineas()

        s_date_expected_gral =  self.date_expected_gral
        s_justificacion_gral =  self.justificacion_gral
        s_area_gral =  self.area_gral

        # Recorremos las lineas para asignarles el total del importe de salida, partida y fecha
        for product_line in self.lineas_productos:
            date_expected2 = product_line.date_expected
            if(product_line.state == 'draft'):
                product_line.action_ejecutar_salida()     
                self.update_importe_salida_params(
                        product_line.name,
                        product_line.partida_producto_clone,
                        date_expected2[:10],
                        s_date_expected_gral,
                        s_justificacion_gral,
                        s_area_gral
                    )

        if (self.state == 'delivered'):
            self.update({'pendiente': False, 'productos_json':self.productos_json_suministro})           
        else:
            self.update({'state': 'done', 'pendiente': False, 'productos_json':self.productos_json_suministro})       
            self.enviarCorreo(self.name, self.id, self.create_uid.login)

    def enviarCorreo(self, name, id, destinatario):
        host = "scio.tjacdmx.gob.mx"
        html = u"""
            <p>
                </p><table border="0" width="100%%" cellpadding="0" bgcolor="#ededed" style="padding: 20px; background-color: #ededed">
                    <tbody>
                      <tr>
                        <td align="center" style="min-width: 590px;">
                          <table width="590" border="0" cellpadding="0" bgcolor="#fff" style="min-width: 590px; background-color: #fff; padding: 20px;">
                            <tbody>
                                <tr>
                                    <td valign="middle">
                                        <span style="font-size:20px; color:#875A7B; font-weight: bold;"> Procesando entrega</span><br><br>
                                        <span style="font-size:20px; color:#875A7B; font-weight: bold;"> Solicitud de suministro %s</span>
                                    </td>
                                    <td valign="middle" align="right">
                                        <img src="http://scio.tjacdmx.gob.mx/logo.png?company=1" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="1">
                                    </td>
                                </tr>
                            </tbody>
                          </table>
                        </td>
                      </tr>
                      <tr>
                        <td align="center" style="min-width: 590px;">
                          <table width="590" border="0" cellpadding="0" bgcolor="#ffffff" style="min-width: 590px; background-color: rgb(255, 255, 255); padding: 20px;">
                            <tbody>
                              <tr><td valign="top" style="font-family:Arial,Helvetica,sans-serif; color: #555; font-size: 14px;"><br></td>
                            </tr><tr>
                            <td valign="top" style="font-family:Arial,Helvetica,sans-serif; color: #555; font-size: 14px;">
                                Buen día. <br><br>
                                Su solicitud de suministro va en camino a ser entregada.
                                <br><br>
                                <br><br>
                                <br><br><a href="http://%s/formatos/suministro/%s"><h4>Da click aquí y confirma la entrega.</h4></a>
                            </td>
                            </tr><tr><td valign="top" style="font-family:Arial,Helvetica,sans-serif; color: #555; font-size: 14px;"><br></td>
                            </tr></tbody>
                          </table>
                        </td>
                      </tr>
                      <tr>
                        <td align="center" style="min-width: 590px;"> 
                          <table width="590" border="0" cellpadding="0" bgcolor="#875A7B" style="min-width: 590px; background-color: rgb(135,90,123); padding: 20px;">
                            <tbody><tr>
                              <td valign="middle" align="left" style="color: #fff; padding-top: 10px; padding-bottom: 10px; font-size: 12px;">
                                Tribunal de Justicia Administrativa de la Ciudad de México<br>
                                SCIO Solicitud de suministro v.1.0
                              </td>
                              <td valign="middle" align="right" style="color: #fff; padding-top: 10px; padding-bottom: 10px; font-size: 12px;">
                             
                             </td>
                            </tr>
                          </tbody></table>
                        </td>
                      </tr>
                      <tr>
                        <td align="center">
                            
                        </td>
                      </tr>
                    </tbody>
                </table>""" % (name, host, id)

        correo = self.env['mail.mail'].create({
            'subject': 'Solicitud de suministro en cammino '+name,
            'email_from':'<odoogrp@tjacdmx.gob.mx>',
            'autor_id': 1,
            'email_to':'<'+destinatario+'>',
            'body_html': html,
        })
        # correo.send()
    
    
    def action_autorizar(self):
        for linea_sum in self.lineas_solicitud_suministro:           
            scrap = self.env['stock.scrap']
            prod1 = self.env['product.product'].search([('product_tmpl_id.name', '=',linea_sum.producto_solicit)], limit=1)
            prod = self.env['product.template'].search([('name', '=',linea_sum.producto_solicit)], limit=1)

            
            #validar si no encuentra prod que lo mande nulo 
            pid=prod1.id if prod1.id else ''
            puom=prod.uom_id.id if prod.uom_id.id else ''
            #raise ValidationError("debug: %s"  % (linea_sum))
            scrap.create({
                        'state': 'draft',
                        'product_id': prod1.id,
                        'product_uom_id': linea_sum.producto_uom_id,
                        'scrap_qty': linea_sum.cantidad_solicit,
                        'area':self.area_gral.id,
                        'date_expected': self.date_expected_gral,
                        'linea_suministro':linea_sum.id,
                        'salida_masiva_id':self.id,
                        'areas':self.str_area,
                        'departamento':self.str_departamento,
                        'ubicacion':self.str_ubicacion,
                        }
                    )


        self.update({'state': 'autorized'})
    
    
    def action_entregar(self):
        self.update({'state': 'delivered'})

    
    def action_pendiente(self):
        self.update({'pendiente': True, 'state': 'done', 'productos_json':self.productos_json_suministro})
        self.enviarCorreo(self.name, self.id, self.create_uid.login)

    def generar_name(self):
        last_id = 0
        self.env.cr.execute('SELECT id FROM "tjacdmx_salida_inventario_masiva" ORDER BY id DESC LIMIT 1')
        ids_data = self.env.cr.fetchone()
        #ids_data = self.id
        if ids_data>=0:
            last_id = ids_data[0]
        else:
            last_id = 0
        
        year = datetime.today().year
        prefijo = 'SS-'+str(year)+'-0'
        serie = last_id+1
        consecutivo = prefijo + str(serie).rjust(4, '0')
        return consecutivo

    @api.onchange('str_area','str_edificio','str_ubicacion')
    
    def update_lineas(self):
        for product_line in self.lineas_productos:
            product_line.justificacion = self.justificacion_gral
            product_line.date_expected = self.date_expected_gral
            product_line.areas = self.str_area
            product_line.departamento = self.str_departamento
            product_line.ubicacion = self.str_ubicacion
            # product_line.area = self.area_gral
    
    
    def update_importe_salida_params(self, move_name, partida, date_expected, s_date_expected_gral, s_justificacion_gral,s_area_gral):
        tjacdmx_select_importe_account_move = "SELECT sum(am.amount) AS importe \
                                                FROM account_move_line aml  \
                                                INNER JOIN account_move am ON aml.move_id = am.id \
                                                WHERE aml.name = '%s' AND aml.debit > 0  AND am.state != 'draft'\
                                                GROUP BY  aml.name" % (move_name)
        self.env.cr.execute(tjacdmx_select_importe_account_move)
        results = self.env.cr.fetchall()
        # if(results):
        importe_salida_move = results[0]
        self.env['stock.scrap'].search([('name', '=', move_name)]).update( { 'importe_salida_clone': importe_salida_move[0]} ) 

        # Actualizamos el importe y el producto de la salida
        
        self.env['stock.scrap'].search([('name', '=', move_name)]).update( { 'partida_producto_clone': partida} ) 

        self.env['stock.scrap'].search([('name', '=', move_name)]).update({'area': s_area_gral}) 
        self.env['stock.scrap'].search([('name', '=', move_name)]).update({'date_expected': s_date_expected_gral}) 
        self.env['stock.scrap'].search([('name', '=', move_name)]).update({'justificacion': s_justificacion_gral}) 


        # Actualizamos la fecha de los asientos por la de la fecha prevista move
        tjacdmx_select_id_account_move = "SELECT am.id FROM account_move am \
                                        INNER JOIN account_move_line aml ON am.id = aml.move_id \
                                        WHERE aml.name = '%s' \
                                        GROUP BY am.id;" % (move_name)

        self.env.cr.execute(tjacdmx_select_id_account_move)
        results = self.env.cr.fetchall()
        
        for ids in results:
            tjacdmx_update_status_account_move = "UPDATE account_move SET date = '%s' WHERE id =%s" % (date_expected,ids[0])
            self.env.cr.execute(tjacdmx_update_status_account_move)

        # Actualizamos la fecha de los asientos por la de la fecha prevista move_line
        tjacdmx_select_id_move_lines = "SELECT aml.id FROM account_move_line aml \
                                        WHERE aml.name = '%s' " % (move_name)

        self.env.cr.execute(tjacdmx_select_id_move_lines)
        results = self.env.cr.fetchall()
        
        for ids in results:
            tjacdmx_update_status_account_move = "UPDATE account_move_line SET date = '%s', date_maturity='%s' WHERE id =%s" % (date_expected,date_expected,ids[0])
            self.env.cr.execute(tjacdmx_update_status_account_move)

EJERCICIO_SELECT = [ (str(year), str(year)) for year in range(2018, 2031) ]
PERIODO_SELECT = [(str(periodo), str(periodo)) for periodo in range(1,13)]

# tjacdmx.commentarios.solicitud.suministro
class ComentariosSolSuministro(models.Model):
    _name = 'tjacdmx.commentarios.solicitud.suministro'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    id_suministro = fields.Integer(string="Sol. suministro") 
    comentario = fields.Text(string="Comentario")

# tjacdmx.cierre.inventario
class cierre_inventario(models.Model):
    _name = 'tjacdmx.cierre.inventario'

    anio=fields.Selection(EJERCICIO_SELECT, default=2019)
    periodo = fields.Selection(PERIODO_SELECT, default=1)
    existencias = fields.Float(String='Existencias')
    importe_existencias = fields.Float(String='Importe existencias')
    product_id= fields.Many2one('product.product', required=False,store=True)
    devolucion = fields.Boolean(default=False)

    def get_is_periodo_cerrado(self, periodo, anio):
        self.env.cr.execute("SELECT COUNT(*) as periodo_cerrado \
                             FROM tjacdmx_cierre_inventario \
                             WHERE periodo = %s AND anio = %s  \
                             AND product_id IS NOT NULL" % (str(periodo),str(anio)))
        periodo_cerrado = self.env.cr.fetchone()
        if periodo_cerrado[0]>0:
            raise ValidationError("El periodo %s/%s ya ha sido cerrado en inventarío. Por favor verifique la fecha."  % (str(periodo),str(anio)) )
            return True
        else:
            return False

# tjacdmx.conteo.inventario
class ConteoInventario(models.Model):
    _name = 'tjacdmx.conteo.inventario'
    _description = 'Conteo de inventario'
    _inherit = ['mail.thread']
    _order = 'name desc'

    name = fields.Char(string="Folio")
    fecha = fields.Date(string="Fecha de conteo", required=True)
    fecha_cierre = fields.Date(string="Fecha de corte")
    state = fields.Selection([
                        ('new','Nuevo'),
                        ('draft','Borrador'),
                        ('genered','Procesado'),
                        ('finish','Finalizado'),
                        ('cancel','Cancelado')],
                        default="new",  track_visibility='onchange') 
    total_existencias = fields.Float(string='Total existencias',  digits=dp.get_precision('Product Price'))
    total_importe_existencias = fields.Float(string='Valoración',  digits=dp.get_precision('Product Price'))
    total_existencias_real = fields.Float(string='Existencias real',  digits=dp.get_precision('Product Price'))
    total_importe_existencias_real = fields.Float(string='Valoración real',  digits=dp.get_precision('Product Price'))
    total_dif_existencias = fields.Float(string='Diferencia de existencias',  digits=dp.get_precision('Product Price'))
    total_dif_importe =fields.Float(string='Diferencia de importe',  digits=dp.get_precision('Product Price'))

    total_sobrante = fields.Float(string='Sobrante',  digits=dp.get_precision('Product Price'))
    total_faltante = fields.Float(string='Faltante',  digits=dp.get_precision('Product Price'))
    total_dif = fields.Float(string='Total direfencia',  digits=dp.get_precision('Product Price'))

    lineas_conteo_inventario = fields.One2many('tjacdmx.conteo.inventario.line', 'conteo_inventario', string="Productos")

    elaboro = fields.Text(string="Elaboró")
    vb = fields.Text(string="Vo. Bo.")
    autorizo = fields.Text(string="Autorizó")
    reviso = fields.Text(string="Revisó")

    procesado = fields.Boolean(default=False)

    def generar_name(self):
        last_id = 0
        self.env.cr.execute('SELECT id FROM "tjacdmx_conteo_inventario" ORDER BY id DESC LIMIT 1')
        ids_data = self.env.cr.fetchone()
        if ids_data>=0:
            last_id = ids_data[0]
        else:
            last_id = 0
        
        year = datetime.today().year
        prefijo = 'CFI-'+str(year)+'-0'
        serie = last_id+1
        consecutivo = prefijo + str(serie).rjust(4, '0')
        return consecutivo

    @api.model
    def create(self, values):
        res = super(ConteoInventario, self).create(values)
        res.update({'name': self.generar_name()})                  
        res.action_generar()
        return res

    
    def action_generar(self):
        date_genered = datetime.datetime.strptime(self.fecha, "%Y-%m-%d")
        periodo = date_genered.month
        anio = date_genered.year

        if(not self.env['tjacdmx.cierre.inventario'].get_is_periodo_cerrado(periodo, anio)):
            fecha_inicio = str(anio)+"-"
            fecha_fin = str(anio)+"-"

            if(periodo<=9):
                fecha_inicio += "0" + str(periodo) + '-01 00:00:01'
            else:
                fecha_inicio += str(periodo) + '-01 00:00:01'
                
            fecha_fin=datetime.datetime(anio,periodo,10)
            fecha_fin=fecha_fin.replace(day=1)+relativedelta(months=1)+datetime.timedelta(minutes=-1)

            qry_select_val_inv =  """SELECT product_id, name, posicion_presupuestaria, sum(qty) as stock_actual, cost as costo, (cost)*sum(qty) as impo_exist_final
                                    FROM stock_quant sq
                                    INNER JOIN product_product pro on pro.id = sq.product_id
                                    INNER JOIN product_template pt on pro.product_tmpl_id = pt.id
                                    WHERE sq.location_id = 15 
                                    GROUP BY  cost, product_id, name, posicion_presupuestaria
                                    ORDER BY  posicion_presupuestaria, name;"""

            self.env.cr.execute(qry_select_val_inv)
            rows_sql = self.env.cr.dictfetchall()
            
            consecutivo = 0
            for i in rows_sql:
                consecutivo += 1
                prod = self.env['product.product'].search([('id', '=',i['product_id'])])

                obj_ci = self.env['tjacdmx.conteo.inventario.line']
                obj_ci.create(
                            {
                            'consecutivo':consecutivo,
                            'fecha':self.fecha,
                            'anio': anio, 
                            'periodo': periodo, 
                            'existencias': i['stock_actual'],
                            'importe_existencias':  i['impo_exist_final'],
                            'product_id':  i['product_id'],
                            'product_partida':  prod.posicion_presupuestaria.partida_presupuestal,
                            'product_oum':  prod.uom_po_id.name,
                            'costo':  i['costo'],
                            'conteo_inventario' : self.id,
                            }
                        )

                self.total_importe_existencias = self.total_importe_existencias+ float(i['impo_exist_final'])
        else:
            raise ValidationError("El periodo %s/%s ya ha sido cerrado."  % (str(self.periodo),str(self.anio)) )
        
        self.update({'state': 'draft'})             
       

    
    def action_finalizar(self):
        #self.action_ajustar()
        self.update({'state': 'finish'})


    
    def action_ajustar(self):
        for linea in self.lineas_conteo_inventario:
            if (linea.dif_existencias != 0):
                qry_select_val_inv =  "select *from stock_quant \
                                    where product_id = %s and location_id = 15 \
                                    and round(cost::numeric,2) =  %s"  % (linea.product_id.id, linea.costo)

                self.env.cr.execute(qry_select_val_inv)
                rows_sql = self.env.cr.dictfetchall()

                if(len(rows_sql)==1):
                    for i in rows_sql:  
                        sq = self.env['stock.quant'].search([('id', '=', i['id'])])
                        sq.update({'qty': linea.existencias_real}) 
                        if(sq.qty <= 0):
                            sq.update({'location_id': 4})    

                    #si llego a cero cambiar location a 4 
                    #si alcanzo para la reducción con el estock que tien el primer elemento si no redicir del segundo y asi sisesivamente

                if(len(rows_sql)>=1):
                    qty_restante = 0
                    for i in rows_sql: 
                        sq = self.env['stock.quant'].search([('id', '=', i['id'])])
                        if(qty_restante == 0):
                            sq.update({'qty': i['qty']+linea.dif_existencias})    
                        
                        if(qty_restante != 0):
                            sq.update({'qty': i['qty']+qty_restante})    
                        
                        
                            
                        if(sq.qty > 0):
                            exit 
                        else:
                            #mientras siga siendo menos a sero quitar del siquiente sqtoc_quant id
                            qty_restante = sq.qty
                            sq.update({'location_id': 4})    
                            sq.update({'qty': 0})    

        self.update({'state': 'finish'})

    
    def action_rechazar(self):
        for linea in self.lineas_conteo_inventario:
             linea.write({'procesado':False})
        
        self.update({'state':'draft',
                    'total_faltante':0,
                    'total_sobrante':0,
                    'procesado':False})

    
    def action_procesar(self):
        self.total_faltante = 0
        self.total_sobrante = 0
        self.total_importe_existencias_real = 0
        self.total_dif = 0

        for linea in self.lineas_conteo_inventario:
            linea.on_change_existencias_real()
            linea.write({'procesado': True})
            self.total_importe_existencias_real += linea.importe_existencias_real
            if(linea.dif_importe < 0):
                self.total_faltante += linea.dif_importe
            
            if(linea.dif_importe > 0):
                self.total_sobrante += linea.dif_importe      


        self.update({
            'total_faltante': self.total_faltante,
            'total_sobrante': self.total_sobrante,
            'total_importe_existencias_real': self.total_importe_existencias_real,
            'total_dif': self.total_importe_existencias_real - self.total_importe_existencias,
            'procesado': True,
            'state': 'genered',
        })

   
    
    def unlink(self):
        date_genered = datetime.datetime.strptime(self.fecha, "%Y-%m-%d")
        periodo = date_genered.month
        anio = date_genered.year
        if(self.state != 'finish'):
            if(not self.env['tjacdmx.cierre.inventario'].get_is_periodo_cerrado(periodo, anio)):
                # for linea in self.lineas_conteo_inventario:
                #     linea.unlink()       
                return models.Model.unlink(self)
            else:
                raise ValidationError("No se puede eliminar el conteo. El periodo %s/%s ya ha sido cerrado."  % (str(self.periodo),str(self.anio)) )
        else:
            raise ValidationError("No se puede eliminar un conteo finalizado.")
        
class ConteoInventarioLine(models.Model):
    _name = 'tjacdmx.conteo.inventario.line'
    _inherit = 'tjacdmx.cierre.inventario'
    _description = 'Conteo de inventario linea'

    consecutivo = fields.Integer('No.')
    fecha = fields.Date(string="Fecha de conteo")
    anio = fields.Char(string="Year")
    periodo = fields.Integer(string="periodo")
    existencias_real = fields.Float(String='Existencias real')
    importe_existencias_real = fields.Float(String='Importe existencias real', digits=dp.get_precision('Product Price'))
    costo = fields.Float(String='Costo', digits=dp.get_precision('Product Price'))

    product_oum = fields.Char(string="Medida")
    product_partida = fields.Char(string="Partida")

    dif_existencias = fields.Float(String='Diferencia de existencias', digits=dp.get_precision('Product Price'))
    dif_importe =fields.Float(String='Diferencia de importe', digits=dp.get_precision('Product Price'))

    conteo_inventario = fields.Many2one('tjacdmx.conteo.inventario', string="Conteo")



    # 
    # def write(self, vals):

    #     print(vals.get('importe_existencias_real'))
    #     vals.update({'importe_existencias_real': vals.get('importe_existencias_real')})
    #     vals.update({'dif_existencias': vals.get('dif_existencias')})
    #     vals.update({'dif_importe': vals.get('dif_importe')})

    #     return super(ConteoInventarioLine, self).write(vals)
    
    procesado = fields.Boolean(default=False)


    
    @api.onchange('existencias_real')
    def on_change_existencias_real(self):
        importe_existencias_real =   self.costo * self.existencias_real
        dif_existencias = self.existencias_real - self.existencias
        dif_importe = importe_existencias_real - self.importe_existencias

        # self.write({
        #     'importe_existencias_real': importe_existencias_real,
        #     'dif_existencias': dif_existencias,
        #     'dif_importe': dif_importe
        # })

        self.importe_existencias_real = importe_existencias_real
        self.dif_existencias = dif_existencias
        self.dif_importe = dif_importe

        self.update({
            'importe_existencias_real': self.importe_existencias_real ,
            'dif_existencias': self.dif_existencias,
            'dif_importe': self.dif_importe,
        })


class SolicitudesPermisos(models.Model):
    _name = 'tjacdmx.solicitudes.permisos'
    _inherit = ['mail.thread']
    _description = 'Solicitudes permisos'
    _rec_name='id_permisos'

    id_permisos = fields.Many2one('presupuesto.permisos.presupuestales', string='Usuario', domain="[('ss_crear','=','true')]", required=True)
    departamentos =  fields.One2many('tjacdmx.solicitudes.lineas.departamentos', 'id_solicitudes_permisos', string='Usuario',required=True)

class SolicitudesPermisosDepartamentosLineas(models.Model):
    _name = 'tjacdmx.solicitudes.lineas.departamentos'
    _inherit = ['mail.thread']
    _description = 'Solicitudes permisos dep lineas'

    departamento = fields.Selection('_get_departamentos', string='Departamento')
    area = fields.Char(u'Área')
    id_solicitudes_permisos = fields.Many2one('tjacdmx.solicitudes.permisos', string='permiso',required=True)

    def _get_departamentos(self):
        choise = []
        ql_all_ht="""SELECT distinct(departamento) FROM tjacdmx_resguardantes where departamento is not null;"""
        self.env.cr.execute(ql_all_ht)
        result = self.env.cr.dictfetchall()
        for item in result:
            choise.append(
                            (item['departamento'], item['departamento'].encode('UTF-8', 'ignore'))
                        )
        return choise

    @api.onchange('departamento')
    
    def change_departamento(self):
        ql_all_ht="""SELECT distinct(area) AS area FROM tjacdmx_resguardantes WHERE departamento = '%s';"""
        self.env.cr.execute(ql_all_ht % (self.departamento))
        result = self.env.cr.dictfetchone()
        if(result):
            self.area = result['area'].encode('utf-8')



class solicitud_compra_materiales_line(models.Model):
    _name = 'tjacdmx.solicitud.compra.materiales.line'
    _order = 'create_date desc'
    _rec_name = 'producto'
    _inherit = ['mail.thread']

    producto =fields.Char(string=u'producto',required=True, track_visibility='onchange')
    cantidad =fields.Integer(string='Cantidad',required=True, track_visibility='onchange')
    solicitud_line_id = fields.Many2one('tjacdmx.solicitud.compra.materiales',index=True)

class solicitud_compra_materiales(models.Model):
    _name = 'tjacdmx.solicitud.compra.materiales'
    _order = 'create_date desc'
    _rec_name = 'number'
    _inherit = ['mail.thread']
    
    @api.model
    def _default_number(self):
        context = dict(self._context or {})
        num_sm=self.env['tjacdmx.solicitud.compra.materiales'].search([])
        identifi=len(num_sm)+1
        fecha = datetime.today()
        number_char="""SC/%s/0%s""" % (str(fecha.year),identifi)
        return number_char
        
    number = fields.Char(default=_default_number)
    fecha = fields.Date('Fecha de solicitud', required=True, track_visibility='onchange')
    area_gral = fields.Char(string='Area',required=True, track_visibility='onchange')
    lineas_productos = fields.One2many('tjacdmx.solicitud.compra.materiales.line', 'solicitud_line_id', string='Lineas solicitud',required=False, default=False, eval="False", track_visibility='onchange')
    justificacion = fields.Text(string=u'Justificación',required=True, track_visibility='onchange') 
    observaciones = fields.Char(string='Observaciones',track_visibility='onchange')
    state = fields.Selection([
        ('draft', 'Solicitado'),
        ('autorized', 'Recibida'),
        ('cancel', 'Rechazada')], string='Status',required=True, default="draft", track_visibility='onchange')

    
    def recibir_compra(self):
        self.write({'state': 'autorized'})
    
    
    def rechaza_compra(self):
        return {
                'name': _("Rechazo"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'rechaza_solicitud_compra.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'solicitud_compra': self.id}
            }

    
    def imprime(self):
        datas = {}
        fecha = parse(self.fecha)
        fechas=datetime.today()
        array_mov=[] 
        for i in self.lineas_productos:
            mov = {
                'producto': i.producto,
                'cantidad': i.cantidad
           }
            array_mov.append(mov)
        res = self.read(['number','fecha','area_gral','justificacion','observaciones','state'])
        res = res and res[0] or {}
        datas['form'] = res
        datas['periodo'] = fecha.month
        datas['anio'] = fecha.year
        datas['fecha_reporte'] = str(datetime.strftime(fechas,"%Y-%m-%d"))
        datas['movimientos'] = array_mov
        # raise ValidationError("%s"%datas)
        return self.env['report'].get_action([], 'reportes.report_solicitud_compra', data=datas)  
    