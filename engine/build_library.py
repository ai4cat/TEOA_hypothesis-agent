"""Build an immutable, flat PDF library and page-grounded FTS index."""
from pathlib import Path
import hashlib, json, shutil, sqlite3, re, datetime, argparse
import pymupdf

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'lib'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,default=SOURCE)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'library')
    args=parser.parse_args();source=args.source_dir.resolve();output=args.output_dir.resolve()
    files=sorted(source.rglob('*.pdf'))
    if not files:raise SystemExit('No PDFs found in source directory.')
    pdfs=output/'pdf';pdfs.mkdir(parents=True,exist_ok=True)
    dbpath=output/'index.sqlite'
    if dbpath.exists():raise SystemExit('Index exists; do not overwrite an existing build.')
    db=sqlite3.connect(dbpath)
    db.executescript('CREATE TABLE papers(paper_id TEXT PRIMARY KEY,sha256 TEXT,path TEXT,pages INTEGER,doi_candidates TEXT,title_candidate TEXT,status TEXT); CREATE TABLE provenance(paper_id TEXT,original_path TEXT,curation TEXT); CREATE TABLE chunks(chunk_id TEXT PRIMARY KEY,paper_id TEXT,page INTEGER,text TEXT); CREATE VIRTUAL TABLE search USING fts5(chunk_id UNINDEXED,paper_id UNINDEXED,text, tokenize="unicode61");')
    seen={};counts=dict(input_pdfs=0,unique_pdfs=0,duplicate_files=0,parse_errors=0,empty_pages=0,pages=0,chunks=0);errors=[]
    for i,p in enumerate(files,1):
        digest=sha(p);pid='P_'+digest;counts['input_pdfs']+=1
        curation='researcher_selected_reference' if p.parent.name=='LIB3_5' else 'provided_corpus'
        db.execute('INSERT INTO provenance VALUES(?,?,?)',(pid,str(p),curation))
        if digest in seen:
            counts['duplicate_files']+=1
        else:
            seen[digest]=pid;target=pdfs/(pid+'.pdf')
            if target.exists():
                if sha(target)!=digest:raise RuntimeError('Existing file has conflicting content: '+str(target))
            else:shutil.copy2(p,target)
            if sha(target)!=digest:raise RuntimeError('Copy integrity failure: '+str(p))
            counts['unique_pdfs']+=1
            try:
                with pymupdf.open(target) as doc:
                    first='';pages=len(doc);title=(doc.metadata or {}).get('title','')
                    for page_index,page in enumerate(doc):
                        text=page.get_text(sort=True).replace('\x00','').strip()
                        if page_index<2:first+='\n'+text
                        counts['pages']+=1
                        if len(text)<40:counts['empty_pages']+=1
                        for start in range(0,len(text),1600):
                            chunk=text[start:start+2000]
                            if not chunk.strip():continue
                            cid=f'{pid}:p{page_index+1}:c{start//1600}'
                            db.execute('INSERT INTO chunks VALUES(?,?,?,?)',(cid,pid,page_index+1,chunk))
                            db.execute('INSERT INTO search VALUES(?,?,?)',(cid,pid,chunk));counts['chunks']+=1
                    dois=sorted(set(x.rstrip('.,;)') for x in re.findall(r'10\.\d{4,9}/[^\s<>]+',first,re.I)))
                    db.execute('INSERT INTO papers VALUES(?,?,?,?,?,?,?)',(pid,digest,str(target),pages,json.dumps(dois),title,'text_extracted'))
            except Exception as e:
                counts['parse_errors']+=1;errors.append(dict(paper_id=pid,error=str(e)))
                db.execute('INSERT OR REPLACE INTO papers VALUES(?,?,?,?,?,?,?)',(pid,digest,str(target),0,'[]','','parse_error'))
        if i%100==0:
            db.commit();print(json.dumps(dict(processed=i,total=len(files),**counts)),flush=True)
    db.commit();db.close()
    report=dict(completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),counts=counts,errors=errors,notes=['Exact-byte duplicates merged by SHA256. DOI candidates are unverified; different files of same article not yet merged.','All original files retained. Flat working copies verified by hash.','Native PDF text only; no OCR. Low-text pages require audit.','Chunk boundaries are page-local windows, not semantic paragraphs. Adjacent context must be checked.','Researcher-selected references retained in internal provenance; no ranking boost based on folder.'])
    (output/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
