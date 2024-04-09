{
    'name': "visuelcode",
    'version': '1.0',
    'depends': ['base'],
    'author': "Visuel Code Technologies",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'views/menu.xml',
        'views/inventario.xml',
    ],
    'installable': True,
    'application': True,  
    # data files containing optionally loaded demonstration data
    'demo': [
        # 'demo/demo_data.xml',
    ],
}
