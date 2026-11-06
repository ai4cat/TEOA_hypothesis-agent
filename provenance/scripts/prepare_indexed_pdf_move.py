import pathlib,sqlite3,json,datetime,hashlib
r=pathlib.Path(r'E:\Paper\4.TEOA\test0_gpt54_triplicate_20261103\engine\library');c=sqlite3.connect((r/'index.sqlite').as_uri()+'?mode=ro',uri=True)
out=r/('pdf_move_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir();rows=[]
for pid,sha,src in c.execute('select paper_id,sha256,path from papers order by paper_id'):
 groups=[x[0] for x in c.execute('select library from corpus_membership where paper_id=?',(pid,))];group='lib1' if 'lib1' in groups else 'lib2'
 source=pathlib.Path(src).resolve(strict=True);dest=(r/group/(pid+'.pdf')).resolve()
 assert source.is_relative_to(pathlib.Path(r'E:\Paper\4.TEOA').resolve())
 assert dest.is_relative_to(r.resolve()) and not dest.exists()
 rows.append(dict(paper_id=pid,sha256=sha,source=str(source),destination=str(dest),library=group,memberships=groups,bytes=source.stat().st_size))
assert len(rows)==2295
(out/'MOVE_PLAN.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(r/'PENDING_PDF_MOVE.txt').write_text(str(out),encoding='utf-8')
print('files',len(rows),'bytes',sum(x['bytes'] for x in rows));print(out)
