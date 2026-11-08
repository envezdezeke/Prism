import sys; sys.path.insert(0,'.')
from harness import *
b=make_baseline()
def links(kind,a,c):
    st={'A':state('A',{kind:[a]}),'B':state('B',{kind:[c]})}
    s=[x for x in signals(b,st) if x.family=='F1' and x.deals[0]=='A' and 'B' in x.deals]
    return 'LINKED' if s else 'miss'
cases=[
 ('phone','(469) 555-0111','469.555.0111'),('phone','469-555-0111','+1 469 555 0111'),('phone','469-555-0111','469-555-0111 x12'),('phone','469-555-0111','1-469-555-0111'),
 ('phone','469-555-0111','4695550111 (cell)'),
 ('remit_account','4471','xxxx4471'),('remit_account','4471','****4471'),('remit_account','4471','Acct #4471'),('remit_account','4471','ending in 4471'),('remit_account','4471','44-71'),('remit_account','000123456789','6789'),('remit_account','4471','0004471'),
 ('preparer','K. Zorn','Zorn, K.'),('preparer','K. Zorn','K Zorn'),('preparer','K. Zorn','Karl Zorn'),('preparer','K. Zorn','K. Zorn, CPA'),('preparer','Karl Zorn, EA','KARL ZORN'),('preparer','Karl Zorn','Karl  Zorn Jr.'),('preparer','Karl Zorn','Karl Zorm'),('preparer','Karl Zorn','Karl Zorn & Associates'),
 ('registered_agent','Quux Agent Services','Quux Agent Svcs'),('registered_agent','Quux Agent Services LLC','Quux Agent Services'),('registered_agent','Quux Agent Services','The Quux Agent Services'),('registered_agent','Quux Agent Services','QUUX AGENT SERVICES, INC.'),
 ('address','12 Elm St Ste 100, Plano, TX 75023','12 Elm Street Suite 100, Plano TX 75023'),('address','12 Elm St Ste 100, Plano, TX 75023','12 Elm St #100, Plano, TX 75023'),('address','12 Elm St Ste 100, Plano, TX 75023','12 Elm St, Plano, TX 75023-1234'),('address','12 Elm St Ste 100, Plano, TX 75023','12 Elm St Ste 200, Plano, TX 75023'),
 ('address','12 N Elm St','12 North Elm Street'),('address','12 Elm Pkwy','12 Elm Parkway'),('address','PO Box 5','P.O. Box 5'),('address','12 Elm St Ste 100','100 Elm St Ste 12'),
 ('pdf_producer','FakeForge PDF 3.1','FakeForge PDF 3.2'),('pdf_producer','FakeForge PDF 3.1','fakeforge pdf 3.1'),
 ('guarantor','Maria Q Lopez','Maria Lopez'),('guarantor','Maria Q Lopez','Lopez, Maria Q.'),('guarantor','Jon Smyth','Jonathan Smyth'),
 ('bank','Zed National Bank','Zed Natl Bank'),
 ('vendor','Zeta Works LLC','Zeta Works, Inc.'),('vendor','Zeta Works LLC','Zeta Works L.L.C.'),('vendor','Zeta Works LLC','Zeta Wrks LLC'),
]
for k,a,c in cases: print(f'{k:17s} {a!r:42s} ~ {c!r:42s} {links(k,a,c)}')
