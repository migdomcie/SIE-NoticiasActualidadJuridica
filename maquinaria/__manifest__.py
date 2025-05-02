# -*- coding: utf-8 -*-

{
    'name': 'Maquinaria',
    'version': '1.0',
    'depends': ['base'],
    'author':"SBM_BFA_CBR",
    'category': 'Manufacturing/Maintenance',
    'description': """
    
    Comprobar el estado de las maquinas de la empresa
    
    """,
    'data': [
        'security/ir.model.access.csv',
        'views/maquinaria_property_views.xml',
        'views/maquinaria_menus.xml'
        
       
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'application': True
}
