#!/usr/bin/env python
# encoding: utf-8
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import sys
import optparse
import socket
import connection
from constants import *


class Server(object):
    """
    El servidor, que crea y atiende el socket en la dirección y puerto
    especificados donde se reciben nuevas conexiones de clientes.
    """

    def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
                 directory=DEFAULT_DIR):
        print "Serving %s on %s:%s." % (directory, addr, port)
        """
        Creamos socket para enlazarlo a una direccion y a un puerto
        Por donde vamos a "escuchar" las peticiones del cliente
        Definimos el maximo numero de conexiones en la cola
        """
        self.dir = directory
        self.addr = addr
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # socket.setsockopt(level, optname, value)
        self.socket.bind((self.addr, self.port))
        self.socket.listen(MAX_CONNECTION)

    def serve(self):
        """
        Loop principal del servidor. Se acepta una conexión a la vez
        y se espera a que concluya antes de seguir.
        """
        # FALTA: Aceptar una conexión al server, crear una
        # Connection para la conexión y atenderla hasta que termine.
        while True:
            # Aceptamos conexion, abriendo una conexion entre el
            # Cliente y servidor
            try:
                # El metodo accept() nos da una tupla addr_client, la cual es
                # una tupla con IP del cliente, y su port.
                socket_client, addr_client = self.socket.accept()
                print "Connected by: %s" % (addr_client,)
                # creamos una conexion con el socket cliente, este objeto es
                # del archivo connection.py
                conexion = connection.Connection(socket_client, self.dir)
                # llamamos al handle() para que atiende los pedidos del cliente
                conexion.handle()
            except:
                print("Servidor caido")
                return 0


def main():
    """Parsea los argumentos y lanza el server"""

    parser = optparse.OptionParser()
    parser.add_option(
        "-p", "--port",
        help=u"Número de puerto TCP donde escuchar", default=DEFAULT_PORT)
    parser.add_option(
        "-a", "--address",
        help=u"Dirección donde escuchar", default=DEFAULT_ADDR)
    parser.add_option(
        "-d", "--datadir",
        help=u"Directorio compartido", default=DEFAULT_DIR)

    options, args = parser.parse_args()
    if len(args) > 0:
        parser.print_help()
        sys.exit(1)
    try:
        port = int(options.port)
    except ValueError:
        sys.stderr.write(
            "Numero de puerto invalido: %s\n" % repr(options.port))
        parser.print_help()
        sys.exit(1)

    server = Server(options.address, port, options.datadir)
    server.serve()

if __name__ == '__main__':
    main()
