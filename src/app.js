import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://kisanlink-api-ksfw.onrender.com';
const TOKEN_KEY = 'kisanlink_token';
const USER_KEY = 'kisanlink_user';
const state = { route: location.hash.slice(1) || '/login', user: null, lang: 'EN', loading: false };

const logo = '/assets/kisanlink-logo.png';

function token(){ return localStorage.getItem(TOKEN_KEY); }
function isAuthed(){ return !!token(); }
function saveSession(data){ localStorage.setItem(TOKEN_KEY, data.access_token); if(data.user) localStorage.setItem(USER_KEY, JSON.stringify(data.user)); state.user=data.user||null; }
function clearSession(){ localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); state.user=null; }
function loadSession(){ try { state.user=JSON.parse(localStorage.getItem(USER_KEY)||'null'); } catch { state.user=null; } }
async function api(path, options={}){
  const headers={'Content-Type':'application/json', ...(options.headers||{})};
  if(token()) headers.Authorization=`Bearer ${token()}`;
  const res=await fetch(`${API_BASE}${path}`,{...options,headers});
  const text=await res.text(); let data={}; try{data=text?JSON.parse(text):{}}catch{data={detail:text}};
  if(!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}
function go(route){ if(!isAuthed() && route!=='/login' && route!=='/') route='/login'; state.route=route; location.hash=route; render(); window.scrollTo(0,0); }
window.addEventListener('hashchange',()=>{state.route=location.hash.slice(1)||'/login'; if(!isAuthed()&&state.route!=='/login'&&state.route!=='/') state.route='/login'; render();});
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function money(v){ if(v==null) return '—'; return `₹${Number(v).toLocaleString('en-IN')}`; }
function time(v){ if(!v) return '—'; const d=new Date(v); return Number.isNaN(d.getTime())?'—':d.toLocaleString('en-IN',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}); }
function status(text){return `<span class="badge">${esc(text)}</span>`}
function header(active=''){return `<header class="topbar"><button class="brand" onclick="go('/dashboard')"><img class="logo-img" src="${logo}" onerror="this.src='/farmer.svg'"/><div><div class="brand-name">KISANLINK ${status('LIVE')}</div><div class="brand-sub">Connecting Farmers to Better Markets</div></div></button><div class="top-actions"><button class="pill" onclick="toggleLang()">${state.lang} ⇄</button><button class="icon-btn" onclick="go('/notifications')">🔔</button><button class="avatar-btn" onclick="go('/profile')"><img class="avatar" src="${logo}" onerror="this.src='/farmer.svg'"/></button></div></header><div class="location">⌖ <strong>Live location</strong><span>• ${esc(active||'KISANLINK')}</span></div>`}
function bottom(active){const items=[['/dashboard','⌂','Home'],['/prices','▦','Prices'],['/sell','↗','Sell'],['/buyers','♙','Buyers'],['/transactions','▤','Wallet']];return `<nav class="bottomnav">${items.map(x=>`<button class="navitem ${active===x[0]?'active':''}" onclick="go('${x[0]}')"><span class="navicon">${x[1]}</span>${x[2]}</button>`).join('')}</nav>`}
function layout(content,active=''){return `<div class="app-shell">${header(active)}<main class="page">${content}</main>${bottom(active)}</div>`}
function toggleLang(){state.lang=state.lang==='EN'?'हि':'EN';render();}
function loading(title='Loading live data…'){return `<section class="loading-card"><div class="spinner"></div><b>${title}</b><span>Fetching from KisanLink backend</span></section>`}
function errorCard(message, retry){return `<section class="card error-card"><b>Live data unavailable</b><p>${esc(message)}</p><button class="small-btn dark" onclick="${retry||'location.reload()'}">Retry</button></section>`}
function empty(text){return `<div class="empty"><b>No live records yet</b><span>${esc(text)}</span></div>`}

async function loginSubmit(){
  const mobile=document.querySelector('#mobile')?.value?.trim(); const password=document.querySelector('#password')?.value;
  if(!mobile||!password) return alert('Enter mobile number and password/PIN');
  try{ const data=await api('/api/auth/login',{method:'POST',body:JSON.stringify({mobile,password})}); saveSession(data); go('/dashboard'); }
  catch(e){ alert(e.message); }
}
async function signup(){
  const name=document.querySelector('#su-name')?.value?.trim(), mobile=document.querySelector('#su-mobile')?.value?.trim(), password=document.querySelector('#su-pass')?.value, role=document.querySelector('#su-role')?.value;
  if(!name||!mobile||!password) return alert('Fill all required fields');
  try{const data=await api('/api/auth/register',{method:'POST',body:JSON.stringify({name,mobile,password,role})}); saveSession(data); go('/dashboard');}catch(e){alert(e.message)}
}
function login(){return `<div class="app-shell auth-shell"><div class="login"><div class="login-head"><img class="login-logo" src="${logo}" onerror="this.src='/farmer.svg'"/><div><h1>KisanLink</h1><span class="badge">SIH26132</span><p>Connecting Farmers to Better Markets</p></div></div><div class="role-tabs"><button class="role active">👨‍🌾 Kisan</button><button class="role">🏢 Buyer</button><button class="role">🌾 FPO</button></div><div class="auth-card"><div class="live-note">● LIVE ACCOUNT LOGIN<br/><span>Use your registered KisanLink credentials. No demo account is used.</span></div><div class="form-group"><label>MOBILE NUMBER OR KISAN ID</label><input id="mobile" class="input" inputmode="tel" placeholder="+91 XXXXX XXXXX" autocomplete="tel"/></div><div class="form-group"><label>SECURITY PIN / PASSWORD</label><input id="password" class="input" type="password" placeholder="Enter password" autocomplete="current-password"/></div><div class="row"><label><input type="checkbox"/> Remember this phone</label><button class="link">Forgot PIN?</button></div><button class="btn primary full" onclick="loginSubmit()">Login to Kisan Dashboard →</button><button class="btn light full" onclick="go('/signup')">Create new account</button></div><div class="secure"><div>✓<strong>Encrypted</strong>API</div><div>🔒<strong>JWT</strong>Session</div><div>⌘<strong>Neon</strong>Database</div></div><p class="login-foot">Your account is required before entering the app.</p></div></div>`}
function signupPage(){return `<div class="app-shell auth-shell"><div class="login"><div class="login-head"><img class="login-logo" src="${logo}" onerror="this.src='/farmer.svg'"/><div><h1>Create KisanLink Account</h1><p>Real account • Real backend • Real data</p></div></div><div class="auth-card"><div class="form-group"><label>FULL NAME</label><input id="su-name" class="input" placeholder="Your name"/></div><div class="form-group"><label>MOBILE NUMBER</label><input id="su-mobile" class="input" inputmode="tel" placeholder="+91 XXXXX XXXXX"/></div><div class="form-group"><label>PASSWORD / PIN</label><input id="su-pass" class="input" type="password" placeholder="Create password"/></div><div class="form-group"><label>PROFILE</label><select id="su-role" class="input"><option value="farmer">Farmer</option><option value="buyer">Buyer</option><option value="fpo">FPO</option></select></div><button class="btn primary full" onclick="signup()">Create Account →</button><button class="btn light full" onclick="go('/login')">Already have an account? Login</button></div></div></div>`}

async function dashboard(){
  let data; try{data=await api('/api/me'); state.user=data;}catch(e){clearSession();return go('/login');}
  return layout(`<span class="eyebrow">LIVE KISAN DASHBOARD</span><h1 class="title">Namaste, ${esc(data.name||'Kisan')} Ji</h1><p class="subtitle">Your market activity is coming from the KisanLink backend.</p><section id="dash-data">${loading()}</section>`,'/dashboard');
}
async function dashboardData(){
  try{const [listings,offers,prices]=await Promise.all([api('/api/listings/my'),api('/api/offers/my'),api('/api/market/prices')]);
    const active=listings.filter(x=>x.status==='active');
    document.querySelector('#dash-data').innerHTML=`<div class="grid2"><div class="stat"><div class="label">Best Market Price</div><div class="value">${prices[0]?money(prices[0].modal_price):'—'}</div><div class="meta">${prices[0]?esc(prices[0].crop):'No live feed'}</div></div><div class="stat"><div class="label">Active Listings</div><div class="value">${active.length}</div><div class="meta">From PostgreSQL</div></div><div class="stat"><div class="label">Buyer Offers</div><div class="value">${offers.length}</div><div class="meta">Live backend records</div></div><div class="stat"><div class="label">Account</div><div class="value">${esc(state.user?.role||'farmer')}</div><div class="meta">${state.user?.kyc_verified?'KYC verified':'KYC pending'}</div></div></div><section class="section ai"><div class="row"><span class="badge">✦ LIVE MARKET INSIGHT</span><span class="mini">${time(prices[0]?.updated_at)}</span></div><p>${prices.length?`Current ${esc(prices[0].crop)} modal price is ${money(prices[0].modal_price)} at ${esc(prices[0].mandi)}. Compare nearby mandis before listing.`:'No market feed is configured yet. Connect an authorized mandi/e-NAM feed to enable real-time insights.'}</p><div class="cta"><button class="btn mint" onclick="go('/prices')">View Live Prices</button><button class="btn light" onclick="go('/sell')">Sell Produce</button></div></section><section class="section"><div class="section-head"><div class="section-title">My Live Listings</div><button class="link" onclick="go('/sell')">+ New Lot</button></div>${active.length?active.map(x=>`<div class="list-card"><div class="row"><div><h4>${esc(x.crop||'Produce')}</h4><p>${esc(x.quantity||0)} ${esc(x.unit||'qtl')} • ${esc(x.quality||'Quality pending')}</p></div>${status(x.status||'active')}</div><div class="row"><b class="price">${money(x.asking_price)}</b><span class="mini">Updated ${time(x.updated_at)}</span></div></div>`).join(''):empty('Create your first produce listing from Sell.')}</section>`;
  }catch(e){document.querySelector('#dash-data').innerHTML=errorCard(e.message);}
}
function prices(){return layout(`<span class="eyebrow">LIVE MARKET API</span><h1 class="title">Mandi Market Prices</h1><p class="subtitle">Only backend-sourced prices are shown here.</p><div class="search">⌕ <input id="price-search" placeholder="Search crop or mandi..." oninput="filterPrices()"/></div><div id="price-list">${loading('Fetching live mandi prices…')}</div>`,'/prices');}
async function priceData(){try{const data=await api('/api/market/prices');window.__prices=data;renderPriceRows(data);}catch(e){document.querySelector('#price-list').innerHTML=errorCard(e.message);}}
function renderPriceRows(data){const el=document.querySelector('#price-list'); if(!el)return; const q=(document.querySelector('#price-search')?.value||'').toLowerCase(); const rows=data.filter(x=>`${x.crop} ${x.mandi} ${x.variety||''}`.toLowerCase().includes(q)); el.innerHTML=rows.length?rows.map(x=>`<div class="list-card"><div class="row"><div class="crop"><div class="crop-emoji">🌾</div><div><h4>${esc(x.crop)}</h4><p>${esc(x.mandi)} • ${esc(x.variety||'')}</p></div></div><span class="badge">LIVE</span></div><div class="row"><span class="price">${money(x.modal_price)}<small> / ${esc(x.unit||'qtl')}</small></span><span class="mini">Min ${money(x.min_price)} • Max ${money(x.max_price)}</span></div><div class="source-line">Source: ${esc(x.source||'KisanLink backend')} • Updated ${time(x.updated_at)}</div><button class="small-btn dark" onclick="go('/sell')">Sell at this market</button></div>`).join(''):empty('No records match your search.');}
function filterPrices(){renderPriceRows(window.__prices||[])}

function sell(){return layout(`<span class="eyebrow">LIVE LISTING → POSTGRESQL</span><h1 class="title">Sell Your Produce</h1><p class="subtitle">Create a real listing. It will be saved to your KisanLink account.</p><div class="card"><div class="form-group"><label>CROP</label><input id="s-crop" class="input" placeholder="e.g. Wheat"/></div><div class="grid2"><div class="form-group"><label>QUANTITY</label><input id="s-qty" class="input" type="number" min="0" placeholder="Quintals"/></div><div class="form-group"><label>UNIT</label><select id="s-unit" class="input"><option>qtl</option><option>kg</option><option>crate</option></select></div></div><div class="grid2"><div class="form-group"><label>QUALITY / GRADE</label><input id="s-quality" class="input" placeholder="Grade A"/></div><div class="form-group"><label>ASKING PRICE ₹</label><input id="s-price" class="input" type="number" min="0" placeholder="Current expected price"/></div></div><div class="form-group"><label>DESCRIPTION</label><textarea id="s-desc" class="input" rows="4" placeholder="Harvest, variety, location…"></textarea></div><button class="btn primary full" onclick="createListing()">List Produce & Request Bids →</button></div><section id="my-listings" class="section">${loading()}</section>`,'/sell');}
async function createListing(){try{const body={crop:document.querySelector('#s-crop').value.trim(),quantity:Number(document.querySelector('#s-qty').value),unit:document.querySelector('#s-unit').value,quality:document.querySelector('#s-quality').value.trim(),asking_price:Number(document.querySelector('#s-price').value),description:document.querySelector('#s-desc').value.trim()}; if(!body.crop||!body.quantity) return alert('Crop and quantity are required'); await api('/api/listings',{method:'POST',body:JSON.stringify(body)}); alert('Listing saved to backend'); await loadMyListings();}catch(e){alert(e.message)}}
async function loadMyListings(){try{const rows=await api('/api/listings/my');document.querySelector('#my-listings').innerHTML=`<div class="section-head"><div class="section-title">My Listings</div>${status(`${rows.length} total`)}</div>${rows.length?rows.map(x=>`<div class="list-card"><div class="row"><div><h4>${esc(x.crop)}</h4><p>${esc(x.quantity)} ${esc(x.unit)} • ${esc(x.quality||'')}</p></div>${status(x.status)}</div><b class="price">${money(x.asking_price)}</b><div class="source-line">Created ${time(x.created_at)}</div></div>`).join(''):empty('No listings yet.')}`;}catch(e){document.querySelector('#my-listings').innerHTML=errorCard(e.message)}}

function buyers(){return layout(`<span class="eyebrow">BACKEND BUYER MARKETPLACE</span><h1 class="title">Buyer Marketplace</h1><p class="subtitle">Verified buyer records and offers loaded from the API.</p><div id="buyer-list">${loading()}</div>`,'/buyers');}
async function buyerData(){try{const rows=await api('/api/offers/my');document.querySelector('#buyer-list').innerHTML=rows.length?rows.map(x=>`<div class="list-card"><div class="row"><div><h4>${esc(x.buyer_name||'Buyer')}</h4><p>Offer for ${esc(x.crop||'produce')} • ${time(x.created_at)}</p></div>${status(x.status||'pending')}</div><div class="row"><span class="price">${money(x.price)}<small> / qtl</small></span><b>${esc(x.quantity||0)} qtl</b></div><div class="cta"><button class="small-btn dark" onclick="acceptOffer('${esc(x.id)}')">Accept Bid</button></div></div>`).join(''):empty('No buyer offers have been created for your account yet.');}catch(e){document.querySelector('#buyer-list').innerHTML=errorCard(e.message)}}
async function acceptOffer(id){try{await api(`/api/offers/${encodeURIComponent(id)}/accept`,{method:'POST'});alert('Offer accepted');buyerData();}catch(e){alert(e.message)}}

function transactions(){return layout(`<span class="eyebrow">REAL TRANSACTION LEDGER</span><h1 class="title">Transactions & Escrow Wallet</h1><p class="subtitle">No fabricated balance or settlement is displayed. Values below come from your transaction ledger.</p><div id="tx-list">${loading()}</div>`,'/transactions');}
async function txData(){try{const rows=await api('/api/transactions/my');document.querySelector('#tx-list').innerHTML=rows.length?rows.map(x=>`<div class="list-card"><div class="row"><div><h4>${esc(x.type||'Transaction')}</h4><p>${esc(x.reference||'')} • ${time(x.created_at)}</p></div>${status(x.status||'pending')}</div><div class="row"><span class="price">${money(x.amount)}</span><span class="mini">${esc(x.payment_method||'—')}</span></div></div>`).join(''):empty('No transactions yet. Complete a real sale to populate this ledger.');}catch(e){document.querySelector('#tx-list').innerHTML=errorCard(e.message)}}
function notifications(){return layout(`<span class="eyebrow">LIVE ACCOUNT NOTIFICATIONS</span><h1 class="title">Notifications</h1><div id="notice-list">${loading()}</div>`,'/notifications');}
async function noticeData(){try{const rows=await api('/api/notifications');document.querySelector('#notice-list').innerHTML=rows.length?rows.map(x=>`<div class="list-card"><div class="row"><h4>${esc(x.title||'Notification')}</h4>${status(x.read?'Read':'New')}</div><p>${esc(x.message||'')}</p><span class="mini">${time(x.created_at)}</span></div>`).join(''):empty('No notifications yet.');}catch(e){document.querySelector('#notice-list').innerHTML=errorCard(e.message)}}
function profile(){return layout(`<span class="eyebrow">ACCOUNT</span><h1 class="title">My Profile</h1><section class="card profile-card"><img class="profile-logo" src="${logo}" onerror="this.src='/farmer.svg'"/><h2>${esc(state.user?.name||'KisanLink User')}</h2><p>${esc(state.user?.mobile||'')}</p><div class="grid2"><div class="stat"><div class="label">Role</div><div class="value">${esc(state.user?.role||'farmer')}</div></div><div class="stat"><div class="label">KYC</div><div class="value">${state.user?.kyc_verified?'Verified':'Pending'}</div></div></div><button class="btn light full" onclick="logout()">Logout</button></section>`,'');}
function logout(){clearSession();location.hash='/login';render();}
function fpo(){return layout(`<span class="eyebrow">FPO HUB</span><h1 class="title">FPO & Collective Hub</h1><p class="subtitle">FPO data is shown only when available from the backend.</p><section id="fpo-data">${loading()}</section>`,'/buyers');}
async function fpoData(){try{const rows=await api('/api/fpo');document.querySelector('#fpo-data').innerHTML=rows?.length?rows.map(x=>`<div class="list-card"><h4>${esc(x.name)}</h4><p>${esc(x.description||'')}</p></div>`).join(''):empty('No FPO records are configured yet.');}catch(e){document.querySelector('#fpo-data').innerHTML=errorCard(e.message)}}
function home(){ if(!isAuthed()) return login(); return dashboard(); }

async function render(){
  loadSession(); if(!isAuthed() && !['/login','/signup','/'].includes(state.route)){state.route='/login';location.hash='/login';}
  const root=document.querySelector('#app'); if(!root)return;
  if(state.route==='/login') root.innerHTML=login();
  else if(state.route==='/signup') root.innerHTML=signupPage();
  else if(state.route==='/dashboard'||state.route==='/') {root.innerHTML=await dashboard(); dashboardData();}
  else if(state.route==='/prices'){root.innerHTML=prices();priceData();}
  else if(state.route==='/sell'){root.innerHTML=sell();loadMyListings();}
  else if(state.route==='/buyers'){root.innerHTML=buyers();buyerData();}
  else if(state.route==='/transactions'){root.innerHTML=transactions();txData();}
  else if(state.route==='/notifications'){root.innerHTML=notifications();noticeData();}
  else if(state.route==='/profile') root.innerHTML=profile();
  else if(state.route==='/fpo'){root.innerHTML=fpo();fpoData();}
  else root.innerHTML=login();
}
window.go=go; window.render=render; window.loginSubmit=loginSubmit; window.signup=signup; window.toggleLang=toggleLang; window.createListing=createListing; window.loadMyListings=loadMyListings; window.filterPrices=filterPrices; window.acceptOffer=acceptOffer; window.logout=logout;
render();
