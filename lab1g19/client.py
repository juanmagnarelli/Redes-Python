#!/usr/bin/env python
# encoding: utf-8
# Revisión: 2015 Matias Molina
# Revisiones 2013-2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: client.py 387 2011-03-22 13:48:44Z nicolasw $

import socket
import logging
import optparse
import sys
import time
from constants import *


class Client(object):

    def __init__(self, server=DEFAULT_ADDR, port=DEFAULT_PORT):
        """
        Nuevo cliente, conectado al `server' solicitado en el `port' TCP
        indicado.

        Si falla la conexión, genera una excepción de socket.
        """
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.status = None
        self.s.connect((server, port))
        self.buffer = ''
        self.connected = True

    def close(self):
        """
        Desconecta al cliente del server, mandando el mensaje apropiado
        antes de desconectar.
        """

        self.send('quit')
        self.status, message = self.read_response_line()
        if self.status != CODE_OK:
            logging.warn("Warning: quit no contesto ok, sino '%s'(%s)'." %
                         (message, self.status))
        self.connected = False
        self.s.close()

    def send(self, message, timeout=None):
        """
        Envía el mensaje 'message' al server, seguido por el terminador de
        línea del protocolo.

        Si se da un timeout, puede abortar con una excepción socket.timeout.

        También puede fallar con otras excepciones de socket.
        """
        self.s.settimeout(timeout)
        message += EOL  # Completar el mensaje con un fin de línea
        while message:
            logging.debug("Enviando el (resto del) mensaje %s." %
                          repr(message))
            bytes_sent = self.s.send(message)
            assert bytes_sent > 0
            message = message[bytes_sent:]

    def _recv(self, timeout=None):
        """
        Recibe datos y acumula en el buffer interno.

        Para uso privado del cliente.
        """
        self.s.settimeout(timeout)
        data = self.s.recv(4096)
        self.buffer += data
        if len(data) == 0:
            logging.info(u"El server interrumpió la conexión.")
            self.connected = False

    def read_line(self, timeout=None):
        """
        Espera datos hasta obtener una línea completa delimitada por el
        terminador del protocolo.

        Devuelve la línea, eliminando el terminador y los espacios en blanco
        al principio y al final.
        """
        while EOL not in self.buffer and self.connected:
            if timeout is not None:
                t1 = time.clock()
            self._recv(timeout)
            if timeout is not None:
                t2 = time.clock()
                timeout -= t2 - t1
                t1 = t2
        if EOL in self.buffer:
            response, self.buffer = self.buffer.split(EOL, 1)
        else:
            response, self.buffer = self.buffer, ''
        return response.strip()

    def read_response_line(self, timeout=None):
        """
        Espera y parsea una línea de respuesta de un comando.

        Devuelve un par (int, str) con el código y el error, o
        (None, None) en caso de error.
        """
        result = None, None
        response = self.read_line(timeout)
        if ' ' in response:
            code, message = response.split(None, 1)
            try:
                result = int(code), message
            except ValueError:
                pass
        else:
            logging.warn(u"Respuesta inválida: '%s'" % response)
        return result

    def read_fragment(self):
        """
        Espera y lee un fragmento de un archivo.

        Devuelve el contenido del fragmento.
        """

        # No podemos usar read_line, por que el fragmento puede tener \r y/o \n
        # adentro

        # Leer hasta tener una longitud, y parsear la longitud del archivo
        while ' ' not in self.buffer and self.connected:
            self._recv()
        if not self.connected:
            return ''
        length, self.buffer = self.buffer.split(' ', 1)
        length = int(length)
        # Ahora, esperamos hasta tener la cantidad de datos necesaria
        while len(self.buffer) < length and self.connected:
            self._recv()
        fragment, self.buffer = self.buffer[:length], self.buffer[length:]
        # Leer el \r\n final
        while len(self.buffer) < len(EOL) and self.connected:
            self._recv()
        assert self.buffer.startswith(EOL)
        self.buffer = self.buffer[len(EOL):]
        return fragment

    def file_lookup(self):
        """
        Obtener el listado de archivos en el server. Devuelve una lista
        de strings.
        """
        result = []
        self.send('get_file_listing\r\nget_file_listing\r\nget_metadata client.py\r\nget_file_listing')
        self.status, message = self.read_response_line()
        if self.status == CODE_OK:
            filename = self.read_line()
            while filename:
                logging.debug("Received filename %s" % filename)
                result.append(filename)
                filename = self.read_line()
        else:
            logging.warn(u"Falló la solicitud de la lista de archivos" +
                         "(code=%s %s)." % (self.status, message))
        return result

    def get_metadata(self, filename):
        """
        Obtiene en el server el tamaño del archivo con el nombre dado.
        Devuelve None en caso de error.
        """
        self.send('get_metadata %s' % filename)
        self.status, message = self.read_response_line()
        if self.status == CODE_OK:
            size = int(self.read_line())
            return size

    def get_slice(self, filename, start, length):
        """
        Obtiene un trozo de un archivo en el server.

        El archivo es guardado localmente, en el directorio actual, con el
        mismo nombre que tiene en el server.
        """
        self.send('get_slice %s %d %d' % (filename, start, length))
        self.status, message = self.read_response_line()
        if self.status == CODE_OK:
            output = open(filename, 'wb')
            fragment = self.read_fragment()
            total = 0
            while fragment:
                total += len(fragment)
                output.write(fragment)
                fragment = self.read_fragment()
            output.close()
        else:
            logging.warn("El servidor indico un error al leer de %s." %
                         filename)

    def retrieve(self, filename):
        """
        Obtiene un archivo completo desde el servidor.
        """
        size = self.get_metadata(filename)
        if self.status == CODE_OK:
            assert size >= 0
            self.get_slice(filename, 0, size)
        elif self.status == FILE_NOT_FOUND:
            logging.info("El archivo solicitado no existe.")
        else:
            logging.warn("No se pudo obtener el archivo %s (code=%s)." %
                         (filename, self.status))


def main():
    """
    Interfaz interactiva simple para el cliente: permite elegir un archivo
    y bajarlo.
    """
    DEBUG_LEVELS = {'DEBUG': logging.DEBUG,
                    'INFO': logging.INFO,
                    'WARN': logging.WARNING,
                    'ERROR': logging.ERROR,
                    }

    # Parsear argumentos
    parser = optparse.OptionParser(usage="%prog [options] server")
    parser.add_option("-p", "--port",
                      help=u"Número de puerto TCP donde escuchar",
                      default=DEFAULT_PORT)
    parser.add_option("-v", "--verbose", dest="level", action="store",
                      help=u"Determina cuanta información "
                      u"de depuración a mostrar"
                      " (valores posibles son: ERROR, WARN, INFO, DEBUG)",
                      default="ERROR")
    options, args = parser.parse_args()
    try:
        port = int(options.port)
    except ValueError:
        sys.stderr.write("Numero de puerto invalido: %s\n" %
                         repr(options.port))
        parser.print_help()
        sys.exit(1)

    if len(args) != 1 or options.level not in DEBUG_LEVELS.keys():
        parser.print_help()
        sys.exit(1)

    # Setar verbosidad
    code_level = DEBUG_LEVELS.get(options.level)  # convertir el str en codigo
    logging.getLogger().setLevel(code_level)

    try:
        client = Client(args[0], port)
    except(socket.error, socket.gaierror):
        sys.stderr.write("Error al conectarse\n")
        sys.exit(1)

    print "* Bienvenido al cliente HFTP - " \
          "the Home-made File Transfer Protocol *\n" \
          "* Estan disponibles los siguientes archivos:"

    files = client.file_lookup()

    for filename in files:
        print filename

    if client.status == CODE_OK:
        print "* Indique el nombre del archivo a descargar:"
        client.retrieve(raw_input().strip())

    client.close()


if __name__ == '__main__':
    main()
