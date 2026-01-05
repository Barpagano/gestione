import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAGANOCAFE", page_icon="☕", layout="wide")

# --- CSS STILE PREMIUM ---
st.markdown("""
    <style>
    .stApp { background-color: #121417; color: #FFFFFF; }
    .stButton > button { border-radius: 8px !important; font-weight: bold !important; }
    .stButton > button[kind="primary"] { background-color: #d4af37 !important; color: black !important; border: none !important; }
    .stButton > button[kind="secondary"] { background-color: #2E7D32 !important; color: white !important; border: none !important; }
    .quantita-display { 
        font-size: 20px; font-weight: bold; color: #00FF00; 
        text-align: center; background-color: #1E2127; padding: 5px; border-radius: 5px;
    }
    .tavolo-card {
        background-color: #1E2127; padding: 15px; border-radius: 12px; border: 1px solid #333; margin-bottom: 15px;
    }
    .esaurito-label {
        color: #FF4B4B; font-weight: bold; text-align: center; border: 1px solid #FF4B4B;
        padding: 5px; border-radius: 8px; display: block;
    }
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
if "tavolo_selezionato" not in st.session_state: st.session_state.tavolo_selezionato = None

# --- HEADER ---
c1, c2 = st.columns([1, 5])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=100)
    else: st.title("☕")
with c2:
    st.title(f"PAGANOCAFE - {'GESTIONE' if admin_mode else 'ORDINA'}")

# ==========================================
# SEZIONE BANCONE (ADMIN)
# ==========================================
if admin_mode:
    tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "💰 CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])

    with tab_ordini:
        tavoli_aperti = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        cols = st.columns(3)
        for idx, t in enumerate(tavoli_aperti):
            with cols[idx % 3]:
                st.markdown(f"<div class='tavolo-card'>", unsafe_allow_html=True)
                st.subheader(f"Tavolo {t}")
                items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                for r in items:
                    c1, c2, c3 = st.columns([1, 4, 1])
                    if c1.button("❌", key=f"del_{r['id_univoco']}"):
                        salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']]); st.rerun()
                    testo_col = "#888" if r['stato'] == "SI" else "#FFF"
                    c2.markdown(f"<span style='color:{testo_col}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                    if r['stato'] == "NO":
                        if c3.button("OK", key=f"ok_{r['id_univoco']}"):
                            for o in ordini_attuali: 
                                if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                            salva_ordini(ordini_attuali); st.rerun()
                    else: c3.write("✅")
                st.markdown("</div>", unsafe_allow_html=True)

    with tab_cassa:
        tavoli_aperti = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        if not tavoli_aperti: st.info("Nessun ordine aperto.")
        for t in tavoli_aperti:
            with st.container(border=True):
                items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                totale = sum(float(x['prezzo']) for x in items)
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"### Tavolo {t} - **€ {totale:.2f}**")
                if c2.button(f"CHIUDI CONTO", key=f"pay_{t}", type="primary"):
                    salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != t]); st.rerun()

    with tab_vetrina:
        stk = carica_stock()
        brioches = menu_df[menu_df['categoria'] == 'BRIOCHE&CORNETTI']['prodotto'].unique()
        cv = st.columns(4)
        for i, p in enumerate(brioches):
            q = stk.get(p, 0)
            if cv[i % 4].button(f"{p} ({q})", key=f"v_{p}", use_container_width=True):
                stk[p] = q + 1; salva_stock(stk); st.rerun()

    with tab_stock:
        st.subheader("📦 Magazzino Cornetti")
        stk = carica_stock()
        brioches = menu_df[menu_df['categoria'] == 'BRIOCHE&CORNETTI']['prodotto'].unique()
        for p in brioches:
            q = stk.get(p, 0)
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{p}**")
            if c2.button("➖", key=f"m_{p}"): stk[p]=max(0, q-1); salva_stock(stk); st.rerun()
            c3.markdown(f"<div class='quantita-display'>{q}</div>", unsafe_allow_html=True)
            if c4.button("➕", key=f"p_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()

    with tab_menu:
        sub_cat, sub_prod = st.tabs(["📂 CATEGORIE", "🍔 PRODOTTI"])
        with sub_cat:
            cats_file = menu_df['categoria'].unique().tolist() if not menu_df.empty else []
            tutte_cats = sorted(list(set(cats_file + st.session_state.nuove_categorie)))
            for cat in tutte_cats:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    nuovo_n = c1.text_input("Rinomina", value=cat, key=f"rn_{cat}")
                    if c2.button("SALVA", key=f"s_{cat}"):
                        menu_df.loc[menu_df['categoria'] == cat, 'categoria'] = nuovo_n.upper().strip()
                        salva_menu(menu_df); st.rerun()
                    if c3.button("ELIMINA", key=f"d_{cat}"):
                        salva_menu(menu_df[menu_df['categoria'] != cat]); st.rerun()
            st.divider()
            nc = st.text_input("Nuova Categoria")
            if st.button("CREA"):
                st.session_state.nuove_categorie.append(nc.upper().strip()); st.rerun()
        with sub_prod:
            cats_p = sorted(list(set(menu_df['categoria'].unique().tolist() + st.session_state.nuove_categorie)))
            with st.form("ap"):
                f_c = st.selectbox("Categoria", cats_p if cats_p else ["BRIOCHE&CORNETTI"])
                f_n = st.text_input("Nome")
                f_p = st.number_input("Prezzo", step=0.1)
                if st.form_submit_button("AGGIUNGI"):
                    nuovo = pd.DataFrame([{"categoria": f_c, "prodotto": f_n, "prezzo": f_p}])
                    salva_menu(pd.concat([menu_df, nuovo])); st.rerun()
            st.divider()
            for i, r in menu_df.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.write(f"**{r['prodotto']}** ({r['categoria']})")
                    c2.write(f"€{r['prezzo']:.2f}")
                    if c3.button("Elimina", key=f"ep_{i}"): salva_menu(menu_df.drop(i)); st.rerun()

# ==========================================
# SEZIONE CLIENTE
# ==========================================
else:
    if st.session_state.tavolo_selezionato is None:
        st.markdown("<h3 style='text-align:center;'>SELEZIONA IL TUO TAVOLO</h3>", unsafe_allow_html=True)
        for riga in range(5):
            cols = st.columns(4)
            for colonna in range(4):
                numero_tavolo = riga * 4 + colonna + 1
                if cols[colonna].button(f"{numero_tavolo}", key=f"tav_{numero_tavolo}", use_container_width=True):
                    st.session_state.tavolo_selezionato = str(numero_tavolo)
                    st.rerun()
    
    else:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"## 🪑 TAVOLO {st.session_state.tavolo_selezionato}")
        if c2.button("CAMBIA"):
            st.session_state.tavolo_selezionato = None
            st.rerun()

        stk = carica_stock()
        
        if st.session_state.carrello:
            with st.container(border=True):
                st.subheader("🛒 Il tuo Ordine")
                for idx, it in enumerate(st.session_state.carrello):
                    cc1, cc2 = st.columns([4, 1])
                    cc1.write(f"{it['prodotto']} - €{it['prezzo']:.2f}")
                    if cc2.button("X", key=f"rc_{idx}"):
                        # Correzione sicurezza stock
                        if it['prodotto'] in stk: 
                            stk[it['prodotto']] += 1
                            salva_stock(stk)
                        st.session_state.carrello.pop(idx); st.rerun()
                if st.button("🚀 INVIA ORDINE AL BAR", type="primary", use_container_width=True):
                    nuovi = ordini_attuali.copy()
                    for it in st.session_state.carrello:
                        nuovi.append({"id_univoco": str(time.time())+it['prodotto'], "tavolo": st.session_state.tavolo_selezionato, "prodotto": it['prodotto'], "prezzo": it['prezzo'], "stato": "NO", "orario": datetime.now().strftime("%H:%M")})
                    salva_ordini(nuovi); st.session_state.carrello = []; st.success("Ordine Inviato!"); time.sleep(1); st.rerun()

        if not menu_df.empty:
            cat_sel = st.radio("COSA DESIDERI?", menu_df['categoria'].unique(), horizontal=True)
            for _, r in menu_df[menu_df['categoria'] == cat_sel].iterrows():
                with st.container(border=True):
                    cp1, cp2 = st.columns([3, 1])
                    q = stk.get(r['prodotto'], 999) if r['categoria'] == 'BRIOCHE&CORNETTI' else 999
                    cp1.write(f"**{r['prodotto']}** - €{r['prezzo']:.2f}")
                    
                    if q > 0:
                        if cp2.button("AGGIUNGI", key=f"add_{r['prodotto']}", use_container_width=True):
                            st.session_state.carrello.append({"prodotto": r['prodotto'], "prezzo": r['prezzo']})
                            if r['categoria'] == 'BRIOCHE&CORNETTI':
                                # CORREZIONE: Inizializza se assente prima di scalare
                                if r['prodotto'] not in stk: stk[r['prodotto']] = 0
                                stk[r['prodotto']] = max(0, stk[r['prodotto']] - 1)
                                salva_stock(stk)
                            st.rerun()
                    else:
                        cp2.markdown("<span class='esaurito-label'>ESAURITO</span>", unsafe_allow_html=True)
