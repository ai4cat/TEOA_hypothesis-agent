import pathlib,sqlite3,json,hashlib,collections
r=pathlib.Path(r'E:\Paper\4.TEOA\test0_gpt54_triplicate_20261103\engine\library');audit=pathlib.Path((r/'PENDING_PDF_MOVE.txt').read_text(encoding='utf-8'));plan=json.loads((audit/'MOVE_PLAN.json').read_text(encoding='utf-8'))
for x in plan:
 p=pathlib.Path(x['destination']);assert p.is_file() and p.stat().st_size==x['bytes'] and not pathlib.Path(x['source']).exists()
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 assert h.hexdigest()==x['sha256'],str(p)
c=sqlite3.connect(r/'index.sqlite');b=sqlite3.connect(audit/'index.before_pdf_path_update.sqlite');c.backup(b);b.close()
c.execute('create table if not exists pdf_relocation(paper_id TEXT PRIMARY KEY,previous_path TEXT,current_path TEXT)')
for x in plan:
 c.execute('update papers set path=? where paper_id=?',(x['destination'],x['paper_id']));c.execute('insert into pdf_relocation values(?,?,?)',(x['paper_id'],x['source'],x['destination']))
 for g,doc in c.execute('select library,source_doc_id from corpus_membership where paper_id=?',(x['paper_id'],)).fetchall():
  p=r/g/(doc+'.json');d=json.loads(p.read_text(encoding='utf-8'));d['paper']['path']=x['destination'];d['current_pdf_path']=x['destination'];p.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
c.commit();assert c.execute('pragma integrity_check').fetchone()[0]=='ok';assert all(pathlib.Path(x[0]).is_file() for x in c.execute('select path from papers'));c.close()
report=dict(status='moved_and_hash_verified',moved_files=len(plan),physical_pdf_counts=dict(collections.Counter(x['library'] for x in plan)),shared_memberships=95,shared_file_location='lib1; lib2 text JSON points to same PDF',bytes_moved=sum(x['bytes'] for x in plan),copied_pdf_files=0,source_files_remaining=0,sha256_checks_passed=len(plan),index_paths_updated=True,audit_directory=str(audit))
(audit/'RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');(r/'PDF_LOCATIONS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
p=r/'README.md';p.write_text(p.read_text(encoding='utf-8')+'\nPDF relocation: the 2,295 indexed PDFs were moved (not copied) into lib1/ (1,991) and lib2/ (304). The 95 shared PDFs reside in lib1 and are referenced by both corpus memberships. papers.path and exported text JSON metadata now point to the new PDF paths. Original provenance paths remain historical. See PDF_LOCATIONS.json and the PDF move audit.\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
