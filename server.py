"""LEXIMASTER LIVE - LAN-ready multi-device quiz server."""
import io, json, os, random, re, secrets, socket, sqlite3, threading, time
from contextlib import contextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import qrcode

ROOT=Path(__file__).parent
DB=Path(os.getenv('LEXIMASTER_DB',str(ROOT/'leximaster_live.sqlite3')))
DB.parent.mkdir(parents=True, exist_ok=True)
WORDS=json.loads((ROOT/'words.json').read_text(encoding='utf8'))
VALID=[w for w in WORDS if w.get('e') and w.get('u') and not w.get('review')]
LOCK=threading.RLock()
app=FastAPI(title='LEXIMASTER LIVE',version='1.0')
app.mount('/static',StaticFiles(directory=str(ROOT/'static')),name='static')

@contextmanager
def db():
 with LOCK:
  con=sqlite3.connect(DB,timeout=15)
  con.row_factory=sqlite3.Row
  try:
   yield con
   con.commit()
  finally:con.close()

def init_db():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS rooms(code TEXT PRIMARY KEY,host_token TEXT NOT NULL, status TEXT NOT NULL,lo INT NOT NULL,hi INT NOT NULL,n INT NOT NULL,created REAL NOT NULL,questions TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS players(token TEXT PRIMARY KEY,room TEXT NOT NULL,name TEXT NOT NULL,joined REAL NOT NULL,FOREIGN KEY(room) REFERENCES rooms(code));
  CREATE TABLE IF NOT EXISTS answers(room TEXT NOT NULL,player TEXT NOT NULL,idx INT NOT NULL,submitted TEXT NOT NULL,correct INT NOT NULL,answered REAL NOT NULL,PRIMARY KEY(player,idx));''')
init_db()

class Create(BaseModel):
 lo:int=Field(ge=2,le=30);hi:int=Field(ge=2,le=30);n:int=Field(ge=1,le=100)
class Join(BaseModel):
 name:str=Field(min_length=1,max_length=40)
class Answer(BaseModel):
 answer:str=Field(max_length=150)

def getroom(c,code):
 r=c.execute('SELECT * FROM rooms WHERE code=?',(code.upper(),)).fetchone()
 if not r:raise HTTPException(404,'Musobaqa topilmadi')
 return r

def checkhost(r,token):
 if not token or not secrets.compare_digest(r['host_token'],token):raise HTTPException(403,'O‘qituvchi kaliti noto‘g‘ri')

def player(c,code,token):
 p=c.execute('SELECT * FROM players WHERE room=? AND token=?',(code,token)).fetchone()
 if not p:raise HTTPException(403,'Ishtirokchi kaliti noto‘g‘ri')
 return p

def norm(x):
 return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9\s\-\']','',x.lower().replace('’',"'").replace('‘',"'"))).strip()

def accepted(w):
 # Explicit synonyms are separated by semicolons or slash only, not by commas inside phrases.
 return [norm(x) for x in re.split(r'\s*[;/]\s*',w['e']) if norm(x)]

def hoststate(c,r):
 ps=c.execute('SELECT * FROM players WHERE room=? ORDER BY joined',(r['code'],)).fetchall()
 scores=[]
 for p in ps:
  a=c.execute('SELECT COUNT(*) total,COALESCE(SUM(correct),0) good FROM answers WHERE player=?',(p['token'],)).fetchone()
  scores.append(dict(name=p['name'],total=a['total'],correct=a['good'],wrong=a['total']-a['good'],percent=round(a['good']/a['total']*100) if a['total'] else 0,finished=a['total']>=r['n']))
 scores.sort(key=lambda x:(-x['correct'],-x['percent'],-x['total'],x['name'].lower()))
 return dict(code=r['code'],status=r['status'],lo=r['lo'],hi=r['hi'],n=r['n'],players=scores,joined=len(scores),finished=sum(p['finished'] for p in scores))

@app.get('/')
def home():return HTMLResponse((ROOT/'static'/'index.html').read_text(encoding='utf8'))

@app.get('/api/info')
def info():return {'books':sorted({w['b'] for w in VALID}),'words':len(VALID)}

@app.post('/api/rooms')
def create(x:Create):
 if x.lo>x.hi:raise HTTPException(400,'BOOK oralig‘i noto‘g‘ri')
 pool=[w for w in VALID if x.lo<=w['b']<=x.hi]
 if len(pool)<x.n:raise HTTPException(400,f'Bu oraliqda {len(pool)} ta savol mavjud, {x.n} ta emas')
 qs=random.sample(pool,x.n)
 with db() as c:
  for _ in range(20):
   code=''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))
   if not c.execute('SELECT 1 FROM rooms WHERE code=?',(code,)).fetchone():break
  else:raise HTTPException(500,'Kod yaratilmadi')
  token=secrets.token_urlsafe(32)
  c.execute('INSERT INTO rooms VALUES (?,?,?,?,?,?,?,?)',(code,token,'waiting',x.lo,x.hi,x.n,time.time(),json.dumps([w['id'] for w in qs])))
 return {'code':code,'host_token':token}

@app.post('/api/rooms/{code}/join')
def join(code:str,x:Join):
 name=' '.join(x.name.split()).strip()
 if not name:raise HTTPException(400,'Ism kiriting')
 code=code.upper()
 with db() as c:
  r=getroom(c,code)
  if r['status']!='waiting':raise HTTPException(409,'Musobaqa boshlangan yoki yakunlangan')
  if c.execute('SELECT 1 FROM players WHERE room=? AND lower(name)=lower(?)',(code,name)).fetchone():raise HTTPException(409,'Bu ism band, boshqa ism tanlang')
  token=secrets.token_urlsafe(32)
  c.execute('INSERT INTO players VALUES (?,?,?,?)',(token,code,name,time.time()))
 return {'token':token,'name':name,'code':code}

@app.get('/api/rooms/{code}/host')
def host(code:str,token:str):
 with db() as c:
  r=getroom(c,code);checkhost(r,token)
  return hoststate(c,r)

@app.post('/api/rooms/{code}/start')
def start(code:str,token:str):
 with db() as c:
  r=getroom(c,code);checkhost(r,token)
  if r['status']!='waiting':raise HTTPException(409,'Musobaqa allaqachon boshlangan')
  if not c.execute('SELECT 1 FROM players WHERE room=?',(r['code'],)).fetchone():raise HTTPException(400,'Kamida bitta ishtirokchi kerak')
  c.execute('UPDATE rooms SET status=? WHERE code=?',('active',r['code']))
 return {'ok':True}

@app.post('/api/rooms/{code}/finish')
def finish(code:str,token:str):
 with db() as c:
  r=getroom(c,code);checkhost(r,token)
  c.execute('UPDATE rooms SET status=? WHERE code=?',('finished',r['code']))
 return {'ok':True}

@app.post('/api/rooms/{code}/restart')
def restart(code:str,token:str):
 with db() as c:
  r=getroom(c,code);checkhost(r,token)
  if r['status']=='active':raise HTTPException(409,'Avval musobaqani yakunlang')
  c.execute('DELETE FROM answers WHERE room=?',(r['code'],))
  c.execute('UPDATE rooms SET status=? WHERE code=?',('waiting',r['code']))
 return {'ok':True}

@app.get('/api/rooms/{code}/player')
def playerstate(code:str,token:str):
 with db() as c:
  r=getroom(c,code);p=player(c,r['code'],token)
  rows=c.execute('SELECT idx,correct,submitted FROM answers WHERE player=? ORDER BY idx',(p['token'],)).fetchall()
  idx=len(rows)
  result={'code':r['code'],'status':r['status'],'name':p['name'],'n':r['n'],'done':idx,'correct':sum(x['correct'] for x in rows)}
  if r['status']=='active' and idx<r['n']:
   ids=json.loads(r['questions']);w=next(w for w in WORDS if w['id']==ids[idx])
   result['question']={'idx':idx,'uz':w['u'],'book':w['b']}
  return result

@app.post('/api/rooms/{code}/answer')
def answer(code:str,token:str,x:Answer):
 with db() as c:
  r=getroom(c,code);p=player(c,r['code'],token)
  if r['status']!='active':raise HTTPException(409,'Musobaqa faol emas')
  idx=c.execute('SELECT COUNT(*) FROM answers WHERE player=?',(p['token'],)).fetchone()[0]
  if idx>=r['n']:raise HTTPException(409,'Savollar tugagan')
  ids=json.loads(r['questions']);w=next(w for w in WORDS if w['id']==ids[idx])
  good=int(norm(x.answer) in accepted(w) and bool(norm(x.answer)))
  c.execute('INSERT INTO answers VALUES (?,?,?,?,?,?)',(r['code'],p['token'],idx,x.answer,good,time.time()))
  return {'correct':bool(good),'expected':w['e'],'idx':idx,'done':idx+1,'finished':idx+1==r['n']}

@app.get('/api/rooms/{code}/qr')
def qr(code:str,request:Request):
 with db() as c:getroom(c,code)
 # Host header gives the LAN address that the teacher used to open the website.
 # Prefer the explicitly configured public HTTPS origin; otherwise use the browser-facing request origin.
 public=os.getenv('PUBLIC_BASE_URL','').strip().rstrip('/')
 if not public:
  proto=request.headers.get('x-forwarded-proto',request.url.scheme).split(',')[0].strip()
  host=request.headers.get('host','').strip()
  public=f'{proto}://{host}'
 url=public+'/join/'+code.upper()
 pic=qrcode.make(url)
 b=io.BytesIO();pic.save(b,format='PNG')
 return Response(b.getvalue(),media_type='image/png',headers={'Cache-Control':'no-store'})

@app.get('/join/{code}')
def join_page(code:str):return home()

@app.get('/health')
def health():return {'status':'ok'}

if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host='0.0.0.0',port=int(os.getenv('PORT','8000')))
