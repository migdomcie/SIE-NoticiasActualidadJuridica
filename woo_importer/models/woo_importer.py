# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from woocommerce import API
import logging
import pytz

_logger = logging.getLogger(__name__)

class WooCommerceOrderImporter(models.Model):
    _name = 'woo.order.importer'
    _description = 'Importador de Pedidos desde WooCommerce'
    
    name = fields.Char('Nombre', required=True, default='WooCommerce Connector')
    active = fields.Boolean('Activo', default=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    
    # Configuración del intervalo
    interval = fields.Selection([
        ('15min', 'Cada 15 minutos'),
        ('30min', 'Cada 30 minutos'),
        ('1h', 'Cada hora'),
        ('6h', 'Cada 6 horas'),
        ('12h', 'Cada 12 horas'),
        ('24h', 'Cada día'),
    ], string='Frecuencia de importación', default='1h')
    
    # Credenciales de WooCommerce
    woo_api_url = fields.Char('URL de la API de WooCommerce', required=True)
    woo_key = fields.Char('Clave API', required=True)
    woo_secret = fields.Char('Secreto API', required=True)
    
    # Estados de pedidos a importar
    order_status_to_import = fields.Selection([
        ('all', 'Todos los estados'),
        ('completed', 'Solo completados'),
        ('processing', 'En proceso'),
        ('custom', 'Personalizado'),
    ], string='Estados a importar', default='completed')
    
    custom_status = fields.Char('Estados personalizados', help='Separados por comas: completed,processing,on-hold')
    
    # Campos para seguimiento
    last_import_date = fields.Datetime('Última importación')
    import_count = fields.Integer('Número de importaciones', default=0)
    total_orders_imported = fields.Integer('Total pedidos importados', default=0)
    
    # Configuración de asignación
    pricelist_id = fields.Many2one('product.pricelist', string='Lista de precios para pedidos')
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén')
    team_id = fields.Many2one('crm.team', string='Equipo de ventas')
    
    # Mapeo de estados
    importer_id = fields.Many2one('woo.order.importer', string="Importador")
    woo_status = fields.Char(string="Estado WooCommerce")
    odoo_status = fields.Selection([
        ('draft', 'Borrador'),
        ('sale', 'Confirmado'),
        ('cancel', 'Cancelado'),
    ], string="Estado Odoo")
    
    # Log de importaciones
    import_log_ids = fields.One2many('woo.import.log', 'importer_id', string='Registro de importaciones')
    
    @api.model
    def _get_interval_seconds(self, interval):
        """Convierte el intervalo seleccionado a segundos"""
        intervals = {
            '15min': 15 * 60,
            '30min': 30 * 60,
            '1h': 60 * 60,
            '6h': 6 * 60 * 60,
            '12h': 12 * 60 * 60,
            '24h': 24 * 60 * 60,
        }
        return intervals.get(interval, 60 * 60)
    
    def get_woo_api(self):
        """Configurar y devolver la conexión con WooCommerce"""
        try:
            return API(
                url=self.woo_api_url,
                consumer_key=self.woo_key,
                consumer_secret=self.woo_secret,
                version="wc/v3",
                timeout=30
            )
        except Exception as e:
            raise UserError(_("Error al conectar con WooCommerce: %s") % str(e))
    
    def get_order_statuses_to_import(self):
        """Obtener los estados de pedido que deben importarse"""
        if self.order_status_to_import == 'all':
            return None  # Sin filtro de estado
        elif self.order_status_to_import == 'custom' and self.custom_status:
            return self.custom_status.split(',')
        else:
            return [self.order_status_to_import]
    
    def _prepare_order_data(self, woo_order):
        """Prepara los datos del pedido de WooCommerce para Odoo"""
        # Buscar o crear el cliente
        partner = self._get_or_create_customer(woo_order)
        
        # Preparar líneas de pedido
        order_lines = self._prepare_order_lines(woo_order)
        
        # Mapear el estado de WooCommerce a Odoo
        status = self._map_order_status(woo_order.get('status', 'pending'))
        
        # Crear diccionario de datos para el pedido de venta
        order_date = datetime.strptime(woo_order.get('date_created', ''), "%Y-%m-%dT%H:%M:%S")
        
        vals = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'date_order': order_date,
            'state': status,
            'woo_order_id': str(woo_order['id']),
            'woo_order_number': woo_order.get('number', ''),
            'woo_order_key': woo_order.get('order_key', ''),
            'note': woo_order.get('customer_note', ''),
            'order_line': order_lines,
        }
        
        # Asignar equipo de ventas si está configurado
        if self.team_id:
            vals['team_id'] = self.team_id.id
            
        # Asignar almacén si está configurado
        if self.warehouse_id:
            vals['warehouse_id'] = self.warehouse_id.id
            
        # Asignar lista de precios si está configurada
        if self.pricelist_id:
            vals['pricelist_id'] = self.pricelist_id.id
            
        return vals
    
    def _map_order_status(self, woo_status):
        """Mapea el estado de WooCommerce a un estado de Odoo"""
        # Buscar si hay un mapeo personalizado para este estado
        mapping = self.woo_status_mapping_ids.filtered(lambda m: m.woo_status == woo_status)
        if mapping:
            return mapping.odoo_status
            
        # Mapeo por defecto si no hay personalizado
        status_map = {
            'pending': 'draft',
            'processing': 'sale',
            'on-hold': 'sent',
            'completed': 'sale',
            'cancelled': 'cancel',
            'refunded': 'cancel',
            'failed': 'cancel',
        }
        return status_map.get(woo_status, 'draft')
    
    def _get_or_create_customer(self, woo_order):
        """Busca o crea un cliente basado en los datos de WooCommerce"""
        Partner = self.env['res.partner']
        
        # Extraer datos del cliente
        billing = woo_order.get('billing', {})
        email = billing.get('email', '')
        
        if not email:
            # Si no hay email, usar un cliente genérico
            return self.env.ref('base.public_partner')
        
        # Buscar si el cliente ya existe por email
        partner = Partner.search([('email', '=', email)], limit=1)
        
        if not partner:
            # Crear nuevo cliente
            partner_vals = {
                'name': f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip(),
                'email': email,
                'phone': billing.get('phone', ''),
                'street': billing.get('address_1', ''),
                'street2': billing.get('address_2', ''),
                'city': billing.get('city', ''),
                'zip': billing.get('postcode', ''),
                'woo_customer_id': woo_order.get('customer_id', '0'),
                'customer_rank': 1,
            }
            
            # Buscar país
            if billing.get('country', ''):
                country = self.env['res.country'].search([('code', '=', billing.get('country'))], limit=1)
                if country:
                    partner_vals['country_id'] = country.id
            
            # Buscar estado/provincia
            if billing.get('state', '') and 'country_id' in partner_vals:
                state = self.env['res.country.state'].search([
                    ('code', '=', billing.get('state')),
                    ('country_id', '=', partner_vals['country_id'])
                ], limit=1)
                if state:
                    partner_vals['state_id'] = state.id
            
            partner = Partner.create(partner_vals)
        
        return partner
    
    def _prepare_order_lines(self, woo_order):
        """Prepara las líneas del pedido"""
        order_lines = []
        
        for item in woo_order.get('line_items', []):
            product = self._get_or_create_product(item)
            
            if not product:
                _logger.warning(f"Producto no encontrado para línea de pedido: {item.get('name')}")
                continue
                
            line_vals = {
                'product_id': product.id,
                'name': item.get('name', ''),
                'product_uom_qty': item.get('quantity', 0),
                'price_unit': float(item.get('price', 0)),
                'woo_line_id': str(item.get('id', '')),
                'tax_id': [(6, 0, self._get_taxes(item).ids)],
            }
            
            order_lines.append((0, 0, line_vals))
            
        # Añadir líneas de envío
        shipping_lines = woo_order.get('shipping_lines', [])
        for shipping in shipping_lines:
            shipping_product = self._get_shipping_product()
            if shipping_product:
                shipping_line = {
                    'product_id': shipping_product.id,
                    'name': shipping.get('method_title', 'Gastos de envío'),
                    'product_uom_qty': 1,
                    'price_unit': float(shipping.get('total', 0)),
                    'is_delivery': True,
                }
                order_lines.append((0, 0, shipping_line))
        
        return order_lines
    
    def _get_or_create_product(self, item):
        """Busca o crea un producto basado en los datos de WooCommerce"""
        Product = self.env['product.product']
        
        # Intentar encontrar por ID de WooCommerce
        product_id = item.get('product_id', False)
        if product_id:
            product = Product.search([('woo_product_id', '=', str(product_id))], limit=1)
            if product:
                return product
                
        # Intentar encontrar por SKU
        sku = item.get('sku', False)
        if sku:
            product = Product.search([('default_code', '=', sku)], limit=1)
            if product:
                # Actualizar el ID de WooCommerce si no lo tenía
                if product_id and not product.woo_product_id:
                    product.write({'woo_product_id': str(product_id)})
                return product
        
        # Intentar encontrar por nombre
        name = item.get('name', '')
        if name:
            product = Product.search([('name', '=', name)], limit=1)
            if product:
                # Actualizar ID y SKU si no los tenía
                vals = {}
                if product_id and not product.woo_product_id:
                    vals['woo_product_id'] = str(product_id)
                if sku and not product.default_code:
                    vals['default_code'] = sku
                if vals:
                    product.write(vals)
                return product
        
        # Crear nuevo producto si está permitido
        if self.env['ir.config_parameter'].sudo().get_param('woo_order_importer.auto_create_products', 'False') == 'True':
            product_vals = {
                'name': name or 'Producto WooCommerce',
                'type': 'product',
                'default_code': sku if sku else f"WOO-{product_id}",
                'woo_product_id': str(product_id) if product_id else '',
                'lst_price': float(item.get('price', 0)),
            }
            return Product.create(product_vals)
        
        # Si no se encuentra y no se puede crear, usar producto genérico
        return self.env.ref('woo_order_importer.product_woo_generic', False)
    
    def _get_shipping_product(self):
        """Obtiene o crea un producto para los gastos de envío"""
        Product = self.env['product.product']
        shipping_product = Product.search([('is_delivery', '=', True)], limit=1)
        
        if not shipping_product:
            shipping_product = Product.create({
                'name': 'Gastos de envío',
                'type': 'service',
                'is_delivery': True,
                'sale_ok': True,
                'purchase_ok': False,
                'lst_price': 0.0,
            })
            
        return shipping_product
    
    def _get_taxes(self, item):
        """Obtiene los impuestos para una línea de pedido"""
        tax_ids = self.env['account.tax']
        
        # Si no hay impuestos o son 0, devolver conjunto vacío
        tax_total = float(item.get('total_tax', 0))
        if tax_total <= 0:
            return tax_ids
            
        # Buscar un impuesto que coincida aproximadamente con el porcentaje
        price = float(item.get('price', 0))
        quantity = float(item.get('quantity', 1))
        if price * quantity > 0:
            tax_percent = (tax_total / (price * quantity)) * 100
            tax_ids = self.env['account.tax'].search([
                ('type_tax_use', '=', 'sale'),
                ('amount', '>', tax_percent - 1),
                ('amount', '<', tax_percent + 1),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
        return tax_ids
    
    def import_orders(self):
        """Importar pedidos desde WooCommerce"""
        self.ensure_one()
        
        if not self.woo_api_url or not self.woo_key or not self.woo_secret:
            raise UserError(_("Debes configurar las credenciales de la API de WooCommerce"))
        
        wcapi = self.get_woo_api()
        SaleOrder = self.env['sale.order']
        
        # Determinar desde qué fecha importar
        date_from = self.last_import_date or fields.Datetime.now() - timedelta(days=30)
        date_from_str = date_from.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Preparar parámetros para la petición
        params = {"after": date_from_str, "per_page": 100}
        
        # Añadir filtro de estado si es necesario
        status_filter = self.get_order_statuses_to_import()
        if status_filter:
            if isinstance(status_filter, list):
                params["status"] = ",".join(status_filter)
            else:
                params["status"] = status_filter
        
        try:
            # Log de inicio
            log_vals = {
                'importer_id': self.id,
                'start_date': fields.Datetime.now(),
                'status': 'running',
            }
            import_log = self.env['woo.import.log'].create(log_vals)
            
            # Primera página
            response = wcapi.get("orders", params=params)
            if response.status_code != 200:
                error_msg = f"Error al obtener pedidos: {response.text}"
                _logger.error(error_msg)
                import_log.write({
                    'status': 'error',
                    'end_date': fields.Datetime.now(),
                    'error_message': error_msg,
                })
                return False
                
            all_orders = response.json()
            total_pages = int(response.headers.get('X-WP-TotalPages', 1))
            
            # Obtener el resto de páginas si hay más de una
            for page in range(2, total_pages + 1):
                params['page'] = page
                page_response = wcapi.get("orders", params=params)
                if page_response.status_code == 200:
                    all_orders.extend(page_response.json())
            
            # Procesar pedidos
            orders_created = 0
            orders_skipped = 0
            
            for woo_order in all_orders:
                # Comprobar si ya existe
                existing = SaleOrder.search([('woo_order_id', '=', str(woo_order['id']))], limit=1)
                if existing:
                    orders_skipped += 1
                    continue
                
                try:
                    # Preparar y crear el pedido
                    order_vals = self._prepare_order_data(woo_order)
                    new_order = SaleOrder.create(order_vals)
                    orders_created += 1
                    
                    # Confirmar automáticamente si está configurado
                    if self.env['ir.config_parameter'].sudo().get_param('woo_order_importer.auto_confirm_orders', 'False') == 'True':
                        if new_order.state == 'draft':
                            new_order.action_confirm()
                    
                    _logger.info(f"Pedido de WooCommerce creado: {woo_order['id']} -> Odoo ID: {new_order.id}")
                
                except Exception as e:
                    _logger.error(f"Error al crear pedido {woo_order['id']}: {str(e)}")
                    import_log.write({
                        'error_message': f"{import_log.error_message or ''}\nError en pedido {woo_order['id']}: {str(e)}",
                    })
            
            # Actualizar el registro de la importación
            self.write({
                'last_import_date': fields.Datetime.now(),
                'import_count': self.import_count + 1,
                'total_orders_imported': self.total_orders_imported + orders_created,
            })
            
            # Finalizar el log
            import_log.write({
                'status': 'completed',
                'end_date': fields.Datetime.now(),
                'orders_created': orders_created,
                'orders_skipped': orders_skipped,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Importación completada'),
                    'message': _('Se han importado %s pedidos. %s pedidos omitidos por ya existir.') % (orders_created, orders_skipped),
                    'sticky': False,
                }
            }
            
        except Exception as e:
            error_msg = f"Error durante la importación: {str(e)}"
            _logger.error(error_msg)
            
            if 'import_log' in locals():
                import_log.write({
                    'status': 'error',
                    'end_date': fields.Datetime.now(),
                    'error_message': error_msg,
                })
            
            raise UserError(error_msg)
    
    @api.model
    def _run_scheduled_import(self):
        """Método para ser llamado por el planificador de tareas"""
        importers = self.search([('active', '=', True)])
        for importer in importers:
            try:
                # Verificar si toca importar según el intervalo
                if importer.last_import_date:
                    interval_seconds = importer._get_interval_seconds(importer.interval)
                    next_import = importer.last_import_date + timedelta(seconds=interval_seconds)
                    if fields.Datetime.now() < next_import:
                        continue
                
                importer.import_orders()
                
            except Exception as e:
                _logger.error(f"Error en importación programada para {importer.name}: {str(e)}")
                # Crear log de error
                self.env['woo.import.log'].create({
                    'importer_id': importer.id,
                    'start_date': fields.Datetime.now(),
                    'end_date': fields.Datetime.now(),
                    'status': 'error',
                    'error_message': str(e),
                })

class WooStatusMapping(models.Model):
    _name = 'woo.status.mapping'
    _description = 'Mapeo de estados entre WooCommerce y Odoo'
    
    importer_id = fields.Many2one('woo.order.importer', string='Importador', required=True, ondelete='cascade')
    woo_status = fields.Char('Estado en WooCommerce', required=True)
    odoo_status = fields.Selection([
        ('draft', 'Presupuesto'),
        ('sent', 'Presupuesto enviado'),
        ('sale', 'Pedido de venta'),
        ('done', 'Bloqueado'),
        ('cancel', 'Cancelado'),
    ], string='Estado en Odoo', required=True, default='draft')
    
    _sql_constraints = [
        ('unique_status_per_importer', 'unique(importer_id, woo_status)', 'El estado de WooCommerce debe ser único por importador')
    ]

class WooImportLog(models.Model):
    _name = 'woo.import.log'
    _description = 'Registro de importaciones de WooCommerce'
    _order = 'start_date desc'
    
    importer_id = fields.Many2one('woo.order.importer', string='Importador', required=True, ondelete='cascade')
    start_date = fields.Datetime('Fecha de inicio', required=True)
    end_date = fields.Datetime('Fecha de fin')
    
    status = fields.Selection([
        ('running', 'En proceso'),
        ('completed', 'Completada'),
        ('error', 'Error'),
    ], string='Estado', default='running')
    
    orders_created = fields.Integer('Pedidos creados', default=0)
    orders_skipped = fields.Integer('Pedidos omitidos', default=0)
    error_message = fields.Text('Mensaje de error')
    
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for log in self:
            if log.start_date and log.end_date:
                duration = log.end_date - log.start_date
                log.duration = duration.total_seconds()
            else:
                log.duration = 0
                
    duration = fields.Float('Duración (seg)', compute='_compute_duration', store=True)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    woo_order_id = fields.Char('ID en WooCommerce', index=True)
    woo_order_number = fields.Char('Número de pedido en WooCommerce')
    woo_order_key = fields.Char('Clave del pedido en WooCommerce')
    
    _sql_constraints = [
        ('unique_woo_order_id', 'unique(woo_order_id)', 'Ya existe un pedido con este ID de WooCommerce')
    ]

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    woo_line_id = fields.Char('ID de línea en WooCommerce')

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    woo_customer_id = fields.Char('ID de cliente en WooCommerce', index=True)

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    woo_product_id = fields.Char('ID de producto en WooCommerce', index=True)