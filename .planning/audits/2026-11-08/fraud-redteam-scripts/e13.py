import sys; sys.path.insert(0,'.')
from harness import *
b=make_baseline()
BAD=dep(8,1.0,'Mon,Thu'); OK=dep()
base=lambda i,**kw: {**dict(guarantor=[f'Person {i}'],address=[f'{i} Elm St'],bank=['Trinity Commercial Bank']),**kw}
kit=dict(preparer=['Zed Quill'],phone=['469-555-0111'],registered_agent=['Quux Agents LLC'])
st={}
for n,(e,d) in {'R1':(base(1,**kit,vendor=['Cedar Equipment Inc'],remit_account=['7777']),BAD),
                'R2':(base(2,**kit,vendor=['Cedar Equipment Inc'],remit_account=['7777']),BAD),
                'R3':(base(3,**kit),OK)}.items():
    st[n]=state(n,e,d); v=verdict(signals(b,st)); print('after',n,{k:v[k][0]+str(v[k][1]) for k in v})
# honest siblings sharing a new bookkeeper, equipment loans from a recurring vendor, normal deposits
print('--- honest siblings (same new bookkeeper, recurring equipment vendor w/ own usual acct), normal deposits')
st={}
for i in (1,2,3):
    st[f'S{i}']=state(f'S{i}',base(i,preparer=['Bea Bookkeeper'],vendor=['Cedar Equipment Co'],remit_account=['4592']),OK)
v=verdict(signals(b,st)); print({k:v[k][0]+str(v[k][1]) for k in v})
