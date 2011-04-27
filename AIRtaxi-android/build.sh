set -x 
set -e
cd resources
bash compress.sh
cd ..
ant clean
ant debug
adb uninstall net.aircable.airtaxi
#adb shell pm uninstall -k net.aircable.airtaxi
adb install bin/AIRtaxi-debug.apk
