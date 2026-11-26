"""Static guard for isolated Fitness presale, no provider calls."""
import ast
from pathlib import Path
root=Path(__file__).parent
f=(root/"feedback_app.py").read_text()
m=(root/"main.py").read_text()
h=(root.parent/"public/classfit.html").read_text()+(root.parent/"public/fitness-presale.js").read_text()
for src in (f,m): ast.parse(src)
tree=ast.parse(f)
catalog=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="FITNESS_PRODUCTS" for t in n.targets))
assert {k:(v["price"],v["classes"],v["credits"]) for k,v in catalog.items()} == {"fitness_single":(2800,1,0),"fitness_five":(11900,5,0),"fitness_ten":(21900,10,0),"fitness_twenty":(29900,20,0)}
assert "fitness_presale_one_per_order" in f and "fitness_presale_consent_required" in f
assert "db.add(core.FitnessPresale(" in f
sync=f.split("def _sync_sumup_order(",1)[1].split("@app.",1)[0]
assert sync.index("if not trusted:") < sync.index('if status == "PAID":') < sync.index("fitness.paid_at =") < sync.index("profile.credits += order.credits")
assert "class FitnessPresale(Base)" in m and "fitness_presale_courses" in m
assert "fitness_reserved" in m and "fitness_presale" in h and "fitnessPresaleConsent:" in h and "fitnessTermsConsent:" in h
assert "checkout/status?reference=" in h and "d.status==='paid'&&d.fitness_courses>0" in h
print("Fitness presale isolation guard OK")
