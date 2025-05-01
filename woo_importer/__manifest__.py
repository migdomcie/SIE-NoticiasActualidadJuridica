# -*- coding: utf-8 -*-
{
    'name': 'WooCommerce Order Importer',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Importa pedidos desde WooCommerce a Odoo',
    'description': """
Módulo para importar pedidos desde WooCommerce a Odoo
=====================================================

Este módulo permite:
* Conectarse a la API de WooCommerce
* Importar pedidos de forma manual o automática
* Mapear estados de pedidos entre WooCommerce y Odoo
* Configurar la frecuencia de importación
* Mantener un registro de importaciones
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'base',
        'sale_management',
        'stock',
        'delivery',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'data/ir_cron_data.xml',
        'views/woo_importer_views.xml',
        'views/menu_views.xml',
    ],
    'external_dependencies': {
        'python': ['woocommerce'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}