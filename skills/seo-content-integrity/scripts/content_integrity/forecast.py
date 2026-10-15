"""Check a forecast's own year/scenario statements, never its predictive accuracy."""
from .comparison import check_pair

MATCH = {'consistent', 'consistent_with_display_precision', 'within_configured_tolerance'}

def check_summary(table, summary, *, at, max_age_hours=24):
    result = {'status': 'insufficient_data', 'confirmed': False,
              'scope': 'internal forecast table-summary consistency; not forecast accuracy',
              'table': table, 'summary': summary, 'matching_other_years': []}
    year = summary.get('year')
    if type(year) is not int or summary.get('period')!=str(year) or summary.get('number', {}).get('status') != 'observed':
        return result
    candidates = []
    for row in table:
        if type(row.get('year')) is not int or row.get('period')!=str(row['year']) or row['year'] == year:
            continue
        # Deliberately ignore year only for a candidate-value lookup. Keep originals above.
        comparison = check_pair({**row, 'period': summary.get('period')}, summary, at=at,max_age_hours=max_age_hours)
        if comparison['status'] in MATCH:
            candidates.append(row['year'])
    result['matching_other_years'] = sorted(set(candidates))
    rows = [row for row in table if row.get('year') == year and type(row.get('year')) is int and row.get('period')==str(year)]
    if not rows:
        return {**result, 'status': 'possible_year_shift' if len(set(candidates)) == 1 else 'summary_year_not_covered'}
    # A year with multiple rows must be unambiguous in both semantics and value.
    if any(check_pair(rows[0], row, at=at,max_age_hours=max_age_hours)['status'] not in MATCH for row in rows[1:]):
        return {**result, 'status': 'ambiguous_table'}
    comparison = check_pair(rows[0], summary, at=at,max_age_hours=max_age_hours)
    status = comparison['status']
    if status in MATCH:
        status = 'consistent'
    elif status == 'conflict':
        status = 'year_value_conflict'
    return {**result, 'status': status, 'confirmed': status == 'year_value_conflict', 'comparison': comparison}
