"""Build reviewed-position browser mappings from retained blank source PDFs.
Run from the repository root after placing current PDFs in tmp/hr-current-forms.
No employee data is read by this build helper.
"""
import base64,hashlib,io,json,zlib
from pathlib import Path
from pypdf import PdfReader,PdfWriter

root=Path(__file__).resolve().parents[1];folder=root/'tmp/hr-current-forms'
def field(id,label,page,x,y,w,h,type='text',role='employee',**kw):
 return dict(id=id,label=label,page=page,x=round(x,3),y=round(y,3),width=round(w,3),height=round(h,3),type=type,role=role,required=False,max_length=120,group='',**kw)
def widgets(reader):
 for i,page in enumerate(reader.pages):
  for a in page.get('/Annots',[]):
   a=a.get_object();p=a.get('/Parent');p=p.get_object() if p else {};name=str(a.get('/T',p.get('/T','')));kind=str(a.get('/FT',p.get('/FT','')))
   if not name or kind not in ('/Tx','/Btn','/Ch'):continue
   x,y,x2,y2=map(float,a['/Rect']);yield i,name,kind,x,float(page.mediabox.height)-y2,x2-x,y2-y
def normalize(reader,extra=None):
 w=PdfWriter();w.clone_document_from_reader(reader)
 if extra:w.append(extra)
 w.compress_identical_objects(remove_duplicates=True,remove_unreferenced=True)
 for p in w.pages:p.compress_content_streams()
 o=io.BytesIO();w.write(o);return o.getvalue()
def record(kind,title,edition,raw,fields,attestations,source,**kw):
 return dict(kind=kind,title=title,edition=edition,pdf=base64.b64encode(zlib.compress(raw,9)).decode(),digest=hashlib.sha256(raw).hexdigest(),fields=fields,attestations=attestations,source=source,**kw)

result=[]
r=PdfReader(folder/'w4.pdf');fields=[]
labels={'f1_01[0]':'First name and middle initial','f1_02[0]':'Last name','f1_03[0]':'Address','f1_04[0]':'City or town, state, and ZIP code','f1_05[0]':'Social security number','c1_1[0]':'Single or Married filing separately','c1_1[1]':'Married filing jointly or Qualifying surviving spouse','c1_1[2]':'Head of household','c1_2[0]':'Step 2(c): Only two jobs total','f1_06[0]':'Step 3(a): Child credit amount','f1_07[0]':'Step 3(b): Other dependent credit amount','f1_08[0]':'Step 3: Total dependent and other credits','f1_09[0]':'Step 4(a): Other income','f1_10[0]':'Step 4(b): Deductions','f1_11[0]':'Step 4(c): Extra withholding','c1_3[0]':'Exempt from withholding for 2026','f1_12[0]':'Employer name and address','f1_13[0]':'First date of employment','f1_14[0]':'Employer identification number (EIN)'}
prefills={'f1_01[0]':'first_middle','f1_02[0]':'last','f1_03[0]':'address','f1_04[0]':'city_state_zip'}
for i,name,kind,x,y,w,h in widgets(r):
 f=field('w4_'+str(len(fields)),labels.get(name,('Multiple Jobs Worksheet' if i==2 else 'Deductions Worksheet')+' - '+name),i,x,y,w,h,'checkbox' if kind=='/Btn' else 'text','employer' if name in ('f1_12[0]','f1_13[0]','f1_14[0]') else 'employee')
 f['source_field']=name;f['profile_key']=prefills.get(name,'');f['required']=name in ('f1_01[0]','f1_02[0]','f1_03[0]','f1_04[0]','f1_05[0]')
 if name.startswith('c1_1'):f['group']='Filing status';f['required']=True
 fields.append(f)
fields += [field('w4_signature','Employee signature',0,95,680,350,22,'signature'),field('w4_date','Signing date',0,462,680,112,22,'date'),field('w4_nra','Nonresident alien notation (if instructed)',0,95,612,300,18)]
result.append(record('w4','Federal Form W-4','2026',normalize(r),fields,dict(employee='Under penalties of perjury, I declare that this certificate, to the best of my knowledge and belief, is true, correct, and complete.',employer='I confirm that the employer information I entered is accurate.'),'https://www.irs.gov/pub/irs-pdf/fw4.pdf'))

r=PdfReader(folder/'ms-normalized.pdf');fields=[]
prefills={'Name':'full_name','Number and Street':'address','City':'city','State':'state','Zip Code':'zip'}
for i,name,kind,x,y,w,h in widgets(r):
 if name in ('Reset','PrintForm'):continue
 f=field('ms_'+str(len(fields)),name,i,x,y,w,h,'date' if name=='Date' else 'checkbox' if kind=='/Btn' else 'text');f['source_field']=name;f['profile_key']=prefills.get(name,'');f['required']=name in ('Name','SSN','Number and Street','City','State','Zip Code','Line 6')
 if name in ('Single','MarrieldSpouseType','HOF'):f['group']='Marital status'
 fields.append(f)
fields.append(field('ms_signature','Employee signature',0,154,532,225,17,'signature'))
result.append(record('ms','Mississippi Withholding Exemption Certificate','89-350-24-8-1-000 · Rev. 10/24',normalize(r),fields,dict(employee='I declare under the penalties imposed for filing false reports that the amount of exemption claimed on this certificate does not exceed the amount to which I am entitled or I am entitled to claim exempt status.'),'https://www.dor.ms.gov/sites/default/files/tax-forms/business/89350248.pdf'))

r=PdfReader(folder/'i9-normalized.pdf');fields=[]
prefills={'Last Name (Family Name)':'last','First Name Given Name':'first','Employee Middle Initial (if any)':'middle_initial','Address Street Number and Name':'address','City or Town':'city','State':'state','ZIP Code':'zip','Employees E-mail Address':'email','Telephone Number':'phone','Employers Business or Org Name':'employer'}
for i,name,kind,x,y,w,h in widgets(r):
 # Supplements are retained on their original pages. Initial onboarding edits Sections 1 and 2.
 if i!=0:continue
 role='employee' if y<380 else 'employer';type='checkbox' if kind=='/Btn' else 'text'
 if name in ('Signature of Employee','Signature of Employer or AR'):type='signature'
 if name in ("Today's Date mmddyyy",'S2 Todays Date mmddyyyy'):type='date'
 f=field('i9_'+str(len(fields)),name,i,x,y,w,h,type,role);f['source_field']=name;f['profile_key']=prefills.get(name,'');f['read_only']=name=='Employers Business or Org Name';f['required']=name in ('Last Name (Family Name)','First Name Given Name','Address Street Number and Name','City or Town','State','ZIP Code','Date of Birth mmddyyyy','FirstDayEmployed mmddyyyy','Last Name First Name and Title of Employer or Authorized Representative','Employers Business or Org Name','Employers Business or Org Address')
 if name in ('CB_1','CB_2','CB_3','CB_4'):f['group']='Citizenship or immigration status';f['required']=True
 fields.append(f)
result.append(record('i9','Form I-9 — Employment Eligibility Verification','01/20/25 · Expires 05/31/2027',normalize(r,PdfReader(folder/'i9-instructions.pdf')),fields,dict(employee='I am aware that federal law provides for imprisonment and/or fines for false statements, or the use of false documents, in connection with the completion of this form. I attest, under penalty of perjury, that this information, including my selection of the box attesting to my citizenship or immigration status, is true and correct.',employer='I attest, under penalty of perjury, that (1) I have examined the documentation presented by the above-named employee, (2) the above-listed documentation appears to be genuine and to relate to the employee named, and (3) to the best of my knowledge, the employee is authorized to work in the United States.'),'https://www.uscis.gov/sites/default/files/document/forms/i-9.pdf',retrieved_from='https://www.hrm.msstate.edu/sites/www.hrm.msstate.edu/files/2025-04/I-9%20Expires%205.31.2027.pdf',instructions_from='https://www.smcm.edu/app/uploads/sites/223/2026/04/I-9-instructions-exp-053127.pdf'))

reference=json.loads((root/'assets/hr-reference-forms.json').read_text(encoding='utf-8'));raw=base64.b64decode(next(x['file'] for x in reference if x['kind']=='background'));r=PdfReader(io.BytesIO(raw));fields=[]
fields += [field('bg_company','Employer',0,36,94,374,16,profile_key='employer',read_only=True),field('bg_disclosure_signature','Disclosure signature',0,79,325,280,14,'signature'),field('bg_disclosure_date','Disclosure date',0,420,325,120,14,'date'),field('bg_print_name','Print name',0,85,364,455,14,profile_key='full_name')]
fields += [field('bg_authorization_signature','Authorization signature',1,79,527,280,14,'signature'),field('bg_authorization_date','Authorization date',1,420,527,120,14,'date'),field('bg_name','Print name: first, middle, last',1,85,552,455,14,profile_key='full_name'),field('bg_maiden','Maiden name (if applicable)',1,154,585,240,13),field('bg_address','Street, city, state and ZIP',1,74,611,465,13,profile_key='full_address'),field('bg_ssn','Social Security number',1,134,643,229,13),field('bg_dob','Date of birth',1,451,643,92,13),field('bg_license','Driver license number',1,139,677,184,13),field('bg_license_state','Driver license state',1,400,677,102,13),field('bg_gender','Gender',1,74,695,75,13),field('bg_phone','Telephone including area code',1,120,713,137,13,profile_key='phone'),field('bg_mn_copy','Minnesota: request copy',1,372,385,8,8,'checkbox'),field('bg_ok_copy','Oklahoma: request copy',1,193,423,8,8,'checkbox'),field('bg_ca_copy','California: request copy',1,225,486,8,8,'checkbox')]
authorization=r.pages[1].extract_text().split('State of Washington')[0].replace('ACKNOWLEDGMENT AND AUTHORIZATION','').strip()
result.append(record('background','Background check disclosure and authorization','Uploaded Praesidium packet · 09/20/2018',raw,fields,dict(employee=authorization),'User-provided Background Check.pdf'))
(root/'assets/hr-source-forms.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('Prepared source layouts:',[(x['kind'],len(x['fields'])) for x in result])
