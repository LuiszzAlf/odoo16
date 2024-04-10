# -*- coding:utf-8 -*-
import requests
from odoo import models, fields, api
import logging
import pymysql.cursors
import time
import json
import sys
import base64
import zlib
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)

DB_HOST='172.16.5.1'
DB_PORT='3306'
DB_DATABASE='siarh2'
DB_USERNAME='root'
DB_PASSWORD='Gdf82506'

def con():
    con = pymysql.connect(host=DB_HOST,user=DB_USERNAME,password=DB_PASSWORD,db=DB_DATABASE,charset='utf8',cursorclass=pymysql.cursors.DictCursor)
    return con

def get(sql):
    try:
        with con().cursor() as cursor:
            cursor.execute(sql)
            result =cursor.fetchall()
            return result
    finally:
        con().close()

def get_one(sql):
    try:
        with con().cursor() as cursor:
            cursor.execute(sql)
            result =cursor.fetchone()
            return result
    finally:
        con().close()

def getHtml(url):
    html = ""
    headers = { 
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }

    try:
        r = requests.get(url, headers = headers)
        if r.status_code == requests.codes.ok:
            html = str(r.content)

    except requests.exceptions.RequestException as e:
        html = "error"

    return html


class Cronjob(models.Model):
    _name="presupuesto.cronjob"
    _description="CronJob Test"

    @api.multi
    def do_cron_task(self, **kwargs):
        resguardantes = self.env['tjacdmx.resguardantes']
        empleados_activos = []
        list_empleados = []
        distint_empleados = []
        #Actuales registrados
        empleados = self.env['tjacdmx.resguardantes'].search([])
        for ids in empleados:
            list_empleados.append(ids.num_empleado)

        #Consulta num_empleados_activos en ISIS
        emp="""
            SELECT b.clave 
            FROM movimientos_personal as a
            INNER JOIN empleados as b
            ON b.id_empleado = a.id_empleado
            WHERE a.fecha_baja IS NULL
            ORDER BY b.clave
        """
        query_empleados_activos = get(emp)
        for i in query_empleados_activos:
            empleados_activos.append(i['clave'])

        for i in empleados_activos:
            if i not in list_empleados:
                distint_empleados.append(i)
                
        sql="""SELECT * FROM empleados WHERE clave = 1003"""
        result = get(sql)
        datos_empleado=[]
        for it in result:
            data = {
                'id_empleado': it ['id_empleado'],
                'rfc': it ['rfc']
            }
            datos_empleado.append(data)

        id_resguardante = resguardantes.search([
            ('num_empleado','=', 1050)
        ])
        id_resguardante.write({
            'edificio': distint_empleados
        })
        
        #urlenvio = "http://siprod.tcadf.gob.mx/isisadmon/web/nomina.php/odoo/sincronizar"
        #getHtml(urlenvio)
