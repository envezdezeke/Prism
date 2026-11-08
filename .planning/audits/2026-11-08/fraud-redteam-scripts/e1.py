import sys; sys.path.insert(0,'.')
from harness import *
b=make_baseline()
ring=lambda **kw: {**dict(preparer=['K. Delacroix'],phone=['(214) 555-0187'],registered_agent=['Commerce Street Agent Services'],
        vendor=['Metroplex Equipment Supply LLC'],remit_account=['4471'],pdf_producer=['DocuForge 2.1 (Windows)'],bank=['First Lakes Bank']),**kw}
D=dep(8,1.0,'Mon,Thu')
def run(label, **kw):
    st={'R1':state('R1',ring(guarantor=['Ann A'],address=['1 Main St'],**kw),D),'R2':state('R2',ring(guarantor=['Bob B'],address=['2 Oak St'],**kw),D)}
    print(label, verdict(signals(b,st)))
run('sample-like baseline')
# drop each signal
for k in ['vendor','remit_account','pdf_producer','preparer','phone','registered_agent']:
    st={'R1':state('R1',{**ring(guarantor=['Ann A'],address=['1 Main St']),},D)}
    kw={}
for drop in ['vendor','remit_account','pdf_producer','preparer','phone','registered_agent']:
    e1=ring(guarantor=['Ann A'],address=['1 Main St']);e2=ring(guarantor=['Bob B'],address=['2 Oak St'])
    e1.pop(drop);e2.pop(drop)
    print('no',drop, verdict(signals(b,{'R1':state('R1',e1,D),'R2':state('R2',e2,D)})))
# R1 alone (first current ring deal; links to history ring only)
print('R1 alone', verdict(signals(b,{'R1':state('R1',ring(guarantor=['Ann A'],address=['1 Main St']),D)})))
# R1 alone no deposits
print('R1 alone, normal deposits', verdict(signals(b,{'R1':state('R1',ring(guarantor=['Ann A'],address=['1 Main St']),dep())})))
# R1 alone, deposits not yet arrived (only 1 statement)
print('R1 alone, 1 month stmt', verdict(signals(b,{'R1':state('R1',ring(guarantor=['Ann A'],address=['1 Main St']),dep(months=1,count=8,round_=1.0,days='Mon,Thu'))})))
