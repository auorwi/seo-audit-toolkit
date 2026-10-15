"""Small deterministic predicates on real captured JSON fields; no code execution."""
import json
OPS={'equals','in','contains','not_contains','nonempty'}
def evaluate(values,rule,*,complete_fields=()):
 field=rule['field'];op=rule['op'];expected=rule.get('expected')
 if not isinstance(field,str) or not field or op not in OPS:raise ValueError('invalid_predicate')
 try:json.dumps(expected,allow_nan=False)
 except (ValueError,TypeError):raise ValueError('invalid_expected_value')
 if op=='in' and (not isinstance(expected,list) or not expected):raise ValueError('expected_nonempty_list')
 if op in {'contains','not_contains'} and (not isinstance(expected,str) or not expected):raise ValueError('expected_nonempty_text')
 value=values.get(field);out={'field':field,'operator':op,'expected':expected,'observed':value,'status':'inconclusive','reason':'field_unavailable'}
 if value is None:return out
 if op=='equals':ok=type(value)==type(expected) and value==expected
 elif op=='in':ok=any(type(value)==type(x) and value==x for x in expected)
 elif op=='nonempty':
  if isinstance(value,str):ok=bool(value.strip())
  elif isinstance(value,list) and all(isinstance(v,str) for v in value):ok=any(v.strip() for v in value)
  else:out['reason']='unsupported_field_type';return out
 else:
  if not isinstance(value,str):out['reason']='unsupported_field_type';return out
  present=expected in value
  if op=='not_contains' and not present and field not in complete_fields:out['reason']='absence_requires_complete_field';return out
  ok=present if op=='contains' else not present
 out.update(status='passed' if ok else 'failed',reason='predicate_satisfied' if ok else 'predicate_not_satisfied');return out
