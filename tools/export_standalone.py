"""Export one offline HTML file containing the generated data and runtime.

No copyrighted standard PDFs or local authentication helpers are included.
"""
from pathlib import Path
import copy,json,re

ROOT=Path(__file__).resolve().parent.parent
data=copy.deepcopy(json.loads((ROOT/'data/standards.json').read_text(encoding='utf-8')))
for regulation in data['regulations']:
    regulation.pop('local',None)
html=(ROOT/'index.html').read_text(encoding='utf-8')
# Use installed fallback fonts so the file requires no network to render.
html=re.sub(r'<link[^>]+(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^>]*>\s*','',html)
inline_data=json.dumps(data,ensure_ascii=False).replace('</','<\\/')
runtime=(ROOT/'app.js').read_text(encoding='utf-8').replace('</script','<\\/script')
notes=(ROOT/'notes.js').read_text(encoding='utf-8').replace('</script','<\\/script')
html=html.replace('<script src="data/standards.js"></script>','<script>window.STANDARDS_DATA = '+inline_data+';</script>')
html=html.replace('<script src="app.js"></script>','<script>'+runtime+'</script>')
html=html.replace('<script src="notes.js"></script>','<script>'+notes+'</script>')
out=ROOT/'dist/atsc3-kr-us-br-reviewed.html';out.parent.mkdir(exist_ok=True)
out.write_bytes(html.encode('utf-8'))
print(out)
