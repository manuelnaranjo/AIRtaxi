#!/usr/bin/env python 
# -*- coding: utf-8 -*-

import sys, imp, os
from os import path

try:
  import bluetooth
except:
  bluetooth = None

parent = path.dirname(path.realpath(__file__))
sys.path.pop(0)
sys.path.insert(0, path.join(parent,"python.zip"))

if not bluetooth:
  imp.load_dynamic("_bluetooth", "%s/bluetooth.so" % parent)
  import bluetooth

os.environ["DATA_PATH"]=parent

try:
  from customer import main
  main()
except Exception, err:
  from android import API
  from traceback import format_exc
  API().log(str(err))
  API().log(format_exc())
  import time
  time.sleep(10)
