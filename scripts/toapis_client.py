# Copyright (c) 2026 ToAPIs contributors. SPDX-License-Identifier: MIT
"""Independent preset-based ToAPIs image/video client. Standard library only.

No upstream application registration is implied. Credentials and receipts stay
local. No POST retry, no account-credential use, pricing is queried on each run.
"""
from pathlib import Path
from decimal import Decimal
from urllib.parse import urlparse,quote
import argparse,hashlib,json,os,time,urllib.request,urllib.error,uuid
from toapis_billing import current_price,observe,refresh_settlement,cost_summary

def assert_model_allowed(model):
 normalized=''.join(c for c in str(model).casefold() if c.isalnum())
 if 'vip' in normalized:
  raise ValueError('VIP models are excluded from new tutorial runs during SKU retirement (2026-10-27)')
 if 'seedance' in normalized and 'global' in normalized:
  raise ValueError('Seedance Global generation is disabled by user policy (2026-10-23)')

def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,path)
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
class Client:
 def __init__(self,key=None,base=None,state=None):
  self.key=key or os.environ.get('TOAPIS_API_KEY');self.origin=base or os.environ.get('TOAPIS_BASE_URL','https://toapis.com');u=urlparse(self.origin)
  if not self.key:raise ValueError('Set TOAPIS_API_KEY privately')
  if u.scheme!='https' or u.hostname not in ('toapis.com',) or u.username or u.password or u.port or u.path not in ('','/') or u.query or u.fragment:raise ValueError('Use HTTPS ToAPIs origin, without /v1')
  self.origin=self.origin.rstrip('/');self.http=urllib.request.build_opener(NoRedirect);self.state=Path(state or Path(__file__).with_name('.state'));self.state.mkdir(parents=True,exist_ok=True)
 def json(self,path,body=None,content_type='application/json'):
  if isinstance(body,dict) and path.startswith(('images/generations','videos/generations')):assert_model_allowed(body.get('model',''))
  if not (path.startswith('pricing?') or path.startswith('images/generations') or path.startswith('videos/generations') or path=='uploads/images'):raise ValueError('Endpoint not enabled')
  data=json.dumps(body).encode() if isinstance(body,dict) else body
  req=urllib.request.Request(self.origin+'/v1/'+path,data=data,method='POST' if data is not None else 'GET',headers={'Authorization':'Bearer '+self.key,'Content-Type':content_type,'Accept':'application/json'})
  try:
   with self.http.open(req,timeout=90) as response:return json.load(response)
  except urllib.error.HTTPError as e:raise RuntimeError('ToAPIs HTTP '+str(e.code)+' at '+path.split('?')[0]) from None
 def asset(self,url):
  u=urlparse(url)
  if u.scheme!='https' or u.username or u.password:raise ValueError('Unsafe result URL')
  with self.http.open(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=120) as r:return r.read()
 def upload_png(self,path):
  raw=Path(path).read_bytes()
  if not raw.startswith(b'\x89PNG\r\n\x1a\n') or len(raw)>10*1024*1024:raise ValueError('First frame must be a PNG <=10 MiB')
  cache=self.state/('upload-'+hashlib.sha256(raw).hexdigest()+'.json')
  if cache.exists():return json.loads(cache.read_text(encoding='utf-8'))['url']
  boundary='ToAPIs'+uuid.uuid4().hex;body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="first-frame.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+raw+f'\r\n--{boundary}--\r\n'.encode());response=self.json('uploads/images',body,'multipart/form-data; boundary='+boundary);url=response['data']['url']
  if not url.startswith('https://'):raise ValueError('Upload must return HTTPS URL')
  save(cache,{'url':url});return url

def prepare(client,preset,prompt,max_usd):
 assert_model_allowed(preset['model'])
 if not isinstance(prompt,str) or not prompt.strip():raise ValueError('Nonempty prompt required')
 price=current_price(client.json,preset['model'],preset['kind'],preset['pricing_conditions'])
 if price['unit']=='request' and price['price_basis']=='request':estimate=Decimal(price['maximum_unit_price'])
 elif price['unit']=='second' and price['price_basis']=='output_seconds':estimate=Decimal(price['maximum_unit_price'])*int(preset['request']['duration'])
 elif preset['kind']=='video' and price['unit']=='1m_tokens' and price['price_basis']=='total_tokens':estimate=Decimal(price['maximum_unit_price'])*Decimal(str(preset.get('estimated_total_tokens',38400)))/1000000
 else:raise ValueError('Token-metered image preset requires a reviewed token budget; quotation only')
 if estimate>Decimal(str(max_usd)):raise ValueError('Estimated charge exceeds per-case allowance')
 return {'request':{**preset['request'],'prompt':prompt},'price':price,'estimated_usd':str(estimate),'token_estimate_not_a_locked_quote':price['unit']=='1m_tokens'}

def generate(client,preset,prompt,output_dir='outputs',max_usd='0.20',live=False,image=None,run_id='default'):
 assert_model_allowed(preset['model'])
 # Stable identity includes the first-frame bytes and run ID. Repeating the same
 # job resumes its saved task; a new run ID is an explicit new paid job.
 image_hash=None
 if preset.get('needs_image'):
  if not image:raise ValueError('This inspected preset requires --image first-frame.png')
  image_hash=hashlib.sha256(Path(image).read_bytes()).hexdigest()
 elif image:raise ValueError('This preset has no image-input mapping')
 prepared=prepare(client,preset,prompt,max_usd)
 if not live:return {'model':preset['model'],'mode':'quote_only','estimated_usd':prepared['estimated_usd'],'unit':prepared['price']['unit'],'unit_price':prepared['price']['maximum_unit_price']}
 ident=hashlib.sha256(json.dumps({'origin':client.origin,'key_hash':hashlib.sha256(client.key.encode()).hexdigest(),'request':prepared['request'],'image_hash':image_hash,'run_id':run_id},sort_keys=True).encode()).hexdigest();path=client.state/(ident+'.json');record=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
 if record and not record['receipt'].get('task_id'):raise RuntimeError('Prior submission uncertain; reconcile it before a new POST')
 if not record:
  body=prepared['request']
  if image_hash:body['image_with_roles']=[{'url':client.upload_png(image),'role':'first_frame'}]
  receipt={'model':preset['model'],'task_id':None,'observations':[]};record={'model':preset['model'],'kind':preset['kind'],'state':'submitting','request':body,'receipt':receipt,'price':prepared['price'],'estimate_usd':prepared['estimated_usd']}
  with path.open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
  try:task=client.json(('images' if preset['kind']=='image' else 'videos')+'/generations',body)
  except Exception as e:record.update(state='submission_uncertain',error_type=type(e).__name__);save(path,record);raise
  receipt['task_id']=task.get('id');observe(receipt,task);record['state']=task.get('status');save(path,record)
  if not receipt['task_id']:raise RuntimeError('No task ID; do not repeat POST')
 receipt=record['receipt'];prefix=('images' if preset['kind']=='image' else 'videos')+'/generations/';deadline=time.monotonic()+1200
 while time.monotonic()<deadline:
  try:task=client.json(prefix+quote(receipt['task_id'],safe=''))
  except Exception:time.sleep(8);continue
  observe(receipt,task);record['state']=task.get('status');save(path,record)
  if record['state'] in ('completed','failed','cancelled','expired'):
   refresh_settlement(client.json,receipt,preset['kind'],lambda:save(path,record),timeout=30);record['cost']=cost_summary(receipt,saved_price=record['price']);save(path,record)
   if record['state']!='completed':return {'model':preset['model'],'status':record['state'],'cost':record['cost']}
   if not record.get('output'):
    raw=client.asset(task['result']['data'][0]['url'])
    if preset['kind']=='video':
     if b'ftyp' not in raw[:40]:raise ValueError('Result is not MP4')
     ext='.mp4'
    elif raw.startswith(b'\x89PNG\r\n\x1a\n'):ext='.png'
    elif raw.startswith(b'\xff\xd8\xff'):ext='.jpg'
    elif raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':ext='.webp'
    else:raise ValueError('Unrecognized image bytes')
    dest=Path(output_dir)/(preset['model']+'-'+ident[:10]+ext);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);record['output']=str(dest.resolve());save(path,record)
   return {'model':preset['model'],'status':'completed','output':record['output'],'cost':record['cost']}
  time.sleep(8)
 raise RuntimeError('Polling timeout; resume this saved task only')

if __name__=='__main__':
 presets=json.loads(Path(__file__).with_name('presets.json').read_text(encoding='utf-8'));p=argparse.ArgumentParser();p.add_argument('--model',choices=sorted(presets),required=True);p.add_argument('--prompt');p.add_argument('--prompt-file',type=Path);p.add_argument('--image',type=Path);p.add_argument('--max-usd',default=None);p.add_argument('--state',default=None);p.add_argument('--output-dir',default=str(Path(__file__).with_name('outputs')));p.add_argument('--run-id',default='default');p.add_argument('--live',action='store_true');a=p.parse_args();prompt=a.prompt_file.read_text(encoding='utf-8') if a.prompt_file else a.prompt;selected=presets[a.model];print(json.dumps(generate(Client(state=a.state),selected,prompt,a.output_dir,a.max_usd or ('0.20' if selected['kind']=='image' else '1.50'),a.live,a.image,a.run_id),ensure_ascii=False))
