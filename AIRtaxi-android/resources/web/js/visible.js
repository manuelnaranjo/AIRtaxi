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


function visible_update_state(){
  var state = droid.bluetoothGetScanMode().result;
  droid.log("scan mode " + state);
  if ( state >= 3 ){
    $("#visible_state").text("Discoverable...")
    $("#visible_spin").css("display", "inline-block")
  }
  else{
    $("#visible_state").text("Not Discoverable")
    $("#visible_spin").css("display", "none")
  }
}

function visible_create() {
}
$("#visible").live("pagecreate",visible_create);

function visible_display() {
}
$("#visible").live("pageshow",visible_display);

function visible_exit() {
  droid.log("Exit from visible")
  droid.eventPost("taxi-web", JSON.stringify(
    {
        "method": "exit", 
        "page": "visible"
    })
  )
}

function update_clock(){
  var t = $("#seconds").attr("time");
  $("#seconds").text(t);
  $("#seconds").attr("time", t-1);
  if (t > 1){
    setTimeout("update_clock();", 1000);
  }
}

function visible_taxi_event(data){
  droid.log("Got a TAXI event during visible " + data.name);
  if ( data.name == "visible-ready" ) {
    droid.log("Server is ready to get connection")
  } else if (data.name == "got-connection") {
    $("#visible_log").text("Got connection from " + data.address + " " + data.remotename)
  } else if (data.name == "lost-connection") {
    $("#visible_log").text("Ended connection with " + data.address + " " + data.remotename)
  } else if (data.name == "got-content") {
    droid.log("web got content " + data.file +" " + data.mime);
    var body = data.body;
    var fill = 4 - (body.length % 4);
    if ( fill < 4 ){
      for(i = 0; i < fill ; i++){
        body += "=";
      }
    }
    var content = $.base64.decode(body);
    $("#content_holder").append("<p>Got: " + data.file+"</p>")
    $("#content_holder").append("<pre>"+content+"</pre>")
    return
  }
  else {
    droid.log("Ignoring: "+data.name)
  }

  return
}

function visible_sl4a_event(data){
  droid.log("Got an SL4A event during visible");
  if (data["action"] == "android.bluetooth.adapter.action.SCAN_MODE_CHANGED"){
    return visible_update_state();
  }
  droid.log(JSON.stringify(data));
}

