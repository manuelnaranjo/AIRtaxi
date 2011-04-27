#!/usr/bin/env python

"""
server.py - Server classes for handling OBEX requests and sending responses.

Copyright (C) 2007 David Boddie <david@boddie.org.uk>

This file is part of the PyOBEX Python package.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from bluetooth import *
#from bluetooth.btcommon BluetoothError

from common import OBEX_Version
import headers
import requests
import responses


class Server:

    def __init__(self, address = "", log = lambda x : None):
        self.address = address
        self.max_packet_length = 0xffff
        self.obex_version = OBEX_Version()
        self.request_handler = requests.RequestHandler()
        self.methods = {
            requests.Connect: self.connect,
            requests.Disconnect: self.disconnect,
            }
        self.log = log
    
    def start_service(self, port, name, uuid, service_classes, service_profiles,
                      provider, description, protocols):
    
        socket = BluetoothSocket(RFCOMM)
        socket.bind((self.address, port))
        socket.listen(0)

        advertise_service(
            socket, name, uuid, service_classes, service_profiles,
            provider, description, protocols
            )

        print "Starting server for %s on port %i" % socket.getsockname()
        #self.serve(socket)
        return socket

    def stop_service(self, socket):
        stop_advertising(socket)

    def serve_connection(self, socket, connection, address):
        while True:
          try:
            request = self.request_handler.decode(connection)
            self.methods[request.__class__](connection, request)
          except KeyError:
            self.log("method not provided %s" % request.__class__)
            self.log(str(self.methods))
            self.reject(connection)
            return
          except BluetoothError, err:
            self.log("error during decode %s" % err)
            return

    def serve(self, socket):
        self.log("Waiting for connection")
        connection, address = socket.accept()
        self.log("Got connection from %s" % str(address))
        return self.serve_connection(socket, connection, address)

    def _send_headers(self, socket, response, header_list, max_length):
        while header_list:
            if response.add_header(header_list[0], max_length):
                header_list.pop(0)
            else:
                socket.sendall(response.encode())
                response.reset_headers()
        
        # Always send at least one request.
        socket.sendall(response.encode())
    
    def reject(self, socket):
        if hasattr(self, "remote_info"):
            max_length = self.remote_info.max_packet_length
        else:
            max_length = self.max_packet_length
        
        response = responses.BadRequest()
        self._send_headers(socket, response, [], max_length)
    
    def connect(self, socket, request):
    
        if request.obex_version > self.obex_version:
            self._reject(socket)
        
        self.remote_info = request
        max_length = self.remote_info.max_packet_length
        
        flags = 0
        data = (self.obex_version.to_byte(), flags, max_length)
        
        response = responses.ConnectSuccess(data)
        header_list = []
        self._send_headers(socket, response, header_list, max_length)
    
    def disconnect(self, socket, request):
    
        max_length = self.remote_info.max_packet_length
        
        response = responses.Success()
        header_list = []
        self._send_headers(socket, response, header_list, max_length)

class BrowserServer(Server):

    def start_service(self, port = None):
    
        if port is None:
            port = get_available_port(RFCOMM)
        
        name = "OBEX File Transfer"
        uuid = "F9EC7BC4-953C-11d2-984E-525400DC9E09" # "E006" also appears to work
        service_classes = [OBEX_FILETRANS_CLASS]
        service_profiles = [OBEX_FILETRANS_PROFILE]
        provider = ""
        description = "File transfer"
        protocols = [OBEX_UUID]
        
        return Server.start_service(
            self, port, name, uuid, service_classes, service_profiles,
            provider, description, protocols
            )

class PushServer(Server):

    def start_service(self, port):
        name = "OBEX Object Push"
        uuid = PUBLIC_BROWSE_GROUP
        service_classes = [OBEX_OBJPUSH_CLASS]
        service_profiles = [OBEX_OBJPUSH_PROFILE]
        provider = ""
        description = "File transfer"
        protocols = [RFCOMM_UUID, OBEX_UUID]
        
        return Server.start_service(
            self, port, name, uuid, service_classes, service_profiles,
            provider, description, protocols
            )

    def __init__(self, put_listener=None, get_listener=None, *args, **kwargs):
      Server.__init__(self, *args, **kwargs)
      self.methods.update({
        requests.Get: self.get,
        requests.Get_Final: self.get,
        requests.Put: self.put,
        requests.Put_Final: self.put,
      })
      self.get_listener = get_listener
      self.put_listener = put_listener

    def _handle_put(self, sock, *args, **kwargs):
      if callable(self.put_listener):
        self.put_listener(conn=sock, *args, **kwargs)

      response = responses.Success()
      header_list = []
      max_length = self.max_packet_length

      self._send_headers(sock, response, header_list, max_length)

    def put(self, sock, request):
      self.log("got a put request")
      name, length, mime = None, None, None
      body = ""
      
      for header in request.header_data:
        if isinstance(header, headers.Name):
          name = header.decode().replace("\x00","")
          self.log("name: %s" % name)
        elif isinstance(header, headers.Type):
          mime = header.decode().replace("\x00","")
          self.log("mime: %s" % mime)
        elif isinstance(header, headers.Length):
          length = header.decode()
          self.log("len: %s" % length)
        elif isinstance(header, headers.Body) or \
            isinstance(header, headers.End_Of_Body):
          body += header.decode().replace("\x00","")
          self.log("body: %s" % body)
        else:
          self.log("Ignored header: %s" % str(header))
      self._handle_put(sock, name=name, mime=mime, length=length, body=body)

    def _handle_get(self, sock, mime=None, name=None):
      body = None
      response = responses.Not_Found()
      header_list = []

      if callable(self.get_listener):
        body = self.get_listener(mime=mime, name=name, conn=sock)
        print body

      if hasattr(self, "remote_info"):
          max_length = self.remote_info.max_packet_length
      else:
          max_length = self.max_packet_length

      if body:
        response = responses.Success()
        if not name:
          name = "vCard.vcf"
        response.add_header(headers.Name(name), max_length)
        response.add_header(headers.Length(len(body)), max_length)
        response.add_header(headers.End_Of_Body(body), max_length)
        #header_list.append(headers.Length(len(body)))
        #header_list.append(headers.End_Of_Body(body))


      self._send_headers(sock, response, header_list, max_length)

    def get(self, sock, request):
      name, mime = (None, None)
      for header in request.header_data:
        if isinstance(header, headers.Type):
          mime = header.decode()
        elif isinstance(header, headers.Name):
          name=header.decode()
      if not name and not mime:
        return self.reject(sock)
      self._handle_get(sock, mime, name)
