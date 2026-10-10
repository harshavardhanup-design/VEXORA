from dataclasses import dataclass

try:
    import psutil
    try:
        psutil.cpu_percent(interval=None)  # prime: the first call is meaningless (always 0.0)
    except Exception:
        pass
except ImportError:
    psutil = None

@dataclass
class Snapshot:
    cpu: float
    ram: float
    disk: float
    battery: float|None
    charging: bool

class PcHealth:
    def snapshot(self):
        if psutil is None:
            return Snapshot(0.0, 0.0, 0.0, None, False)
        try: cpu=psutil.cpu_percent(interval=None)
        except Exception: cpu=0
        try: ram=psutil.virtual_memory().percent
        except Exception: ram=0
        try:
            root=__import__('os').path.abspath(__import__('os').sep)
            disk=psutil.disk_usage(root).percent
        except Exception: disk=0
        try: b=psutil.sensors_battery()
        except Exception: b=None
        return Snapshot(cpu,ram,disk,None if b is None else b.percent,False if b is None else bool(b.power_plugged))
    def top_memory(self, limit=6):
        rows=[]
        try:
            for p in psutil.process_iter(['pid','name','memory_percent']):
                try: rows.append((p.info['name'] or 'Unknown', p.info['pid'], float(p.info['memory_percent'] or 0)))
                except Exception: pass
        except Exception: pass
        return sorted(rows,key=lambda x:x[2],reverse=True)[:limit]
    def running(self, limit=10):
        rows=[]
        try:
            for p in psutil.process_iter(['pid','name']): rows.append((p.info['name'] or 'Unknown',p.info['pid']))
        except Exception: pass
        return rows[:limit]
