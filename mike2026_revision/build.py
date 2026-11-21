import json
g=json.load(open('gen.json')); t=open('template.tex').read()
t=t.replace('Mean standard deviations are of the order of the means because tile difficulty varies widely; the paired differences are consistent in sign.','Standard deviations are of the order of the means because tile difficulty varies widely, but the paired differences are consistent in sign.')
t=t.replace('{{TAB5}}',g['TAB5']).replace('{{TAB6}}',g['TAB6'])
open('main.tex','w').write(t)
