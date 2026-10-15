"""Official field thresholds in milliseconds, except unitless CLS."""
import math
LIMITS={'LCP':(2500,4000),'INP':(200,500),'CLS':(0.1,0.25)}

def rating(metric,value):
    if type(value) not in {int,float} or not math.isfinite(value) or value<0:return 'unknown'
    if metric not in LIMITS:return 'supplementary'
    good,poor=LIMITS[metric]
    return 'good' if value<=good else 'needs_improvement' if value<=poor else 'poor'

def assess_field(values,policy='strict'):
    if policy not in {'strict','psi'}:raise ValueError('unknown_assessment_policy')
    ratings={k:rating(k,values.get(k)) for k in LIMITS};complete=all(v!='unknown' for v in ratings.values())
    if ratings['LCP']=='unknown' or ratings['CLS']=='unknown':status='insufficient_data'
    elif ratings['INP']=='unknown':
        status='pass_inp_unavailable' if policy=='psi' and ratings['LCP']==ratings['CLS']=='good' else 'not_pass' if policy=='psi' else 'insufficient_data'
    else:status='pass' if all(v=='good' for v in ratings.values()) else 'not_pass'
    return {'assessment':status,'all_three_observed':complete,'ratings':ratings,'policy':policy,'basis':'real_user_p75'}
