# encoding: utf-8

# Copyright 2008 Natalia Bidart and Daniel Moisset
# $Id: server_test_lab2.py 441 2011-04-25 01:56:50Z nicolasw $

import sys
sys.path.append('../../Lab1/hftp')

import unittest
import client
import constants
import select
import time
import socket
import os
import os.path

DATADIR = 'testdata'
TIMEOUT = 3 # Una cantidad razonable de tiempo para esperar respuestas


class TestBase(unittest.TestCase):

    # Test environment...
    def setUp(self):
        os.system('rm -rf %s' % DATADIR)
        os.mkdir(DATADIR)
        self.clients = []

    def tearDown(self):
        os.system('rm -rf %s' % DATADIR)
        while self.clients:
            if self.clients[0].connected:
                self.clients[0].close()
            del self.clients[0]
        if hasattr(self, 'output_file'):
            if os.path.exists(self.output_file):
                os.remove(self.output_file)
            del self.output_file

    # Auxiliary functions
    def new_client(self):
        assert not hasattr(self, 'client')
        try:
            c = client.Client()
        except socket.error:
            self.fail("No se pudo establecer conexión al server")
        self.clients.append(c)
        return c

    
class TestHFTPMulti(TestBase):
    
    # Tests
    
    def test_multiple_connect_and_quit(self):
        c1 = self.new_client()
        c2 = self.new_client()
        c1.close()
        self.assertEqual(c1.status, constants.CODE_OK)
        c2.close()
        self.assertEqual(c2.status, constants.CODE_OK)
      
    def test_partial_send_does_not_block(self):
        command1 = 'get_file_listing\r\n'
        half1, half2 = command1[:7], command1[7:]

        open(os.path.join(DATADIR, 'xyz'), 'w').close()

        c1 = self.new_client()
        c2 = self.new_client()

        c1.s.send(half1)
        os.system('sleep 3') # Despaciiiiiiiiiiito
        listing = c2.file_lookup()
        self.assertEqual(c2.status, constants.CODE_OK)

        c1.s.send(half2)
        print 'a'
        code, msg = c1.read_response_line()
        print 'b'
        l1 = c1.read_line()
        l2 = c1.read_line()
        self.assertEqual(code, constants.CODE_OK)
        self.assertEqual(l1, 'xyz')
        self.assertEqual(l2, '')
        
    def test_simultaneous_listings(self):
        command = 'get_file_listing\r\n'
        for i in range(100):
            open(os.path.join(DATADIR, 'xyz%d' % i), 'w').close()

        c1 = self.new_client()
        c2 = self.new_client()

        c1.s.send(command)
        c2.s.send(command)

        code1, msg1 = c1.read_response_line()
        code2, msg2 = c2.read_response_line()
        self.assertEqual(code1, code2)
        self.assertEqual(code1, constants.CODE_OK)

        for i in range(100):
            l1 = c1.read_line()
            l2 = c2.read_line()
            self.assertEqual(l1, l2)
            self.assert_(l1.startswith('xyz'))
        l1 = c1.read_line()
        l2 = c2.read_line()
        self.assertEqual(l1, l2)
        self.assertEqual(l1, '')

    def test_partial_read_does_not_block(self):
        PREFIX = 'xxxxxxxxxxxxxxxxxxxxxxxyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyz'
        command = 'get_file_listing\r\n'
        for i in range(100):
            open(os.path.join(DATADIR, (PREFIX + '%d') % i), 'w').close()

        c1 = self.new_client()
        c2 = self.new_client()

        # Send on c1, read half the answer
        c1.s.send(command)
        code, msg = c1.read_response_line()
        self.assertEqual(code, constants.CODE_OK)
        for i in range(50):
            l1 = c1.read_line()
            self.assert_(l1.startswith(PREFIX))

        # Send on c2, read all the answer
        c2.s.send(command)
        code, msg = c2.read_response_line()
        self.assertEqual(code, constants.CODE_OK)
        for i in range(100):
            l2 = c2.read_line()
            self.assert_(l2.startswith(PREFIX))
        c2.read_line() # Ending empty line

        # Missing half answer on c1
        for i in range(50):
            l1 = c1.read_line()
            self.assert_(l1.startswith(PREFIX))
        c1.read_line() # Ending empty line
       

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHFTPMulti))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())