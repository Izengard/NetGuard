# Glosario Tecnico

"""
Respuesta HTTP (Response)

┌──────────────────────────────────────────┐
│ STATUS LINE                              │
│ HTTP/1.1 200 OK\r\n                      │
├──────────────────────────────────────────┤
│ HEADERS                                  │
│ Content-Type: text/html\r\n              │
│ Content-Length: 150\r\n                  │
│ ...\r\n                                  │
├──────────────────────────────────────────┤
│ BLANK LINE                               │
│ \r\n                                     │
├──────────────────────────────────────────┤
│ BODY                                     │
│ <html>...</html>                         │
└──────────────────────────────────────────┘
"""
'''

            Estructura de un Mensaje HTTP

            HTTP usa **CRLF** (`\r\n`) como terminador de línea.

            Petición HTTP (Request)

            ┌──────────────────────────────────────────┐
            │ REQUEST LINE                             │
            │ GET /path HTTP/1.1\r\n                   │
            ├──────────────────────────────────────────┤
            │ HEADERS                                  │
            │ Header1: value1\r\n                      │
            │ Header2: value2\r\n                      │
            │ ...\r\n                                  │
            ├──────────────────────────────────────────┤
            │ BLANK LINE (separador)                   │
            │ \r\n                                     │
            ├──────────────────────────────────────────┤
            │ BODY (opcional)                          │
            │ username=admin&password=123              │
            └──────────────────────────────────────────┘
        '''

 responses = {
        200: ('OK', 'Solicitud exitosa'),
        201: ('Creado', 'Recurso creado exitosamente'),
        204: ('Sin Contenido', 'Solicitud exitosa sin contenido que devolver'),
        301: ('Movido Permanentemente', 'El recurso ha sido movido permanentemente'),
        302: ('Encontrado', 'El recurso ha sido movido temporalmente'),
        400: ('Solicitud Incorrecta', 'El servidor no pudo entender la solicitud'),
        401: ('No Autorizado', 'Debe autenticarse para acceder a este recurso'),
        403: ('Prohibido', 'No tiene permisos para acceder a este recurso'),
        404: ('No Encontrado', 'La página que está buscando no existe'),
        405: ('Método No Permitido', 'Método HTTP no permitido para esta ruta'),
        500: ('Error Interno del Servidor', 'El servidor encontró un error inesperado'),
        502: ('Gateway Incorrecto', 'El servidor recibió una respuesta inválida'),
        503: ('Servicio No Disponible', 'El servidor no está disponible temporalmente'),
    }
