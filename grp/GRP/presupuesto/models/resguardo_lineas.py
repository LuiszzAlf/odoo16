# -*- coding: UTF-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime

class resguardo_lineas(models.Model):
    _name = 'tjacdmx.resguardo_lineas'
    resguardo_id = fields.Integer(string='resguardo',track_visibility='onchange')
    # resguardo_id = fields.Many2one('tjacdmx.resguardos',string='Resguardo',track_visibility='onchange')
    id_activo = fields.Many2one('account.asset.asset',string='Nombre de activo',  domain=[('state', '=', 'open'),('status', '=', 'open')],required=True,track_visibility='onchange')
    status=fields.Char(string='Status',default='espera')

    _edificio = fields.Char(compute="_put_location", string="Edificio",track_visibility='onchange')
    _piso = fields.Char(compute="_put_location", string="Piso")
    fecha_creacion = fields.Char(compute="_put_date", string="Fecha de creación",track_visibility='onchange')
    fecha_modificacion = fields.Char(compute="_put_date", string="Ultima modificación",track_visibility='onchange')

    code = fields.Char(compute="_get_code", string="No. de Inventario")
    check_line= fields.Boolean(string='Select',default=True)

    @api.model
    def create(self,vals):
        result = super(resguardo_lineas, self).create(vals)
        resguardo = self.env['tjacdmx.resguardos'].search([('id','=',result.resguardo_id)])
        mov_activo = self.env['tjacdmx.movimientos_resguardante']
        mov_activo.create({
                            'resguardante': resguardo.resguardante.id,
                            'activo': result.id_activo.id,
                            'tipo': 'asignacion'
                        })
        return result

    
    def unlink(self):
        mov_activo = self.env['tjacdmx.movimientos_resguardante']
        resguardo = self.env['tjacdmx.resguardos'].search([('id','=',self.resguardo_id)])
        mov_create= mov_activo.create({
                            'resguardante': resguardo.resguardante.id,
                            'activo': self.id_activo.id,
                            'tipo': 'desasignacion'
                        })
        return super(resguardo_lineas, self).unlink()
    
    
    def _put_location(self):
        location = self.env['account.asset.asset'].search([('id','=',self.id_activo.id)])
        if (location.piso==13):
            self._piso = 'PB'
        elif (location.piso==14):
            self._piso = 'E1'
        elif (location.piso==15):
            self._piso = 'E2'
        elif (location.piso==16):
            self._piso = 'Almacén General'
        else:
            self._piso = location.piso
            
        if location.edificio == 'Insurgentes':
            self._edificio = 'Insurgentes'
        elif location.edificio == 'Coyoacan':
            self._edificio = 'Coyoacan'
        elif location.edificio == 'Nebraska':
            self._edificio = 'Nebraska'

    
    def _put_date(self):
        self.fecha_creacion = self.create_date
        self.fecha_modificacion = self.write_date

    
    def liberar_activos(self):
        fecha_actual = datetime.now()
        idx = self.env['tjacdmx.resguardos'].search([('id','=',self.resguardo_id)])
        #raise ValidationError("debug: %s" % (idx.id_empleado))
        id_emple_lib=idx.id_empleado
        query = "UPDATE account_asset_asset SET status='open', id_empleado_linea=Null, emple_asig=Null,write_date = '%s' WHERE id = %s;" % (fecha_actual,self.id_activo.id)
        query1 = "UPDATE tjacdmx_log_resguardo_lineas SET tipo_mov = 'Liberado', write_date = '%s' WHERE resguardo_id = %s AND id_activo = %s;" % (fecha_actual,self.resguardo_id,self.id_activo.id)
        query2 = "UPDATE tjacdmx_log_resguardos SET write_date = '%s' WHERE id_empleado = %s;" % (fecha_actual,idx.id_empleado)
        query3 = "UPDATE tjacdmx_resguardos SET write_date = '%s' WHERE id = %s AND id_empleado = %s" % (fecha_actual,self.resguardo_id,id_emple_lib)
        query4 = "DELETE FROM tjacdmx_resguardo_lineas WHERE resguardo_id = %s AND id_activo = %s;" % (self.resguardo_id,self.id_activo.id)
        # raise ValidationError("%s, %s ,%s, %s, %s" % (query,query1,query2,query3,query4))
        self.env.cr.execute(query)
        self.env.cr.execute(query1)
        self.env.cr.execute(query2)
        self.env.cr.execute(query3)
        self.env.cr.execute(query4)
        return {
                'type': 'ir.actions.client',
                'tag': 'reload',
        }

    
    def _get_code(self):
        _code = self.env['account.asset.asset'].search([('id','=',self.id_activo.id)])
        self.code = _code.code
    
    @api.onchange('id_activo')
    
    def onchange_id_activo(self):
        self._get_code()


class resguardo_lineas_no_capitalisable(models.Model):
    _name = 'tjacdmx.resguardo_lineas_no_capitalisable'
    resguardo_id = fields.Integer(string='resguardo',track_visibility='onchange')
    id_activo = fields.Many2one('tjacdmax.activos_no_capitalizables',string='Nombre de activo',required=True,track_visibility='onchange')
    status=fields.Char(string='Status',default='espera')

    _edificio = fields.Char(compute="_put_location", string="Edificio",track_visibility='onchange')
    _piso = fields.Char(compute="_put_location", string="Piso")
    fecha_creacion = fields.Char(compute="_put_date", string="Fecha de creación",track_visibility='onchange')
    fecha_modificacion = fields.Char(compute="_put_date", string="Ultima modificación",track_visibility='onchange')

    code = fields.Char(compute="_get_code", string="No. de Inventario")
    check_line= fields.Boolean(string='Select',default=True)


    @api.model
    def create(self,vals):
        result = super(resguardo_lineas_no_capitalisable, self).create(vals)
        resguardo = self.env['tjacdmx.resguardos'].search([('id','=',result.resguardo_id)])
        mov_activo = self.env['tjacdmx.mov_activos_no_capitalizables']
        mov_activo.create({
                            'resguardante': resguardo.resguardante.id,
                            'activo_no_capitalizable': result.id_activo.id,
                            'tipo': 'asignacion'
                        })
        return result

    
    def unlink(self):
        mov_activo = self.env['tjacdmx.mov_activos_no_capitalizables']
        resguardo = self.env['tjacdmx.resguardos'].search([('id','=',self.resguardo_id)])
        mov_create= mov_activo.create({
                            'resguardante': resguardo.resguardante.id,
                            'activo_no_capitalizable': self.id_activo.id,
                            'tipo': 'desasignacion'
                        })
        return super(resguardo_lineas_no_capitalisable, self).unlink()

    
    def liberar_activos(self):
        query4 = "DELETE FROM tjacdmx_resguardo_lineas_no_capitalisable WHERE resguardo_id = %s AND id_activo = %s;" % (self.resguardo_id,self.id_activo.id)
        query_linnc = "UPDATE tjacdmax_activos_no_capitalizables SET status='open', id_empleado_linea=Null, resguardante=Null WHERE id = %s;" % (self.id_activo.id)
        self.env.cr.execute(query_linnc)
        self.env.cr.execute(query4)

        return {
                'type': 'ir.actions.client',
                'tag': 'reload',
        }

    
    def _get_code(self):
        _code = self.env['tjacdmax.activos_no_capitalizables'].search([('id','=',self.id_activo.id)])
        self.code = _code.clave
    
    @api.onchange('id_activo')
    
    def onchange_id_activo(self):
        self._get_code()

    
    def _put_location(self):
        location = self.env['tjacdmax.activos_no_capitalizables'].search([('id','=',self.id_activo.id)])
        if (location.piso==13):
            self._piso = 'PB'
        elif (location.piso==14):
            self._piso = 'E1'
        elif (location.piso==15):
            self._piso = 'E2'
        elif (location.piso==16):
            self._piso = 'Almacén General'
        else:
            self._piso = location.piso
            
        if location.edificio == 'Insurgentes':
            self._edificio = 'Insurgentes'
        elif location.edificio == 'Coyoacan':
            self._edificio = 'Coyoacan'
        elif location.edificio == 'Nebraska':
            self._edificio = 'Nebraska'


class resguardo_archivo(models.Model):
    _name = 'tjacdmx.resguardos.archivo'

    archivo = fields.Binary('File', required=True)
    archivo_filename = fields.Char("Image Filename")
    descripcion = fields.Text(string=u'Descripción') 
    resguardo_id = fields.Integer(string=u'resguardo_id') 


class resguardo_lineas_arrendamiento(models.Model):
    _name = 'tjacdmx.resguardo_lineas_arrendamiento'
    resguardo_id = fields.Integer(string='resguardo',track_visibility='onchange')
    id_activo = fields.Many2one('tjacdmax.arrendamiento',string='Nombre de activo',required=True,track_visibility='onchange')
    status=fields.Char(string='Status',default='espera')

    _edificio = fields.Char(compute="_put_location", string="Edificio",track_visibility='onchange')
    _piso = fields.Char(compute="_put_location", string="Piso")
    no_serie=fields.Char(compute="_put_location", string="Piso")
    fecha_creacion = fields.Char(compute="_put_date", string="Fecha de creación",track_visibility='onchange')
    fecha_modificacion = fields.Char(compute="_put_date", string="Ultima modificación",track_visibility='onchange')

    code = fields.Char(compute="_get_code", string="Referencia")
    check_line= fields.Boolean(string='Select',default=True)


    @api.model
    def create(self,vals):
        result = super(resguardo_lineas_arrendamiento, self).create(vals)
        resguardo = self.env['tjacdmx.resguardos'].search([('id','=',result.resguardo_id)])
        mov_activo = self.env['tjacdmx.mov_resguardante_arrendamiento']
        mov_activo.create({
                            'resguardante': resguardo.resguardante.id,
                            'activo_arrendamiento': result.id_activo.id,
                            'tipo': 'asignacion'
                        })
        return result

    
    def unlink(self):
        mov_activo = self.env['tjacdmx.mov_resguardante_arrendamiento']
        resguardo = self.env['tjacdmx.resguardos'].search([('id','=',self.resguardo_id)])
        mov_create= mov_activo.create({
                            'resguardante': resguardo.resguardante.id,
                            'activo_arrendamiento': self.id_activo.id,
                            'tipo': 'desasignacion'
                        })
        return super(resguardo_lineas_arrendamiento, self).unlink()

    
    def liberar_activos(self):
        query4 = "DELETE FROM tjacdmx_resguardo_lineas_arrendamiento WHERE resguardo_id = %s AND id_activo = %s;" % (self.resguardo_id,self.id_activo.id)
        query_linnc = "UPDATE tjacdmax_arrendamiento SET status='open', id_empleado_linea=Null, resguardante=Null WHERE id = %s;" % (self.id_activo.id)
        self.env.cr.execute(query_linnc)
        self.env.cr.execute(query4)

        return {
                'type': 'ir.actions.client',
                'tag': 'reload',
        }

    
    def _get_code(self):
        _code = self.env['tjacdmax.arrendamiento'].search([('id','=',self.id_activo.id)])
        self.code = _code.descripcion
    
    @api.onchange('id_activo')
    
    def onchange_id_activo(self):
        self._get_code()

    
    def _put_location(self):
        location = self.env['tjacdmax.arrendamiento'].search([('id','=',self.id_activo.id)])
        self.no_serie=location.no_serie
        if (location.piso==13):
            self._piso = 'PB'
        elif (location.piso==14):
            self._piso = 'E1'
        elif (location.piso==15):
            self._piso = 'E2'
        elif (location.piso==16):
            self._piso = 'Almacén General'
        else:
            self._piso = location.piso
            
        if location.edificio == 'Insurgentes':
            self._edificio = 'Insurgentes'
        elif location.edificio == 'Coyoacan':
            self._edificio = 'Coyoacan'
        elif location.edificio == 'Nebraska':
            self._edificio = 'Nebraska'
    
    
    def report_resguardo_arrendamiento(self):
        datas ={}
        resguardo = self.env['tjacdmx.resguardos'].search([('id','=',self.resguardo_id)])
        if(self.id_activo):
            datas['marca']='-'
            datas['modelo']='-'
            datas['serie']='-'
            datas['placa']='-'
            datas['no_inventario']='-'

            datas['marca_asigna']= self.id_activo.marca  if self.id_activo.marca else '-'
            datas['modelo_asigna']=self.id_activo.modelo  if self.id_activo.modelo else '-'
            datas['serie_asigna']=self.id_activo.no_serie  if self.id_activo.no_serie else '-'
            datas['placa_asigna']= self.id_activo.referencia  if self.id_activo.referencia else '-'
            datas['no_inventario_asigna']=self.id_activo.referencia  if self.id_activo.referencia else '-'
            
            datas['fecha']=self.write_date  if self.write_date else '-'
            datas['usuario']=resguardo.nombre_empleado  if resguardo.nombre_empleado else '-'
            datas['area']=resguardo.area  if resguardo.area else '-'
            datas['piso']=resguardo.piso  if resguardo.piso else '-'
            datas['cargo']=resguardo.puesto  if resguardo.puesto else '-'
            datas['titular']= '-'
        return self.env['report'].get_action([], 'reportes.print_resguardo_arrendamiento', data=datas)

