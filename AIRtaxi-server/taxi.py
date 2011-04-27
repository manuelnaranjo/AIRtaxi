#!/usr/bin/env python
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



import bluetooth, os, sys
from PyOBEX import client, responses, headers
from functools import partial
from vcard import VCard

VCARD = '''BEGIN: VCARD
VERSION: 2.1
FN: Taxi %s
TEL: %s
GEO: %s
NOTE: %s
END: VCARD
'''

global name, tel

def show_chooser(options, title=None):
  opts = [ (i, options[i]) for i in range(len(options)) ]
  def internal_work():
    if title:
      print title
    print "Options:"
    for i in opts:
      print "\t* %2i - %s" % i
    return raw_input("Choose Option: ")
  opt = None
  try:
    opt = internal_work()
    return int(opt)
  except ValueError, IndexError:
    return None

def show_yesno(title, message):
  print title
  print message
  opt = raw_input("[Yes]/No? ")
  return opt.lower() in ["yes", "y"]
  
def doput(conn):
  global name, tel
  try:
    geo = raw_input("What's the taxi position: ")
    note = raw_input("Any notes for the customer: ")
  except:
    return
  vcard = VCARD % (name, tel, geo, note)
  conn.put("taxi.vcf", vcard)

def dowork(device_address):
    services = bluetooth.find_service(address=device_address, uuid="1105",)
    port = None

    if services:
        port = services[0]["port"]

    if not port:
      print "Service not provided"
      return

    print "Connecting to", device_address, port
    c = client.Client(device_address, port)

    response = c.connect()
    if not isinstance(response, responses.ConnectSuccess):
        print "Failed to connect"
        return

    reply = c.get(header_list=[headers.Type("text/x-vcard"),])[1]
    if reply and type(reply)==str:
      result = VCard(reply)
      print result.values
      doput(c)

    c.disconnect()


def main():
    device_address = None

    print "discovering devices..."
    devices = bluetooth.discover_devices(lookup_names=True)
    res = show_chooser([b[1] for b in devices], title="Select Target Device")
    if res == None:
      return
    dowork(devices[res][0])


if __name__ == "__main__":
  try:
    name = raw_input("What's the taxi number: ")
    tel = raw_input("What's the agency phone number: ")
  except:
    sys.exit()

  if len(sys.argv) > 1:
    for addr in sys.argv[1:]:
      dowork(addr)
    sys.exit(0)
  try:
    while True:
      main()
  except KeyboardInterrupt, err:
    print "Bye"
