import pandas as pd, numpy as np
from scipy.stats import wilcoxon
df=pd.read_csv('/home/user/archana519/smart_village_infrastructure/final_100_distinct_samples_and_baselines (1).csv')
act=df[df.proposed_new_road_connections>0]
q=lambda s:np.percentile(s,[25,50,75])
def ms(s,d=2): return f"{s.mean():,.{d}f} $\\pm$ {s.std():,.{d}f}"
def mi(s,d=2):
    a,b,c=q(s); return f"{b:,.{d}f} [{a:,.{d}f}, {c:,.{d}f}]"
rows=[("Buildings per tile","total_buildings",2),("Connectivity before (\\%)","connectivity_before_pct",2),
("Connectivity after (\\%)","connectivity_after_pct",2),("Proposed routes per tile","proposed_new_road_connections",2),
("Total proposed length (px)","total_proposed_road_length_px",1),("Mean route length (px)","average_proposed_road_length_px",1),
("Mean nearest-road distance (px)","avg_connection_distance_px",1),("Path efficiency","average_path_efficiency",3)]
t5="\n".join(f"{n} & {ms(df[c],d)} & {ms(act[c],d)} & {mi(act[c],d)} \\\\" for n,c,d in rows)
T=df.total_buildings.sum();B=df.connected_buildings_before.sum();A=df.connected_buildings_after.sum()
L=df.total_proposed_road_length_px.sum()
m=0.3*1024/560
out={}
out['TAB5']=t5
out['POOL']=dict(T=T,B=B,A=A,iso=df.isolated_buildings_before.sum(),R=df.proposed_new_road_connections.sum(),L=L,Lm=L*m,
  Tact=act.total_buildings.sum(),Bact=act.connected_buildings_before.sum(),Aact=act.connected_buildings_after.sum(),m=m)
def cost_row(n,c,v=None):
    r=f"{n} & {ms(act[c],1)} & {mi(act[c],1)} & {ms(df[c],1)} "
    return r
t6=[cost_row("Terrain-aware A$^*$ (ours)","proposed_astar_cost"),cost_row("Unweighted A$^*$","unweighted_astar_cost"),cost_row("Euclidean line","euclidean_line_cost")]
v=lambda c:f"{ms(df[c],3)}"
t6[0]+=f"& {v('proposed_water_violation_pct')} \\\\"
t6[1]+="& n/a$^{\\ddagger}$ \\\\"
t6[2]+=f"& {v('euclidean_water_violation_pct')} \\\\"
out['TAB6']="\n".join(t6)
for k,v_ in out['POOL'].items(): print(k,v_)
print(t5); print(out['TAB6'])
import json; json.dump({'TAB5':t5,'TAB6':out['TAB6']},open('gen.json','w'))
