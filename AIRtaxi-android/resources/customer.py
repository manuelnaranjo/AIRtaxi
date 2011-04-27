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

import bluetooth, os, sys, select, socket, json
from webserver import register_server
from base64 import b64encode as b64e
from PyOBEX import responses, headers
from PyOBEX import server as obex_server
from functools import partial
from time import time, sleep
from android import API
import mimetypes
droid = API(debug=True)

ENTRY   = 10
ARGS    = 20
RESULT  = 30

class report:
  """
  Decorator that prints information about function calls.
  Based on: http://paulbutler.org/archives/python-debugging-with-decorators/
  """

  def __init__(self, level=ENTRY):
    self.level=level

  def __call__(self, fn):
    def wrap(*args, **kwargs):
      if self.level >= ARGS:
        fc="call to %s.%s (%s,%s)" % (
          fn.__module__, fn.__name__,
          ', '.join( [ repr(a) for a in args ] ),
          ', '.join( ["%s = %s" % (a, repr(b)) for a,b in kwargs.items()] )
        )
        droid.log(fc)
      elif self.level >= ENTRY:
        droid.log("call to %s.%s" % (fn.__module__, fn.__name__))

      ret = fn(*args, **kwargs)
      if self.level >= RESULT:
        droid.log("%s returned %s" % (fc, ret))
      return ret
    if self.level > 0:
      return wrap
    return fn


VCARD='''BEGIN: VCARD
VERSION: 2.1
FN: %s
TEL: %s
END: VCARD'''

CFG=".aircable-taxi.cfg"

@report()
def UUID(val):
  val = "%08X" % val
  return "%s-0000-1000-8000-00805F9B34FB" % (val)

@report()
def getSetting(key, default=None):
  res = droid.prefGetValue(key, CFG)
  if not res:
    return default
  return res

@report()
def setSetting(key, value):
  return droid.prefPutValue(key, value, CFG)

@report()
def make_bizcard(name, tel):
  out = VCARD % (name, tel)
  return "\r\n".join(out.splitlines())

@report()
def show_input(title, message, default=None):
  reply = droid.dialogGetInput(title, message, default)
  return reply

@report()
def show_chooser(options, title=None):
  droid.dialogCreateAlert(title)
  droid.dialogSetPositiveButtonText("Continue")
  droid.dialogSetNegativeButtonText("Cancel")
  droid.dialogSetSingleChoiceItems( options )
  droid.dialogShow()
  response = droid.dialogGetResponse()["which"]
  if response != u"positive":
    return None

  sel = droid.dialogGetSelectedItems()
  droid.dialogDismiss()

  if len(sel) == 0:
    return None
  return sel[0]
  
@report()
def show_yesno(title, message):
  droid.dialogCreateAlert(title, message)
  droid.dialogSetPositiveButtonText("Yes")
  droid.dialogSetNegativeButtonText("No")
  droid.dialogShow()
  response = droid.dialogGetResponse()["which"]
  return response == "positive"

@report()
def place_call(number):
  droid.phoneCallNumber(number)

@report()
def resolve_name(address):
  sock = bluetooth.bluez._gethcisock()
  try:
    name = bluetooth.bluez._bt.hci_read_remote_name(sock, address, 1000)
  except:
    name = None
  sock.close()
  return name

class Server:
  @report()
  def __init__(self, name, number, sharedID, timeout=300):
    self.name = name
    self.number = number
    self.sharedID = sharedID
    self.timeout = timeout
    
  def prepareSocket(self):
    if "com.android.bluetooth" in droid.getRunningPackages():
      droid.forceStopPackage("com.android.bluetooth")

    self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    self.sock.bind(("", 12))
    self.sock.listen(0)

  @report()
  def handle_connection(self, sock, loop):
    conn, address = sock.accept()
    remote_name = resolve_name(address[0])
    droid.eventPost("taxi-server", json.dumps( {
      "name": "got-connection",
      "address": address[0],
      "port": address[1],
      "remotename": remote_name
      })
    )
    self.server.serve_connection(self.sock, conn, address)
    droid.eventPost("taxi-server", json.dumps({
      "name": "lost-connection",
      "address": address[0],
      "port": address[1],
      "remotename": remote_name
      })
    )

  @report()
  def initialSetup(self):
    droid.bluetoothMakeDiscoverable(300)
    self.oldName = droid.bluetoothGetLocalName()
    self.newName = "%s %s" % (self.oldName, self.sharedID)
    droid.bluetoothSetLocalName(self.newName)
    self.server = obex_server.PushServer(get_listener=self.handle_get, 
      put_listener = self.handle_put,
      log=droid.log)
    self.prepareSocket()
    return True

  @report()
  def postSetup(self):
    droid.bluetoothSetLocalName(self.oldName)
    if "com.android.bluetooth" in droid.getRunningPackages():
      droid.forceStopPackage("com.android.bluetooth")

  @report()
  def handle_get(self, mime=None, name=None, conn=None):
    if not mime or mime.replace("\x00","") != "text/x-vcard":
      droid.log("mime is not set or wrong %s" % mime)
      return None
    reply = show_yesno("Allow access", 
      "Do you want to share your phone number with %s" % 
        resolve_name(conn.getpeername()[0]))
    if not reply:
      return None
    return make_bizcard(self.name, self.number)

  @report()
  def handle_put(self, conn, body=None, length=None, mime=None, name=None):
    droid.log("Got %s" % name)
    droid.eventPost("taxi-server", json.dumps({
        "name": "got-content",
        "body": b64e(body),
        "length": length,
        "mime": mime or mimetypes.guess_type(name)[0],
        "file": name
    }))

class Loop:
  def __init__(self):
    self.running = False
    self.listeners = {}

  def addListener(self, sock, listener=None):
    self.listeners[sock] = listener

  def run(self):
    self.running = True
    while self.running:
      inpr = select.select(self.listeners.keys(), [], [])[0]
      for s in inpr:
        if callable(self.listeners[s]):
          self.listeners[s](sock=s, loop=self)

  def stop(self):
    self.running = False

WELCOME=0
VISIBLE=1
TRANSFER=2
class FiniteStateMachine():
  state = 0
  name = None
  number = None
  sharedID = None
  exit = False

  def __parseEvent(self):
    b = self.socketf.readline()
    droid.log("__parseEvent %s %s" % ( type(b), b ))
    try:
      event = json.loads(b)
      event["data"] = json.loads(event["data"])
      return event
    except Exception, err:
      droid.log(str(err))
      while True:
        r = self.socket.recv(4096)
        droid.log(str(r))
        if not r or len(r) < 4096:
          break
      return None

  def handle_taxi_web(self, event, loop):
    if self.state == WELCOME:
      self.handle_WELCOME(event)
      loop.stop()
      return
    elif self.state == VISIBLE:
      if self.handle_VISIBLE(event):
        loop.stop()
      return
    elif self.state == TRANSFER:
      return self.handle_TRANSFER(event)
    droid.log("Broken state %s" % self.state)
    loop.stop()
    

  def handle_sl4a(self, event, loop):
    droid.log("sl4a event")
    droid.log(str(event))

  def handle_ignore(self, event, loop):
    droid.log("ignoring event")
    return
  
  HANDLERS = {
    "taxi-web": handle_taxi_web,
    "sl4a": handle_sl4a,
    "taxi-server": handle_ignore
  }

  def handle(self, sock, loop):
    event = self.__parseEvent()
    if not event:
      droid.log("got empty event!")
      return

    droid.log("got event type: %s" % event["name"])
    handler = self.HANDLERS.get(event["name"], None)
    if not handler:
      droid.log("bad event")
      loop.stop()
    return handler(self, event["data"], loop)

  def handle_WELCOME(self, event):
    if event["method"] != "dowork":
      droid.makeToast("See you again soon")
      sleep(3)
      self.exit = True
      return
    for i in ["name", "number", "sharedID"]:
      setattr(self, i, event[i])

  def handle_VISIBLE(self, event):
    if event["method"] == "exit":
      droid.makeToast("See you again soon")
      sleep(3)
      self.exit = True
      return True
    droid.log("Ignoring during visibile %s" % str(event))

  def handle_TRANSFER(self, event):
    droid.log(str(event))

def main():
    if not droid.checkBluetoothState():
      if not droid.toggleBluetoothState(True):
        droid.makeToast("Can't go on without enabling Bluetooth, sorry")
        sleep(3)
        return
    events = socket.socket()
    p = droid.startEventDispatcher()
    droid.log("%s %s" % (p, type(p)))
    events.connect(("localhost", p))

    loop = Loop()
    fsm = FiniteStateMachine()
    fsm.socket = events
    fsm.socketf = events.makefile()
    loop.addListener(events, fsm.handle)

    webserver = register_server()
    loop.addListener(webserver.socket, lambda sock, loop: webserver._handle_request_noblock() )

    droid.webViewShow("http://localhost:%s/main.html" % webserver.server_port)
    loop.run()

    if fsm.exit:
      return

    server = Server(fsm.name, fsm.number, fsm.sharedID)
    droid.eventRegisterForBroadcast("android.bluetooth.adapter.action.SCAN_MODE_CHANGED", False)
    ready = server.initialSetup()
    if not ready:
      droid.makeToast("Bye, can't do my job")
      sleep(3)
      return
    fsm.state = VISIBLE
    loop.addListener(server.sock, server.handle_connection)
    droid.eventPost("taxi-server", json.dumps({"name": "visible-ready"}))
    loop.run()
    server.postSetup()

if __name__ == "__main__":
  main()
