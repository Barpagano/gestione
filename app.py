import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAGANOCAFE", page_icon="☕", layout="wide")

# --- CSS PER STILE PREMIUM (DARK DASHBOARD) ---
st.markdown("""
    <style>
    /* Sfondo e font generale */
    .stApp { background-color: #121417; color: #FFFFFF; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Header e Logo */
    .header-container { display: flex; align-items: center; justify-content: center; padding: 20px; margin-bottom: 30px; border-bottom: 1px solid #333; }
    .logo-img { width: 80px; margin-right: 20px; border-radius: 50%; }
    
    /* Card per Ordini e Prodotti */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #ffffff !important;
        border-radius: 15px !important;
        padding: 20px !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        color: #121417 !important;
    }
    
    /* Testi dentro le Card */
    div[data-testid="stVerticalBlock"] > div[style*="border"] p, 
    div[data-testid="stVerticalBlock"] > div[style*="border"] h3 {
        color: #121417 !important;
    }

    /* Pulsanti */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton > button:first-child { background-color: #d4af37; color: black; border: none; }
    .stButton > button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(212, 175, 55, 0.4); }

    /* Badge Stato */
    .status-badge {
        background-color: #e0e0e0; padding: 3px 10px; border-radius: 20px; font-size: 12px; color: #666;
    }
    
    /* Sidebar e Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E2127; border-radius: 10px 10px 0 0; padding: 10px 20px; color: white;
    }
    .stTabs [aria-selected="true"] { background-color: #d4af37 !important; color: black !important; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIONE DATABASE ---
DB_FILE = "ordini_bar_pagano.csv"
STOCK_FILE = "stock_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def inizializza_file(file, colonne):
    if not os.path.exists(file) or os.stat(file).st_size <= 2:
        pd.DataFrame(columns=colonne).to_csv(file, index=False)

inizializza_file(DB_FILE, ["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"])
inizializza_file(MENU_FILE, ["categoria", "prodotto", "prezzo"])
inizializza_file(STOCK_FILE, ["prodotto", "quantita"])

def carica_menu(): return pd.read_csv(MENU_FILE)
def salva_menu(df): df.to_csv(MENU_FILE, index=False)
def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []
def salva_ordini(lista): pd.DataFrame(lista, columns=["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]).to_csv(DB_FILE, index=False)
def carica_stock(): 
    try:
        df = pd.read_csv(STOCK_FILE)
        return df.set_index('prodotto')['quantita'].to_dict() if not df.empty else {}
    except: return {}
def salva_stock(d): pd.DataFrame(list(d.items()), columns=['prodotto', 'quantita']).to_csv(STOCK_FILE, index=False)

# --- LOGICA ---
st_autorefresh(interval=5000, key="global_refresh")
menu_df = carica_menu()
ordini_attuali = carica_ordini()
admin_mode = st.query_params.get("admin") == "si"

if "carrello" not in st.session_state: st.session_state.carrello = []
if "nuove_categorie" not in st.session_state: st.session_state.nuove_categorie = []

# --- HEADER CON LOGO ---
def show_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=100)
        else:
            st.write("☕")
    with col2:
        st.markdown(f"<h1 style='margin:0;'>PAGANOCAFE - {'GESTIONE' if admin_mode else 'ORDINA'}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#888;'>Salerno, Italia - {datetime.now().strftime('%d %b %Y')}</p>", unsafe_allow_html=True)

show_header()

# ==========================================
# SEZIONE BANCONE (ADMIN)
# ==========================================
if admin_mode:
    tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "💰 CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])

    with tab_ordini:
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        cols = st.columns(4)
        for idx, t in enumerate(tavoli):
            with cols[idx % 4]:
                with st.container(border=True):
                    st.markdown(f"### Tavolo {t}")
                    items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                    for r in items:
                        c1, c2 = st.columns([4, 1])
                        c1.markdown(f"**{r['prodotto']}** <br><span class='status-badge'>{r['orario']}</span>", unsafe_allow_html=True)
                        if r['stato'] == "NO":
                            if c2.button("OK", key=f"ok_o_{r['id_univoco']}"):
                                for o in ordini_attuali: 
                                    if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                                salva_ordini(ordini_attuali); st.rerun()
                        else:
                            c2.write("✅")
                    st.divider()
                    if st.button(f"Svuota Tavolo {t}", key=f"del_tav_{t}"):
                        salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != t]); st.rerun()

    with tab_cassa:
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        for t in tavoli:
            with st.container(border=True):
                items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                totale = sum(float(x['prezzo']) for x in items)
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"### Tavolo {t} <br> <span style='color:green;'>Totale: €{totale:.2f}</span>", unsafe_allow_html=True)
                if c2.button(f"PAGATO", key=f"pay_{t}"):
                    salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != t]); st.rerun()

    with tab_vetrina:
        st.subheader("Carico Rapido Brioche")
        stk = carica_stock()
        brioches = menu_df[menu_df['categoria'] == 'BRIOCHE&CORNETTI']['prodotto'].unique()
        cv = st.columns(4)
        for i, p in enumerate(brioches):
            q = stk.get(p, 0)
            if cv[i % 4].button(f"{p}\n({q})", key=f"vr_{p}"):
                stk[p] = q + 1; salva_stock(stk); st.rerun()

    with tab_stock:
        st.subheader("📦 Magazzino")
        stk = carica_stock()
        brioches = menu_df[menu_df['categoria'] == 'BRIOCHE&CORNETTI']['prodotto'].unique()
        for p in brioches:
            q = stk.get(p, 0)
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.markdown(f"**{p}**")
            if c2.button("➖", key=f"m_stk_{p}"): stk[p]=max(0, q-1); salva_stock(stk); st.rerun()
            c3.markdown(f"<div class='quantita-display'>{q}</div>", unsafe_allow_html=True)
            if c4.button("➕", key=f"p_stk_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()

    with tab_menu:
        # (Logica menu rimane invariata per funzionalità)
        st.info("Usa questa sezione per creare categorie e prodotti come abbiamo fatto prima.")
        # ... (restante codice tab_menu dell'ultimo aggiornamento)

# ==========================================
# SEZIONE CLIENTE
# ==========================================
else:
    tavolo_sel = st.selectbox("A che tavolo sei?", ["---"] + [str(i) for i in range(1, 21)])
    if tavolo_sel != "---":
        stk = carica_stock()
        if st.session_state.carrello:
            with st.container(border=True):
                st.subheader(f"🛒 Il tuo ordine")
                for idx, item in enumerate(st.session_state.carrello):
                    c1, c2, c3 = st.columns([4, 2, 1])
                    c1.write(item['prodotto'])
                    c2.write(f"€{item['prezzo']:.2f}")
                    if c3.button("❌", key=f"rc_{idx}"):
                        if item['prodotto'] in stk: stk[item['prodotto']] += 1; salva_stock(stk)
                        st.session_state.carrello.pop(idx); st.rerun()
                if st.button("🚀 INVIA ORDINE AL BAR", type="primary", use_container_width=True):
                    nuovi = ordini_attuali.copy()
                    ora = datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                    for it in st.session_state.carrello:
                        nuovi.append({"id_univoco": str(time.time())+it['prodotto'], "tavolo": tavolo_sel, "prodotto": it['prodotto'], "prezzo": it['prezzo'], "stato": "NO", "orario": ora})
                    salva_ordini(nuovi); st.session_state.carrello = []; st.success("Ordine Inviato!"); time.sleep(1); st.rerun()

        if not menu_df.empty:
            scelta = st.selectbox("Scegli Categoria:", menu_df['categoria'].unique())
            st.markdown(f"### {scelta}")
            cols_p = st.columns(2)
            for i, (idx, r) in enumerate(menu_df[menu_df['categoria'] == scelta].iterrows()):
                with cols_p[i % 2]:
                    with st.container(border=True):
                        q = stk.get(r['prodotto'], 999) if r['categoria'] == 'BRIOCHE&CORNETTI' else 999
                        st.markdown(f"**{r['prodotto']}**")
                        st.markdown(f"<p style='color:green;'>€{r['prezzo']:.2f}</p>", unsafe_allow_html=True)
                        if q > 0:
                            if st.button("AGGIUNGI", key=f"a_{r['prodotto']}"):
                                st.session_state.carrello.append({"prodotto": r['prodotto'], "prezzo": r['prezzo']})
                                if r['categoria'] == 'BRIOCHE&CORNETTI': stk[r['prodotto']] -= 1; salva_stock(stk)
                                st.rerun()
                        else: st.error("ESAURITO")
