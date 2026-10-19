# MeshLink macOS V10 - Official English
import socket, threading, json, os, time, uuid, hashlib, tkinter as tk, datetime, secrets
from tkinter import ttk, filedialog, messagebox
UDP_A=50000; UDP_B=50002; UDP_C=50001; TCP_TRY=list(range(50001,50101)); CHUNK=65536
IDENT=os.path.expanduser("~/.meshlink_v10_id.json"); RH="mesh-v10"
MY_MAC=':'.join(['{:02x}'.format((uuid.getnode()>>e)&0xff) for e in range(0,48,8)][::-1])
def now(): return datetime.datetime.now().strftime("%H:%M:%S")
def ph(p,s): return hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),150000).hex()
def login():
  if os.path.exists(IDENT):
    d=json.load(open(IDENT,encoding='utf-8'))
    w=tk.Tk(); w.geometry("400x250"); w.configure(bg="#0b1220"); w.title("Login V10")
    tk.Label(w,text=f"Welcome {d['name']}",bg="#0b1220",fg="white").pack(pady=10)
    e=tk.Entry(w,justify='center',show="•"); e.pack(padx=30,fill='x'); e.focus(); r={}
    def ok():
      if ph(e.get(),d['salt'])!=d['ph']: messagebox.showerror("Error","Incorrect"); return
      r['o']=1; w.destroy()
    e.bind('<Return>',lambda x:ok()); tk.Button(w,text="Login",command=ok).pack(pady=10)
    w.mainloop()
    if 'o' not in r: raise SystemExit
    return d['name'],d['id'],d['sec']
  w=tk.Tk(); w.geometry("420x300"); w.configure(bg="#0b1220")
  e1=tk.Entry(w,justify='center'); e1.pack(padx=30,fill='x',pady=8); e2=tk.Entry(w,justify='center',show="•"); e2.pack(padx=30,fill='x',pady=8); r={}
  def ok():
    n=e1.get().strip(); p=e2.get()
    if len(n)<2 or len(n)>10 or len(p)<6: return
    r['n']=n; r['p']=p; w.destroy()
  tk.Button(w,text="Create",command=ok).pack(pady=10)
  w.mainloop()
  if 'n' not in r: raise SystemExit
  s=secrets.token_hex(12); sec=secrets.token_hex(12); json.dump({"name":r['n'],"id":MY_MAC,"sec":sec,"salt":s,"ph":ph(r['p'],s)},open(IDENT,'w',encoding='utf-8'))
  return r['n'],MY_MAC,sec
MY_NAME,MY_ID,MY_SEC=login()
MY_PUB=hashlib.sha256(MY_SEC.encode()).hexdigest()[:16]
def find_tcp():
  for p in TCP_TRY:
    try: s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(('',p)); s.listen(30); return s,p
    except: continue
  raise SystemExit
TCP_SOCK,MY_TP=find_tcp()
peers={}; seq_out=0; seen=set(); running=True
def bcast():
  s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
  while running:
    m=json.dumps({"id":MY_ID,"name":MY_NAME,"rh":RH,"pub":MY_PUB,"tp":MY_TP}).encode()
    for po in (UDP_A,UDP_B):
      try: s.sendto(m,('<broadcast>',po))
      except: pass
    time.sleep(1)
root=tk.Tk(); root.title(f"MeshLink V10 - {MY_NAME}"); root.geometry("1100x760"); root.configure(bg="#0b1220")
tk.Label(root,text=f"MESHLINK V10 | Welcome {MY_NAME}",bg="#0b1220",fg="white").pack(pady=6)
body=tk.Frame(root,bg="#0b1220"); body.pack(fill='both',expand=True,padx=12)
left=tk.Frame(body,bg="#111c33"); left.pack(side='left',fill='y',padx=(0,10))
cnt=tk.Label(left,text="Please Wait...",bg="#111c33",fg="#60a5fa"); cnt.pack()
box=tk.Listbox(left,width=34,height=25,bg="#0a0f1e",fg="white"); box.pack(padx=10,fill='y',expand=True)
right=tk.Frame(body,bg="#0b1220"); right.pack(side='right',fill='both',expand=True)
nb=ttk.Notebook(right); nb.pack(fill='both',expand=True)
tp=tk.Frame(nb,bg="#0f172a"); ti=tk.Frame(nb,bg="#0f172a"); ts=tk.Frame(nb,bg="#0b0f1a")
nb.add(tp,text=" Public "); nb.add(ti,text=" Inbox "); nb.add(ts,text=" Log ")
pub=tk.Text(tp,bg="#0f172a",fg="white"); pub.pack(fill='both',expand=True); pub.config(state='disabled')
inb=tk.Text(ti,bg="#0f172a",fg="#e2e8f0"); inb.pack(fill='both',expand=True); inb.config(state='disabled')
sec=tk.Text(ts,bg="#0b0f1a",fg="#94a3b8"); sec.pack(fill='both',expand=True); sec.config(state='disabled')
def lp(m):
  pub.config(state='normal'); pub.insert(tk.END,m+"\n"); pub.see(tk.END); pub.config(state='disabled')
def li(m):
  inb.config(state='normal'); inb.insert(tk.END,m+"\n"); inb.see(tk.END); inb.config(state='disabled')
def ls(m):
  sec.config(state='normal'); sec.insert(tk.END,f"[{now()}] {m}\n"); sec.see(tk.END); sec.config(state='disabled')
ent=tk.Entry(right,bg="#111c33",fg="white"); ent.pack(fill='x',pady=8,ipady=8); ent.focus()
bf=tk.Frame(right,bg="#0b1220"); bf.pack()
def get_target():
  s=box.curselection()
  if s:
    raw=box.get(s[0]).replace("●","").strip().split("|"); nm=raw[0].strip(); ip=raw[1].strip()
    for pid,(pn,pip,pp,ptp) in peers.items():
      if pip==ip: return nm,ip,ptp
    return nm,ip,50001
  if len(peers)==1:
    pid,(nm,ip,pb,ptp)=list(peers.items())[0]; return nm,ip,ptp
  return None,None,None
def rel(ip,port,p):
  for i in range(3):
    try: s=socket.socket(); s.settimeout(3); s.connect((ip,port)); s.send(p.encode()); s.close(); return True
    except: time.sleep(0.2)
  try: u=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); u.sendto(("UDP:"+p).encode(),(ip,UDP_C)); u.close(); return True
  except: return False
def s_pub(e=None):
  t=ent.get().strip()
  if not t: return
  ent.delete(0,tk.END)
  global seq_out; seq_out+=1; lp(f"{MY_NAME}: {t}")
  for pid,(nm,ip,pb,ptp) in list(peers.items()): rel(ip,ptp,f"PUB|{MY_ID}|{MY_NAME}|{MY_PUB}|{seq_out}|{t}")
def s_prv():
  t=ent.get().strip()
  if not t: return
  nm,ip,ptp=get_target()
  if not ip: return
  ent.delete(0,tk.END)
  global seq_out; seq_out+=1; li(f"To {nm}: {t}"); rel(ip,ptp,f"PRV|{MY_ID}|{MY_NAME}|{MY_PUB}|{seq_out}|{t}")
def sfo(ip,port,path):
  import hashlib as H
  sz=os.path.getsize(path); h=H.sha256(open(path,'rb').read()).hexdigest(); fn=os.path.basename(path)
  global seq_out; seq_out+=1
  for a in range(2):
    try:
      s=socket.socket(); s.connect((ip,port)); s.send(f"FILE|{MY_ID}|{MY_NAME}|{MY_PUB}|{seq_out}|{fn}|{sz}|{h}".encode())
      if s.recv(16)!=b"OK": s.close(); continue
      f=open(path,'rb')
      while True:
        d=f.read(CHUNK)
        if not d: break
        s.sendall(d)
      f.close(); s.close(); return True
    except: pass
  return False
def s_fprv():
  nm,ip,ptp=get_target()
  if not ip: return
  p=filedialog.askopenfilename(parent=root)
  if p: threading.Thread(target=lambda:(lp("Uploading..."),sfo(ip,ptp,p),lp("Done")),daemon=True).start()
def s_fpub():
  if not peers: return
  p=filedialog.askopenfilename(parent=root)
  if not p: return
  def run():
    for pid,(nm,ip,pb,ptp) in list(peers.items()):
      try: sfo(ip,ptp,p)
      except: pass
    lp("Finished")
  threading.Thread(target=run,daemon=True).start()
ent.bind('<Return>',s_pub)
tk.Button(bf,text="Send Public",command=s_pub).pack(side='left',padx=4)
tk.Button(bf,text="Private",command=s_prv).pack(side='left',padx=4)
tk.Button(bf,text="Send File",command=s_fprv).pack(side='left',padx=4)
tk.Button(bf,text="File to All",command=s_fpub).pack(side='left',padx=4)
def ht(h):
  if h.startswith("PUB|"):
    _,sid,sn,sp,q,t=h.split("|",5)
    if (sid+q) not in seen: seen.add(sid+q); lp(f"{sn}: {t}")
  elif h.startswith("PRV|"):
    _,sid,sn,sp,q,t=h.split("|",5)
    if (sid+q) not in seen: seen.add(sid+q); li(f"From {sn}: {t}"); nb.select(ti)
def ul():
  ss=[]
  for pr in (UDP_A,UDP_B,UDP_C):
    try: s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(('',pr)); ss.append(s)
    except: pass
  def loop(s):
    while running:
      try:
        d,a=s.recvfrom(65535); t=d.decode(errors='ignore')
        if t.startswith("UDP:"): ht(t[4:])
        elif t.startswith("{"):
          j=json.loads(t)
          if j.get('id')==MY_ID or j.get('rh')!=RH: continue
          peers[j['id']]=(j['name'],a[0],j.get('pub'),j.get('tp',50001)); box.delete(0,tk.END)
          for pid,(n2,i2,_,_) in peers.items(): box.insert(tk.END,f"● {n2}  |  {i2}")
          cnt.config(text=f"{len(peers)+1} Online")
      except: pass
  for s in ss: threading.Thread(target=loop,args=(s,),daemon=True).start()
def handle(c):
  try:
    h=c.recv(4096).decode()
    if h.startswith("PUB|") or h.startswith("PRV|"): ht(h)
    elif h.startswith("FILE|"):
      _,sid,sn,sp,q,fn,fs,dg=h.split("|",7); fs=int(fs); save=os.path.join(os.path.expanduser("~/Downloads"),"recv_"+fn); c.send(b"OK")
      import hashlib as H; hh=H.sha256(); f=open(save,'wb'); left=fs
      while left>0:
        d=c.recv(min(CHUNK,left))
        if not d: break
        f.write(d); hh.update(d); left-=len(d)
      f.close(); lp(f"From {sn}: {save}")
    c.close()
  except: pass
def ts():
  while running:
    try: c,a=TCP_SOCK.accept(); threading.Thread(target=handle,args=(c,),daemon=True).start()
    except: pass
threading.Thread(target=bcast,daemon=True).start(); threading.Thread(target=ul,daemon=True).start(); threading.Thread(target=ts,daemon=True).start()
root.mainloop()