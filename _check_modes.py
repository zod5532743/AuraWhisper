import json

# Check APPDATA
with open(r'C:\Users\zod5532743\AppData\Roaming\aurawhisper\modes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print('APPDATA modes.json:')
print(f'  Total: {len(data)}')
for i, m in enumerate(data):
    print(f'  {i}: id={m["id"]}, name={m["name"]}')

# Check workspace
with open('D:/VSCODE/AuraWhisper/modes.json', 'r', encoding='utf-8') as f:
    data2 = json.load(f)
print('Workspace modes.json:')
print(f'  Total: {len(data2)}')
for i, m in enumerate(data2):
    print(f'  {i}: id={m["id"]}, name={m["name"]}')
