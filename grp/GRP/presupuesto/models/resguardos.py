# -*- coding: UTF-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime
import time

class resguardos(models.Model):
    _name = 'tjacdmx.resguardos'
    _description = "Resguardo" 
    _rec_name = 'nombre_empleado'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    resguardante =fields.Many2one('tjacdmx.resguardantes',string='Resguardante', domain="[('activo','=',1),('resguardo','!=',1)]",track_visibility='onchange')
    no_empleado = fields.Integer(string='Num empleado', required=True,track_visibility='onchange')
    id_empleado=fields.Integer(string='ID empleado',compute='_onchange_empleado')
    nombre_empleado = fields.Char(string='Nombre de empleado',compute='_onchange_empleado', required=True)
    puesto=fields.Char(string='Puesto',compute='_onchange_empleado', required=True)
    departamento = fields.Char(string='Departamento',compute='_onchange_empleado', required=True)
    area = fields.Char(string='Area',compute='_onchange_empleado', required=True)
    ubicacion = fields.Char(string='Ubicación',compute='_onchange_empleado', required=True)
    status = fields.Char(string='status')
    changes = fields.Char(string='cambios', default='false')
    lineas_resguardo = fields.One2many('tjacdmx.resguardo_lineas', 'resguardo_id', string='Lineas resguardo',required=True,track_visibility='onchange')
    lineas_resguardo_nocapitalizable = fields.One2many('tjacdmx.resguardo_lineas_no_capitalisable', 'resguardo_id', string='Activos no capitalisable',track_visibility='onchange')
    _status = fields.Char(compute="_put_status", string="status")
    fecha_creacion = fields.Date(compute="_put_date", string="Fecha de creación")
    fecha_modificacion = fields.Date(compute="_put_date", string="Ultima modificación")
    folio = fields.Char(string="Folio")
    edificio = fields.Char(string="Edificio",compute='_onchange_empleado')
    piso = fields.Char(string="Piso",compute='_onchange_empleado')
    fecha_creacion_resguardo = fields.Date(string="Fecha de creacion",track_visibility='onchange')
    no_empleado_comp = fields.Integer(string='Num empleado',compute='_onchange_empleado_2')
    nombre_empleado_comp = fields.Char(string='Nombre de empleado',compute='_onchange_empleado_2')
    puesto_comp=fields.Char(string='Puesto',compute='_onchange_empleado_2')
    _status_comp = fields.Char(compute="_onchange_empleado_2", string="status")
    fecha_creacion_comp = fields.Date(compute="_put_date2", string="Fecha de creación")
    fecha_modificacion_comp = fields.Date(compute="_put_date2", string="Ultima modificación",track_visibility='onchange')
    archivos = fields.One2many('tjacdmx.resguardos.archivo', 'resguardo_id', string="Achivos")
    check_state = fields.Boolean(u'Estado', default=False,track_visibility='onchange')
    lineas_resguardo_arrendamiento= fields.One2many('tjacdmx.resguardo_lineas_arrendamiento', 'resguardo_id', string='Activos Arrendamiento',track_visibility='onchange')


    @api.model
    def create(self,vals):
        result = super(resguardos, self).create(vals)
        serie = result.id
        consecutivo = str(serie).rjust(7, '0')
        result.folio=consecutivo
        return result

    def toggle_state(self):
        if(self.check_state==True):
            self.check_state=False
        else:
            self.check_state=True

    
    def _onchange_empleado_2(self):
        search_resguardantes= self.env['tjacdmx.resguardantes'].search([('id', '=', self.resguardante.id)], limit=1)
        self.nombre_empleado_comp = search_resguardantes.nombre
        self.puesto_comp = search_resguardantes.puesto
        self.no_empleado_comp = search_resguardantes.num_empleado
        self._status_comp=search_resguardantes.activo


    @api.onchange('resguardante')
    
    def _onchange_empleado(self):
        _folio = self._onchange_folio()
        search_resguardantes= self.env['tjacdmx.resguardantes'].search([('id', '=', self.resguardante.id)], limit=1)
        self.id_empleado = search_resguardantes.id
        self.no_empleado = search_resguardantes.num_empleado
        self.nombre_empleado = search_resguardantes.nombre
        self.puesto = search_resguardantes.puesto
        self.departamento = search_resguardantes.departamento
        self.area = search_resguardantes.area
        self.ubicacion = search_resguardantes.ubicacion
        self.status = search_resguardantes.activo
        self.edificio = search_resguardantes.edificio
        self.piso = search_resguardantes.piso
        self.folio = _folio['folio']
        self.update({'status': search_resguardantes.activo, 'no_empleado':search_resguardantes.num_empleado})
            

    
    
    def btn_save_resguardo(self):
        search_valida_emple = self.env['tjacdmx.resguardos'].search([('no_empleado', '=', self.no_empleado),('changes', '=', 'open')], limit=1)
        data=search_valida_emple.no_empleado
        if data!=0:
               raise ValidationError("El empleado  ya tiene un resguardo")
        else:
            tjacdmx_update_asig_resg = "UPDATE tjacdmx_resguardantes SET resguardo='1' WHERE id=%s" % (self.resguardante.id)
            self.env.cr.execute(tjacdmx_update_asig_resg)
            today = datetime.now()
            tjacdmx_insert_reg = """
                                    INSERT INTO tjacdmx_log_resguardos (id,status,create_uid,nombre_empleado,create_date,id_empleado,area,departamento,write_uid,puesto,no_empleado,write_date,ubicacion,folio)
                                    VALUES (%s,%s,%s,'%s','%s',%s,'%s','%s',%s,'%s',%s,'%s','%s','%s')
                                """ % (self.id,self.status,self.create_uid.id,self.nombre_empleado,self.create_date,self.id_empleado,self.area,self.departamento,self.write_uid.id,self.puesto,self.no_empleado,self.write_date,self.ubicacion,self.folio)
            # raise ValidationError("EL INSERT: %s" % (tjacdmx_insert_reg))
            self.env.cr.execute(tjacdmx_insert_reg)
            tjacdmx_update_changes_ = "UPDATE tjacdmx_resguardos SET changes='open' WHERE id=%s" % (self.id)
            self.env.cr.execute(tjacdmx_update_changes_)
            self.env.cr.execute('SELECT id_activo,resguardo_id  FROM "tjacdmx_resguardo_lineas" WHERE resguardo_id=%s' % (self.id))
            ids_data = self.env.cr.fetchall()
            indice = 0
            while indice < len(ids_data):
                linea=(ids_data[indice][0])
                linea_id = (ids_data[indice][1])
                tjacdmx_update_asset = "UPDATE account_asset_asset SET emple_asig='%s',status='close', id_empleado_linea=%s WHERE id=%s" % \
                                    (self.nombre_empleado,self.id, linea)
                self.env.cr.execute(tjacdmx_update_asset)
                self.env['tjacdmx.log_resguardo_lineas'].create({'resguardo_id': linea_id, 'id_activo':linea, 'status': 'espera'})
                indice += 1

    def action_update_asset(self):
        tjacdmx_update_asset = "UPDATE accou_onchange_foliont_asset_asset SET status='asignado', id_empleado_linea=1 WHERE id ='3400'"
        self.env.cr.execute(tjacdmx_update_asset)
        self.env.cr.commit()

    
    def _put_status(self):
        self._status = 'Activo' if self.status == '1' else 'Inactivo'


    
    def _put_date(self):
        self.fecha_creacion = self.create_date
        self.fecha_modificacion = self.write_date

    
    def _put_date2(self):
        self.fecha_creacion_comp = self.create_date
        self.fecha_modificacion_comp = self.write_date

    #Libera activos del resguardo
    
    def liberar_activos_all(self):
        idx = self.env['tjacdmx.resguardo_lineas'].search([('resguardo_id','=',self.id)])
        for i in idx:
            fecha_actual = datetime.now()
            query = "UPDATE account_asset_asset SET status='open', id_empleado_linea=Null, emple_asig=Null,write_date = '%s' WHERE id = %s;" % (fecha_actual,i.id_activo.id)
            query1 = "UPDATE tjacdmx_log_resguardo_lineas SET tipo_mov = 'Liberado', write_date = '%s' WHERE resguardo_id = %s AND id_activo = %s;" % (fecha_actual,i.resguardo_id,i.id_activo.id)
            query2 = "UPDATE tjacdmx_log_resguardos SET write_date = '%s' WHERE id_empleado = %s;" % (fecha_actual,self.id_empleado)
            query3 = "DELETE FROM tjacdmx_resguardo_lineas WHERE resguardo_id = %s AND id_activo = %s;" % (i.resguardo_id,i.id_activo.id)
            query4 = "DELETE FROM tjacdmx_resguardos WHERE id = %s AND id_empleado = %s;" % (i.resguardo_id,self.id_empleado)
            # raise ValidationError("%s, %s ,%s, %s, %s" % (query,query1,query2,query3,query4))
            self.env.cr.execute(query)
            self.env.cr.execute(query1)
            self.env.cr.execute(query2)
            self.env.cr.execute(query3)
            self.env.cr.execute(query4)


    
    def report_resguardo(self):
        return self.env['report'].get_action([], 'reportes.resguardos_impre', data= self.get_data_for_report_resguardo())
    
    
    def get_data_for_report_resguardo(self):
        datas ={}
        res = self.read(['nombre_empleado','no_empleado','write_date','area','ubicacion','folio','edificio','piso'])
        res = res and res[0] or {}
        datas['form'] = res
        date_fin=time.strptime(self.write_date, '%Y-%m-%d %H:%M:%S')
        datas['fecha_up'] =str(date_fin.tm_year)+'-'+str(date_fin.tm_mon)+'-'+str(date_fin.tm_mday)
        lines_activos = self.env['tjacdmx.resguardo_lineas'].search([
                ('resguardo_id','=',self.id),
                ('check_line','=',True)
                ])
        lines_activos_nocapitalisables = self.env['tjacdmx.resguardo_lineas_no_capitalisable'].search([
                ('resguardo_id','=',self.id),
                ('check_line','=',True)
                ])
        lines_activos_arrendamiento = self.env['tjacdmx.resguardo_lineas_arrendamiento'].search([
                ('resguardo_id','=',self.id),
                ('check_line','=',True)
                ])
        lineas_arr=[]
        for i in lines_activos:
            lin = self.env['account.asset.asset'].search([('id','=',i.id_activo.id)])
            linea={
                    'id':lin.id,
                    'code':lin.code,
                    'name':lin.name,
                    'marca':lin.marca,
                    'no_serie':lin.no_serie,
                    'estado_fisico':lin.estado_fisico,
                    'piso':lin.piso,
                    'edificio':lin.edificio,
                    }
            lineas_arr.append(linea)
        lineas_arr_nocapitalisables=[]
        for i in lines_activos_nocapitalisables:
            lin = self.env['tjacdmax.activos_no_capitalizables'].search([('id','=',i.id_activo.id)])
            linea={
                    'id':lin.id,
                    'code':lin.no_inventario,
                    'name':lin.descripcion,
                    'marca':lin.marca,
                    'no_serie':lin.no_serie,
                    'estado_fisico':lin.estado_fisico,
                    'piso':lin.piso,
                    'edificio':lin.edificio,
                    }
            lineas_arr_nocapitalisables.append(linea)
        lineas_arrendamiento=[]
        for i in lines_activos_arrendamiento:
            lin = self.env['tjacdmax.arrendamiento'].search([('id','=',i.id_activo.id)])
            linea={
                    'id':lin.id,
                    'code':'',
                    'name':lin.descripcion,
                    'marca':lin.marca,
                    'no_serie':lin.no_serie,
                    'estado_fisico':'',
                    'piso':lin.piso,
                    'edificio':lin.edificio,
                    }
            lineas_arrendamiento.append(linea)
        datas['account_asset_asset_data'] = lineas_arr
        datas['account_asset_asset_data_nc'] = lineas_arr_nocapitalisables
        datas['account_asset_asset_data_arr'] = lineas_arrendamiento
        return datas

    
    def report_resguardo_arrendamiento(self):
        return self.env['report'].get_action([], 'reportes.print_resguardo_arrendamiento', data= self.get_data_for_report_resguardo_arrendamiento())
    
    
    def get_data_for_report_resguardo_arrendamiento(self):
        datas ={}
        res = self.read(['nombre_empleado','no_empleado','write_date','area','ubicacion','folio','edificio','piso'])
        res = res and res[0] or {}
        datas['form'] = res
        date_fin=time.strptime(self.write_date, '%Y-%m-%d %H:%M:%S')
        datas['fecha_up'] =str(date_fin.tm_year)+'-'+str(date_fin.tm_mon)+'-'+str(date_fin.tm_mday)
        lines_activos = self.env['tjacdmx.resguardo_lineas'].search([
                ('resguardo_id','=',self.id),
                ('check_line','=',True)
                ])
        lines_activos_nocapitalisables = self.env['tjacdmx.resguardo_lineas_no_capitalisable'].search([
                ('resguardo_id','=',self.id),
                ('check_line','=',True)
                ])
        lines_activos_arrendamiento = self.env['tjacdmx.resguardo_lineas_arrendamiento'].search([
                ('resguardo_id','=',self.id),
                ('check_line','=',True)
                ])
        lineas_arr=[]
        for i in lines_activos:
            lin = self.env['account.asset.asset'].search([('id','=',i.id_activo.id)])
            linea={
                    'id':lin.id,
                    'code':lin.code,
                    'name':lin.name,
                    'marca':lin.marca,
                    'no_serie':lin.no_serie,
                    'estado_fisico':lin.estado_fisico,
                    'piso':lin.piso,
                    'edificio':lin.edificio,
                    }
            lineas_arr.append(linea)
        lineas_arr_nocapitalisables=[]
        for i in lines_activos_nocapitalisables:
            lin = self.env['tjacdmax.activos_no_capitalizables'].search([('id','=',i.id_activo.id)])
            linea={
                    'id':lin.id,
                    'code':lin.no_inventario,
                    'name':lin.descripcion,
                    'marca':lin.marca,
                    'no_serie':lin.no_serie,
                    'estado_fisico':lin.estado_fisico,
                    'piso':lin.piso,
                    'edificio':lin.edificio,
                    }
            lineas_arr_nocapitalisables.append(linea)
        lineas_arrendamiento=[]
        for i in lines_activos_arrendamiento:
            lin = self.env['tjacdmax.arrendamiento'].search([('id','=',i.id_activo.id)])
            linea={
                    'id':lin.id,
                    'code':'',
                    'name':lin.descripcion,
                    'marca':lin.marca,
                    'no_serie':lin.no_serie,
                    'estado_fisico':'',
                    'piso':lin.piso,
                    'edificio':lin.edificio,
                    }
            lineas_arrendamiento.append(linea)
        datas['account_asset_asset_data'] = lineas_arr
        datas['account_asset_asset_data_nc'] = lineas_arr_nocapitalisables
        datas['account_asset_asset_data_arr'] = lineas_arrendamiento
        return datas



    def _onchange_folio(self):
        last_id = 0
        self.env.cr.execute('SELECT id FROM "tjacdmx_resguardos" ORDER BY id DESC LIMIT 1')
        ids_data = self.env.cr.fetchone()
        if ids_data>=0:
            last_id = ids_data[0]
        else:
            last_id = 0
        prefijo = '00'
        serie = last_id+1
        consecutivo = prefijo + str(serie).rjust(5, '0')
        return {
            'folio': consecutivo
        }

    
    def btn_sync_changes(self):
        activos = self.env['account.asset.asset']
        activos_res = activos.search([('id_empleado_linea', '=', self.id)])
        new_arr = []
        old_arr = []
        past = 0
        for i in self.lineas_resguardo:
            if past == i.id_activo:
                del_repetido = "DELETE FROM tjacdmx_resguardo_lineas WHERE resguardo_id = %s AND id = %s;" % (self.id,i.id)
                self.env.cr.execute(del_repetido)
            else:
                past = i.id_activo
            new_arr.append(i.id_activo.id)
        for i in activos_res:
            old_arr.append(i.id)
        sum_arr = set(old_arr + new_arr)
        for i in list(sum_arr):
            if i in new_arr:
                tjacdmx_update_asset = "UPDATE account_asset_asset SET emple_asig='%s',status='close', id_empleado_linea=%s WHERE id=%s" % (self.nombre_empleado,self.id, int(i))
            else:
                tjacdmx_update_asset = "UPDATE account_asset_asset SET emple_asig=Null,status='open', id_empleado_linea=Null WHERE id=%s" % (int(i))
            self.env.cr.execute(tjacdmx_update_asset)
            _exist = self.env['tjacdmx.log_resguardo_lineas'].search([('id_activo','=',int(i)),('resguardo_id','=',self.id)])
            if not _exist:
                self.env['tjacdmx.log_resguardo_lineas'].create({'resguardo_id': self.id, 'id_activo':int(i), 'status': 'espera'})

        # for i in self.lineas_resguardo:
        #     i.id_activo.write({'piso': self.getPisoId(self.piso.encode('utf-8')),
        #                         'edificio':self.edificio}) 
        # for i in self.lineas_resguardo_nocapitalizable:
        #     i.id_activo.write({'piso': self.getPisoId(self.piso.encode('utf-8')),
        #                         'edificio':self.edificio})

        activos_nc = self.env['tjacdmax.activos_no_capitalizables']
        activos_res_nc = activos_nc.search([('resguardante', '=', self.id)])
        new_arr_nc = []
        old_arr_nc = []
        past_nc = 0
        for i in self.lineas_resguardo_nocapitalizable:
            if past_nc == i.id_activo:
                del_repetido = "DELETE FROM tjacdmx_resguardo_lineas_no_capitalisable WHERE resguardo_id = %s AND id = %s;" % (self.id,i.id)
                self.env.cr.execute(del_repetido)
            else:
                past_nc = i.id_activo
            new_arr_nc.append(i.id_activo.id)
        for i in activos_res_nc:
            old_arr_nc.append(i.id)
        sum_arr = set(old_arr_nc + new_arr_nc)
        for i in list(sum_arr):
            if i in new_arr_nc:
                tjacdmx_update_asset = "UPDATE tjacdmax_activos_no_capitalizables SET resguardante='%s',status='close',id_empleado_linea=%s WHERE id=%s" % (self.resguardante.id,self.id, int(i))
            else:
                tjacdmx_update_asset = "UPDATE tjacdmax_activos_no_capitalizables SET resguardante=Null,status='open',id_empleado_linea=Null  WHERE id=%s" % (int(i))
            self.env.cr.execute(tjacdmx_update_asset)
            _exist = self.env['tjacdmx.resguardo_lineas_no_capitalisable'].search([('id_activo','=',int(i)),('resguardo_id','=',self.id)])
            # if not _exist:
            #     self.env['tjacdmx.resguardo_lineas_no_capitalisable'].create({'resguardo_id': self.id, 'id_activo':int(i), 'status': 'espera'})

        # for i in self.lineas_resguardo:
        #     i.id_activo.write({'piso': self.getPisoId(self.piso.encode('utf-8')),
        #                         'edificio':self.edificio}) 
        # for i in self.lineas_resguardo_nocapitalizable:
        #     i.id_activo.write({'piso': self.getPisoId(self.piso.encode('utf-8')),
        #                         'edificio':self.edificio}) 

    def getPisoId(serf, strPiso):
        if(strPiso == 'Piso 1'):
            return 1
        if(strPiso == 'Piso 2'):
            return 2
        if(strPiso == 'Piso 3'):
            return 3
        if(strPiso == 'Piso 4'):
            return 4
        if(strPiso == 'Piso 5'):
            return 5
        if(strPiso == 'Piso 6'):
            return 7
        if(strPiso == 'Piso 7'):
            return 7
        if(strPiso == 'Piso 8'):
            return 8
        if(strPiso == 'Piso 9'):
            return 9
        if(strPiso == 'Piso 10'):
            return 10
        if(strPiso == 'Piso 11'):
            return 11
        if(strPiso == 'Piso 12'):
            return 12
        if(strPiso == 'PB'):
            return 13
        if(strPiso == 'Planta baja'):
            return 13
        if(strPiso == 'Edificio Coyoacán - Piso 5'):
            return 5
        if(strPiso == 'Planta baja'):
            return 13
        if(strPiso == 'E1'):
            return 14
        if(strPiso == 'E2'):
            return 15
        if(strPiso == 'Almacén General'):
            return 16
        if(strPiso == 'Archivo General'):
            return 1
        if(strPiso == 'Sindicato'):
            return 1
        if(strPiso == 'Archivo de Sala Superior'):
            return 1
        if(strPiso == 'Edificio Coyoacán - Piso PB'):
            return 13
        if(strPiso == 'Estacionamiento 2'):
            return 15
        if(strPiso == 'Estacionamiento 1'):
            return 14

        	

            


class update_tjacdmx_account_asset(models.Model): 
    _inherit = 'account.asset.asset'
    _inherit = 'asset.asset.report'
    _inherit = 'account.asset.category'
