# encoding: utf-8
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from string import *
from constants import *
import os
from os import listdir, stat
from os.path import isfile, exists


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    # FALTA: Inicializar atributos de Connection
    def __init__(self, socket, directory):

        self.sock_client = socket
        self.dir = directory
        """Este atributo nos dice si el socket sigue conectado o no"""
        self.sock_active = True
        self.buffer = ''

    def is_file_in_directory(self, file):
        if file in listdir(self.dir):
            return True
        return False

    def state_line(self, message):
        state = str(message) + ' ' + error_messages[message] + EOL
        self.sock_client.send(state)

    def block_generator(self, filename, npack, package_size):
        for i in range(npack):
            data = filename.read(package_size)
            yield data

    def get_file_listing(self): 
        path = os.path.join('.',self.dir)
        self.state_line(CODE_OK)
        try:
            """Crea una lista de todos los elementos en la carpeta self.dir"""
            enviar = ''
            for x in listdir(path): 
                if isfile(os.path.join(path,x)):
                    enviar += (x + EOL)
            enviar += EOL
            self.sock_client.send(enviar)
        except IOExcep:
            self.sock_client.send("Directory invalid\n")
        return CODE_OK

    """ command = ["get_metadata", "FILE"] """
    def get_metadata(self, command, file):
        try:
            file = os.path.join('.',file)
            if not self.is_file_in_directory(file):
                self.state_line(FILE_NOT_FOUND)
                return FILE_NOT_FOUND
            self.state_line(CODE_OK)
            """Obtiene metadatos del path archive """
            info_archive = stat(file)
            """Obtiene el tamañano de archivo en bytes desde los metadatos"""
            size = info_archive.st_size
            self.sock_client.send(str(size) + ' ' + EOL)
            return CODE_OK
        except IOError:
            self.state_line(FILE_NOT_FOUND)
            return FILE_NOT_FOUND

    """command = ["get_slice", "FILE", "OFFSET", "SIZE"]"""
    def get_slice(self, command):
        archive = os.path.join('.',command[1])
        offset = command[2]
        size = command[3]
        if not self.is_file_in_directory(archive):
            self.state_line(FILE_NOT_FOUND)
            return FILE_NOT_FOUND

        filesize = stat(archive)
        filesize = filesize.st_size
        try:
            offset = int(offset)
            size = int(size)
            if offset > filesize and filesize <= (offset + size):
                self.state_line(BAD_OFFSET)
                return BAD_OFFSET
            self.state_line(CODE_OK)
            archive = open(archive, "r")
            archive.seek(offset)
            cantidad_blokes = size/BUFSIZE
            resto = size % BUFSIZE
            data = self.block_generator(archive, cantidad_blokes,  BUFSIZE)
            for i in range(cantidad_blokes):
                self.sock_client.send(str(BUFSIZE) + " " + data.next() + EOL)
            if resto != 0:
                self.sock_client.send(str(resto) + " " + archive.read(resto) +
                                      EOL)
            self.sock_client.send("0" + " " + EOL)
            archive.close()
            return CODE_OK
        except IOError:
            self.state_line(FILE_NOT_FOUND)
            return FILE_NOT_FOUND
        except ValueError:
            self.state_line(INVALID_ARGUMENTS)
            return INVALID_ARGUMENTS
        except StopIteration:
            print "Error read file"
            return INTERNAL_ERROR

    def quit(self):
        self.state_line(CODE_OK)
        self.sock_client.close()
        self.sock_active = False
        return constants.CODE_OK

    def parser_command(self, request):
        """
        El primer if verifica que el pedido del cliente no tenga
        el \n ya que no deberia. Luego ve que comando
        intrudujo el cliente y llama a la funcion para atederlo.
        """
        if '\n' in request:
            return constants.BAD_E
        command = request.split(" ")
        if command[0] == "get_file_listing":
            if len(command) != 1:
                self.state_line(INVALID_ARGUMENTS)
                return INVALID_ARGUMENTS    
            return self.get_file_listing()

        if command[0] == "get_metadata":
            if len(command) != 2:
                self.state_line(INVALID_ARGUMENTS)
                return INVALID_ARGUMENTS
            return self.get_metadata(command[0], command[1])

        if command[0] == "get_slice":
            if len(command) != 4:
                self.state_line(INVALID_ARGUMENTS)
                return constants.INVALID_ARGUMENTS
            return self.get_slice(command)

        if command[0] == "quit":
            print "quit", len(command)
            if len(command) != 1:
                self.state_line(INVALID_ARGUMENTS)
                return INVALID_ARGUMENTS
            return self.quit()
        else:
            self.state_line(INVALID_COMMAND)
            return INVALID_COMMAND

    def receive(self):
        while EOL not in self.buffer:
            data = self.sock_client.recv(BUFSIZE)
            if not data:
                return data
            self.buffer += data
        request, self.buffer = self.buffer.split(EOL, 1)
        return request

    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.
        """
        """
        El while va tomando los diferentes pedidos del cliente
        y los va procesando, con split(constants.EOL) le saca
        el \n\r al pedido y luego lo pasa a parser_command() para
        que vea que pidio el cliente
        """
        request = ""
        try:
            while self.sock_active:
                request = self.receive()
                print "Request:", request
                if request == "":
                    print "Pedido invalido"
                    self.sock_client.close()
                    self.sock_active = False
                    break
                code_return = self.parser_command(request)
                if fatal_status(code_return):
                    self.sock_client.send("Fatal Error\nFinished connection\n")
                    self.sock_client.close()
                    self.sock_active = False
                    break
        except:
            ("Except handle\n")
