"""Versioned browser forms and separately authenticated electronic signatures.

The approved PDF is the document of record; form fields are positioned over its
original pages. Publishing a mapping is an HR configuration action, not a legal
certification. Signed PDFs and evidence remain immutable when templates change.
"""
import io,zlib
HR_SOURCE_FORMS=[] # prepared HR source forms
from zoneinfo import ZoneInfo

def hr_browser_init(c):
    c.executescript('''
CREATE TABLE IF NOT EXISTS hr_browser_forms(id TEXT PRIMARY KEY,template TEXT NOT NULL,active INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hr_browser_drafts(id TEXT PRIMARY KEY,enrollment TEXT NOT NULL,form TEXT NOT NULL,role TEXT NOT NULL,parent TEXT NOT NULL,revision INTEGER NOT NULL,body BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS hr_browser_signatures(document TEXT PRIMARY KEY,draft TEXT UNIQUE NOT NULL,body BLOB NOT NULL);
CREATE TRIGGER IF NOT EXISTS hr_browser_signature_update BEFORE UPDATE ON hr_browser_signatures BEGIN SELECT RAISE(ABORT,'Signature evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS hr_browser_signature_delete BEFORE DELETE ON hr_browser_signatures BEGIN SELECT RAISE(ABORT,'Signature evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS hr_browser_form_update BEFORE UPDATE OF template,body ON hr_browser_forms BEGIN SELECT RAISE(ABORT,'Published form mapping is immutable'); END;
CREATE TRIGGER IF NOT EXISTS hr_browser_form_delete BEFORE DELETE ON hr_browser_forms BEGIN SELECT RAISE(ABORT,'Published form mapping is retained'); END;
CREATE TRIGGER IF NOT EXISTS hr_template_content BEFORE UPDATE OF kind,title,edition,mime,body,digest ON hr_templates BEGIN SELECT RAISE(ABORT,'Form template content is immutable'); END;
CREATE TRIGGER IF NOT EXISTS hr_docs_no_delete BEFORE DELETE ON hr_documents BEGIN SELECT RAISE(ABORT,'Submitted document is retained'); END;
''')

def hr_pdf_libraries():
    try:
        from pypdf import PdfReader, PdfWriter
        import pypdfium2
        from reportlab.pdfgen import canvas
        return PdfReader,PdfWriter,pypdfium2,canvas.Canvas
    except ImportError:raise Problem('Browser signing needs the updated server installer. Existing records are safe; install the server with its PDF components.',503)

def hr_pdf_info(raw):
    reader=hr_pdf_libraries()[0](io.BytesIO(raw))
    if reader.is_encrypted or not 1<=len(reader.pages)<=30:raise Problem('Use an unencrypted PDF with 1–30 pages.')
    result=[]
    for p in reader.pages:
        if p.rotation or list(p.cropbox)!=list(p.mediabox):raise Problem('Normalize PDF page rotation and cropping before configuring fields.')
        w,h=float(p.mediabox.width),float(p.mediabox.height)
        if not 72<=w<=1500 or not 72<=h<=1500:raise Problem('PDF page dimensions are unsupported.')
        result.append(dict(width=w,height=h))
    return result

def hr_browser_config(c,template,body):
    raw=base64.b64decode(hr_unpack(template['body'])['file']);pages=hr_pdf_info(raw)
    reader=hr_pdf_libraries()[0](io.BytesIO(raw))
    for i,page in enumerate(pages):page['text']=reader.pages[i].extract_text()[:30000]
    fields=body.get('fields');attest=body.get('attestations',{})
    if not isinstance(fields,list) or not 1<=len(fields)<=300:raise Problem('Configure 1–300 document fields.')
    clean=[];ids=set()
    for f in fields:
        ident=str(f.get('id',''));role=f.get('role');kind=f.get('type')
        if not re.fullmatch('[a-zA-Z][a-zA-Z0-9_]{0,59}',ident) or ident in ids:raise Problem('Each field needs a unique identifier.')
        if role not in ('employee','employer') or kind not in ('text','checkbox','signature','date'):raise Problem('Choose a supported field and signer.')
        ids.add(ident);page=f.get('page')
        if type(page)!=int or not 0<=page<len(pages):raise Problem('Choose a valid page for every field.')
        try:x,y,w,h=[float(f[k]) for k in ('x','y','width','height')]
        except (ValueError,KeyError,TypeError):raise Problem('Enter field position and size in PDF points.')
        if not all(math.isfinite(v) for v in (x,y,w,h)) or min(x,y)<0 or min(w,h)<8 or x+w>pages[page]['width'] or y+h>pages[page]['height']:raise Problem('Keep each field inside its page.')
        length=f.get('max_length',100)
        if type(length)!=int or not 1<=length<=1000:raise Problem('Field length must be 1–1000 characters.')
        clean.append(dict(source_field=str(f.get('source_field',''))[:200],profile_key=str(f.get('profile_key',''))[:40],read_only=f.get('read_only') is True,id=ident,label=customer_text(f.get('label',ident),'field label',200),type=kind,role=role,page=page,x=x,y=y,width=w,height=h,required=f.get('required') is True,max_length=length,group=customer_text(f.get('group',''),'checkbox group',60)))
    roles={f['role'] for f in clean}
    if 'employee' not in roles or (template['kind']=='i9' and 'employer' not in roles):raise Problem('An employee signature is required; I-9 also needs employer fields and signature.')
    for role in roles:
        needs_signature=role=='employee' or template['kind']=='i9'
        if needs_signature and not any(f['role']==role and f['type']=='signature' for f in clean):raise Problem('Place a signature field for each signer.')
        if needs_signature and not any(f['role']==role and f['type']=='date' for f in clean):raise Problem('Place a signing-date field for each signer.')
        attest[role]=customer_text(attest.get(role,''),'exact form attestation',6000)
        if not attest[role]:raise Problem('Enter the exact attestation from the form for each signer.')
    if body.get('reviewed') is not True:raise Problem('Review the complete form, field mapping, required choices and attestations before enabling it.')
    return dict(fields=clean,pages=pages,attestations={r:attest[r] for r in roles},edition=template['edition'],title=template['title'],kind=template['kind'],source_digest=template['digest'])

def hr_source_seed(c):
    for source in HR_SOURCE_FORMS:
        ident='source-'+source['kind']+'-'+source['digest'][:16]
        if c.execute('SELECT 1 FROM hr_templates WHERE id=?',(ident,)).fetchone():continue
        raw=zlib.decompress(base64.b64decode(source['pdf']))
        if hashlib.sha256(raw).hexdigest()!=source['digest']:raise Problem('Source form integrity check failed.',503)
        c.execute('INSERT INTO hr_templates VALUES(?,?,?,?,0,?,?,?)',(ident,source['kind'],source['title'],source['edition'],'application/pdf',hr_pack({'file':base64.b64encode(raw).decode()}),source['digest']))
        template=c.execute('SELECT * FROM hr_templates WHERE id=?',(ident,)).fetchone()
        cfg=hr_browser_config(c,template,dict(source,reviewed=True));cfg['source']=source['source']
        c.execute('INSERT INTO hr_browser_forms VALUES(?,?,0,?)',(ident,ident,json.dumps(cfg)))
    c.commit()

def hr_browser_prefill(r,cfg,role,values):
    profile=hr_unpack(r['body']);full=' '.join(profile.get(k,'') for k in ('first','middle','last')).strip()
    defaults=dict(profile,full_name=full,first_middle=' '.join([profile.get('first',''),profile.get('middle','')[:1]]).strip(),middle_initial=profile.get('middle','')[:1],city_state_zip=', '.join(filter(None,[profile.get('city',''), ' '.join(filter(None,[profile.get('state',''),profile.get('zip','')]))])),full_address=', '.join(filter(None,[profile.get('address',''),profile.get('city',''),profile.get('state',''),profile.get('zip','')])))
    values=dict(values)
    for f in cfg['fields']:
        if f['role']==role and f.get('profile_key') and (f['id'] not in values or f.get('read_only')):values[f['id']]=defaults.get(f['profile_key'],'')
    return values

def hr_browser_access(h,c,d,editable=False):
    role=d.get('role','employee')
    if role=='employee':r=hr_auth(h,c);actor=r['account']
    elif role=='employer':
        actor=hr_admin(h)['name'];r=hr_row(c,d.get('enrollment'))
    else:raise Problem('Invalid signer.',403)
    b=hr_unpack(r['body'])
    if editable and (r['status'] in ('revoked','complete') or not b.get('password_changed') or not b.get('consent') or b.get('paper_requested')):raise Problem('Complete password setup and electronic consent before editing forms.',403)
    form=c.execute('SELECT f.*,t.kind,t.body AS pdf,t.active AS template_active FROM hr_browser_forms f JOIN hr_templates t ON t.id=f.template WHERE f.id=?',(d.get('form'),)).fetchone()
    if not form or (editable and (not form['active'] or not form['template_active'])):raise Problem('The form version changed. Reopen the section.',409)
    cfg=json.loads(form['body']);parent=d.get('parent','')
    if role=='employer':
        p=c.execute('SELECT d.*,s.body AS evidence FROM hr_documents d JOIN hr_browser_signatures s ON s.document=d.id WHERE d.id=? AND d.enrollment=? AND d.template=?',(parent,r['id'],form['template'])).fetchone()
        if not p or hr_unpack(p['evidence'])['role']!='employee':raise Problem('Select this employee’s signed form before completing employer fields.',403)
        if hr_unpack(p['evidence'])['form']!=form['id']:raise Problem('Use the mapping version the employee signed.',409)
        latest=next((x['id'] for x in c.execute('SELECT d.id,s.body FROM hr_documents d JOIN hr_browser_signatures s ON s.document=d.id WHERE d.enrollment=? AND d.kind=? ORDER BY d.at DESC',(r['id'],form['kind'])) if hr_unpack(x['body'])['role']=='employee'),None)
        if editable and latest!=parent:raise Problem('The employee submitted a newer form. Complete the employer portion of that version.',409)
    elif parent:raise Problem('Employee submissions cannot replace another signature.',403)
    if role not in {f['role'] for f in cfg['fields']}:raise Problem('This document does not have fields for this signer.')
    correction=d.get('correction','')
    if correction:
        old=c.execute("SELECT d.*,s.body AS evidence FROM hr_documents d JOIN hr_browser_signatures s ON s.document=d.id WHERE d.id=? AND d.enrollment=? AND d.status='needs_correction'",(correction,r['id'])).fetchone()
        if not old or hr_unpack(old['evidence'])['role']!=role or hr_unpack(old['evidence'])['form']!=form['id']:raise Problem('HR must request a correction before creating a replacement.',403)
    draft_id=hashlib.sha256((r['id']+form['id']+role+parent+correction).encode()).hexdigest()
    return r,actor,form,cfg,draft_id,parent

def hr_field_format(f):
    label=(f.get('source_field','')+' '+f.get('label','')).lower()
    if f['type']!='text':return ''
    if 'social security' in label or 'ssn' in label:return 'ssn'
    if 'phone' in label or 'telephone' in label:return 'phone'
    if re.search(r'\bdate\b',label) or any(x in label for x in ('birth','firstdayemployed','mmddyyyy','mmddyyy')):return 'date'
    return f.get('format','')

def hr_format_value(f,value,complete=False):
    kind=hr_field_format(f)
    if not value or not kind:return value
    digits=re.sub(r'\D','',value)
    if kind=='phone':
        if len(digits)==11 and digits.startswith('1'):digits=digits[1:]
        if len(digits)==10:return '('+digits[:3]+') '+digits[3:6]+'-'+digits[6:]
    elif kind=='ssn':
        if len(digits)==9:return digits[:3]+'-'+digits[3:5]+'-'+digits[5:]
    elif kind=='date':
        if value.upper()=='N/A' and 'exp' in (f.get('label','')+f.get('source_field','')).lower():return 'N/A'
        for pattern in ('%m/%d/%Y','%Y-%m-%d','%m%d%Y'):
            try:return dt.datetime.strptime(value,pattern).strftime('%m/%d/%Y')
            except ValueError:pass
    if complete:raise Problem('Enter '+f['label']+' as '+{'phone':'a 10-digit phone number including area code','ssn':'a 9-digit Social Security number','date':'a valid date (MM/DD/YYYY)'}[kind]+'.')
    return value

def hr_browser_values(cfg,role,values,complete=False):
    if not isinstance(values,dict):raise Problem('Invalid form values.')
    fields={f['id']:f for f in cfg['fields'] if f['role']==role and f['type'] in ('text','checkbox')}
    if set(values)-set(fields):raise Problem('You cannot change another signer’s fields.',403)
    clean={}
    for ident,f in fields.items():
        v=values.get(ident,False if f['type']=='checkbox' else '')
        if f['type']=='checkbox':
            if type(v)!=bool:raise Problem('Invalid checkbox value.')
        else:
            if not isinstance(v,str) or len(v)>f['max_length'] or any(ord(k)<32 and k not in '\n\t' for k in v):raise Problem('Check the value for '+f['label']+'.')
            v=hr_format_value(f,v.strip(),complete)
        if complete and f['required'] and not v and not f['group']:raise Problem('Complete '+f['label']+'.')
        clean[ident]=v
    groups={f['group'] for f in fields.values() if f['group']}
    for g in groups:
        group=[f for f in fields.values() if f['group']==g];count=sum(bool(clean[f['id']]) for f in group)
        if count>1 or (complete and any(f['required'] for f in group) and count!=1):raise Problem('Choose one option for '+g+'.')
    return clean

def hr_browser_render(c,form,cfg,values,role,parent='',name='',signed_at=None):
    Reader,Writer,_,Canvas=hr_pdf_libraries()
    raw=base64.b64decode(hr_unpack(form['pdf'])['file'])
    if parent:raw=base64.b64decode(hr_unpack(c.execute('SELECT body FROM hr_documents WHERE id=?',(parent,)).fetchone()[0])['file'])
    reader=Reader(io.BytesIO(raw));writer=Writer();writer.clone_document_from_reader(reader)
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab
    if 'HRVera' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('HRVera',str(Path(reportlab.__file__).parent/'fonts/Vera.ttf')))
    for index,page in enumerate(writer.pages):
        buf=io.BytesIO();canvas=Canvas(buf,pagesize=(float(page.mediabox.width),float(page.mediabox.height)))
        for f in cfg['fields']:
            if f['page']!=index or f['role']!=role:continue
            value=values.get(f['id'],'')
            if f['type']=='signature':value=name
            if f['type']=='date':value=dt.datetime.fromtimestamp(signed_at,ZoneInfo('America/Chicago')).strftime('%m/%d/%Y') if signed_at else ''
            if f['type']=='checkbox':value='X' if value else ''
            text=str(value).replace('\n',' ');size=min(11,f['height']-3)
            while text and pdfmetrics.stringWidth(text,'HRVera',size)>f['width']-4 and size>5:size-=.25
            if text and pdfmetrics.stringWidth(text,'HRVera',size)>f['width']-4:raise Problem('The entry for '+f['label']+' is too long to print legibly. Shorten it or ask HR to enlarge the field.')
            canvas.setFont('HRVera',size);canvas.setFillColorRGB(.05,.12,.2);canvas.drawString(f['x']+2,float(page.mediabox.height)-f['y']-f['height']+3,text)
        canvas.showPage();canvas.save();page.merge_page(Reader(io.BytesIO(buf.getvalue())).pages[0])
    # Immutable submissions intentionally flatten the original widgets. Original PDF is retained.
    writer.remove_annotations(subtypes='/Widget')
    from pypdf.generic import NameObject
    writer.root_object.pop(NameObject('/AcroForm'),None)
    for key in ('/OpenAction','/AA'):writer.root_object.pop(NameObject(key),None)
    result=io.BytesIO();writer.write(result);return result.getvalue()

def hr_browser_get(h,c,path,q):
    d={k:v[0] for k,v in q.items()}
    if path=='browser-config':
        hr_admin(h);t=c.execute('SELECT * FROM hr_templates WHERE id=?',(d.get('template'),)).fetchone()
        if not t or t['mime']!='application/pdf':raise Problem('Choose an approved PDF template.')
        existing=c.execute('SELECT body FROM hr_browser_forms WHERE template=? AND active=1',(t['id'],)).fetchone()
        cfg=json.loads(existing[0]) if existing else {}
        return h.send(dict(template=t['id'],pages=hr_pdf_info(base64.b64decode(hr_unpack(t['body'])['file'])),fields=cfg.get('fields',[]),attestations=cfg.get('attestations',{})))
    if path=='browser-template-page':
        hr_admin(h);t=c.execute('SELECT * FROM hr_templates WHERE id=?',(d.get('template'),)).fetchone()
        if not t:raise Problem('Template not found.',404)
        raw=base64.b64decode(hr_unpack(t['body'])['file'])
    elif path=='browser-evidence':
        doc=c.execute('SELECT * FROM hr_documents WHERE id=?',(d.get('document'),)).fetchone()
        if not doc:raise Problem('Document not found.',404)
        try:actor=hr_admin(h)['name']
        except Problem:
            r=hr_auth(h,c);actor=r['account']
            if r['id']!=doc['enrollment']:raise Problem('Document not found.',404)
        evidence=c.execute('SELECT body FROM hr_browser_signatures WHERE document=?',(doc['id'],)).fetchone()
        if not evidence:raise Problem('Signature evidence not found.',404)
        hr_event(c,doc['enrollment'],actor,'Downloaded signature evidence',doc['id']);c.commit()
        return h.send(json.dumps(hr_unpack(evidence[0]),indent=2).encode(),kind='application/json',attachment=True)
    else:
        r,actor,form,cfg,ident,parent=hr_browser_access(h,c,d)
        draft=c.execute('SELECT * FROM hr_browser_drafts WHERE id=?',(ident,)).fetchone();values=hr_unpack(draft['body']) if draft else {}
        signature=c.execute('SELECT document FROM hr_browser_signatures WHERE draft=?',(ident,)).fetchone()
        if not draft and d.get('correction'):
            old=hr_unpack(c.execute('SELECT body FROM hr_documents WHERE id=?',(d['correction'],)).fetchone()[0]);values=old.get('values',{})
        values=hr_browser_prefill(r,cfg,d.get('role','employee'),values)
        if path=='browser-form':
            for field in cfg['fields']:field['format']=hr_field_format(field)
            hr_event(c,r['id'],actor,'Opened browser form',form['id']);c.commit()
            return h.send(dict(form=form['id'],template=form['template'],config=cfg,revision=draft['revision'] if draft else 0,values=values,document=signature[0] if signature else '',role=d.get('role','employee'),parent=parent,enrollment=r['id']))
        if path!='browser-page':raise Problem('Unknown browser form page.',404)
        raw=base64.b64decode(hr_unpack(form['pdf'])['file'])
        if parent:raw=base64.b64decode(hr_unpack(c.execute('SELECT body FROM hr_documents WHERE id=?',(parent,)).fetchone()[0])['file'])
        if d.get('signed')=='1' and signature:raw=base64.b64decode(hr_unpack(c.execute('SELECT body FROM hr_documents WHERE id=?',(signature[0],)).fetchone()[0])['file'])
        if d.get('preview')=='1':raw=hr_browser_render(c,form,cfg,values,d.get('role','employee'),parent)
        hr_event(c,r['id'],actor,'Viewed form page',form['id']+':'+str(d.get('page','0')));c.commit()
    try:page=int(d.get('page','0'))
    except ValueError:raise Problem('Invalid page.')
    pdf=hr_pdf_libraries()[2].PdfDocument(raw)
    try:
        if not 0<=page<len(pdf):raise Problem('Page not found.',404)
        p=pdf[page];bitmap=p.render(scale=1.5);out=io.BytesIO();bitmap.to_pil().save(out,format='PNG');bitmap.close();p.close()
    finally:pdf.close()
    return h.send(out.getvalue(),kind='image/png')

def hr_browser_post(h,c,path,d):
    if path=='browser-source-activate':
        u=hr_admin(h);hr_source_seed(c);ident=d.get('template','')
        if not ident.startswith('source-') or not c.execute('SELECT 1 FROM hr_browser_forms WHERE template=?',(ident,)).fetchone():raise Problem('Choose an included source form.')
        if d.get('reviewed') is not True:raise Problem('Review the source form and its field layout before enabling it.')
        t=c.execute('SELECT * FROM hr_templates WHERE id=?',(ident,)).fetchone()
        c.execute('UPDATE hr_templates SET active=0 WHERE kind=?',(t['kind'],));c.execute('UPDATE hr_templates SET active=1 WHERE id=?',(ident,));c.execute('UPDATE hr_browser_forms SET active=1 WHERE template=?',(ident,))
        hr_event(c,'configuration',u['name'],'Enabled source browser form',ident);c.commit();return h.send({'id':ident})
    if path=='browser-publish':
        u=hr_admin(h);t=c.execute('SELECT * FROM hr_templates WHERE id=? AND active=1',(d.get('template'),)).fetchone()
        if not t or t['mime']!='application/pdf':raise Problem('Approve a PDF template before configuring browser completion.')
        cfg=hr_browser_config(c,t,d);ident=secrets.token_hex(16)
        c.execute('UPDATE hr_browser_forms SET active=0 WHERE template=?',(t['id'],));c.execute('INSERT INTO hr_browser_forms VALUES(?,?,1,?)',(ident,t['id'],json.dumps(cfg)))
        hr_event(c,'configuration',u['name'],'Published browser form mapping',ident);c.commit();return h.send({'id':ident})
    r,actor,form,cfg,ident,parent=hr_browser_access(h,c,d,editable=True);role=d.get('role','employee')
    prior=c.execute('SELECT document FROM hr_browser_signatures WHERE draft=?',(ident,)).fetchone()
    if prior:
        if path=='browser-sign':return h.send({'document':prior[0],'already_signed':True})
        raise Problem('This form is signed. HR must request a new version for corrections.',409)
    draft=c.execute('SELECT * FROM hr_browser_drafts WHERE id=?',(ident,)).fetchone();revision=draft['revision'] if draft else 0
    if d.get('revision')!=revision:raise Problem('This form was changed in another tab. Reopen it before continuing.',409)
    if path=='browser-save':
        values=hr_browser_values(cfg,role,hr_browser_prefill(r,cfg,role,d.get('values',{})))
        c.execute('INSERT INTO hr_browser_drafts VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(ident,r['id'],form['id'],role,parent,revision+1,hr_pack(values)))
        hr_event(c,r['id'],actor,'Saved encrypted form draft',ident);c.commit();return h.send({'revision':revision+1})
    if path!='browser-sign':raise Problem('Unknown signing action.',404)
    if not draft:raise Problem('Save and review the form before signing.')
    values=hr_browser_values(cfg,role,hr_unpack(draft['body']),True)
    if d.get('acknowledged') is not True or not (d.get('reviewed_document') is True or d.get('reviewed_pages')==list(range(len(cfg['pages'])))):raise Problem('Confirm that you reviewed the entire form and its instructions before signing.')
    viewed={row[0] for row in c.execute("SELECT detail FROM hr_events WHERE enrollment=? AND actor=? AND action='Viewed form page'",(r['id'],actor))}
    if any(form['id']+':'+str(i) not in viewed for i in range(len(cfg['pages']))):raise Problem('Open every page of the form before signing.')
    if role=='employer' and form['kind']=='i9' and d.get('examined_documents') is not True:raise Problem('Complete the required identity and work-authorization document examination before signing Section 2.')
    attempts_key='hr-sign:'+actor;now=time.time();attempts=[t for t in ATTEMPTS.get(attempts_key,[]) if t>now-300]
    if len(attempts)>=5:raise Problem('Too many signing password attempts. Wait five minutes.',429)
    user=c.execute('SELECT * FROM users WHERE name=?',(actor,)).fetchone()
    if not user or not hmac.compare_digest(user['hash'],password(str(d.get('password','')),user['salt'])):
        ATTEMPTS[attempts_key]=attempts+[now];raise Problem('Enter your current password to sign.',403)
    ATTEMPTS.pop(attempts_key,None);name=customer_text(d.get('name',''),'signature name',100)
    if not name:raise Problem('Type your full legal name to sign.')
    raw=hr_browser_render(c,form,cfg,values,role,parent,name,now);digest=hashlib.sha256(raw).hexdigest();doc=secrets.token_hex(32)
    evidence=dict(version=1,document=doc,form=form['id'],template=form['template'],source_digest=cfg['source_digest'],document_sha256=digest,parent=parent,corrects=d.get('correction',''),role=role,account=actor,typed_name=name,signed_at=dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),authentication='Authenticated invitation or HR account plus password re-entry',attestation=cfg['attestations'][role],consent=hr_unpack(r['body'])['consent'],reviewed_pages=list(range(len(cfg['pages']))),review_acknowledgment='I have reviewed this entire form and its instructions.',examined_documents=bool(d.get('examined_documents')) if role=='employer' else False,values_sha256=hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest())
    payload=dict(file=base64.b64encode(raw).decode(),mime='application/pdf',signature=evidence,values=values)
    c.execute("INSERT INTO hr_documents VALUES(?,?,?,?,?,?,?,'submitted','')",(doc,r['id'],form['kind'],form['template'],now,hr_pack(payload),digest))
    c.execute('INSERT INTO hr_browser_signatures VALUES(?,?,?)',(doc,ident,hr_pack(evidence)))
    hr_event(c,r['id'],actor,'Electronically signed '+role+' '+form['kind'],doc+':'+digest);hr_completion_sync(c,r['id']);c.commit()
    return h.send({'document':doc,'sha256':digest})
