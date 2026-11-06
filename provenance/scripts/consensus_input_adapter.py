"""Offline normalization of final consensus outputs for the hypothesis reader."""
import csv
import hashlib
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

SOURCE = Path(r'C:\Users\dell\Nutstore\1\1.Paper\11-12_AI_photocatalyst\2.Paper2\5.agent\0.for submit\Research-English-release_20261102_final\Research-English-release-v1.0.1_20261030')
ENGINE = Path(r'E:\Paper\4.TEOA\test0_gpt54_triplicate_20261103\engine')
DEST = Path(r'E:\Paper\4.TEOA\consensus_to_hypothesis_inputs_20261103_v1')
STATS = DEST / 'statistics/verified_results'

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def read_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(line for line in stream if not line.startswith('#')))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def write_rows(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def main():
    if DEST.exists():
        raise RuntimeError('Destination exists; do not overwrite an inspected input version.')
    source_files = {
        'entity_selection': 'outputs/01_entity_statistics/entity_selection.json',
        'entity_ranking': 'outputs/01_entity_statistics/entity_ranking.csv',
        'selected_claim': 'outputs/02_claim_ranking/selected_claim.json',
        'themes_ranking': 'outputs/02_claim_ranking/themes_ranking.csv',
        'system_summary': 'outputs/03_systems399/summary.json',
        'photo_centers': 'outputs/03_systems399/photocatalytic_co2_center_ranking.csv',
        'all_metal_centers': 'outputs/03_systems399/metal_center_ranking.csv',
        'raw_claims': 'outputs/04_intermediates/claims/01_raw_claim_candidates.csv',
    }
    source_hashes = {key: sha(SOURCE / rel) for key, rel in source_files.items()}
    entities = read_rows(SOURCE / source_files['entity_ranking'])
    themes = read_rows(SOURCE / source_files['themes_ranking'])
    photo = read_rows(SOURCE / source_files['photo_centers'])
    metals = read_rows(SOURCE / source_files['all_metal_centers'])
    claims = read_rows(SOURCE / source_files['raw_claims'])
    selection = read_json(SOURCE / source_files['entity_selection'])
    selected_claim = read_json(SOURCE / source_files['selected_claim'])
    systems = read_json(SOURCE / source_files['system_summary'])
    assert len(entities) == 10 and len(themes) == 51
    assert selection['document_count'] == 1991
    assert themes[0]['consensus_claim_id'] == selected_claim['consensus_claim_id']
    for row in themes:
        pi = Fraction(int(row['df'])) * (1 - Fraction(row['mean_evidence_exact']) / 3) * Fraction(row['top_impact_exact']) / 4
        assert pi == Fraction(row['full_PI_exact'])
    ratio = float(Fraction(themes[0]['full_PI_exact']) / Fraction(themes[1]['full_PI_exact']))
    entity_rows = [dict(id='entity:' + re.sub(r'[^a-z0-9]+', '_', row['entity_name'].lower()).strip('_'),
                        name=row['entity_name'], doc_count=int(row['chunk_doc_count']), rank=int(row['rank']),
                        mentions=int(row['chunk_mentions']), aliases=row['aliases']) for row in entities]
    theme_rows = [dict(id=row['consensus_claim_id'], name=row['consensus_claim_text'],
                       doc_count=int(row['df']), rank=int(row['rank']), member_count=int(row['raw_member_count']),
                       mean_evidence=float(row['mean_evidence']), top_impact_mean=float(row['top_impact_mean']),
                       priority_index=float(Fraction(row['full_PI_exact']))) for row in themes]
    center_rows = [dict(id='center:' + row['element'], name=row['element'] + ' catalytic-center element label',
                        doc_count=int(row['documents']), rank=int(row['rank']),
                        scope='photocatalytic CO2 subset of 399-document systems corpus') for row in photo]
    cobalt = next(row for row in metals if row['element'] == 'Co')
    summary = dict(
        schema='hypothesis_statistics_input.final_consensus.v1',
        body_paragraph_count=selection['body_paragraphs'], body_document_count=selection['document_count'],
        selected_entity_id=entity_rows[0]['id'], candidate_count=len(entity_rows),
        theme_count=len(theme_rows), selected_theme_id=theme_rows[0]['id'],
        platform_category_count=len(center_rows), platform_document_count=systems['documents'],
        selected_platform_id=center_rows[0]['id'], pi_top_to_second_ratio=ratio,
        entity_selection_method=selection['method'],
        entity_selection_rule=selection['ranking_rule'],
        entity_statistics=[dict(id=x['id'], name=x['name'], rank=x['rank'], mentions=x['mentions'], document_count=x['doc_count']) for x in entity_rows],
        selected_claim=dict(claim_id=selected_claim['consensus_claim_id'], text=selected_claim['consensus_claim_text'],
                            document_count=selected_claim['df'], member_count=selected_claim['raw_member_count'],
                            mean_evidence=selected_claim['mean_evidence'], mean_evidence_exact=selected_claim['mean_evidence_exact'],
                            top_impact_mean=selected_claim['top_impact_mean'], priority_index=selected_claim['PI_unrounded'],
                            formula='df * (1 - mean_evidence/3) * top_k_mean_impact/4'),
        raw_claim_count=len(claims), total_theme_memberships=sum(x['member_count'] for x in theme_rows),
        system_statistics=dict(corpus_documents=systems['documents'], model=systems['model'],
                               ranking_scope='photocatalytic CO2 subset',
                               cobalt_photo_co2_documents=center_rows[0]['doc_count'],
                               cobalt_all_documents=int(cobalt['documents']),
                               cobalt_authors_experiment_documents=int(cobalt['authors_experiment_documents'])),
        platform_scope='Element-center ranking, not ligand-defined or molecular-platform ranking. Co does not independently select Co-bpy. The published center table includes non-metal element labels.',
        corpus_relationship='Entity nomination and claim extraction share the 1991-document base; the systems corpus is a separate 399-document collection.',
        evidence_score_scope='Claim-specific evidence in the retained source context; the selected claim assigns an electron-donor/hole-scavenger function and does not assert that it is the only role.',
        numeric_results='Mapped from the final consensus release outputs; all theme priority indices independently checked using exact fractions.',
        upstream_status='Memberships and scores from the final consensus release, normalized for the hypothesis-generation reader.',
        comparator_status='Research brief supplies the Co-bpy context and preliminary TEA/TEOA comparison; statistics do not establish a mechanism.',
    )
    STATS.mkdir(parents=True)
    write_json(STATS / 'summary.json', summary)
    write_rows(STATS / 'entity_ranking.csv', entity_rows)
    write_rows(STATS / 'theme_ranking.csv', theme_rows)
    write_rows(STATS / 'platform_ranking.csv', center_rows)
    # Execute the unchanged reader, overriding only its input location in memory.
    sys.path.insert(0, str(ENGINE / 'app'))
    import workflow
    workflow.STATS = STATS
    model_input = workflow.stat_inputs()
    assert model_input['research_brief'] == (ENGINE / 'app/spec/research_prompt.txt').read_text(encoding='utf-8')
    assert len(model_input['rankings']['entity']) == 10
    assert len(model_input['rankings']['theme']) == 1
    assert len(model_input['rankings']['platform']) == 10
    assert all(set(row) == {'id', 'name', 'doc_count', 'rank'} for rows in model_input['rankings'].values() for row in rows)
    assert model_input['summary']['body_document_count'] == 1991
    assert model_input['rankings']['theme'][0]['doc_count'] == '69'
    assert model_input['rankings']['platform'][0]['doc_count'] == '119'
    write_json(DEST / 'preview/generation_inputs.preview.json', model_input)
    visible = {key: value for key, value in model_input.items() if key != 'research_brief'}
    write_json(DEST / 'preview/statistics_seen_by_model.json', visible)
    old = read_json(ENGINE / 'app/runs/test0_gpt54_repeat1/generation_inputs.json')
    checks = dict(offline_only=True, api_requests=0, original_reader_unchanged=True, original_research_prompt_unchanged=True,
                  old_to_new=dict(documents=[old['summary']['body_document_count'], summary['body_document_count']],
                                  themes=[old['summary']['theme_count'], summary['theme_count']],
                                  selected_claim=[old['summary']['selected_theme_id'], summary['selected_theme_id']],
                                  cobalt_count=[old['rankings']['platform'][0]['doc_count'], center_rows[0]['doc_count']]),
                  caution='Old Co count is a broad platform-category statistic; new Co count is an extracted element-center statistic in the photocatalytic CO2 subset. These are different scopes.',
                  reader_rows=dict(entities=10, themes=1, centers=10),
                  detailed_claim_rows_sent=False, full_theme_ranking_rows_on_disk=len(theme_rows))
    write_json(DEST / 'VALIDATION.json', checks)
    assert all(sha(SOURCE / rel) == source_hashes[key] for key, rel in source_files.items())
    write_json(DEST / 'SOURCE_MANIFEST.json', dict(source_release=str(SOURCE), inputs=[dict(role=key,path=rel,sha256=source_hashes[key]) for key,rel in source_files.items()],
        normalized_files=[dict(path=p.relative_to(DEST).as_posix(), sha256=sha(p)) for p in sorted(STATS.iterdir())]))
    write_json(DEST / 'DELIVERY_READINESS.json', dict(status='statistics_input_conversion_and_offline_preview_complete', new_inference_run_performed=False,
        old_five_runs_modified=False, ready_for_new_run=True,
        package_tasks=['Use a new engine working copy and a new run name.',
                       'Replace the old four normalized statistics files with these four files.',
                       'Do not copy old runs, old generation_inputs, old source manifests or frozen candidate outputs into the new run.',
                       'Replace the legacy statistics/evidence payloads and evidence_tools recomputation command with the final consensus release entry or an explicit source reference; the legacy command would regenerate old statistics.',
                       'Update default report/menu paths and documentation to the new run. Regenerate delivery manifests after new outputs are complete.']))
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print('Output: ' + str(DEST))

if __name__ == '__main__':
    main()
