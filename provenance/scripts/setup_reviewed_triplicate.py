"""Prepare three independent engines using reviewed statistics and PDF-verified index text."""
import concurrent.futures, csv, hashlib, json, pathlib, re, shutil, sqlite3, subprocess, sys

BASE = pathlib.Path(r'C:\Users\dell\Nutstore\1\1.Paper\11-12_AI_photocatalyst\2.Paper2\5.agent\0.for submit')
SOURCE = BASE/'reviewed_11_5'
OLD = pathlib.Path(r'E:\Paper\4.TEOA\hypothesis_agent_ponytail_20261104\engine')
ROOT = pathlib.Path(r'E:\Paper\4.TEOA\reviewed_gpt54_triplicate_20261105')
PYTHON = pathlib.Path(r'E:\Paper\4.TEOA\agent_teoa_prompt_v2\.venv\Scripts\python.exe')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def rows(path):
    return list(csv.DictReader(line for line in path.open(encoding='utf-8-sig',newline='') if not line.startswith('#')))

def main():
    ROOT.mkdir(exist_ok=True)
    assert not (ROOT/'PRELAUNCH_VERIFICATION.json').exists(), 'Preparation already complete'
    common=ROOT/'shared_inputs'
    # Reuse the existing normalization, changing only source paths and current counts/schema.
    adapter=pathlib.Path(r'E:\Paper\4.TEOA\consensus_input_adapter_20261103.py').read_text(encoding='utf-8')
    replacements={
        'outputs/01_entity_statistics/':'outputs/03_entity/',
        'outputs/02_claim_ranking/':'outputs/11_ranking/',
        'outputs/03_systems399/':'outputs/12_systems/statistics/',
        'outputs/04_intermediates/claims/':'outputs/04_claims/',
        'len(themes) == 51':'len(themes) == 28',
        "selected_claim['PI_unrounded']":"selected_claim['PI_unrounded']",
        '1991':'1988','399-document':'395-document','separate 399':'separate 395',
        "== '69'":"== '190'","== '119'":"== '37'",
    }
    for a,b in replacements.items():adapter=adapter.replace(a,b)
    # The historical comparison is only a preview reference; do not read historical run data.
    start=adapter.index("    old = read_json(ENGINE / 'app/runs/")
    end=adapter.index('    checks = dict(',start)
    adapter=adapter[:start]+"    old = {'summary': {'body_document_count':1991,'theme_count':51,'selected_theme_id':'C_af620528'},'rankings':{'platform':[{'doc_count':119}]}}\n"+adapter[end:]
    script=ROOT/'normalize_statistics.py';script.write_text(adapter,encoding='utf-8')
    namespace={'__name__':'normalizer'};exec(compile(adapter,str(script),'exec'),namespace)
    namespace.update(SOURCE=SOURCE,ENGINE=OLD,DEST=common,STATS=common/'statistics/verified_results')
    if not common.exists():namespace['main']()
    else:
        for item in json.loads((common/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))['inputs']:
            assert sha(SOURCE/item['path'])==item['sha256'],'Statistics changed during preparation'
    idx=common/'index.sqlite';shutil.copy2(OLD/'library/index.sqlite',idx)
    db=sqlite3.connect(idx)
    memberships=[];identity_changes=[]
    all_indexed={digest:pid for pid,digest in db.execute('select paper_id,sha256 from papers')}
    cachepath=common/'PDF_HASH_CACHE.jsonl'
    cache={item['path']:item for item in (json.loads(line) for line in cachepath.read_text(encoding='utf-8').splitlines())} if cachepath.exists() else {}
    for lib,manifest,folder in [('lib1',SOURCE/'outputs/01_corpus/documents.csv','LIB_1988'),('lib2',SOURCE/'inputs/03_platform_documents/catalog.csv','LIB_395')]:
        ids={r['doc_id'] for r in rows(manifest)}
        pdfs={p.stem:p for p in (BASE/'PDF_database'/folder/'pdfs').rglob('*.pdf')}
        assert ids==set(pdfs),(lib,'PDF membership mismatch')
        indexed={doc:(pid,digest) for doc,pid,digest in db.execute('select m.source_doc_id,m.paper_id,p.sha256 from corpus_membership m join papers p using(paper_id) where library=?',(lib,))}
        assert ids<=set(indexed),(lib,'Source not indexed')
        digests={}
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool, cachepath.open('a',encoding='utf-8') as log:
            futures={}
            for doc in sorted(ids):
                p=pdfs[doc];stat=p.stat();cached=cache.get(str(p))
                if cached and cached['bytes']==stat.st_size and cached['mtime_ns']==stat.st_mtime_ns:digests[doc]=cached['sha256']
                else:futures[pool.submit(sha,p)]=(doc,p,stat)
            for future in concurrent.futures.as_completed(futures):
                doc,p,stat=futures[future];digest=future.result();digests[doc]=digest
                log.write(json.dumps(dict(path=str(p),bytes=stat.st_size,mtime_ns=stat.st_mtime_ns,sha256=digest))+'\n');log.flush()
            print('PDF hashes complete:',lib,len(digests),flush=True)
        for doc in sorted(ids):
            pid,digest=indexed[doc]
            if digests[doc]!=digest:
                old_pid=pid;digest=digests[doc];pid=all_indexed.get(digest,'P_'+digest)
                if digest not in all_indexed:
                    import fitz
                    with fitz.open(pdfs[doc]) as pdf:
                        pages=[page.get_text() for page in pdf]
                    assert any(text.strip() for text in pages),(lib,doc,'PDF has no extractable text')
                    dois=sorted(set(re.findall(r'10\.\d{4,9}/[^\s<>"\\]+','\n'.join(pages)[:15000])))
                    db.execute('insert into papers values(?,?,?,?,?,?,?)',(pid,digest,str(pdfs[doc]),len(pages),json.dumps(dois),'','text_extracted'))
                    db.execute('insert into provenance values(?,?,?)',(pid,str(pdfs[doc]),'current PDF identity re-extracted'))
                    for page,text in enumerate(pages,1):
                        for start in range(0,len(text),1600):
                            value=text[start:start+1600]
                            if not value.strip():continue
                            cid=pid+f':p{page}:{start}'
                            db.execute('insert into chunks values(?,?,?,?)',(cid,pid,page,value));db.execute('insert into search values(?,?,?)',(cid,pid,value))
                    all_indexed[digest]=pid
                db.execute('update corpus_membership set paper_id=?,match_method=? where library=? and source_doc_id=?',(pid,'current_pdf_sha256',lib,doc))
                identity_changes.append(dict(library=lib,doc_id=doc,old_paper_id=old_pid,current_paper_id=pid))
            memberships.append(dict(library=lib,source_doc_id=doc,paper_id=pid,pdf_path=str(pdfs[doc]),sha256=digest))
        db.executemany('delete from corpus_membership where library=? and source_doc_id=?',[(lib,doc) for doc in set(indexed)-ids])
    for item in memberships:
        db.execute('update corpus_membership set local_pdf_path=?,local_text_path=NULL where library=? and source_doc_id=?',(item['pdf_path'],item['library'],item['source_doc_id']))
        db.execute('update papers set path=? where paper_id=?',(item['pdf_path'],item['paper_id']))
    for table in ['search','chunks','provenance','pdf_relocation','papers']:
        db.execute(f'delete from {table} where paper_id not in (select paper_id from corpus_membership)')
    db.execute('delete from pdf_relocation')
    db.execute('update provenance set original_path=(select path from papers where papers.paper_id=provenance.paper_id)')
    db.commit()
    assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
    assert db.execute('select count(*) from papers where paper_id not in (select paper_id from chunks)').fetchone()[0]==0
    assert db.execute('select count(*) from search').fetchone()[0]==db.execute('select count(*) from chunks').fetchone()[0]
    validation=dict(lib1=1988,lib2=395,pdf_files_verified=len(memberships),paper_records=db.execute('select count(*) from papers').fetchone()[0],text_chunks=db.execute('select count(*) from chunks').fetchone()[0],all_pdf_sha256_match=True,identity_changes=identity_changes,source=str(BASE/'PDF_database'),index_text='Existing text reused only for byte-identical PDFs; changed identities re-matched or re-extracted; excluded memberships and orphan records removed.')
    db.close();save(common/'PDF_MEMBERSHIP_SHA256.json',memberships);save(common/'LIBRARY_VALIDATION.json',validation)
    expected={}
    for n in [1,2,3]:
        engine=ROOT/f'test{n}/engine';engine.mkdir(parents=True)
        for f in OLD.glob('*.py'):shutil.copy2(f,engine/f.name)
        shutil.copy2(OLD/'requirements.txt',engine/'requirements.txt')
        (engine/'app/runs').mkdir(parents=True)
        for f in (OLD/'app').glob('*.py'):shutil.copy2(f,engine/'app'/f.name)
        shutil.copytree(OLD/'app/spec',engine/'app/spec')
        shutil.copytree(common/'statistics',engine/'statistics')
        shutil.copy2(common/'SOURCE_MANIFEST.json',engine/'statistics/SOURCE_MANIFEST.json')
        (engine/'library').mkdir();shutil.copy2(idx,engine/'library/index.sqlite');shutil.copy2(common/'LIBRARY_VALIDATION.json',engine/'library/LIBRARY_VALIDATION.json')
        run=engine/'app/runs'/f'reviewed_gpt54_repeat{n}';run.mkdir()
        config=json.loads((engine/'app/spec/runtime.json').read_text(encoding='utf-8'))
        config.update(budget_authorization='User authorized three independent parallel end-to-end runs to frozen results on 2026-11-05; same provider and settings.',auto_reconnect=True)
        save(engine/'app/spec/runtime.json',config);save(run/'runtime.json',config)
        save(engine/'app/latest.json',dict(path='runs/'+run.name))
        fingerprints={str(p.relative_to(engine)):sha(p) for p in engine.rglob('*') if p.is_file() and 'runs' not in p.parts and p.suffix in {'.py','.txt','.csv','.sqlite'}}
        if expected:assert expected==fingerprints,'Independent engine copies differ'
        else:expected=fingerprints
    save(ROOT/'PRELAUNCH_VERIFICATION.json',dict(model='gpt-5.4',parallel_runs=3,independent_indices=True,independent_caches=True,source_code=str(OLD),prompt_sha256=sha(OLD/'app/spec/research_prompt.txt'),library=validation,equivalent_file_hashes=expected,historical_runs_copied=False))
    print(json.dumps(validation),flush=True)

if __name__=='__main__':main()
