from test_live import c

def test_teacher_groups_reports():
    assert c.post('/api/v6/auth/register',json={'username':'teacher1','password':'securepass123'}).status_code==200
    assert c.post('/api/v6/auth/register',json={'username':'teacher1','password':'securepass123'}).status_code==409
    assert c.post('/api/v6/auth/login',json={'username':'teacher1','password':'wrong'}).status_code==401
    t=c.post('/api/v6/auth/login',json={'username':'teacher1','password':'securepass123'}).json()['token']
    h={'Authorization':'Bearer '+t}
    assert c.get('/api/v6/groups').status_code==401
    g=c.post('/api/v6/groups',json={'name':'English A1'},headers=h)
    assert g.status_code==200
    gid=g.json()['id']
    assert c.post(f'/api/v6/groups/{gid}/students',json={'name':'Aziza'},headers=h).status_code==200
    assert c.get(f'/api/v6/groups/{gid}/students',headers=h).json()['students'][0]['name']=='Aziza'
    assert c.get('/api/v6/groups',headers=h).json()['groups'][0]['students']==1
    assert c.get('/api/v6/reports',headers=h).status_code==200
    assert c.get('/api/v6/reports.csv',headers=h).status_code==200
    assert c.get('/api/v6/reports.csv').status_code==401

def test_individual():
    x=c.post('/api/v6/individual',json={'lo':2,'hi':3,'n':2})
    assert x.status_code==200
    token=x.json()['token']
    for i in range(2):
        state=c.get('/api/v6/individual/'+token).json()
        assert state['done']==i
        a=c.post('/api/v6/individual/'+token+'/answer',json={'answer':'test'})
        assert a.status_code==200
    state=c.get('/api/v6/individual/'+token).json()
    assert state['finished'] and len(state['review'])==2
    assert c.post('/api/v6/individual/'+token+'/answer',json={'answer':'test'}).status_code==409
