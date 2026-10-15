"""Conservative host-load guard, not a CPU-utilization or quiet-machine certificate."""
import math,os

def assess_load(before,after,cpus,*,max_load_per_cpu=2.0):
    if type(max_load_per_cpu) not in {int,float} or not math.isfinite(max_load_per_cpu) or max_load_per_cpu<=0:raise ValueError('invalid_host_load_threshold')
    result={'status':'environment_data_missing','suitable_for_regression':False,'quiet_machine_proven':False,'max_load_per_cpu':None,'threshold':max_load_per_cpu,'load_before':before,'load_after':after,'cpu_count':cpus,'basis':'Engineering guard: 1-minute host load / logical CPU count. Load is not CPU utilization.'}
    if type(cpus) is not int or cpus<=0:return result
    values=[]
    for sample in [before,after]:
        if not isinstance(sample,(list,tuple)) or not sample:return result
        value=sample[0]
        if type(value) not in {int,float} or not math.isfinite(value) or value<0:return result
        values.append(value/cpus)
    ratio=max(values);high=ratio>max_load_per_cpu
    result.update(status='high_host_load' if high else 'no_high_load_detected',suitable_for_regression=not high,max_load_per_cpu=ratio);return result

def preflight(*,max_load_per_cpu=2.0):
    try:load=os.getloadavg()
    except (AttributeError,OSError):load=None
    return assess_load(load,load,os.cpu_count(),max_load_per_cpu=max_load_per_cpu)
