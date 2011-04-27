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

class VCard():
  ignore = ["BEGIN", "VERSION", "END", "REV"]
  map_ = {
    "N": "name",
    "FN": "formated",
    "ORG": "organization",
    "NICKNAME": "Nickname",
    "PHOTO": "Photograph",
    "BDAY": "Birthday",
    "ADR": "Delivary Address",
    "LABEL": "Label Address",
    "TEL": "Telephone",
    "EMAIL": "email",
  }
  
  def __add(self, tag, value):
    if tag.upper() in self.ignore:
        return False
    if tag.upper() in self.map_:
      self.values[tag.upper()] = value.strip()
      return True
    elif ";" in tag:
      tag, modifiers = tag.split(";", 1)
      tag = tag.upper().strip()
      if tag not in self.map_:
        return False
      if tag not in self.values:
        self.values[tag] = dict()
      if not isinstance(self.values[tag], dict):
        self.values[tag] = {"default": self.values[tag]}
      self.values[tag][modifiers.upper().strip()] = value.strip()
      return True
    else:
      return False

  def __init__(self, body):
    self.values = {}
    for line in body.splitlines():
      tag, value = line.split(":", 1)
      if not self.__add(tag, value):
        print "ignoring", tag

  def __getattr__(self, name):
    if name in self.values:
      return self.values[name]
    else:
      return object.__getattr__(self, name)
