# -*- coding: utf-8 -*-
#
#  Copyright 2011 Manuel Francisco Naranjo <manuel at aircable dot net>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#


import string, cgi, time, os, mimetypes
from zipfile import ZipFile
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class MyHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    if not getattr(self, "provider", None):
      self.provider = ZipFile( os.path.join( os.environ["DATA_PATH"], "python.zip" ) )
    fname = "web" + self.path
    if not self.provider.NameToInfo.get(fname):
      self.send_response(404, 'File Not Found: %s' % self.path)
    self.send_response(200)
    mime = mimetypes.guess_type( self.path )[0]
    if mime:
      self.send_header("Content-type", mime)
    self.end_headers()
    self.wfile.write(self.provider.read(fname))

def register_server(port=0):
  try:
    server = HTTPServer( ('', 0), MyHandler)
    return server
  except Exception, err:
    print err
    return None

if __name__ == '__main__':
  os.environ["DATA_PATH"] = "/data/data/net.aircable.airtaxi/files"
  p = register_server()
  print "listening on port", p.socket.getsockname()
  if p:
    p.serve_forever()
