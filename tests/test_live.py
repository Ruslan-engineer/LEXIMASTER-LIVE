import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['LEXIMASTER_DB']=tempfile.mktemp(suffix='.sqlite3')
from fastapi.testclient import TestClient
from server import app
c=TestClient(app)
def test_lifecycle():
 assert c.get('/health').json()['status']=='ok'
 r=c.post('/api/rooms',json={'lo':2,'hi':3,'n':2});assert r.status_code==200
 x=r.json();code=x['code'];host=x['host_token']
 assert c.get('/api/rooms/'+code+'/qr').headers['content-type']=='image/png'
 assert c.post('/api/rooms/'+code+'/start',params={'token':host}).status_code==400
 p=c.post('/api/rooms/'+code+'/join',json={'name':'Aziz'}).json()['token']
 assert c.post('/api/rooms/'+code+'/join',json={'name':'Aziz'}).status_code==409
 assert c.post('/api/rooms/'+code+'/start',params={'token':host}).status_code==200
 assert c.post('/api/rooms/'+code+'/join',json={'name':'Malika'}).status_code==409
 assert c.get('/api/rooms/'+code+'/host',params={'token':'bad'}).status_code==403
 for i in range(2):
  q=c.get('/api/rooms/'+code+'/player',params={'token':p}).json();assert q['question']['idx']==i
  a=c.post('/api/rooms/'+code+'/answer',params={'token':p},json={'answer':'no-way'});assert a.status_code==200
  assert a.json()['idx']==i
 assert c.post('/api/rooms/'+code+'/answer',params={'token':p},json={'answer':'abc'}).status_code==409
 h=c.get('/api/rooms/'+code+'/host',params={'token':host}).json();assert h['players'][0]['total']==2
 assert c.post('/api/rooms/'+code+'/restart',params={'token':host}).status_code==409
 assert c.post('/api/rooms/'+code+'/finish',params={'token':host}).status_code==200
 assert c.post('/api/rooms/'+code+'/restart',params={'token':host}).status_code==200
 assert c.get('/api/rooms/'+code+'/player',params={'token':p}).json()['done']==0

def test_validation():
 assert c.post('/api/rooms',json={'lo':7,'hi':3,'n':10}).status_code==400
 assert c.post('/api/rooms',json={'lo':2,'hi':2,'n':100}).status_code in (200,400)

def test_online_routes():
 from unittest.mock import patch
 r=c.post('/api/rooms',json={'lo':2,'hi':3,'n':1})
 code=r.json()['code']
 assert c.get('/join/'+code).status_code==200
 with patch('server.qrcode.make') as make:
  class Dummy:
   def save(self, f, format): f.write(b'PNG')
  make.return_value=Dummy()
  with patch.dict(os.environ, {'PUBLIC_BASE_URL':'https://leximaster.example'}):
   qr=c.get('/api/rooms/'+code+'/qr')
   assert qr.status_code==200
   assert qr.content==b'PNG'
   assert make.call_args.args[0]=='https://leximaster.example/join/'+code
