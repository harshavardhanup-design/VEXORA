from dataclasses import dataclass
import os, time

@dataclass
class PerformanceReport:
    cpu: float
    ram: float
    disk: float
    processes: int
    top_memory: list


def snapshot():
    try:
        import psutil
        vm=psutil.virtual_memory(); du=psutil.disk_usage(os.path.abspath(os.sep))
        rows=[]
        process_count=0
        for p in psutil.process_iter(['pid','name','memory_percent']):
            process_count += 1
            try:
                m=float(p.info.get('memory_percent') or 0)
                if m>0: rows.append((p.info.get('name') or 'Unknown',p.info.get('pid'),m))
            except Exception: pass
        rows.sort(key=lambda x:x[2], reverse=True)
        return PerformanceReport(float(psutil.cpu_percent(interval=None)),float(vm.percent),float(du.percent),process_count,rows[:8])
    except Exception:
        return PerformanceReport(0.0,0.0,0.0,0,[])


def diagnose():
    s=snapshot(); findings=[]
    if s.ram>=85: findings.append('RAM usage is high; close or pause unnecessary memory-heavy apps.')
    elif s.ram>=70: findings.append('RAM usage is elevated; keep an eye on heavy applications.')
    if s.cpu>=90: findings.append('CPU usage is very high right now; check active workloads before troubleshooting.')
    if s.disk>=90: findings.append('Primary storage is nearly full; freeing space may improve reliability.')
    if not findings: findings.append('No obvious pressure signal was detected in this snapshot.')
    return s, findings
