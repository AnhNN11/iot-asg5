"""Run against the real Android app and official local Firebase RTDB emulator.
Never writes to the cloud project. Requires debug APK installed and emulator on :9000.
"""
import json, pathlib, re, subprocess, time, urllib.request, xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'evidence'
ADB = pathlib.Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
PACKAGE = 'com.example.lab2_firebase_connectedmonitoringapp'
BASE = 'http://127.0.0.1:9000'
NS = 'demo-exercise3-default-rtdb'
results = []

def adb(*args):
    return subprocess.check_output([str(ADB), *args], timeout=60)

def request(path, value=None, method='GET', owner=False):
    headers = {'Content-Type': 'application/json'}
    if owner: headers['Authorization'] = 'Bearer owner'
    data = None if value is None else json.dumps(value).encode()
    req = urllib.request.Request(f'{BASE}/{path}.json?ns={NS}', data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)

def screenshot(name):
    (OUT / f'{name}.png').write_bytes(adb('exec-out', 'screencap', '-p'))

def tree():
    adb('shell', 'uiautomator', 'dump', '--compressed', '/sdcard/window.xml')
    return ET.fromstring(adb('shell', 'cat', '/sdcard/window.xml').decode())

def wait_text(text, timeout=90):
    end = time.monotonic()+timeout
    while time.monotonic()<end:
        root=tree()
        if any(text in n.attrib.get('text','') for n in root.iter('node')): return root
        time.sleep(.4)
    screenshot('failure')
    raise AssertionError('Text not visible: '+text)

def click_id(name):
    root=tree()
    node=next(n for n in root.iter('node') if n.attrib.get('resource-id')==PACKAGE+':id/'+name)
    assert node.attrib.get('enabled')=='true', name+' disabled'
    x1,y1,x2,y2=map(int,re.findall(r'\d+',node.attrib['bounds']))
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))

def passed(name, evidence):
    results.append({'test':name,'result':'PASS','evidence':evidence})
    print('PASS:', name, flush=True)

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    request('.settings/rules',json.loads((ROOT/'tools/emulator.rules.json').read_text()),'PUT',True)
    sample={'Temperature':27.5,'Humidity':65.0,'Mode':True,'Threshold':30,'Timestamp':int(time.time()*1000)}
    request('Config/Latest',sample,'PUT',True)
    adb('reverse','tcp:9000','tcp:9000')
    adb('logcat','-b','main','-c')
    adb('shell','am','force-stop',PACKAGE)
    adb('shell','am','start','-n',PACKAGE+'/.MainActivity','--ez','localEmulator','true')
    wait_text('27.5 °C'); wait_text('65.0 %'); wait_text('Live • LOCAL')
    screenshot('01-normal')
    passed('Realtime temperature and humidity', '01-normal.png')
    click_id('increase'); wait_text('31.0 °C')
    assert request('Config/Latest/Threshold')==31
    screenshot('02-threshold-increased')
    passed('Increase threshold writes to Firebase', '02-threshold-increased.png')
    click_id('decrease'); wait_text('30.0 °C')
    assert request('Config/Latest/Threshold')==30
    passed('Decrease threshold writes to Firebase', 'logcat.txt')
    request('Config/Latest',{'Temperature':36.5,'Humidity':72.0,'Timestamp':int(time.time()*1000)},'PATCH')
    time.sleep(.7); screenshot('03-high-toast')
    wait_text('HIGH TEMPERATURE'); wait_text('72.0 %')
    screenshot('04-high-temperature')
    log=adb('logcat','-b','main','-d','-s','FirebaseMonitor:D','*:S').decode(errors='replace')
    assert 'ALERT: Warning: Temperature exceeds threshold!' in log
    assert 'Notification sound started' in log
    passed('Threshold exceeded: Toast and MediaPlayer started','03-high-toast.png; logcat.txt')
    alert_count=log.count('ALERT: Warning:')
    request('Config/Latest/Humidity',73,'PUT'); wait_text('73.0 %')
    log=adb('logcat','-b','main','-d','-s','FirebaseMonitor:D','*:S').decode(errors='replace')
    assert log.count('ALERT: Warning:')==alert_count
    passed('Repeated high snapshot does not repeat alert','logcat.txt')
    click_id('mode'); wait_text('Alerts paused')
    assert request('Config/Latest/Mode') is False
    screenshot('05-mode-off')
    passed('Mode OFF persisted and pauses alerts','05-mode-off.png')
    click_id('mode'); wait_text('HIGH TEMPERATURE')
    log=adb('logcat','-b','main','-d','-s','FirebaseMonitor:D','*:S').decode(errors='replace')
    assert log.count('ALERT: Warning:')==alert_count+1
    passed('Mode ON rearms warning while high','logcat.txt')
    request('Config/Latest/Temperature',30,'PUT'); wait_text('Normal • temperature within threshold')
    screenshot('06-equal-threshold')
    passed('Equality does not trigger warning','06-equal-threshold.png')
    request('Config/Latest/Humidity','invalid','PUT',True); wait_text('Connected • missing or invalid data')
    screenshot('07-invalid-humidity')
    root=tree()
    assert all(n.attrib.get('enabled')=='false' for n in root.iter('node') if n.attrib.get('resource-id') in [PACKAGE+':id/increase',PACKAGE+':id/decrease',PACKAGE+':id/mode'])
    passed('Invalid humidity disables controls without crashing','07-invalid-humidity.png')
    request('Config/Latest',{'Humidity':65,'Threshold':100},'PATCH',True); wait_text('100.0 °C')
    root=tree(); node=next(n for n in root.iter('node') if n.attrib.get('resource-id')==PACKAGE+':id/increase')
    assert node.attrib['enabled']=='false'
    passed('Upper threshold bound disables increase','UI hierarchy assertion')
    request('Config/Latest/Threshold',-50,'PUT',True); wait_text('-50.0 °C')
    root=tree(); node=next(n for n in root.iter('node') if n.attrib.get('resource-id')==PACKAGE+':id/decrease')
    assert node.attrib['enabled']=='false'
    passed('Lower threshold bound disables decrease','UI hierarchy assertion')
    request('Config/Latest',sample,'PUT',True); wait_text('27.5 °C')
    request('.settings/rules',{'rules':{'.read':False,'.write':False}},'PUT',True)
    wait_text('Database error: This client does not have permission')
    screenshot('08-permission-denied')
    passed('Locked database reports Permission denied','08-permission-denied.png')
    request('.settings/rules',json.loads((ROOT/'tools/emulator.rules.json').read_text()),'PUT',True)
    adb('shell','am','force-stop',PACKAGE)
    adb('shell','am','start','-n',PACKAGE+'/.MainActivity','--ez','localEmulator','true')
    wait_text('27.5 °C'); wait_text('Live • LOCAL')
    screenshot('09-final-normal')
    passed('Activity restart restores data and listeners','09-final-normal.png')
    (OUT/'logcat.txt').write_bytes(adb('logcat','-b','main','-d','-s','FirebaseMonitor:D','*:S'))
    (OUT/'local-final-data.json').write_text(json.dumps(request('Config/Latest'),indent=2))

try:
    run()
finally:
    (OUT/'test-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


