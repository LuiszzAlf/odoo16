# -*- coding: utf-8 -*-
{
    'name': 'Financieros',
    'version': '1.0',
    'author': "TJACDMX",
    'category': 'Accounting/Accounting',
    'depends': ['base', 'mail','account','purchase','stock'],
    'description': """
Este módulo contiene los catálogos, procesos y funcionalidades presupuestales y contables para el proceso gubernamental en 
Tribunal de Justicia Administrativa de la Ciudad de México.
========================================================================

Presupuestos:
-------------------
    * Control de presupuesto 
    * Ministraciones 
    * Cuentas de orden 
    * Reportes CONAC y LDF

Contabilidad:
-------------------
    * Facturación 
    * Inventario 
    * Activo fijo 
    * Compras
    
    """,
    'data': [
        'wizard/wizard_cp_acumulado_view.xml',
        'wizard/wizard_remanentes_view.xml',
        'wizard/wizard_control_periodo_view.xml',
        'wizard/wizard_polizas_presupuestales.xml',
        
        'views/polizas_presupuestales.xml',
        'views/transferencia.xml',
        'views/control_presupuesto.xml',
        'views/control_presupuestal_view.xml',
        'views/documento.xml',
        'views/ministracion_presupuestal.xml',
        'views/notas_estados_financieros.xml',
        'views/contabilidad.xml',
        'views/account_account_views.xml',
        'views/configuracion/version.xml',
        'views/configuracion/clase_documento.xml',
        'views/fondo_economico.xml',
        'views/cuenta_orden.xml',
        'views/centro_gestor.xml',
        'views/area_funcional.xml',
        'views/partida_presupuestal.xml',
        'views/menu.xml',
        # 'report/product_pricelist_report_templates.xml',
    ],
    'demo': [
      
    ],
    'installable': True,
    'application': True,
    'assets': {
        # 'web.assets_backend': [
        #     'product/static/src/js/**/*',
        #     'product/static/src/xml/**/*',
        # ],
    },
    'license': 'LGPL-3',
}
