#!/usr/bin/env python3
"""Send drafts via Mailgun as aidan@brickandmortar.dev. Logs ONLY accepted sends.
Mailgun enforces 100 REQUESTS per rolling 24h on this domain (refusal text:
'daily request limit (100) exceeded'), counted across every bricks campaign.

    python3 scripts/send.py drafts/a.txt drafts/b.txt
"""
import os,sys,csv,json,subprocess,datetime
k=os.environ['MAILGUN_API_KEY'];D=os.environ['MAILGUN_DOMAIN']
new=not os.path.exists('ledger.csv')
w=csv.writer(open('ledger.csv','a',newline=''))
if new: w.writerow(['sent','slug','to','attach','message_id','reply_kind'])
for f in sys.argv[1:]:
    t=open(f).read(); h,b=t.split('\n\n',1)
    hd=dict(l.split(': ',1) for l in h.splitlines())
    cmd=['curl','-s','-u',f'api:{k}',f'https://api.mailgun.net/v3/{D}/messages',
         '-F','from=Aidan <aidan@brickandmortar.dev>','-F',f"to={hd['To']}",'-F',f"subject={hd['Subject']}",'-F',f'text={b}']
    if hd.get('Attach'): cmd+=['-F',f"attachment=@{hd['Attach']}"]
    r=json.loads(subprocess.run(cmd,capture_output=True,text=True).stdout)
    ok=bool(r.get('id')); print('SENT' if ok else 'REFUSED', f, r.get('message'))
    if not ok: sys.exit(1)
    w.writerow([datetime.date.today().isoformat(),os.path.basename(f)[:-4],hd['To'],hd.get('Attach',''),r['id'],''])
