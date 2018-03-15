#!/usr/bin/env python
# encoding: utf-8
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import sys
import optparse
import socket
import select
import os
from connection import Connection
from constants import DEFAULT_ADDR, DEFAULT_PORT, DEFAULT_DIR, MAX_CONNECTION
import os.path

class AsyncServer(object):
  """
  El servidor, que crea y atiende el socket en la dirección y puerto
  especificados donde se reciben nuevas conexiones de clientes.
  """

  def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
               directory=DEFAULT_DIR):
    """
    Creamos socket para enlazarlo a una direccion y a un puerto
    Por donde vamos a "escuchar" las peticiones del cliente
    Definimos el maximo numero de conexiones en la cola
    """
    self.directory = os.path.join('.', directory)
    if not os.path.exists(self.directory) or os.path.isfile(self.directory):
      print 'You must create one directory, because no exist'
      sys.exit(0)
    self.addr = addr
    self.port = port
    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server.setblocking(0)
    self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.server.bind((self.addr, self.port))
    self.server.listen(MAX_CONNECTION)
    self.clients = {}
    self.poll = select.poll()
    

  def serve(self):
    print "Serving %s on %s:%s." % (self.directory, self.addr, self.port)
    # Registramos el servidor en el poll
    self.poll.register(self.server.fileno(), select.POLLIN)

    try:
      while True:
        # Poll contiene (fd, evento) el cual a cada fd le corresponde un 
        # evento(mascara de bits) o un error a informar
        events_list = self.poll.poll()

        for fileno, event in events_list:
          if fileno == self.server.fileno():
            sock_client, address = self.server.accept()
            print "Connected by: " + str(address)
            sock_client.setblocking(0)
            # Registramos el cliente en el poll agregando el fd del socket
            # cliente y el evento que no intereza
            self.poll.register(sock_client.fileno(), select.POLLIN)
            self.clients[sock_client.fileno()] = Connection(sock_client,
                                                            address,
                                                            self.directory)
            print "Connected clients: ", str(len(self.clients))

          elif event & select.POLLIN:
            client = self.clients[fileno]
            client.handle_input()

          elif event & select.POLLOUT:
            client = self.clients[fileno]
            client.handle_output()


        for fileno, client in self.clients.items():
          # Actualizamos los eventos que interezan
          event_client = client.events()
          if not(select.POLLHUP & event_client):
            self.poll.modify(fileno, event_client)
          else:
            print "Remove client: ", str(client.address)
            self.poll.unregister(fileno)
            self.clients[fileno].sock_client.close()
            del self.clients[fileno]

    except Exception as a:
      print "Server off.\n"

    finally:
      # eliminar y cerrar el sock server
      self.poll.unregister(self.server.fileno())
      self.server.close()

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
    help=u"Directorio compartido en sub-niveles", default=DEFAULT_DIR)

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

  if '..' in options.datadir:
    sys.stderr.write(
      "Directory invalid: %s\n" % repr(options.datadir))
    parser.print_help()
    sys.exit(1)

  server = AsyncServer(options.address, port, options.datadir)
  server.serve()

if __name__ == '__main__':
  main()
