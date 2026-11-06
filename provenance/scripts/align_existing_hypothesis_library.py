import pathlib,sqlite3,csv,json,re,collections,hashlib,shutil,datetime
ROOT=pathlib.Path(r'E:\Paper\4.TEOA\test0_gpt54_triplicate_20261103\engine\library');DB=ROOT/'index.sqlite'
SRC=pathlib.Path(r'C:\Users\dell\Nutstore\1\1.Paper\11-12_AI_photocatalyst\2.Paper2\5.agent\0.for submit\Research-English-release_20261102_final\Research-English-release-v1.0.1_20261030\inputs')
STAMP=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');AUD=ROOT/('alignment_'+STAMP);AUD.mkdir()
c=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
old={r['paper_id']:dict(r) for r in c.execute('select * from papers')};docmap=collections.defaultdict(set)
for r in c.execute('select * from provenance'):
 if 'LIB2_1997' in r['original_path']:
  m=re.search(r'doc_\d+',r['original_path'])
  if m:docmap[m[0]].add(r['paper_id'])
maprows=[]
for d in csv.DictReader((SRC/'04_claims_corpus/documents.csv').open(encoding='utf-8-sig')):
 hits=docmap[d['doc_id']];method='source_doc_id'
 if not hits:
  hits={pid for pid,r in old.items() if d['doi'] and d['doi'].lower() in [x.lower() for x in json.loads(r['doi_candidates'] or '[]')]};method='exact_doi_candidate'
 assert len(hits)==1,(d['doc_id'],hits)
 maprows.append(dict(library='lib1',source_doc_id=d['doc_id'],paper_id=next(iter(hits)),method=method))
for d in json.loads((SRC/'02_systems399/library.json').read_text(encoding='utf-8-sig'))['files']:
 hits=[pid for pid,r in old.items() if r['sha256'].startswith(d['doc_id'].split('_',1)[1])];assert len(hits)==1
 maprows.append(dict(library='lib2',source_doc_id=d['doc_id'],paper_id=hits[0],method='source_pdf_sha256_prefix'))
sets={g:{x['paper_id'] for x in maprows if x['library']==g} for g in ['lib1','lib2']};assert len(sets['lib1'])==1991 and len(sets['lib2'])==399
keep=sets['lib1']|sets['lib2'];extra=set(old)-keep
BACK=AUD/'index.before_alignment.sqlite';b=sqlite3.connect(BACK);c.backup(b);b.close()
TMP=AUD/'index.aligned.sqlite';w=sqlite3.connect(TMP);c.backup(w)
w.execute('create table corpus_membership(library TEXT,source_doc_id TEXT,paper_id TEXT,match_method TEXT,local_text_path TEXT,primary key(library,source_doc_id))')
for g in sets:(ROOT/g).mkdir(exist_ok=True)
cached_chunks=collections.defaultdict(list)
for row in c.execute('select * from chunks order by page,chunk_id'):
 cached_chunks[row['paper_id']].append(dict(row))
for m in maprows:
 target=ROOT/m['library']/(m['source_doc_id']+'.json')
 chunks=cached_chunks[m['paper_id']]
 payload=dict(source_mapping=m,paper=old[m['paper_id']],chunks=chunks,text_origin='Existing historical hypothesis index; not replaced by consensus parsed text')
 target.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
 w.execute('insert into corpus_membership values(?,?,?,?,?)',(m['library'],m['source_doc_id'],m['paper_id'],m['method'],str(target)))
for pid in extra:
 w.execute('delete from search where paper_id=?',(pid,));w.execute('delete from chunks where paper_id=?',(pid,));w.execute('delete from provenance where paper_id=?',(pid,));w.execute('delete from papers where paper_id=?',(pid,))
w.commit();w.execute('vacuum');assert w.execute('pragma integrity_check').fetchone()[0]=='ok'
n=w.execute('select count(*) from chunks').fetchone()[0];assert w.execute('select count(*) from search').fetchone()[0]==n
assert w.execute('select count(*) from papers').fetchone()[0]==len(keep)
fts=w.execute("select count(*) from search where search match 'TEOA'").fetchone()[0]
no_text=[r[0] for r in w.execute('select paper_id from papers where paper_id not in (select distinct paper_id from chunks)')]
w.close();c.close()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(DB)==digest(BACK),'Original index changed during preparation'
for name,rows in [('MATCHED_DOCUMENTS.csv',maprows),('REMOVED_RECORDS.csv',[old[x] for x in sorted(extra)])]:
 with (AUD/name).open('w',encoding='utf-8-sig',newline='') as h:
  writer=csv.DictWriter(h,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
TMP.replace(DB)
report=dict(status='active_index_aligned',index=str(DB),backup=str(BACK),lib1_documents=1991,lib2_documents=399,shared_index_records=len(sets['lib1']&sets['lib2']),retained_index_records=len(keep),removed_index_records=len(extra),indexed_chunks=n,records_without_chunks=no_text,fts_teoa_hits=fts,integrity_check='ok',before_sha256=digest(BACK),after_sha256=digest(DB),text_content='Retained original index chunks; source membership aligned to final consensus release',original_pdfs_moved=False,api_requests=0,historical_run_outputs_modified=False,archived_zip_modified=False)
(AUD/'RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'CURRENT_LIBRARY_ALIGNMENT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False));print('audit',AUD)
