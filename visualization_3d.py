"""Interactive 3D view of the validated 2D footprint and individual stack layers."""
import html
import plotly.graph_objects as go
from visualization import szin


def terv_3d(terv):
    fig = go.Figure()
    groups = {c.index: c.csoport for c in terv.csoportok}
    # Combine boxes per group into a single mesh, avoiding thousands of traces.
    meshes = {}
    for e in terv.pakolas.elhelyezesek:
        g = groups[e.csoport]
        data = meshes.setdefault(e.csoport, dict(x=[], y=[], z=[], i=[], j=[], k=[], text=[]))
        for level in range(terv.halmok.get(e.sorszam, 1)):
            base = len(data['x'])
            for a,b,c in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]:
                data['x'].append(e.x_cm+a*e.hossz_cm)
                data['y'].append(e.y_cm+b*e.szelesseg_cm)
                data['z'].append((level+c)*g.magassag_cm)
                data['text'].append(f"{html.escape(g.nev)}<br>Hely: {e.sorszam}, szint: {level+1}<br>{e.hossz_cm:g} × {e.szelesseg_cm:g} × {g.magassag_cm:g} cm<br>Forgatva: {'igen' if e.forgatott else 'nem'}")
            for a,b,c in [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]:
                data['i'].append(base+a);data['j'].append(base+b);data['k'].append(base+c)
    for group,data in meshes.items():
        fig.add_trace(go.Mesh3d(**data,color=szin(group),name=groups[group].nev,showlegend=True,flatshading=True,hovertemplate='%{text}<extra></extra>',lighting=dict(ambient=.65,diffuse=.8)))
    pk=terv.potkocsi
    L,W,H=pk.rakter_hossz_cm,pk.rakter_szelesseg_cm,pk.rakter_magassag_cm
    corners=[(0,0,0),(L,0,0),(L,W,0),(0,W,0),(0,0,H),(L,0,H),(L,W,H),(0,W,H)]
    xs,ys,zs=[],[],[]
    for a,b in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:
        for c in (corners[a],corners[b],(None,None,None)):
            xs.append(c[0]);ys.append(c[1]);zs.append(c[2])
    fig.add_trace(go.Scatter3d(x=xs,y=ys,z=zs,mode='lines',line=dict(color='#365778',width=3),name='Használható raktér',hoverinfo='skip'))
    fig.update_layout(height=620,margin=dict(l=0,r=0,t=20,b=0),legend=dict(orientation='h'),scene=dict(aspectmode='data',xaxis_title='Hosszúság (cm)',yaxis_title='Szélesség (cm)',zaxis_title='Magasság (cm)',camera=dict(eye=dict(x=1.4,y=1.8,z=1.1))),uirevision='cargo-3d')
    return fig
