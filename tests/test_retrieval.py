from sagasmith_core.retrieval import enrich_query

from sagasmith_coc.retrieval import COC7E_QUERY_HINTS


def test_coc_query_hints_restore_system_vocabulary_outside_core() -> None:
    enriched = enrich_query("理智检定与追逐", extra_terms=COC7E_QUERY_HINTS)

    assert "sanity" in enriched
    assert "check" in enriched
    assert "chase" in enriched
