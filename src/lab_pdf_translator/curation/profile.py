"""Document-specific structural profiling for Curated normalization.

Bitácora: 2026-09-06 — Fase 2 Revision 2 — deterministic document profiling.
"""
from __future__ import annotations
import re, statistics, uuid
from collections import Counter, defaultdict
from typing import Any

PROFILE_NS=uuid.UUID("a6fae7df-b8af-52c2-bffd-2dc4eeb01e84")
NAVIGATION=re.compile(r"^\s*(?P<label>.+?)[ .·…]{1,}(?P<reference>\d{1,4})\s*$")

def build_document_profile(raw:dict[str,Any])->dict[str,Any]:
 styles=Counter(); families=Counter(); sizes=Counter(); page_nav:dict[int,int]=defaultdict(int); page_lines=Counter(); mono=Counter(); widths=[]; short_styles=Counter(); style_lines=Counter()
 for page in raw['pages']:
  for block in page['blocks']:
   widths.append((block['bbox'][2]-block['bbox'][0])/page['width'])
   for line in block['lines']:
    text=''.join(s['text'] for s in line['spans']).strip(); page_lines[page['page_number']]+=bool(text)
    if NAVIGATION.match(text):page_nav[page['page_number']]+=1
    for span in line['spans']:
     font=span['font']; key=(font.get('family'),font.get('size'),font.get('weight'),font.get('style')); styles[key]+=max(1,len(span['text']));families[font.get('family')]+=max(1,len(span['text']));sizes[font.get('size')]+=max(1,len(span['text']))
     if any(x in (font.get('family') or '').lower() for x in ('mono','courier','consolas','inconsolata')):mono[font.get('family')]+=1
     style_lines[key]+=1
     if 2<=len(text)<=30:short_styles[key]+=1
 body=styles.most_common(1)[0][0] if styles else (None,10,'normal','normal'); nav_pages=sorted(p for p,n in page_nav.items() if n>=4 and n/max(1,page_lines[p])>=.25)
 groups=[]
 for page in nav_pages:
  if not groups or page>groups[-1][-1]+1:groups.append([page])
  else:groups[-1].append(page)
 navigation=[]
 for group in groups:
  role='toc_entry' if group[0] <= len(raw['pages'])*.25 else 'index_entry'
  navigation.append({'pages':group,'document_role':role,'line_count':sum(page_nav[p] for p in group),'signals':['line-ending-page-reference','repeated-page-density','contiguous-document-region'],'confidence':.93})
 clusters=[]
 for index,(key,count) in enumerate(styles.most_common(30),1):
  family,size,weight,style=key; clusters.append({'family_id':str(uuid.uuid5(PROFILE_NS,f"{raw['document_id']}:{key}")),'classification_family':f'typography_{index}','semantic_type':'body_text' if key==body else 'unknown','document_role':'paragraph' if key==body else 'unassigned','signals':{'typography':{'family':family,'size':size,'weight':weight,'style':style},'repetition':{'weighted_characters':count}},'confidence':.98 if key==body else .55})
 cover_page=None
 for page in raw['pages']:
  if any((s['font'].get('size') or 0)>body[1]*2.5 for b in page['blocks'] for l in b['lines'] for s in l['spans']):cover_page=page['page_number'];break
 label_families=[{'classification_family':'structured_label','typography':{'family':k[0],'size':k[1],'weight':k[2],'style':k[3]},'short_lines':v,'short_ratio':v/style_lines[k],'signals':['recurrent-short-line-typography'],'confidence':.78} for k,v in short_styles.items() if v>=10 and v/style_lines[k]>=.6 and k!=body]
 return {'profile_version':'1.0.0','document_id':raw['document_id'],'body_text_baseline':{'family':body[0],'size':body[1],'weight':body[2],'style':body[3]},'cover_page':cover_page,'typography_clusters':clusters,'navigation_families':navigation,'structural_label_families':label_families,'technical_families':[{'classification_family':'monospace_technical','font_families':sorted(x for x in mono if x),'occurrences':sum(mono.values()),'signals':['monospace-typography','syntax-required'],'confidence':.85}],'geometry':{'median_block_width_ratio':statistics.median(widths) if widths else 0,'page_count':len(raw['pages'])},'font_distribution':[{'family':k,'weighted_characters':v} for k,v in families.most_common()],'font_size_distribution':[{'size':k,'weighted_characters':v} for k,v in sizes.most_common()]}

def navigation_role(profile:dict[str,Any],page_number:int)->str|None:
 for family in profile['navigation_families']:
  if page_number in family['pages']:return family['document_role']
 return None

def structural_label_family(profile:dict[str,Any],spans:list[dict[str,Any]])->bool:
 keys={(s['font'].get('family'),s['font'].get('size'),s['font'].get('weight'),s['font'].get('style')) for s in spans}
 known={(f['typography']['family'],f['typography']['size'],f['typography']['weight'],f['typography']['style']) for f in profile['structural_label_families']}
 return bool(keys and keys<=known)
