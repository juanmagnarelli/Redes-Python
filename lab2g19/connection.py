# encoding: utf-8
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
import select
from constants import *
from re import match
from os import listdir, stat
from os.path import isfile, join

""" La idea es que en get_slice se vaya leyendo y enviando por partes para dejar ejecurtar
    pedidos a los otros clientes, asi que habia que indicar que se estaba ejecundo y leer
    desde la ultima parte enviada. yo hice una boludez.
"""

class Connection(object):
    """Abstracción de conexión. Maneja colas de entrada y salida de datos.
    """

    def __init__ (self, socket, address, directory):
        """Crea una conexión asociada al descriptor fd"""
        self.sock_client = socket   # socket del cliente
        self.address = address      # dirección del cliente
        self.directory = directory  # directory sobre el que estamos
        self.input = ''             # cola de entrada
        self.output = ''            # cola de salida
        self.generador = None       # comando en ejecucion
        self.fd = None              # Archivo que se esta enviando.
        self.remove = False         # flag para señalar al servidor
                                    # que la conexión terminó

    def handle_output(self):
        # Aquí esta la única llamada a `socket.send` del programa
        # Saca datos de la cola de salida
        # debería ser llamado por AsyncServer cuando `poll` dice que
        # está lista para mandar
        try:
            if self.generador:
                # Comando get_slice o get_file_listing ejecutando
                data = ''
                try:
                    data += self.generador.next()
                except StopIteration: 
                    # Termino la descarga
                    self.generador = None
                finally:
                    self.output += data

            if self.output:
                # Enviar el maximo posible
                print 'Send data to: ', str(self.address)
                send_count = self.sock_client.send(self.output[:BUFSIZE])
                # Eliminar del buff output lo datos ya enviados
                self.output = self.output[send_count:]
            elif EOL in self.input:
                # Ejecutar comandos ya recibidos
                self.handle_input(False)

        except Exception as e:
            print 'Except handle output: ', e

    def handle_input(self, is_recv=True):
        # Aquí esta la única llamada a `socket.recv` del programa
        # Mete datos en la cola de entrada
        # debería ser llamado por AsyncServer cuando `poll` dice que hay
        # datos
        request = ''
        try:
            if is_recv:
                # Hay pedidos para recibir
                print 'Recive data from: ', str(self.address)
                data = self.sock_client.recv(BUFSIZE)
                if not data:
                    # Conexion perdida
                    self.remove = True
                self.input += data

            if EOL in self.input:
                # Extraemos un comando
                request, self.input = self.input.split(EOL, 1)
            else:
                return

            print 'Client: ', str(self.address), '. Execute: ', request
            code_msg = self.execute_command(request)
            if code_msg != CODE_OK: 
                if fatal_status(code_msg):
                    # Eliminar la conexion
                    self.output = ''
                    self.input = ''
                    self.remove = True
                else:
                    # Informar del error producido
                    self.output += '%s %s %s' % (code_msg, 
                                                 error_messages[code_msg],
                                                 EOL)
        except Exception as e:
            print 'Except handle input: ', e

    def events(self):
        # Devuelve los eventos (POLLIN, POLLOUT) que le interesan
        # a la conexión en este momento
        if self.output or self.generador or (EOL in self.input):
            return select.POLLOUT
        else: 
            if self.remove and self.output == '' and self.input == '':
                return select.POLLHUP
            else :
                return select.POLLIN

    def block_generator(self, npack, package_size):
        # Lee partes de archivos para evitar sobrecargar la memoria
        block = ''
        for i in range(npack):
            block =  self.fd.read(package_size)
            yield (str(len(block)) + ' ' + block + EOL)
        self.fd.close()
        self.fd = None
        yield '0 \r\n'

    def list_generator(self, list):
        for file in list:
            if isfile(join(self.directory, file)):
                # Cargamos en data solo los file's del directorio
                yield (file + EOL)
        yield EOL

    def is_valid_file(self, file):
        # Comprueba que el file este formado por caracteres aceptados
        # y si existe en el directorio actual
        if match((r'^[%s]+$' % ''.join(VALID_CHARS)), file):
            return isfile(join(self.directory, file))
        return False

    def execute_command(self, request):
        # Verifica si el pedido de el cliente es un comando aceptado
        # Si lo es, y esta bien formado lo ejecuta
        if '\n' in request:
            return BAD_EOL

        command = request.split(' ')

        if command[0] == 'get_file_listing':
            if len(command) != 1:
                return INVALID_ARGUMENTS
            return self.get_file_listing()
        if command[0] == 'get_metadata':
            if len(command) != 2:
                return INVALID_ARGUMENTS
            return self.get_metadata(command[0], command[1])
        if command[0] == 'get_slice':
            if len(command) != 4:
                return INVALID_ARGUMENTS
            return self.get_slice(command)
        if command[0] == 'quit':
            if len(command) != 1:
                return INVALID_ARGUMENTS
            return self.quit()
        else:
            return INVALID_COMMAND

    def get_file_listing(self):
        try:
            data = '%s %s %s' %(CODE_OK, error_messages[CODE_OK], EOL)
            self.generador = self.list_generator(listdir(self.directory))
            data += self.generador.next()
            self.output += data
            return CODE_OK
        except IOError:
            return INTERNAL_ERROR
        
    def get_metadata(self, command, file):
        try:
            data = '%s %s %s' %(CODE_OK, error_messages[CODE_OK], EOL)
            if not self.is_valid_file(file):
                return FILE_NOT_FOUND
            # Extraemos el tamaño de archivo (st_size) de la estructura stat
            size = stat(join(self.directory, file)).st_size
            data += str(size) + ' ' + EOL
            self.output += data
            return CODE_OK
        except IOError:
            return FILE_NOT_FOUND

    def get_slice(self, command):
        try:
            data = '%s %s %s' % (CODE_OK, error_messages[CODE_OK], EOL)

            file = command[1]
            offset = int(command[2])
            size = int(command[3])

            if not self.is_valid_file(file):
                return FILE_NOT_FOUND

            # Obtenemos la ruta correcta del file
            file = join(self.directory, file)
            file_size = stat(file).st_size

            # Verificamos los limites de tamaño
            if (offset > file_size or file_size < (offset + size) or 
                offset < 0 or size < 0): 
                return BAD_OFFSET

            self.fd = open(file, 'r')
            self.fd.seek(offset)

            # Cantida de bloques mas el resto
            blocks = (size - offset)/BUFSIZE + 1
            # generador sera el objeto generador para leer el file
            self.generador = self.block_generator(blocks,  BUFSIZE)
            return CODE_OK
        except IOError:
            return FILE_NOT_FOUND
        except ValueError:
            return INVALID_ARGUMENTS

    def quit(self):
        self.output += '%s %s %s' % (CODE_OK, error_messages[CODE_OK], EOL)
        self.remove = True
        return CODE_OK
