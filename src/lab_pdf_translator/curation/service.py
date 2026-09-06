"""Deterministic RAW → Curated normalization.

Bitácora: 2026-09-05 — Fase 2 Revision 1 — pagination, recurrence, confidence,
conditional reading order and exact code-line preservation.
"""
from __future__ import annotations
import hashlib, json, logging, os, re, statistics, uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from lab_pdf_translator.validation.curated import validate_curated_semantics
from lab_pdf_translator.validation.schema import load_json, validate_schema
from lab_pdf_translator.curation.profile import NAVIGATION, build_document_profile, navigation_role, structural_label_family

UNIT_NS=uuid.UUID("5b9b4fc2-993c-51a6-b4a6-af04068bcf74")
TECH=re.compile(r"https?://[^\s]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b(?:SHA-?256|0x[0-9a-fA-F]{6,}|[a-fA-F0-9]{32,}|v?\d+(?:\.\d+){1,}|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\b|[A-Za-z_]\w*\([^)]*\)")
LIST=re.compile(r"^\s*((?:\d+|[A-Za-z])[.)]|[•*–-])\s+(.+)$")
CAPTION=re.compile(r"^(?:figure|fig\.|table)\s*\d",re.I)
CODE=re.compile(r"(?:^\s*(?:def |class |(?:if|for|while|return)\s|[\[{].*[:}]|\$ )|[{};]|\b(?:pragma|contract|function|SELECT|FROM|return)\b)")
ROMAN=re.compile(r"^(?=[ivxlcdm]+$)m{0,3}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})$",re.I)
class CurationError(RuntimeError): pass

def normalize(root: str|Path,input_path: str|Path|None=None,output_path: str|Path|None=None)->dict[str,Any]:
 root=Path(root).resolve(); source=Path(input_path or root/'data/raw/document.json')
 if not source.is_file(): raise CurationError(f'RAW input not found: {source}')
 raw_bytes=source.read_bytes(); raw_sha=hashlib.sha256(raw_bytes).hexdigest(); raw=json.loads(raw_bytes)
 profile=build_document_profile(raw); units,warnings=_units(raw,profile)
 assets=[{'asset_id':o['asset_id'],'asset_occurrence_id':o['asset_occurrence_id'],'page_id':p['page_id']} for p in raw['pages'] for o in p['asset_occurrences']]
 document={'schema_version':'2.1.0','document_id':raw['document_id'],'source_raw':{'path':'data/raw/document.json','sha256':raw_sha,'document_id':raw['document_id']},'document_profile':profile,'units':units,'assets':assets,'quality':{'metrics':_metrics(units,warnings)},'warnings':warnings}
 issues=(*validate_schema(document,load_json(root/'schemas/curated-document.schema.json')),*validate_curated_semantics(document,raw))
 if issues: raise CurationError('Curated validation failed: '+'; '.join(str(x) for x in issues[:5]))
 profile_issues=validate_schema(profile,load_json(root/'schemas/document-profile.schema.json'))
 if profile_issues:raise CurationError('DocumentProfile validation failed: '+'; '.join(str(x) for x in profile_issues[:5]))
 output=Path(output_path or root/'data/curated/document.json'); output.parent.mkdir(parents=True,exist_ok=True); temp=output.with_suffix(output.suffix+'.tmp'); temp.write_text(json.dumps(document,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf8')
 if output_path is None:
  profile_output=root/'data/curated/document-profile.json'; profile_temp=profile_output.with_suffix('.json.tmp'); profile_temp.write_text(json.dumps(profile,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf8');os.replace(profile_temp,profile_output)
 os.replace(temp,output)
 if hashlib.sha256(source.read_bytes()).hexdigest()!=raw_sha: raise CurationError('RAW immutability check failed')
 _logger(root).info('revision-1 curated units=%s raw_sha=%s',len(units),raw_sha); return document

def _units(raw,profile):
 median=statistics.median([s['font']['size'] for p in raw['pages'] for b in p['blocks'] for l in b['lines'] for s in l['spans'] if s['font']['size']] or [10])
 pnums,psignals=_pagination(raw); recurrence=_recurrence(raw,pnums); candidates=[]; warnings=[]
 for page in raw['pages']: candidates.extend(_page_units(page,median,pnums,psignals,recurrence,profile))
 candidates=_order(candidates,raw,warnings)
 result=[]
 for unit in candidates:
  if result and _can_merge(result[-1],unit): _merge(result[-1],unit)
  else: result.append(unit)
 headings=[]
 for order,u in enumerate(result,1):
  u['reading_order']=order; u['unit_id']=str(uuid.uuid5(UNIT_NS,f"{raw['document_id']}:{u['type']}:{','.join(u['source']['span_ids'])}:{order}"))
  if u['type'] in {'chapter_title','section_heading','subsection_heading'}:
   if u['type']=='chapter_title': headings=[]
   headings.append(u['unit_id'])
  u['section_path']=list(headings); u.pop('_bbox',None)
  semantic,role=_semantics(u['type']);u.setdefault('semantic_type',semantic);u.setdefault('document_role',role);u.setdefault('classification_family',u['document_role'])
  if u['type']=='unknown':u['unknown_reason']='insufficient_evidence'
 return result,warnings

def _pagination(raw):
 candidates=[]; offsets=Counter()
 for p in raw['pages']:
  for b in p['blocks']:
   if b['bbox'][1]<=p['height']*.85: continue
   for l in b['lines']:
    for s in l['spans']:
     value=_number(s['text'].strip())
     if value is not None:
      kind='roman' if ROMAN.fullmatch(s['text'].strip()) else 'arabic'; candidates.append((p,s,kind,value)); offsets[(kind,value-p['page_number'])]+=1
 selected=set(); signals={}
 for p,s,kind,value in candidates:
  support=offsets[(kind,value-p['page_number'])]
  if support>=5: selected.add(s['span_id']); signals[s['span_id']]=['bottom-edge',f'{kind}-sequence',f'offset-support:{support}']
 return selected,signals

def _number(text):
 if text.isdigit() and len(text)<=4:return int(text)
 if not ROMAN.fullmatch(text):return None
 d={'i':1,'v':5,'x':10,'l':50,'c':100,'d':500,'m':1000}; t=text.lower(); return sum(-d[c] if i+1<len(t) and d[c]<d[t[i+1]] else d[c] for i,c in enumerate(t))
def _fp(text): return re.sub(r'\b(?:\d+|[ivxlcdm]+)\b','<NUMBER>',text.lower(),flags=re.I).strip()
def _recurrence(raw,pnums):
 c=Counter()
 for p in raw['pages']:
  for b in p['blocks']:
   zone='top' if b['bbox'][3]<p['height']*.15 else 'bottom' if b['bbox'][1]>p['height']*.85 else None
   if not zone:continue
   for l in b['lines']:
    text=''.join(s['text'] for s in l['spans'] if s['span_id'] not in pnums).strip()
    if text:c[(zone,_fp(text))]+=1
 return {k:v for k,v in c.items() if v>=5 and re.search('[A-Za-z]',k[1])}

def _page_units(page,median,pnums,psignals,recurrence,profile):
 out=[]
 for b in page['blocks']:
  if b['block_type']=='image': out.extend(_image(page,b,oid) for oid in b['asset_occurrence_ids']); continue
  lines=b['lines']; spans=[s for l in lines for s in l['spans']]
  if not spans:continue
  raw_text='\n'.join(''.join(s['text'] for s in l['spans']) for l in lines)
  if page['page_number']==profile.get('cover_page'):
   maximum=max((s['font'].get('size') or median for s in spans),default=median); text=raw_text.strip(); lower_y=b['bbox'][1]/page['height']
   if maximum>=median*2.5:out.append(_unit(page,b,lines,spans,'document_title',.98,['document-profile-cover','dominant-font-outlier','aligned-title-region']));continue
   if maximum>=median*1.5 and lower_y>.65 and re.search(r'(?:\band\b|&)',text,re.I):
    unit=_unit(page,b,lines,spans,'paragraph',.92,['document-profile-cover','author-name-pattern','lower-cover-region']);unit.update({'semantic_type':'metadata','document_role':'author','classification_family':'cover_author'});out.append(unit);continue
   if maximum>=median*1.5:out.append(_unit(page,b,lines,spans,'document_subtitle',.94,['document-profile-cover','secondary-font-outlier','aligned-subtitle-region']));continue
  nav_role=navigation_role(profile,page['page_number'])
  if nav_role and not any(s['span_id'] in pnums for s in spans):
   for line in lines:
    text=''.join(s['text'] for s in line['spans']).strip();match=NAVIGATION.match(text)
    if match:
     unit=_unit(page,b,[line],line['spans'],'paragraph',.93,['document-profile-navigation','line-ending-page-reference']);source_ids=[s['span_id'] for s in line['spans']];style=unit['segments'][0]['style'];reference=match.group('reference');start=unit['text'].rfind(reference);unit.update({'semantic_type':'navigation','document_role':nav_role,'classification_family':nav_role,'label':match.group('label').strip(),'page_reference':reference,'page_reference_source_span_ids':source_ids,'segments':[{'text':match.group('label').strip(),'protected':False,'style':style,'source_span_ids':source_ids},{'text':reference,'protected':True,'start':start,'end':start+len(reference),'style':style,'source_span_ids':source_ids}]});out.append(unit)
    elif text:
     if re.search(r'[A-Za-z]{2,}',text):
      unit=_unit(page,b,[line],line['spans'],'paragraph',.82,['document-profile-navigation','navigation-continuation']);unit.update({'semantic_type':'navigation','document_role':nav_role.replace('_entry','_continuation'),'classification_family':nav_role});out.append(unit)
     else:out.append(_unit(page,b,[line],line['spans'],'unknown',.35,['document-profile-navigation','unsupported-navigation-fragment']))
   continue
  line_flags=[_is_code([line],''.join(s['text'] for s in line['spans'])) for line in lines]
  block_mono=all(any(x in (s['font'].get('family') or '').lower() for x in ('mono','courier','consolas','inconsolata')) for line in lines for s in line['spans'])
  if block_mono and sum(line_flags)>=2:line_flags=[flag or len(re.findall(r'[A-Za-z]{3,}',''.join(s['text'] for s in line['spans'])))<=8 for flag,line in zip(line_flags,lines)]
  if line_flags and all(line_flags):out.append(_unit(page,b,lines,spans,'code_block',.95,['document-profile-technical','strong-syntax','raw-lines-preserved'])); continue
  if any(line_flags):
   for line,is_code in zip(lines,line_flags):
    text=''.join(s['text'] for s in line['spans']).strip()
    if not text:continue
    if is_code:out.append(_unit(page,b,[line],line['spans'],'code_block',.93,['mixed-block-split','strong-line-syntax','raw-lines-preserved']))
    else:
     typ,conf,signals,overrides=_profile_classify(text,page,b,[line],median,profile);unit=_unit(page,b,[line],line['spans'],typ,conf,signals+['mixed-block-split','natural-language-line']);unit.update(overrides);out.append(unit)
   continue
  structural_boundary=any(s['span_id'] in pnums for s in spans)
  for line in lines:
   line_text=''.join(s['text'] for s in line['spans']).strip();zone='top' if line['bbox'][3]<page['height']*.15 else 'bottom' if line['bbox'][1]>page['height']*.85 else 'middle'
   structural_boundary=structural_boundary or bool(line_text and (zone,_fp(line_text)) in recurrence)
  if not structural_boundary:
   text=' '.join(''.join(s['text'] for s in line['spans']) for line in lines).strip();typ,conf,signals,overrides=_profile_classify(text,page,b,lines,median,profile);unit=_unit(page,b,lines,spans,typ,conf,signals+(['logical-block-reconstruction'] if len(lines)>1 else []));unit.update(overrides);out.append(unit);continue
  used=set()
  for l in lines:
   nums=[s for s in l['spans'] if s['span_id'] in pnums]
   for s in nums:out.append(_unit(page,b,[l],[s],'page_number',.99,psignals[s['span_id']])); used.add(s['span_id'])
   remaining=[s for s in l['spans'] if s['span_id'] not in used]
   text=''.join(s['text'] for s in remaining).strip()
   if not text:continue
   zone='top' if l['bbox'][3]<page['height']*.15 else 'bottom' if l['bbox'][1]>page['height']*.85 else 'middle'
   if (zone,_fp(text)) in recurrence:
    typ='header' if zone=='top' else 'footer'; out.append(_unit(page,b,[l],remaining,typ,.93,['edge-region','recurrence-fingerprint',f"occurrences:{recurrence[(zone,_fp(text))]}"]))
   else:
    typ,conf,signals,overrides=_profile_classify(text,page,b,[l],median,profile);unit=_unit(page,b,[l],remaining,typ,conf,signals);unit.update(overrides);out.append(unit)
 return out

def _is_code(lines,text):
 families=[(s['font'].get('family') or '').lower() for l in lines for s in l['spans']]; mono=any(any(x in f for x in ('mono','courier','consolas','inconsolata')) for f in families); syntax=bool(CODE.search(text)); structured=text.count('{')+text.count(';')+text.count('=')>=3
 isolated_call=bool(re.fullmatch(r'\s*[A-Za-z_]\w*\([^\n]*\)\s*=\s*',text));syntax=syntax or bool(re.match(r'\s*["\']?[A-Za-z_]\w*["\']?\s*:\s*',text));prose_heavy=len(re.findall(r'[A-Za-z]{3,}',text))>25 and text.count('{')+text.count(';')+text.count('=')<=1 and not re.match(r'\s*(?:def|class|pragma|contract|function|SELECT)\b',text)
 return (syntax and (mono or structured) or isolated_call) and not prose_heavy
def _classify(text,page,block,lines,median):
 fonts=[s['font'] for l in lines for s in l['spans']]; size=max((f['size'] or median for f in fonts),default=median); bold=bool(fonts and all(f['weight']=='bold' for f in fonts)); short=len(text)<120
 if CAPTION.match(text):return 'caption',.94,['caption-prefix']
 if LIST.match(text):return 'list_item',.94,['list-marker']
 if short and size>=median*1.35:
  if page['page_number']<=3:return ('document_title' if size>=median*2 else 'document_subtitle'),.92,['front-matter','font-size-outlier','short-text']
  chapter=bool(re.search(r'\bchapter\s+\d+\b',text,re.I));return ('chapter_title' if chapter else 'section_heading'),(.95 if chapter else .84),['font-size-outlier','short-text']+(['chapter-number'] if chapter else [])
 if short and bold:return 'subsection_heading',.80,['bold','short-text']
 words=re.findall(r'[A-Za-z]{2,}',text); prose=len(words)>=3 and(len(text)>=25 or any(c in text for c in '.,;:'))
 return ('paragraph',min(.90,.58+min(len(words),20)*.015),['prose-token-count','natural-language-punctuation']) if prose else ('unknown',.35,['insufficient-structural-evidence'])
def _profile_classify(text,page,block,lines,median,profile):
 spans=[s for line in lines for s in line['spans']]
 stripped=text.strip()
 isolated=bool(re.fullmatch(r'(?:0x)?[0-9a-fA-F]{8,}|(?:\[\d+\]:\s*)?[0-9a-fA-F]{16,}|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+|\d+(?:\.\d+)?\s+[A-Z]{2,8}',stripped) or (stripped.count('=')>=2 and bool(re.search(r'\d',stripped))))
 if isolated:return 'identifier',.97,['technical-value-pattern','non-linguistic-token'],{'semantic_type':'technical','document_role':'technical_value','classification_family':'isolated_technical_value','translatable':False}
 if re.search(r'[A-Za-z]{2,}',stripped) and re.search(r'(?:0x)?[0-9a-fA-F]{24,}',stripped):return 'paragraph',.92,['natural-language-label','protected-technical-value'],{'semantic_type':'technical','document_role':'mixed_technical_prose','classification_family':'mixed_technical_prose','translatable':True}
 typ,confidence,signals=_classify(text,page,block,lines,median)
 if typ=='unknown' and re.search(r'[A-Za-z]{2,}',text) and structural_label_family(profile,spans):return 'paragraph',.78,['document-profile-family','recurrent-short-line-typography'],{'semantic_type':'metadata','document_role':'structured_label','classification_family':'structured_label'}
 return typ,confidence,signals,{}

def _unit(page,b,lines,spans,typ,confidence,signals):
 source={'page_ids':[page['page_id']],'block_ids':[b['block_id']],'line_ids':[l['line_id'] for l in lines],'span_ids':[s['span_id'] for s in spans]}; ids=set(source['span_ids']); code=typ=='code_block'
 parts=[''.join(s['text'] for s in l['spans'] if s['span_id'] in ids) for l in lines]
 raw_text='\n'.join(parts) if code else ' '.join(parts)
 text,positions=_canonical_text_positions(raw_text,code)
 bbox=[min(l['bbox'][0] for l in lines),min(l['bbox'][1] for l in lines),max(l['bbox'][2] for l in lines),max(l['bbox'][3] for l in lines)]
 u={'type':typ,'text':text,'translatable':typ not in {'code_block','header','footer','page_number','hash','url','email','identifier'},'confidence':confidence,'classification_signals':signals,'source':source,'segments':_segments(lines,positions,typ=='identifier'),'_bbox':bbox}
 if code:u['lines']=parts
 return u
def _canonical_text_positions(raw_text,code):
 if code:return raw_text,list(range(len(raw_text)))
 output=[]; positions=[]; index=0
 while index<len(raw_text):
  if raw_text[index].isspace():
   end=index
   while end<len(raw_text) and raw_text[end].isspace():end+=1
   if output and end<len(raw_text):
    output.append(' ');positions.extend([len(output)-1]*(end-index))
   else:positions.extend([None]*(end-index))
   index=end
  else:
   output.append(raw_text[index]);positions.append(len(output)-1);index+=1
 return ''.join(output),positions
def _segments(lines,positions,all_protected=False):
 out=[]
 raw_cursor=0
 for line_index,line in enumerate(lines):
  for s in line['spans']:
   text=s['text']; style={'family':s['font'].get('family'),'size':s['font'].get('size'),'weight':s['font'].get('weight'),'style':s['font'].get('style')}; cursor=0
   for m in TECH.finditer(text):
    if m.start()>cursor:out.append(_segment(text[cursor:m.start()],all_protected,style,s['span_id'],raw_cursor+cursor,raw_cursor+m.start(),positions,all_protected))
    out.append(_segment(m.group(),True,style,s['span_id'],raw_cursor+m.start(),raw_cursor+m.end(),positions,all_protected));cursor=m.end()
   if cursor<len(text) or not out or out[-1]['source_span_ids']!=[s['span_id']]:out.append(_segment(text[cursor:],all_protected,style,s['span_id'],raw_cursor+cursor,raw_cursor+len(text),positions,all_protected))
   raw_cursor+=len(text)
  if line_index<len(lines)-1:raw_cursor+=1
 return [x for x in out if x and x['text']]
def _segment(text,protected,style,span_id,raw_start,raw_end,positions,all_protected=False):
 result={'text':text,'protected':protected,'style':style,'source_span_ids':[span_id]}
 if not protected:return result
 mapped=[p for p in positions[raw_start:raw_end] if p is not None]
 if text.isspace() and mapped:
  # Canonical normalization collapses internal whitespace to one space.  Preserve
  # the protection decision using the exact canonical substring, not RAW spacing.
  start,end=min(mapped),max(mapped)+1
  if end-start==1:return {**result,'text':' ','start':start,'end':end}
 if len(mapped)!=len(text) or not mapped or mapped[-1]-mapped[0]+1!=len(mapped):
  # Whitespace collapsed by canonical normalization is not a protectable substring.
  if all_protected:return None
  result['protected']=False;return result
 start,end=mapped[0],mapped[-1]+1
 if end-start==len(text):result.update({'start':start,'end':end})
 elif all_protected:return None
 else:result['protected']=False
 return result
def _image(page,b,oid):return {'type':'image_reference','text':'','translatable':False,'confidence':1.,'classification_signals':['raw-image-block'],'source':{'page_ids':[page['page_id']],'block_ids':[b['block_id']],'line_ids':[],'span_ids':[]},'segments':[],'asset_occurrence_id':oid,'_bbox':b['bbox']}
def _semantics(typ):
 mapping={'document_title':('title','document_title'),'document_subtitle':('title','document_subtitle'),'chapter_title':('heading','chapter_title'),'section_heading':('heading','section_heading'),'subsection_heading':('heading','subsection_heading'),'paragraph':('body_text','paragraph'),'list_item':('list','list_item'),'caption':('caption','caption'),'code_block':('code','code_block'),'page_number':('page_structure','page_number'),'header':('page_structure','header'),'footer':('page_structure','footer'),'image_reference':('image','image_reference'),'unknown':('unknown','unknown')}
 return mapping.get(typ,('unknown',typ))
def _order(units,raw,warnings):
 out=[]
 for page in raw['pages']:
  xs=[u for u in units if u['source']['page_ids']==[page['page_id']]]; narrow=[u for u in xs if u['_bbox'][2]-u['_bbox'][0]<page['width']*.46];left=sum(u['_bbox'][0]<page['width']*.42 for u in narrow);right=sum(u['_bbox'][0]>page['width']*.52 for u in narrow);columns=left>=3 and right>=3;ambiguous=not columns and left>=2 and right>=2
  confidence=.85 if columns else .55 if ambiguous else .92
  if ambiguous:warnings.append({'code':'AMBIGUOUS_READING_ORDER','message':'Competing horizontal clusters lack sufficient evidence for column ordering; top-to-bottom order retained.','ref_id':page['page_id']})
  xs.sort(key=(lambda u:(0 if u['_bbox'][0]<page['width']/2 else 1,u['_bbox'][1],u['_bbox'][0])) if columns else lambda u:(u['_bbox'][1],u['_bbox'][0]))
  for u in xs:u['reading_order_confidence']=confidence
  out.extend(xs)
 return out
def _can_merge(a,b):
 if a['type']!=b['type'] or a['type']!='paragraph' or a['source']['page_ids']!=b['source']['page_ids']:return False
 x,y=a['_bbox'],b['_bbox'];return 0<=y[1]-x[3]<max(18,(x[3]-x[1])*1.8) and abs(x[0]-y[0])<18
def _merge(a,b):
 join='' if a['text'].endswith('-') and b['text'][:1].islower() else ' '
 if not join:a['text']=a['text'][:-1]
 offset=len(a['text'])+len(join)
 for segment in b['segments']:
  if segment.get('protected'):
   segment['start']+=offset;segment['end']+=offset
 a['text']+=join+b['text'];a['segments']+=b['segments'];a['classification_signals']=sorted(set(a['classification_signals']+b['classification_signals']+['paragraph-merge']))
 for k in a['source']:
  for v in b['source'][k]:
   if v not in a['source'][k]:a['source'][k].append(v)
 a['_bbox']=[min(a['_bbox'][0],b['_bbox'][0]),min(a['_bbox'][1],b['_bbox'][1]),max(a['_bbox'][2],b['_bbox'][2]),max(a['_bbox'][3],b['_bbox'][3])]
def _metrics(units,warnings):
 c=Counter(u['type'] for u in units);t=len(units);return {'TOTAL_UNITS':t,'DOCUMENT_TITLES':c['document_title'],'DOCUMENT_SUBTITLES':c['document_subtitle'],'CHAPTER_TITLES':c['chapter_title'],'SECTION_HEADINGS':c['section_heading'],'SUBSECTION_HEADINGS':c['subsection_heading'],'PARAGRAPHS':c['paragraph'],'LIST_ITEMS':c['list_item'],'CODE_BLOCKS':c['code_block'],'CAPTIONS':c['caption'],'HEADERS':c['header'],'FOOTERS':c['footer'],'PAGE_NUMBERS':c['page_number'],'UNKNOWN':c['unknown'],'UNKNOWN_RATIO':c['unknown']/t if t else 0,'LOW_CONFIDENCE':sum(u['confidence']<.6 for u in units),'PROTECTED_SEGMENTS':sum(s['protected'] for u in units for s in u['segments']),'UNITS_WITHOUT_PROVENANCE':sum(not u['source']['span_ids'] and u['type']!='image_reference' for u in units),'WARNINGS':len(warnings)}
def _logger(root):
 logger=logging.getLogger('lab_pdf_translator.curation')
 if not logger.handlers:
  (root/'logs').mkdir(exist_ok=True);h=logging.FileHandler(root/'logs'/'phase-2-normalization.log',encoding='utf8');h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));logger.addHandler(h);logger.setLevel(logging.INFO)
 return logger
