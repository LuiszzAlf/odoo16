# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError

class cotizaciones(models.Model):
    _name = 'tjacdmx.cotizaciones'
    _rec_name='area'

    area = fields.Char(string="Area Solicitante", required=True)
    fecha = fields.Date(string="Fecha")
    fecha_comite = fields.Date(string="Fecha de comite")
    conceptos = fields.One2many('tjacdmx.cotizacion_lineas', 'id_cotizacion', string="Conceptos", copy=True)
    procedimiento = fields.Text(string="procedimiento", required=True)

    # CAMPOS PARA LOS PROVEEDORES
    id_partner_1 = fields.Many2one('tjacdmx.proveedor_provisional', string="Nuevo proveedor")
    id_partner_odoo_1 = fields.Many2one('res.partner', string="Proveedor existente")
    exist_in_odoo_1 = fields.Selection([('1','Si'),('0','No')], string="¿El proveedor es nuevo?", required=True, default="1")
    condiciones_pago_1 = fields.Char(string="Condiciones de pago", required=True)
    vigencia_1 = fields.Char(string="Vigencia", required=True)
    tiempo_1 = fields.Char(string="Tiempo de entrega", required=True)
    garantia_1 = fields.Char(string="Garantia", required=True)
    observaciones_1 = fields.Text(string="Observaciones", required=True)

    id_partner_2 = fields.Many2one('tjacdmx.proveedor_provisional', string="Nuevo proveedor")
    id_partner_odoo_2 = fields.Many2one('res.partner', string="Proveedor existente")
    exist_in_odoo_2 = fields.Selection([('1','Si'),('0','No')], string="¿El proveedor es nuevo?", default="1")
    condiciones_pago_2 = fields.Char(string="Condiciones de pago")
    vigencia_2 = fields.Char(string="Vigencia")
    tiempo_2 = fields.Char(string="Tiempo de entrega")
    garantia_2 = fields.Char(string="Garantia")
    observaciones_2 = fields.Text(string="Observaciones")

    id_partner_3 = fields.Many2one('tjacdmx.proveedor_provisional', string="Nuevo proveedor")
    id_partner_odoo_3 = fields.Many2one('res.partner', string="Proveedor existente")
    exist_in_odoo_3 = fields.Selection([('1','Si'),('0','No')], string="¿El proveedor es nuevo?", default="1")
    condiciones_pago_3 = fields.Char(string="Condiciones de pago")
    vigencia_3 = fields.Char(string="Vigencia")
    tiempo_3 = fields.Char(string="Tiempo de entrega")
    garantia_3 = fields.Char(string="Garantia")
    observaciones_3 = fields.Text(string="Observaciones")
    # CAMPOS PARA LOS PROVEEDORES

    # CAMPO PARA CONOCER EL ESTATUS DE LA COTIZACION, ABIERTA O CERRADA
    status = fields.Char(string="Estatus",default="open")
    _status = fields.Char(compute="_put_status")
    # CAMPO QUE ALMACENA EL ID DEL PROVEEDOR GANADOR
    provee_ganador = fields.Integer(string="Proveedor ganador")
    provee = fields.Char(compute="_put_prove", string="Proveedor")
    # BANDERA PARA SABER DE DONDE TOMAR EL ID DEL PROVEEDOR GANADOR, 1=PROVEEDOR_PROVISIONAL, 0=RES_PARTNER
    isNew = fields.Integer(default=1)

    num_requisicion = fields.Char(string="No. de requisicion")

    muestra_boton = fields.Boolean(compute="_show_button")

    def _def_num_requisicion(self,):
        last_id = 0
        self.env.cr.execute('SELECT id FROM "tjacdmx_cotizaciones" ORDER BY id DESC LIMIT 1')
        ids_data = self.env.cr.fetchone()
        if ids_data>=0:
            last_id = ids_data[0]
        else:
            last_id = 0
        prefijo = '00'
        serie = last_id+1
        consecutivo = prefijo + str(serie).rjust(5, '0')
        self._show_button()
        return {
            'num_requisicion':consecutivo
        }

    @api.onchange('procedimiento')
    def _onchange_tipo(self):
        values = self._def_num_requisicion()
        self.update(values)

    #FUNCIONES PARA COLOCAR AL PROVEEDOR COMO GANADOR
    def activate_prove(self,data):
        fecha_actual = datetime.now()
        self.env.cr.execute("""
                                INSERT INTO res_partner(name,display_name,street,street2,city,state_id,zip,country_id,phone,notify_email,picking_warn,invoice_warn,purchase_warn,write_date,create_date,is_company,active)
                                VALUES ('%s','%s','%s','%s','%s',%s,'%s',%s,'%s','always','no-message','no-message','no-message','%s','%s',true,true)
                            """ %(data.nombre,data.nombre,data.street,data.colonia,data.city,data.state_id.id,data.cp,data.country_id.id,data.tel,fecha_actual,fecha_actual))
        # AGREGA EL REPRESENTANTE DEL PROVEEDOR
        query = "SELECT id FROM res_partner ORDER BY id DESC LIMIT 1"
        self.env.cr.execute(query)
        idx = self.env.cr.dictfetchone()
        self.env.cr.execute("""
                                INSERT INTO res_partner(name,display_name,street,street2,city,state_id,zip,country_id,phone,notify_email,picking_warn,invoice_warn,purchase_warn,write_date,create_date,parent_id,is_company,active)
                                VALUES ('%s','%s','%s','%s','%s',%s,'%s',%s,'%s','always','no-message','no-message','no-message','%s','%s',%s,false,true)
                            """ %(data.representante,data.representante,data.street,data.colonia,data.city,data.state_id.id,data.cp,data.country_id.id,data.tel,fecha_actual,fecha_actual,idx['id']))
        # BORRA EL REGISTRO DE LA TABLA DE PROVEEDORES PROVISIONALES DE MANERA LOGICA
        self.env.cr.execute("UPDATE tjacdmx_proveedor_provisional SET \"isDelete\" = 2 WHERE id = %s;" % (data.id))

    #ALMACENA LOS PRODUCTOS EN ODOO AL SELECCIONAR UN GANADOR DE LA COTIZACION
    def _put_product(self,idx):
      product = self.env['tjacdmx.cotizacion_lineas'].search([('id_cotizacion','=',idx)])
      fecha_actual = datetime.now()
      tipo = {1:"consu",2:"service",3:"product"}
      for i in product:
          self.env.cr.execute("""
                                  INSERT INTO product_template(name,type,uom_id,uom_po_id,categ_id,tracking,purchase_line_warn,write_date,create_date)
                                  VALUES ('%s','%s',%s,%s,%s,'%s','%s','%s','%s')
                              """ %(i.concepto,tipo[i.tipo],i.unidad_.id,i.unidad_.id,141,'none','no-message',fecha_actual,fecha_actual))

    def put_prove_ganador(self,idx):
        _id = False
        if idx == 1:
            if self.exist_in_odoo_1 == '1':
                _id = self.id_partner_1.id
                if _id != False:
                    data = self.env['tjacdmx.proveedor_provisional'].search([('id','=',self.id_partner_1.id)])
                    self.activate_prove(data)
            else:
                _id = self.id_partner_odoo_1.id
        elif idx == 2:
            if self.exist_in_odoo_2 == '1':
                _id = self.id_partner_2.id
                if _id != False:
                    data = self.env['tjacdmx.proveedor_provisional'].search([('id','=',self.id_partner_2.id)])
                    self.activate_prove(data)
            else:
                _id = self.id_partner_odoo_2.id
        elif idx == 3:
            if self.exist_in_odoo_3 == '1':
                _id = self.id_partner_3.id
                if _id != False:
                    data = self.env['tjacdmx.proveedor_provisional'].search([('id','=',self.id_partner_3.id)])
                    self.activate_prove(data)
            else:
                _id = self.id_partner_odoo_3.id

        if _id != False:
            self._put_product(self.id)
            self.write({'status':'close','provee_ganador':_id})

    def activate_prove_1(self):
        self.put_prove_ganador(1)

    def activate_prove_2(self):
        self.put_prove_ganador(2)

    def activate_prove_3(self):
        self.put_prove_ganador(3)

    #----------------------------------------------------------------- IMPRESION DE LOS REPORTES DE COTIZACION ------------------------------------------------------------------------------------------------------------------
    def _data_prove(self,flag,id_cotizacion,id_proveedor):
        if flag:
            query_prove = """
                          SELECT
                            CONCAT('new-',tpp.id) AS id_proveedor,tpp.nombre AS proveedor,CONCAT(tpp.street,', Col. ',tpp.colonia,', ',tpp.city,', ',rcs.name,', C.P. ',tpp.cp,', ',rc.name) as direccion,tpp.representante,tpp.tel
                          FROM tjacdmx_proveedor_provisional tpp
                          INNER JOIN res_country_state rcs ON tpp.state_id = rcs.id
                          INNER JOIN res_country rc ON tpp.country_id = rc.id
                          WHERE tpp.id=%s;
                          """ % (id_proveedor)
        else:
            query_prove = """
                         SELECT
                            CONCAT('old-',rp.id) AS id_proveedor,(CASE WHEN rp.parent_id isnull THEN rp.name ELSE rp.display_name END) AS proveedor,CONCAT(rp.street,', Col. ',rp.street2,', ',rcs.name,', C.P. ',rp.zip,', ',rc.name) as direccion,(CASE WHEN rp.parent_id isnull THEN 'No disponible' ELSE rp.name END) AS representante,rp.phone AS tel
                         FROM res_partner rp
                         INNER JOIN res_country_state rcs ON rp.state_id = rcs.id
                         INNER JOIN res_country rc ON rp.country_id = rc.id
                         WHERE rp.id=%s;
                          """ % (id_proveedor)
        self.env.cr.execute(query_prove)
        response = self.env.cr.dictfetchall()
        for j in response:
            info = {
                     'proveedor':j['proveedor'],
                     'representante':j['representante'],
                     'direccion':j['direccion'],
                     'tel':j['tel']
                    }
        return info

    def _put_info_report(self,proveedor1 = True,proveedor2 = True,proveedor3 = True):
        datas = {}
        totales = {1:0,2:0,3:0}
        query = """
                SELECT
                	tc.*,
                	tcl.id as id_lineas,tcl.concepto,tcl.tipo,tcl.unidad,tcl.cantidad,tcl.precio_unitario_1,tcl.precio_unitario_2,tcl.precio_unitario_3,
                	(tcl.cantidad * tcl.precio_unitario_1) as importe_1,(tcl.cantidad * tcl.precio_unitario_2) as importe_2,(tcl.cantidad * tcl.precio_unitario_3) as importe_3
                FROM tjacdmx_cotizaciones tc
                INNER JOIN tjacdmx_cotizacion_lineas tcl ON tc.id = tcl.id_cotizacion
                WHERE tc.id = %s;
                """ % (self.id)
        self.env.cr.execute(query)
        arr = self.env.cr.dictfetchall()
        if arr:
            datas['info'] = {
                                'folio':arr[0]['num_requisicion'],
                                'area':arr[0]['area'],
                                'fecha':arr[0]['fecha'],
                                'fecha_comite':arr[0]['fecha_comite'],
                                'requisicion': self.num_requisicion,
                                'procedimiento':arr[0]['procedimiento'] if arr[0]['procedimiento'] else 'No disponible'
                            }
            datas['conceptos'] = {}
            datas['proveedores'] = {}
            for i in arr:
                datas['conceptos'][int(i['id_lineas'])] = {'concepto':i['concepto'],'cantidad':i['cantidad'],'unidad':i['unidad'],'proveedores':{}}
                if proveedor1 and i['exist_in_odoo_1'] != None and (i['id_partner_1'] != None or i['id_partner_odoo_1'] != None):
                    if i['exist_in_odoo_1'] == '1':
                        _id = i['id_partner_1']
                        label = 'a'+'-'+str(_id)
                        flag = True
                    else:
                        _id = i['id_partner_odoo_1']
                        label = 'b'+'-'+str(_id)
                        flag = False
                    totales[1] += i['importe_1']
                    datas['proveedores']['proveedor1'] = self._data_prove(flag,self.id,_id)
                    datas['proveedores']['proveedor1']['total'] = totales[1]
                    datas['proveedores']['proveedor1']['condiciones_pago'] = i['condiciones_pago_1']
                    datas['proveedores']['proveedor1']['vigencia'] = i['vigencia_1']
                    datas['proveedores']['proveedor1']['tiempo'] = i['tiempo_1']
                    datas['proveedores']['proveedor1']['garantia'] = i['garantia_1']
                    datas['proveedores']['proveedor1']['observaciones'] = i['observaciones_1']
                    datas['conceptos'][int(i['id_lineas'])]['proveedores']['proveedor1'] = {'precio_unitario':i['precio_unitario_1'],'importe':i['importe_1']}

                if proveedor2 and i['exist_in_odoo_2'] != None and (i['id_partner_2'] != None or i['id_partner_odoo_2'] != None):
                    if i['exist_in_odoo_2'] == '1':
                        _id = i['id_partner_2']
                        label = 'a'+'-'+str(_id)
                        flag = True
                    else:
                        _id = i['id_partner_odoo_2']
                        label = 'b'+'-'+str(_id)
                        flag = False
                    totales[2] += i['importe_2']
                    datas['proveedores']['proveedor2'] = self._data_prove(flag,self.id,_id)
                    datas['proveedores']['proveedor2']['total'] = totales[2]
                    datas['proveedores']['proveedor2']['condiciones_pago'] = i['condiciones_pago_2']
                    datas['proveedores']['proveedor2']['vigencia'] = i['vigencia_2']
                    datas['proveedores']['proveedor2']['tiempo'] = i['tiempo_2']
                    datas['proveedores']['proveedor2']['garantia'] = i['garantia_2']
                    datas['proveedores']['proveedor2']['observaciones'] = i['observaciones_2']
                    datas['conceptos'][int(i['id_lineas'])]['proveedores']['proveedor2'] = {'precio_unitario':i['precio_unitario_2'],'importe':i['importe_2']}

                if proveedor3 and i['exist_in_odoo_3'] != None and (i['id_partner_3'] != None or i['id_partner_odoo_3'] != None):
                    if i['exist_in_odoo_3'] == '1':
                        _id = i['id_partner_3']
                        label = 'a'+'-'+str(_id)
                        flag = True
                    else:
                        _id = i['id_partner_odoo_3']
                        label = 'b'+'-'+str(_id)
                        flag = False
                    totales[3] += i['importe_3']
                    datas['proveedores']['proveedor3'] = self._data_prove(flag,self.id,_id)
                    datas['proveedores']['proveedor3']['total'] = totales[3]
                    datas['proveedores']['proveedor3']['condiciones_pago'] = i['condiciones_pago_3']
                    datas['proveedores']['proveedor3']['vigencia'] = i['vigencia_3']
                    datas['proveedores']['proveedor3']['tiempo'] = i['tiempo_3']
                    datas['proveedores']['proveedor3']['garantia'] = i['garantia_3']
                    datas['proveedores']['proveedor3']['observaciones'] = i['observaciones_3']
                    datas['conceptos'][int(i['id_lineas'])]['proveedores']['proveedor3'] = {'precio_unitario':i['precio_unitario_3'],'importe':i['importe_3']}
        datas['cat'] = {'condiciones_pago':'CONDICIONES DE PAGO:','vigencia':'VIGENCIA DE COTIZACIÓN','tiempo':'TIEMPO DE ENTREGA:','garantia':'GARANTIA:','observaciones':'OBSERVACIONES'}
        return datas

    #FUNCION QUE IMPRIME EL REPORTE
    
    def report_cotizacion(self):
        datas = self._put_info_report()
        datas['ids'] = self.id
        # raise ValidationError("%s" % (datas))
        return self.env['report'].get_action([], 'reportes.cotizacion_impre', data=datas)

    
    def _put_prove(self):
        self.provee = "No se ha seleccionado un proveedor ganador"
        if self.provee_ganador != 0:
            if self.exist_in_odoo_1 == '1':
                if self.provee_ganador == self.id_partner_1.id:
                    self.provee = self.env['tjacdmx.proveedor_provisional'].search([('id','=',self.id_partner_1.id)], limit=1).nombre
            if self.exist_in_odoo_1 == '0':
                if self.provee_ganador == self.id_partner_odoo_1.id:
                    self.provee = self.env['res.partner'].search([('id','=',self.id_partner_odoo_1.id)], limit=1, order='id desc').name

            if self.exist_in_odoo_2 == '1':
                if self.provee_ganador == self.id_partner_2.id:
                    self.provee = self.env['tjacdmx.proveedor_provisional'].search([('id','=',self.id_partner_2.id)], limit=1).nombre
            if self.exist_in_odoo_2 == '0':
                if self.provee_ganador == self.id_partner_odoo_2.id:
                    self.provee = self.env['res.partner'].search([('id','=',self.id_partner_odoo_2.id)], limit=1, order='id desc').name

            if self.exist_in_odoo_3 == '1':
                if self.provee_ganador == self.id_partner_3.id:
                    self.provee = self.env['tjacdmx.proveedor_provisional'].search([('id','=',self.id_partner_3.id)], limit=1).nombre
            if self.exist_in_odoo_3 == '0':
                if self.provee_ganador == self.id_partner_odoo_3.id:
                    self.provee = self.env['res.partner'].search([('id','=',self.id_partner_odoo_3.id)], limit=1, order='id desc').name


    
    def print_repo_1(self):
        idprove = self.id_partner_1.id if self.exist_in_odoo_1 == '1' else self.id_partner_odoo_1.id
        datas = self._put_info_report(True,False,False)
        datas['idcoti'] = self.id
        datas['idprove'] = idprove
        return self.env['report'].get_action([], 'reportes.cotizacion_prove_impre', data=datas)
    
    def print_repo_2(self):
        idprove = self.id_partner_2.id if self.exist_in_odoo_2 == '1' else self.id_partner_odoo_2.id
        datas = self._put_info_report(False,True,False)
        datas['idcoti'] = self.id
        datas['idprove'] = idprove
        return self.env['report'].get_action([], 'reportes.cotizacion_prove_impre', data=datas)
    
    def print_repo_3(self):
        idprove = self.id_partner_3.id if self.exist_in_odoo_3 == '1' else self.id_partner_odoo_3.id
        datas = self._put_info_report(False,False,True)
        datas['idcoti'] = self.id
        datas['idprove'] = idprove
        return self.env['report'].get_action([], 'reportes.cotizacion_prove_impre', data=datas)

    def _show_button(self):
        if type(self.id) != int:
            self.muestra_boton = False
        else:
            self.muestra_boton = True

    
    def _put_status(self):
        self._status = "Abierta" if self.status == 'open' else 'Cerrada'

    total_1 = fields.Float(compute="_def_total")
    total_2 = fields.Float(compute="_def_total")
    total_3  = fields.Float(compute="_def_total")

    def _def_total(self):
        self.env.cr.execute("SELECT precio_unitario_1,precio_unitario_2,precio_unitario_3 FROM tjacdmx_cotizacion_lineas WHERE id_cotizacion = %s" % (self.id))
        data = self.env.cr.dictfetchall()
        total = [0,0,0]
        # raise ValidationError("%s" % (data))
        for i in data:
            total[0] += i['precio_unitario_1']
            total[1] += i['precio_unitario_2']
            total[2] += i['precio_unitario_3']
        self.total_1 = total[0]
        self.total_2 = total[1]
        self.total_3 = total[2]

class cotizacion_lineas(models.Model):
    _name = 'tjacdmx.cotizacion_lineas'

    id_cotizacion = fields.Integer(string="cotizacion",required=True)
    concepto = fields.Char(string="Concepto",required=True)
    # proveedores = fields.One2many('tjacdmx.cotizacion_proveedores', 'id_cotizacion_lineas', string="Proveedores", copy=True, required=True)
    tipo = fields.Selection([
                              (1, 'Consumible'),
                              (2, 'Servicio'),
                              (3,'Almacenable')], string='Tipo de concepto', required=True)
    unidad = fields.Char(string="Unidad")
    unidad_ = fields.Many2one('product.uom', 'Unidad',
                              default=1, required=True,
                              help="Unidad de medida predeterminada utilizada para todas las operaciones del almacen.")
    cantidad = fields.Integer(string="Cantidad")
    #CAMPOS QUE SE RELACIONAN CON LOS PROVEEDORES
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)
    precio_unitario_1 = fields.Float(string="Precio unitario del proveedor 1", required=True)
    precio_unitario_2 = fields.Float(string="Precio unitario del proveedor 2")
    precio_unitario_3 = fields.Float(string="Precio unitario del proveedor 3")
    #CAMPOS QUE SE RELACIONAN CON LOS PROVEEDORES
    #TOTALES
    # tot_x_proveedor = fields.Float(string="Total", group_operator="sum")

class proveedor(models.Model):
    _name = 'tjacdmx.proveedor_provisional'
    _rec_name = 'nombre'

    nombre = fields.Char(string="Nombre", required=True)
    representante = fields.Char(string="Representante", required=True)
    street = fields.Char(string="Calle", required=True)
    colonia = fields.Char(string="Colonia", required=True)
    city = fields.Char(string="Ciudad", required=True)
    state_id = fields.Many2one("res.country.state", string="Estado", required=True)
    cp = fields.Char(string="C.P.", required=True)
    country_id = fields.Many2one("res.country", string="País", required=True)
    tel = fields.Char(string="Telefono", required=True)
    status = fields.Char(string="Status", default="Inactivo")
    isDelete = fields.Integer(string="isDelete", default=1, required=True)
    # Campo para saber si existe o no el proveedor en la tabla de proveedores de odoo
    _exist = fields.Integer(string="Existe", compute="_put_exist")

    
    def _put_exist(self):
        exist = self.env['res.partner'].search([('name','=',self.nombre)])
        if not exist:
            self._exist = 0
        else:
            self._exist = 1
