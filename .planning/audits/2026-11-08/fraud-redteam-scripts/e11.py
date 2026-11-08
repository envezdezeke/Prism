import sys; sys.path.insert(0,'.')
from harness import *
from prism.fraud.baseline import DealProfile
from prism.fraud.signals import score_f3, _modal_form
from prism.fraud.canon import split_legal_suffix
b=make_baseline(); cal=b.calibration; p=b.params
print('tau F3',cal.tau['F3'], 'groups', len(b.vendor_groups()))
for base,g in b.vendor_groups().items():
    modal=_modal_form(list(g.members)); suf=split_legal_suffix(modal[0]).suffix
    newsuf='llc' if suf!='llc' else 'inc'
    for label,vend,acct in [('suffix swap, modal acct',f'{base} {newsuf}',modal[1]),('exact name, NEW acct',modal[0],'7777'),('typo name(1 edit)',base[:-1]+'x'+' '+suf,modal[1])]:
        prof=DealProfile('x',{'vendor':(vend,),'remit_account':(acct,)} if acct else {'vendor':(vend,)})
        f=score_f3(prof,b,p)
        print(f'{base:28s} n={len(g.members):2d} modal={modal} {label:26s}', 'bits=%.2f fires=%s'%(f.bits,f.bits>=cal.tau['F3']) if f else 'None')
