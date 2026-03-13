import json
with open('backend/knowledge_base/layer_1/genesis_key/system/keys_2026-03-12.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

res = []
keys = list(data.values())
for i, v in enumerate(keys):
    if not isinstance(v, dict): continue
    if v.get('key_id') == 'GK-2ae2686decba61dd43c21d001b2c70e0':
        res.append(keys[i-1])
        res.append(v)

with open('keys_out.txt', 'w', encoding='utf-8') as f:
    f.write(json.dumps(res, indent=2))
