# Research

## Questions
- Cuantas paginas reales hay en priority_pages (48 vs 97)?
- Que patrones HTML contienen terminos + definiciones (tablas, negritas, frases tipo "Se entiende por")?
- Que categoria usar para nuevos terminos (regulatory vs regulatory_report)?

## Findings
- priority_pages tiene 48 archivos; el JSON anexo36_priority_pages.json tambien lista 48 entradas con page_number maximo 97 (no hay 97 archivos).
- priority_pages contiene HTML con tablas tipo indice (page_0001) y texto narrativo con codigos en negritas (page_0056, page_0057).
- anexo36_terms.json contiene 61 report codes con category=regulatory_report y source_refs en formato doc:Anexo_36_page_N.
- consolidate_anexo36.py genera term_id con md5; en report codes usa el codigo como input al hash.
- El HTML incluye <p>/<b> y tablas que se pueden mapear a terminos y definiciones con heuristicas.

## References
- plugins/bank-advisor-private/data/results/anexo36_extraction/priority_pages/page_0001.json
- plugins/bank-advisor-private/data/results/anexo36_extraction/priority_pages/page_0056.json
- plugins/bank-advisor-private/data/results/anexo36_extraction/priority_pages/page_0057.json
- plugins/bank-advisor-private/scripts/consolidate_anexo36.py
- plugins/bank-advisor-private/data/results/anexo36_extraction/anexo36_terms.json
