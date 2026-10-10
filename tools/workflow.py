from datetime import datetime

def build_workflow(tasks, recent=None):
    active=[t.get('title','').strip() for t in tasks if not t.get('done') and t.get('title','').strip()]
    steps=[]
    if active:
        steps.append(f'1. Focus: {active[0]}')
        if len(active)>1: steps.append(f'2. Next: {active[1]}')
        if len(active)>2: steps.append(f'3. Then: {active[2]}')
    else:
        steps=['1. Choose one concrete outcome.','2. Create it as a VEXORA task.','3. Work in one focused block.']
    if recent:
        names=[p.name for _,p in recent[:3]]
        steps.append('4. Recent work to review: ' + ', '.join(names))
    return "Today's workflow\n\n"+'\n'.join(steps)+"\n\nRule: finish the current concrete outcome before switching context."
