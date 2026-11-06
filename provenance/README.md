# Historical index preparation

These files document the preparation chain associated with the frozen hypothesis-agent release. Their contents are preserved byte for byte from local source scripts; filename date suffixes have been removed for readability; `SCRIPTS_SHA256.json` records their origins by basename and SHA-256. No scripts in this directory were executed while adding them to the release.

## Which script should a reader use?

Use [`../engine/build_library.py`](../engine/build_library.py) to create a compatible local index for **new analyses** from PDFs you have obtained lawfully. It accepts `--source-dir` and `--output-dir`. See the root README for installation, extraction settings and a minimal integration check.

The archival scripts below explain historical transformations. They are **not** a turnkey reconstruction of the exact frozen SQLite file from DOI lists alone. They require earlier local assets, source catalogs and, in several cases, a pre-existing index. Original filesystem paths have intentionally not been rewritten as if they were portable public inputs.

## Preparation chain

| Script | Role | Required inputs and effects |
| --- | --- | --- |
| `../engine/build_library.py` | Original PDF ingestion/index construction | Native PDF text extraction, SHA-256 deduplication, page-local overlapping chunks, SQLite FTS5 and verified working PDF copies. No API calls. |
| `scripts/align_existing_hypothesis_library.py` | Align an existing historical index to the earlier consensus collections | Requires the historical index, `documents.csv` and system `library.json`; keeps existing chunks, removes excluded papers, adds membership records and replaces the active index after backing it up. Earlier counts were 1,991/399, not the final 1,988/395. |
| `scripts/prepare_indexed_pdf_move.py` | Prepare historical PDF relocation | Requires the aligned index and original local PDFs; writes a move plan. It does not itself move the PDFs. |
| `scripts/finish_indexed_pdf_move.py` | Verify completed relocation and update paths | Requires the recorded move plan and already-relocated PDFs, verifies hashes, backs up the index and updates PDF/provenance paths. It does not perform the missing physical move step itself. |
| `scripts/consensus_input_adapter.py` | Normalize upstream consensus statistics | Requires a separate consensus release and earlier hypothesis inputs; produces statistics and validation records. The current archived setup adapts this script in memory for the final release layout/counts. |
| `scripts/setup_reviewed_triplicate.py` | Prepare final reviewed inputs and three isolated engines | Requires the preceding hypothesis engine/index, final `reviewed_11_5` consensus outputs, actual `PDF_database/LIB_1988` and `LIB_395` files and the adapter above. Matches PDFs by hash, reuses unchanged text, re-extracts changed identities, removes excluded records and copies prepared inputs into three independent engines. It does not perform hypothesis-generation inference. |

The released reference run is `reviewed_gpt54_repeat1`. Its final corpus validation records 2,383 memberships, 2,291 PDF-hash records and 131,045 text chunks. The final preparation script applies different extraction/chunk-ID rules for changed identities than the original builder; this is one reason a clean native-text build cannot be assumed to match historical quotation offsets or database bytes.

## Before adapting historical scripts

1. Inspect source code and replace historical paths in a **working copy**. Several scripts have top-level side effects and no command-line interface: do not import them merely to inspect functions.
2. Obtain the required upstream catalogs, prior index/engine and PDF versions. DOI lists identify publications but do not specify exact historical PDF bytes or the complete intervening extraction history.
3. Preserve the frozen results and original index. Use a separate clone and new destination directories. The alignment/setup scripts modify database membership, paths and output directories; the finish script also updates historical JSON metadata.
4. Install the root environment. PyMuPDF supplies both the `pymupdf` import used by the builder and the historical `fitz` import used in changed-PDF extraction. The other imports in these archived scripts are Python standard-library modules.
5. Compare corpus membership, PDF hashes, chunk counts, extraction versions and quotation offsets. Do not edit the frozen manifest to make a different build pass.

These source scripts do not supply third-party PDFs or permission to redistribute extracted full text. Native extraction and an unchanged model name do not guarantee reproduction of historical scientific responses. The root README distinguishes output inspection, exact frozen verification and new inference.
