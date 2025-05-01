# WooCommerce Order Importer para Odoo

Este módulo proporciona una integración completa entre WooCommerce y Odoo, permitiendo importar pedidos de forma automática o manual. Simplifica la sincronización de datos entre tu tienda online WooCommerce y tu sistema de gestión Odoo.

## Características

- **Importación flexible**: Programa importaciones automáticas o ejecútalas manualmente
- **Mapeo personalizable**: Configura cómo se traducen los estados de WooCommerce a Odoo
- **Gestión completa**: Importa productos, clientes, impuestos y gastos de envío
- **Seguimiento detallado**: Registros completos de todas las importaciones
- **Fácil configuración**: Configura la conexión con unos pocos parámetros

## Requisitos

- Odoo 14.0 o superior
- Biblioteca Python WooCommerce (`pip install woocommerce`)
- Acceso a la API REST de WooCommerce (v3)

## Instalación

1. Copia este módulo a tu carpeta de addons de Odoo
2. Actualiza la lista de módulos en Odoo
3. Instala el módulo "WooCommerce Order Importer"
4. Instala la biblioteca Python requerida:
   ```
   pip install woocommerce
   ```

## Configuración

1. Accede al menú **WooCommerce > Importadores**
2. Crea un nuevo importador
3. Configura la conexión API:
   - URL de la API de WooCommerce (ej: https://tutienda.com)
   - Clave API de WooCommerce
   - Secreto API de WooCommerce
4. Establece la frecuencia de importación
5. Configura opcionalmente el mapeo de estados y otros parámetros
6. Guarda la configuración

## Uso

### Importación Manual

1. Accede al importador configurado
2. Haz clic en el botón "Importar Ahora"
3. Revisa el registro de importación generado

### Importación Automática

Una vez configurado el importador con una frecuencia, el sistema ejecutará las importaciones automáticamente según el intervalo establecido.

Para ver los resultados de las importaciones automáticas, accede a **WooCommerce > Registros de Importación**.

## Solución de problemas

Si experimentas problemas durante la importación:

1. Verifica las credenciales de la API de WooCommerce
2. Asegúrate de que la URL de la API sea correcta y accesible
3. Revisa los registros de importación para ver mensajes de error específicos
4. Comprueba los registros de Odoo para errores técnicos (`/var/log/odoo/odoo.log`)

## Licencia

Este módulo está disponible bajo la licencia LGPL-3.

## Soporte

Para obtener soporte, contacta a [soporte@tuempresa.com](mailto:soporte@tuempresa.com) o visita nuestro sitio web [www.tuempresa.com](https://www.tuempresa.com).

---

Desarrollado por TuEmpresa