import sys; sys.path.insert(0,'.')
from harness import *
b=make_baseline()
BAD=dep(8,1.0,'Mon,Thu'); OK=dep()
def seq(label, deals):
    print('==',label)
    st={}
    for name,(ents,dp) in deals:
        st[name]=state(name,ents,dp)
        v=verdict(signals(b,st)); print('  after',name,'->',{k:v[k][0]+str(v[k][1]) for k in v})
base=lambda i,**kw: {**dict(guarantor=[f'Person {i}'],address=[f'{i} Elm St'],bank=['Trinity Commercial Bank']),**kw}
kit=dict(preparer=['Zed Quill'],phone=['469-555-0111'],registered_agent=['Quux Agents LLC'],pdf_producer=['FakeForge PDF 3.1'])
seq('A. full kit, equipment lookalike vendor, bad deposits, ring of 3, no history', [(f'R{i}',(base(i,**kit,vendor=['Riverbend Equipment Inc'],remit_account=['7777']),BAD)) for i in (1,2,3)])
seq('B. same but NEW (non-imitating) vendor name', [(f'R{i}',(base(i,**kit,vendor=['Zeta Works LLC'],remit_account=['7777']),BAD)) for i in (1,2,3)])
seq('C. non-equipment loan (no vendor), full kit + bad deposits', [(f'R{i}',(base(i,**kit),BAD)) for i in (1,2,3)])
seq('D. shared kit, normal-looking deposits (careful fraudster)', [(f'R{i}',(base(i,**kit,vendor=['Riverbend Equipment Inc'],remit_account=['7777']),OK)) for i in (1,2,3)])
seq('E. shared kit w/ light formatting variants in preparer/phone, bad deposits+lookalike', [('R1',(base(1,preparer=['Zed Quill, CPA'],phone=['469-555-0111'],vendor=['Riverbend Equipment Inc'],remit_account=['7777']),BAD)),('R2',(base(2,preparer=['Quill, Zed'],phone=['(469) 555-0111 x2'],vendor=['Riverbend Equipment Inc'],remit_account=['7777']),BAD))])
seq('F. ring where only the payout acct is shared (new), lookalike vendor, deposits normal', [(f'R{i}',(base(i,vendor=['Riverbend Equipment Inc'],remit_account=['7777'],preparer=[f'Prep {i}'],registered_agent=[f'Agent {i}']),OK)) for i in (1,2)])
seq('G. single fraudulent deal: lookalike vendor + bad deposits, nothing shared', [('S1',(base(1,vendor=['Riverbend Equipment Inc'],remit_account=['7777']),BAD))])
