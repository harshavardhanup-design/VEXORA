from pathlib import Path
from datetime import datetime
import os

HOME = Path.home()


def recent_files(limit=10):
    roots = [HOME/'Desktop', HOME/'Documents', HOME/'Downloads']
    rows=[]
    for root in roots:
        try:
            with os.scandir(root) as it:
                for entry in it:
                    if entry.is_file(follow_symlinks=False):
                        try: rows.append((entry.stat(follow_symlinks=False).st_mtime, Path(entry.path)))
                        except OSError: pass
        except OSError: pass
    rows.sort(key=lambda x:x[0], reverse=True)
    return rows[:limit]


def workday_summary(tasks):
    active=[t.get('title','').strip() for t in tasks if not t.get('done') and t.get('title','').strip()]
    done=sum(1 for t in tasks if t.get('done'))
    if active:
        lines=["Today's work focus", "", f"1. {active[0]}"]
        if len(active)>1: lines.append(f"2. {active[1]}")
        if len(active)>2: lines.append(f"3. {active[2]}")
        lines += ["", f"Active tasks: {len(active)} • Completed: {done}", "Finish the first concrete outcome before switching context."]
    else:
        lines=["Today's work focus", "", "1. Choose one concrete outcome.", "2. Create it as a task.", "3. Work in one focused block and review before switching.", "", f"Completed: {done}"]
    return '\n'.join(lines)
