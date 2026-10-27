#!/usr/bin/env python3
"""Exercise templates against an isolated local server binary with disposable data."""
import argparse
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]

class Client:
    def __init__(self, port):
        self.port=port;self.origin=f'http://127.0.0.1:{port}';self.cookie='';self.csrf='';self.key='';self.checks=[]
    def request(self, method, path, body=None, expected=200, etag=None, raw=False):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=15)
        headers={'Origin':self.origin,'Content-Type':'application/json'}
        if self.key:headers['Authorization']='Bearer '+self.key
        else:headers.update(Cookie=self.cookie,**{'X-CSRF-Token':self.csrf})
        if etag:headers['If-Match']=etag
        try:
            conn.request(method,path,None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers)
            response=conn.getresponse();data=response.read(8*1024*1024+1)
            if response.status != expected:raise RuntimeError(f'{method} {path} returned HTTP {response.status}: '+data.decode(errors='replace')[:500])
            assert len(data)<=8*1024*1024
            if response.getheader('Set-Cookie'):self.cookie=response.getheader('Set-Cookie').split(';',1)[0]
            result=data if raw else json.loads(data)
            if isinstance(result,dict) and 'csrf_token' in result:self.csrf=result['csrf_token']
            self.checks.append({'method':method,'path':path,'status':response.status})
            return (result,dict(response.getheaders())) if raw else result
        finally:conn.close()

def example(name):return json.loads((ROOT/'examples'/name).read_text())
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--server-binary',type=Path,required=True);args=parser.parse_args()
    binary=args.server_binary.resolve();assert binary.is_file()
    output=ROOT/'outputs';output.mkdir(exist_ok=True)
    fixture=Path(tempfile.mkdtemp(prefix='http-examples-',dir=output));process=None;result={'status':'failed','checks':[]}
    try:
        with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
        client=Client(port);result["checks"]=client.checks
        environment={k:v for k,v in os.environ.items() if not k.startswith('MLBOARD_')}
        environment['TMPDIR']=str(fixture)
        with (fixture/'server.log').open('w') as log:
            process=subprocess.Popen([str(binary),'-listen',f'127.0.0.1:{port}','-public-url',client.origin,
                                      '-database','sqlite','-dsn',str(fixture/'data.sqlite'),'-data-dir',str(fixture/'files')],
                                     cwd=fixture,env=environment,stdout=log,stderr=subprocess.STDOUT)
            for _ in range(100):
                if process.poll() is not None:raise RuntimeError('Isolated server exited during startup')
                try:
                    client.request('GET','/readyz',raw=True)
                    if process.poll() is not None:raise RuntimeError('Isolated server exited during startup')
                    break
                except (OSError,http.client.HTTPException):time.sleep(.1)
            else:raise RuntimeError('Isolated server readiness timeout')
            assert client.request('GET','/api/v1/auth/status')['setup_required'] is True
            client.request('POST','/api/v1/auth/setup',{'username':'docs_fixture','password':secrets.token_urlsafe(32)},201)
            caps=client.request('GET','/api/v1/capabilities')
            assert caps['limits']['query_runs']==1000 and caps['limits']['query_series']==2000 and caps['limits']['query_scanned_points']==10000000
            registry=client.request('GET','/api/v1/registry');assert 'html' in [p['type'] for p in registry['panels']]
            schemas=client.request('GET','/api/v1/schemas')['schemas']
            expected_schemas={p.name:json.loads(p.read_text()) for p in (ROOT/'schemas').glob('*.json')}
            assert schemas==expected_schemas
            project=client.request('POST','/api/v1/projects',{'name':'Documentation fixture'},201);pid=project['id']
            key=client.request('POST','/api/v1/keys',{'name':'Temporary documentation test','kind':'project','project_id':pid,
                               'scopes':['runs:read','runs:write','data:read','data:write','dashboards:read','dashboards:write','html:publish','html:bind_data']},201)
            client.key=key['secret']
            rid='run_docs_fixture'
            client.request('POST',f'/api/v1/projects/{pid}/runs',{'run_id':rid,'run_path':'docs/synthetic','config':{'synthetic':True},'tags':['docs-fixture']},201)
            client.request('POST',f'/api/v1/runs/{rid}/sessions',{'session_id':'session_docs','ordinal':'0','primary_producer':'trainer'},201)
            client.request('POST',f'/api/v1/runs/{rid}/sessions/session_docs/producers',{'producer_id':'trainer','role':'primary'},201)
            events=[{'schema_version':'mlboard.event/v1','run_id':rid,'session_id':'session_docs','producer_id':'trainer','seq':str(i+1),'step':str(i),
                     'event_time':'2026-10-27T00:00:00Z','elapsed_seconds':i/10,'fields':[{'name':'train/loss','kind':'scalar','value':1/(i+1)}]} for i in range(10)]
            client.request('POST',f'/api/v1/runs/{rid}/events',{'schema_version':'mlboard.batch/v1','events':events})
            run=client.request('GET',f'/api/v1/runs/{rid}?include_summary=false')
            def replace(template):
                return json.loads(json.dumps(template).replace('run_REPLACE',rid).replace('inc_REPLACE',run['run_incarnation']).replace('prj_REPLACE',pid))
            query=replace(example('query.json'))
            queried=client.request('POST',f'/api/v1/projects/{pid}/query',query)
            assert queried['complete'] and sum(f['row_count'] for f in queried['frames'])==10
            assert queried['frames'][0]['columns']['x'][0]=='0', repr(queried['frames'][0]['columns']['x'][:2])
            known_limitations=[]
            if queried['frames'][0]['columns']['elapsed_seconds'][-1] != .9:
                raw_query=copy.deepcopy(query);raw_query['transform']={'kind':'raw'}
                raw_result=client.request('POST',f'/api/v1/projects/{pid}/query',raw_query)
                assert raw_result['frames'][0]['columns']['elapsed_seconds'][-1]==.9
                known_limitations.append('step_downsample_elapsed_seconds_missing; raw query preserves recorded elapsed time')
            dashboard=client.request('POST',f'/api/v1/projects/{pid}/dashboards',{'title':'Documentation example','visibility':'personal','spec':replace(example('dashboard.json'))},201)
            did=dashboard['id'];base=f'/api/v1/dashboards/{did}'
            client.request('POST',base+'/validate',{'spec':dashboard['spec']})
            change=example('change.json');change['base_revision']=dashboard['revision'];change['client_request_id']=uuid.uuid4().hex
            preview=client.request('POST',base+'/preview',change)
            client.request('POST',base+'/apply',{'preview_id':preview['preview_id'],'client_request_id':change['client_request_id']},etag=dashboard['etag'])
            dashboard=client.request('GET',base);assert dashboard['spec']['layout']['items'][0]['h']==16
            panel=example('html-panel.json');panel['options']['html']=(ROOT/'examples/html-panel.html').read_text()
            html_change={'schema_version':'mlboard.dashboard-change/v1','base_revision':dashboard['revision'],'client_request_id':uuid.uuid4().hex,'reason':'Documentation HTML fixture',
                         'operations':[{'op':'add_panel','panel':panel,'position':{'panel_id':panel['panel_id'],'x':0,'y':20,'w':12,'h':12}}]}
            preview=client.request('POST',base+'/preview',html_change)
            client.request('POST',base+'/apply',{'preview_id':preview['preview_id'],'client_request_id':html_change['client_request_id']},etag=dashboard['etag'])
            dashboard=client.request('GET',base)
            html,headers=client.request('GET',base+f'/panels/p_html/render?revision={dashboard["revision"]}',raw=True)
            assert b'mlboard.html-bridge/v1' in html and 'sandbox allow-scripts' in headers['Content-Security-Policy']
            for file in ['mcp-initialize.json','mcp-list-tools.json','mcp-tool-call.json']:
                value=client.request('POST','/mcp',example(file));assert 'error' not in value and not value['result'].get('isError')
                if file=='mcp-list-tools.json':assert len(value['result']['tools'])==10
            value=client.request('POST','/mcp',{'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'mlboard.query','arguments':{'project_id':pid,'query':query}}})
            assert not value['result'].get('isError') and value['result']['structuredContent']['complete']
            result={'status':'passed_with_known_limitations' if known_limitations else 'passed','known_limitations':known_limitations,'checks':client.checks,'server_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
                    'schema_files':len(schemas),'query_rows':10,'mcp_tools':10,'dashboard_preview_apply':True,'html_render_csp':True,
                    'not_executed':['SDK training process','browser HTML MessageChannel execution','load/performance benchmarks'],
                    'isolation':'fresh loopback-only SQLite instance; generated credentials stay in memory'}
    except Exception as error:
        result.update(error_type=type(error).__name__,error=str(error)[:600])
        raise
    finally:
        if process is not None:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        shutil.rmtree(fixture)
        result['temporary_instance_removed']=True
        (output/'example-http-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':result['status'],'http_checks':len(result['checks']),'temporary_instance_removed':True}))

if __name__=='__main__':main()
