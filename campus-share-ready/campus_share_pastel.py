"""Campus Share - a local, offline web app for college students.
Post anything you HAVE or NEED (books, notes, lab equipment...).
A local open-weight model (Ollama) matches similar items.
Only matched students see each other's contact details and chat.
Chats stay open after an item is handed over, so students can talk again
when they need their next book.

Run:  python campus_share_pastel.py
Then open http://localhost:8000  (no internet needed).
Uses only Python's built-in libraries. No pip install.
"""
import sqlite3, json, urllib.request, urllib.parse, threading, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

MODEL = "qwen3.5:4b"      # change if needed (see: ollama list)
PORT = 8000
HOST = "127.0.0.1"        # this laptop only. Use "0.0.0.0" to share on the same Wi-Fi.
CATEGORIES = ["Book", "Notes / past papers", "Lab equipment / tools", "Other"]
MODES = ["Lend", "Give free", "Sell"]
DB = "campus_share.db"


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


with conn() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY, kind TEXT, category TEXT, item TEXT, student TEXT,
        contact TEXT, mode TEXT, price TEXT, urgent TEXT, done INTEGER DEFAULT 0)""")
    try:
        c.execute("ALTER TABLE posts ADD COLUMN done INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    c.execute("CREATE TABLE IF NOT EXISTS matches (need_id INTEGER, have_id INTEGER)")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY, need_id INTEGER, have_id INTEGER, sender TEXT, text TEXT)""")


def ollama_ready():
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return True
    except Exception:
        return False


def same_item(a, b, category):
    if a.lower().strip() == b.lower().strip():
        return True
    prompt = (f'Category: {category}\n'
              f'Do these two items refer to the same thing (for example the same textbook, '
              f'subject notes, or piece of equipment)?\n1: "{a}"\n2: "{b}"\n'
              f'Answer with only YES or NO.')
    body = json.dumps({"model": MODEL, "stream": False, "think": False, "options": {"num_predict": 8, "temperature": 0}, "keep_alive": "30m",
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)["message"]["content"].strip().upper().startswith("YES")
    except Exception as e:
        print("Model error:", e)
        return False


def add_post(d):
    kind = d.get("kind")
    category = d.get("category")
    item = (d.get("item") or "").strip()
    student = (d.get("student") or "").strip()
    contact = (d.get("contact") or "").strip()
    if kind not in ("HAVE", "NEED") or category not in CATEGORIES \
            or not item or not student or not contact:
        return {"error": "Please fill in item, name and contact."}
    mode = d.get("mode") if d.get("mode") in MODES else "Lend"
    price = (d.get("price") or "").strip() if mode == "Sell" else ""
    urgent = (d.get("urgent") or "").strip() if kind == "NEED" else ""
    with conn() as c:
        cur = c.execute("INSERT INTO posts (kind,category,item,student,contact,mode,price,urgent,done) "
                        "VALUES (?,?,?,?,?,?,?,?,0)",
                        (kind, category, item, student, contact, mode, price, urgent))
        new_id = cur.lastrowid
        other = "HAVE" if kind == "NEED" else "NEED"
        cands = c.execute("SELECT * FROM posts WHERE kind=? AND category=? AND done=0 "
                          "ORDER BY id DESC LIMIT 3", (other, category)).fetchall()
    found = []
    for o in cands:
        if same_item(item, o["item"], category):
            need_id, have_id = (new_id, o["id"]) if kind == "NEED" else (o["id"], new_id)
            with conn() as c:
                c.execute("INSERT INTO matches VALUES (?,?)", (need_id, have_id))
            found.append(dict(item=o["item"], student=o["student"], contact=o["contact"],
                              mode=o["mode"], price=o["price"], urgent=o["urgent"]))
    return {"saved": True, "matches": found}


def public_posts():
    with conn() as c:   # contact details are NOT included here
        rows = c.execute("SELECT kind,category,item,student,mode,price,urgent FROM posts "
                         "WHERE done=0 ORDER BY urgent='' , id DESC").fetchall()
    return [dict(r) for r in rows]


def my_matches(name):
    q = """SELECT me.id AS my_id, m.need_id, m.have_id, me.item AS mine, o.item, o.student,
                  o.contact, o.mode, o.price, o.urgent
           FROM posts me
           JOIN matches m ON (m.need_id = me.id OR m.have_id = me.id)
           JOIN posts o ON o.id = CASE WHEN m.need_id = me.id THEN m.have_id ELSE m.need_id END
           WHERE lower(me.student) = lower(?) AND me.done = 0 AND o.done = 0"""
    with conn() as c:
        return [dict(r) for r in c.execute(q, (name.strip(),)).fetchall()]


def my_chats(name):
    """Every conversation, including ones where the item was already handed over."""
    q = """SELECT m.need_id, m.have_id, me.item AS mine, o.item, o.student AS partner,
                  (me.done OR o.done) AS done,
                  (SELECT text FROM messages WHERE need_id = m.need_id AND have_id = m.have_id
                   ORDER BY id DESC LIMIT 1) AS last
           FROM posts me
           JOIN matches m ON (m.need_id = me.id OR m.have_id = me.id)
           JOIN posts o ON o.id = CASE WHEN m.need_id = me.id THEN m.have_id ELSE m.need_id END
           WHERE lower(me.student) = lower(?)"""
    with conn() as c:
        return [dict(r) for r in c.execute(q, (name.strip(),)).fetchall()]


def get_chat(need_id, have_id, name):
    try:
        need_id, have_id = int(need_id), int(have_id)
    except Exception:
        return {"error": "Bad request."}
    name = name.strip().lower()
    with conn() as c:
        ok = c.execute("SELECT 1 FROM matches WHERE need_id=? AND have_id=?",
                       (need_id, have_id)).fetchone()
        rows = c.execute("SELECT student FROM posts WHERE id IN (?,?)",
                         (need_id, have_id)).fetchall()
        students = [r["student"].strip() for r in rows]
        if not ok or name not in [s.lower() for s in students]:
            return {"error": "Only the two matched students can open this chat."}
        partner = next((s for s in students if s.lower() != name), students[0])
        msgs = c.execute("SELECT sender, text FROM messages WHERE need_id=? AND have_id=? "
                         "ORDER BY id", (need_id, have_id)).fetchall()
    return {"partner": partner, "messages": [dict(m) for m in msgs]}


def mark_done(d):
    try:
        pid = int(d.get("id"))
    except Exception:
        return {"error": "Bad request."}
    name = (d.get("name") or "").strip().lower()
    with conn() as c:
        row = c.execute("SELECT student FROM posts WHERE id=?", (pid,)).fetchone()
        if not row or row["student"].strip().lower() != name:
            return {"error": "Only the person who posted can mark it done."}
        ids = {pid}
        for m in c.execute("SELECT need_id, have_id FROM matches WHERE need_id=? OR have_id=?",
                           (pid, pid)).fetchall():
            ids.update([m["need_id"], m["have_id"]])
        for i in ids:
            c.execute("UPDATE posts SET done=1 WHERE id=?", (i,))
    return {"ok": True}


def add_message(d):
    text = (d.get("text") or "").strip()
    sender = (d.get("sender") or "").strip().lower()
    try:
        need_id, have_id = int(d.get("need_id")), int(d.get("have_id"))
    except Exception:
        return {"error": "Bad request."}
    if not text:
        return {"error": "Write a message first."}
    with conn() as c:
        ok = c.execute("SELECT 1 FROM matches WHERE need_id=? AND have_id=?",
                       (need_id, have_id)).fetchone()
        names = [r["student"].strip().lower() for r in c.execute(
            "SELECT student FROM posts WHERE id IN (?,?)", (need_id, have_id)).fetchall()]
        if not ok or sender not in names:
            return {"error": "Only the two matched students can message."}
        c.execute("INSERT INTO messages (need_id, have_id, sender, text) VALUES (?,?,?,?)",
                  (need_id, have_id, d.get("sender").strip(), text[:500]))
    return {"ok": True}


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campus Share</title>
<style>
:root{--text:#3b3355;--muted:#7a7396;--primary:#7c68b8;--border:#eadff5;--card:rgba(255,255,255,.85);--input:#fff}
*{box-sizing:border-box}
body{font-family:Segoe UI,Arial,sans-serif;margin:0;color:var(--text);min-height:100vh;
 background:linear-gradient(135deg,#ffe1ef 0%,#e3ecff 45%,#dcf7ec 100%) fixed}
body::before{content:"";position:fixed;inset:0;z-index:-2;
 background:radial-gradient(circle at 10% 15%,rgba(255,200,221,.75),transparent 34%),
 radial-gradient(circle at 88% 10%,rgba(189,224,254,.85),transparent 36%),
 radial-gradient(circle at 80% 90%,rgba(184,234,212,.85),transparent 36%),
 radial-gradient(circle at 12% 88%,rgba(255,214,192,.75),transparent 34%)}
body::after{content:"";position:fixed;inset:0;z-index:-1;
 background-image:radial-gradient(rgba(124,104,184,.16) 1.6px,transparent 1.6px);background-size:28px 28px}
header{background:linear-gradient(135deg,#d9c8f0,#b9e0ff);padding:18px 24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;box-shadow:0 2px 12px rgba(124,104,184,.2)}
header h1{margin:0;font-size:25px}header small{color:#5b5378}
#status{padding:4px 12px;border-radius:14px;font-size:13px;background:#ffd6d6;color:#8a1c1c}
#status.ok{background:#c9f2dc;color:#14532d}
.bar{max-width:1150px;margin:14px auto 0;padding:0 20px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.bar input{width:200px}.bar .lbl{font-size:14px;color:var(--muted)}
.tabs{max-width:1150px;margin:10px auto 0;padding:0 20px;display:flex;gap:8px;flex-wrap:wrap}
.tabs button{margin:0;background:rgba(255,255,255,.7);color:var(--text);border:1px solid var(--border)}
.tabs button.active{background:var(--primary);color:#fff}
.wrap{max-width:1150px;margin:auto;padding:16px 20px}
.grid2{display:grid;grid-template-columns:minmax(290px,400px) 1fr;gap:20px}
.grid3{display:grid;grid-template-columns:minmax(260px,340px) 1fr;gap:20px}
@media(max-width:820px){.grid2,.grid3{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:18px;box-shadow:0 4px 16px rgba(124,104,184,.12);margin-bottom:18px;backdrop-filter:blur(4px)}
h2{margin:0 0 10px;font-size:18px}
label{display:block;font-size:13px;margin:10px 0 4px;color:var(--muted)}
input,select{width:100%;padding:9px;border:1px solid var(--border);background:var(--input);color:var(--text);border-radius:10px;font-size:14px}
button{margin-top:12px;padding:10px 16px;border:0;border-radius:10px;background:var(--primary);color:#fff;font-size:14px;cursor:pointer}
button.small{margin:6px 6px 0 0;padding:6px 11px;font-size:12px}
button.alt{background:#5fa8b8}button.warn{background:#d9778f}
button:disabled{opacity:.6}.row{display:flex;gap:8px}.row>*{flex:1}
.post{border-bottom:1px solid var(--border);padding:10px 0;font-size:14px}.post:last-child{border:0}
.tag{display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;margin-right:6px}
.HAVE{background:#b8ead4;color:#14532d}.NEED{background:#ffd6c0;color:#7c2d12}.urg{background:#ffc8dd;color:#9f1239}
.match{background:#eefbf4;border:1px solid #b8ead4;border-radius:12px;padding:12px;margin-top:10px;font-size:14px}
.mh{font-weight:600;margin-bottom:4px}
.chatitem{border:1px solid var(--border);background:rgba(255,255,255,.7);border-radius:12px;padding:10px;margin-bottom:8px;cursor:pointer}
.chatitem:hover{background:#f3ecff}
#chatMsgs{height:340px;overflow-y:auto;padding:8px;background:rgba(255,255,255,.6);border:1px solid var(--border);border-radius:12px}
.bubble{max-width:75%;padding:8px 12px;border-radius:16px;margin:5px 0;font-size:14px;word-wrap:break-word}
.me{margin-left:auto;background:#d9c8f0}.them{background:#fff;border:1px solid var(--border)}
.hidden{display:none}.muted{color:var(--muted);font-size:13px}
</style></head><body>
<header><div><h1>Campus Share</h1><small>Borrow, lend or sell within your college. Open-weight AI. Works offline.</small></div>
<span id="status">Checking local model...</span></header>

<div class="bar"><span class="lbl">Who are you?</span><input id="who" placeholder="Your name">
<button id="whoBtn" style="margin:0">Continue</button><span id="whoLabel" class="lbl"></span></div>
<div class="tabs"><button id="t-home" class="active">Browse and Post</button>
<button id="t-matches">My matches</button><button id="t-chats">Chats</button></div>

<div class="wrap">
<div id="v-home" class="grid2"><div>
 <div class="card"><h2>Post something</h2>
  <label>I want to</label><select id="kind"><option value="HAVE">Share something I HAVE</option><option value="NEED">Find something I NEED</option></select>
  <label>Category</label><select id="category"></select>
  <label>What is it?</label><input id="item" placeholder="e.g. DBMS by Korth, Chemistry lab coat">
  <label>Your name</label><input id="student">
  <label>Contact (shown only to your match)</label><input id="contact" placeholder="phone / hostel / block">
  <div id="haveBox"><label>Offer as</label>
   <div class="row"><select id="mode"><option>Lend</option><option>Give free</option><option>Sell</option></select>
   <input id="price" class="hidden" placeholder="Price"></div></div>
  <div id="needBox" class="hidden"><label>Needed by when? (optional)</label><input id="urgent" placeholder="e.g. exam in 2 days"></div>
  <button id="postBtn">Post</button>
  <div id="result"></div>
 </div></div>
 <div class="card"><h2>All posts <span class="muted">(contacts hidden until matched)</span></h2><div id="posts"></div></div>
</div>

<div id="v-matches" class="hidden"><div class="card"><h2>My matches</h2>
 <div class="muted">Your contact details are shared only with the student you matched with.</div><div id="mine"></div></div></div>

<div id="v-chats" class="hidden grid3">
 <div class="card"><h2>Your chats</h2>
  <div class="muted">Chats stay open after you mark an item done, so you can talk again when you need your next book.</div>
  <div id="chatList" style="margin-top:10px"></div></div>
 <div class="card hidden" id="chatBox"><h2 id="chatHead">Chat</h2>
  <div id="chatMsgs"></div>
  <div class="row" style="margin-top:8px"><input id="chatInput" placeholder="Write a message (e.g. Can we meet at 6 pm?)">
  <button id="sendBtn" style="margin:0;flex:0 0 90px">Send</button></div></div>
</div>
</div>

<script>
const CATS=__CATS__;const $=id=>document.getElementById(id);
let me='',cur=null,tab='home';
CATS.forEach(c=>{const o=document.createElement('option');o.textContent=c;$('category').appendChild(o)});
function btn(text,cls,fn){const b=document.createElement('button');b.textContent=text;b.className='small '+cls;b.onclick=fn;return b}
function terms(m){return m.mode+(m.price?' '+m.price:'')+(m.urgent?' [URGENT: '+m.urgent+']':'')}
async function post(path,body){return (await fetch(path,{method:'POST',body:JSON.stringify(body)})).json()}
function toggle(){const need=$('kind').value==='NEED';$('needBox').classList.toggle('hidden',!need);$('haveBox').classList.toggle('hidden',need);
 $('price').classList.toggle('hidden',$('mode').value!=='Sell')}
$('kind').onchange=toggle;$('mode').onchange=toggle;toggle();

function showTab(t){tab=t;['home','matches','chats'].forEach(x=>{
 $('v-'+x).classList.toggle('hidden',x!==t);$('t-'+x).classList.toggle('active',x===t)});
 if(t==='matches')loadMatches();if(t==='chats')loadChats();if(t==='home')loadPosts()}
['home','matches','chats'].forEach(x=>{$('t-'+x).onclick=()=>showTab(x)});

function setWho(){const v=$('who').value.trim();if(!v){alert('Type your name first.');return}
 me=v;$('whoLabel').textContent='Signed in as '+me;$('student').value=me;
 try{localStorage.setItem('who',me)}catch(e){}
 cur=null;$('chatBox').classList.add('hidden');showTab(tab)}
$('whoBtn').onclick=setWho;

async function health(){try{const r=await (await fetch('/api/health')).json();
 $('status').textContent=r.ok?'Local model: ready':'Start Ollama first';$('status').className=r.ok?'ok':''}catch(e){}}

async function loadPosts(){const ps=await (await fetch('/api/posts')).json();$('posts').textContent='';
 if(!ps.length){$('posts').textContent='No posts yet.';return}
 ps.forEach(p=>{const d=document.createElement('div');d.className='post';
  const k=document.createElement('span');k.className='tag '+p.kind;k.textContent=p.kind;d.appendChild(k);
  if(p.urgent){const u=document.createElement('span');u.className='tag urg';u.textContent='URGENT: '+p.urgent;d.appendChild(u)}
  d.appendChild(document.createTextNode(p.item+' ('+p.category+') - '+p.student+' - '+p.mode+(p.price?' '+p.price:'')));
  $('posts').appendChild(d)})}

$('postBtn').onclick=async()=>{const b=$('postBtn');b.disabled=true;
 $('result').textContent='Saving and checking for matches with the local model. This can take a minute...';
 const body={kind:$('kind').value,category:$('category').value,item:$('item').value,student:$('student').value,
  contact:$('contact').value,mode:$('mode').value,price:$('price').value,urgent:$('urgent').value};
 try{const r=await post('/api/post',body);$('result').textContent='';
  if(r.error){$('result').textContent=r.error}
  else{if(!me){$('who').value=body.student.trim();setWho()}
   $('result').textContent=r.matches.length?'Saved! Matches found. Open the My matches tab to chat.':'Saved! No match yet. Check My matches later.';
   r.matches.forEach(m=>{const d=document.createElement('div');d.className='match';
    d.textContent='MATCH: '+m.item+' - '+m.student+' ('+m.contact+') - '+terms(m);$('result').appendChild(d)});
   $('item').value='';loadPosts()}}
 catch(e){$('result').textContent='Something went wrong. Is the app still running?'}
 b.disabled=false};

async function loadMatches(){const box=$('mine');box.textContent='';
 if(!me){box.textContent='Enter your name above and click Continue.';return}
 const r=await (await fetch('/api/mymatches?name='+encodeURIComponent(me))).json();
 if(!r.length){box.textContent='No active matches yet.';return}
 r.forEach(m=>{const d=document.createElement('div');d.className='match';
  const h=document.createElement('div');h.className='mh';
  h.textContent='Your post: '+m.mine+'  |  Match: '+m.item+' by '+m.student;d.appendChild(h);
  const t=document.createElement('div');t.textContent='Terms: '+terms(m);d.appendChild(t);
  const c=document.createElement('div');c.textContent='Contact: '+m.contact;d.appendChild(c);
  const cp=btn('Copy contact','alt',()=>{try{navigator.clipboard.writeText(m.contact);cp.textContent='Copied!'}catch(e){}});
  d.appendChild(cp);
  d.appendChild(btn('Open chat','',()=>openChat(m.need_id,m.have_id)));
  d.appendChild(btn('Mark as done','warn',async()=>{
   const r2=await post('/api/done',{id:m.my_id,name:me});
   if(r2.error){alert(r2.error)}else{alert('Marked as done. You can still chat from the Chats tab.');loadMatches();loadPosts()}}));
  box.appendChild(d)})}

async function loadChats(){const box=$('chatList');box.textContent='';
 if(!me){box.textContent='Enter your name above and click Continue.';return}
 const r=await (await fetch('/api/chats?name='+encodeURIComponent(me))).json();
 if(!r.length){box.textContent='No chats yet. A chat opens when you get a match.';return}
 r.forEach(c=>{const d=document.createElement('div');d.className='chatitem';
  const t=document.createElement('div');t.className='mh';t.textContent=c.partner+(c.done?' (completed)':'');
  const s=document.createElement('div');s.className='muted';s.textContent=c.mine+' / '+c.item;
  const l=document.createElement('div');l.className='muted';l.textContent=c.last?c.last:'No messages yet';
  d.appendChild(t);d.appendChild(s);d.appendChild(l);
  d.onclick=()=>openChat(c.need_id,c.have_id);box.appendChild(d)})}

function openChat(n,h){cur={n:n,h:h};showTab('chats');$('chatBox').classList.remove('hidden');refreshChat(true)}
async function refreshChat(scroll){if(!cur||!me)return;
 const r=await (await fetch('/api/chat?need_id='+cur.n+'&have_id='+cur.h+'&name='+encodeURIComponent(me))).json();
 if(r.error){$('chatHead').textContent=r.error;return}
 $('chatHead').textContent='Chat with '+r.partner;
 const box=$('chatMsgs');box.textContent='';
 if(!r.messages.length){const e=document.createElement('div');e.className='muted';e.textContent='No messages yet. Say hello!';box.appendChild(e)}
 r.messages.forEach(x=>{const b=document.createElement('div');
  b.className='bubble '+(x.sender.trim().toLowerCase()===me.toLowerCase()?'me':'them');b.textContent=x.text;box.appendChild(b)});
 if(scroll)box.scrollTop=box.scrollHeight}
async function sendMsg(){const t=$('chatInput').value.trim();if(!t||!cur)return;
 const r=await post('/api/message',{need_id:cur.n,have_id:cur.h,sender:me,text:t});
 if(r.error){alert(r.error);return}$('chatInput').value='';refreshChat(true)}
$('sendBtn').onclick=sendMsg;$('chatInput').onkeydown=e=>{if(e.key==='Enter')sendMsg()};
setInterval(()=>{if(tab==='chats'&&cur)refreshChat(false)},4000);

health();loadPosts();
try{const w=localStorage.getItem('who');if(w){$('who').value=w;setWho()}}catch(e){}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, data, ctype="application/json"):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        name = q.get("name", [""])[0]
        if u.path == "/":
            self.send(PAGE.replace("__CATS__", json.dumps(CATEGORIES)).encode(), "text/html")
        elif u.path == "/api/posts":
            self.send(public_posts())
        elif u.path == "/api/health":
            self.send({"ok": ollama_ready()})
        elif u.path == "/api/mymatches":
            self.send(my_matches(name) if name.strip() else [])
        elif u.path == "/api/chats":
            self.send(my_chats(name) if name.strip() else [])
        elif u.path == "/api/chat":
            self.send(get_chat(q.get("need_id", [""])[0], q.get("have_id", [""])[0], name))
        else:
            self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n))
        except Exception:
            data = {}
        if self.path == "/api/post":
            self.send(add_post(data))
        elif self.path == "/api/done":
            self.send(mark_done(data))
        elif self.path == "/api/message":
            self.send(add_message(data))
        else:
            self.send_error(404)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Campus Share running at {url}  (press Ctrl+C to stop)")
    threading.Timer(1, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")

