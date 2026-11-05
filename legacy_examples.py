# A régi alkalmazás 24 példájának változatlan adatai
PELDÁK = []
for group, counts, stated in [
    ('A – EUR', (10,0,0), (4.0,2.0)),
    ('B – angol', (0,10,0), (5.0,2.5)),
    ('C – US', (0,0,10), (6.0,3.0)),
    ('D – vegyes', (12,4,0), (6.8,3.4)),
]:
    for i,h in enumerate((135,140,145)):
        for stacked in (False,True):
            n=2*i+int(stacked)+1
            # A levél D/3–D/6 példáiban 6 EUR + 4 angol szerepel
            current_counts=(6,4,0) if group.startswith('D') and i>0 else counts
            PELDÁK.append(dict(csoport=group,szam=n,eur=current_counts[0],angol=current_counts[1],us=current_counts[2],magassag=h,halmozhato=stacked,level_ldm=stated[int(stacked)]))
