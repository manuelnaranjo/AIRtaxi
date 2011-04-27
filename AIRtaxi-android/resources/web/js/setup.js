//   Copyright 2011 Manuel Francisco Naranjo <manuel at aircable dot net>
// 
//   Licensed under the Apache License, Version 2.0 (the "License");
//   you may not use this file except in compliance with the License.
//   You may obtain a copy of the License at
// 
//       http://www.apache.org/licenses/LICENSE-2.0
// 
//   Unless required by applicable law or agreed to in writing, software
//   distributed under the License is distributed on an "AS IS" BASIS,
//   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//   See the License for the specific language governing permissions and
//   limitations under the License.

function getValue(id){
  var val = $("#"+id).attr("value");

  if  ( val==null || val.length == 0 ) {
    $("#"+id+"_error").addClass("myerror-visible");
    return null
  }
  $("#"+id+"_error").removeClass("myerror-visible");
  return val;
}

function getSetting(key, default_){
  if (droid==null)
    return default_;

  var res = droid.prefGetValue(key, ".taxi.cfg").result;
  if (res != null)
    return res
  return default_
}

function loadSetting(id, default_){
  $("#"+id).attr("value", getSetting(id, default_));
}

function setSetting(key, value){
  if (droid==null)
    return;
  return droid.prefPutValue(key, value, ".taxi.cfg").result;
}

function getLineNumber(){
  if (droid==null)
    return "Can't detect";
  var ret = droid.getLine1Number().result;
  if (ret != null)
    return ret;
  return "Can't detect"
}

function setup_dowork() {
  var name, number, id;
  var remember;
  name = getValue("name");
  number = getValue("number");
  id = getValue("sharedID");

  if (name==null || number==null || id==null){
    return;
  }

  if ($("#remember").attr("checked")){
    droid.log("remember settings")
    setSetting("name", name);
    setSetting("number", number);
    setSetting("sharedID", id);
  }

  if ( droid != null ){
    droid.eventPost("taxi-web", 
    JSON.stringify({
      method: "dowork", 
      name: name, 
      number: number, 
      sharedID: id
    })
  )
  } else {
    console.log("simulating dowork")
  }

  $.mobile.changePage($("#visible"));
}

function setup_cancel() {
  if ( droid == null ){
    console.log("simulating cancel")
    return;
  }

  droid.eventPost("taxi-web", 
    JSON.stringify({
    method: "cancel"
    })
  )
  droid.dismiss();
}

function setup_ready() {
  $("input[type=text]").live("blur", function(event){
    getSetting(this);
  });

  $("#form").submit(function(){
    var fields = $(this).serializeArray();
    jQuery.each(fields, 
      function(i, field){
        if (field.name == "action"){
          if (field.value == "dowork"){
            setup_dowork(fields);
          } else if (field.value == "cancel"){
            setup_cancel();
          }
          return false;
        }
      });
    return false;
  })
  return true;
}
$("#setup").live("pagecreate", setup_ready);

function setup_display(){
  loadSetting("name", "John Doe");
  loadSetting("number", getLineNumber());
  loadSetting("sharedID", "GETMEATAXI!");
}
$("#setup").live("pageshow", setup_display);
