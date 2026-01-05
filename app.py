import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAGANOCAFE", page_icon="☕", layout="wide")

# --- CSS PRESTAZIONALE E GRAFICA ---
st.markdown("""
    <style>
    .stApp { background-color: #121417; color: #FFFFFF; }
    
    /* Stile Card */
    .card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        color: #121417;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    
    /* Pulsanti Giallo Oro */
    .stButton > button {
        border-radius: 8px !important;
        background-color: #d4af37 !important;
        color: black !important;
        font-weight: bold !important;
        border: none !important;
    }
    
    .quantita-display { 
        font-size: 20px; font-weight: bold; color: #00FF00; 
        text-align: center; background-color: #1E2127; padding: 5px; border-radius: 5px;
    }
    
    .stTabs [aria-selected="true"] { background-color: #d4af37 !important; color: black !important; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIONE DATI ---
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

# --- HEADER ---
c_l, c_t = st.columns([1, 5])
with c_l:
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    else: st.title("☕")
with c_t:
    st.markdown(f"# PAGANOCAFE - {'GESTIONE' if admin_mode else 'ORDINA'}")

# ==========================================
# SEZIONE ADMIN
# ==========================================
if admin_mode:
    tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "💰 CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])

    with tab_ordini:
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        cols = st.columns(4)
        for idx, t in enumerate(tavoli):
            with cols[idx % 4]:
                st.markdown(f"### Tavolo {t}")
                items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                for r in items:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        c1.write(f"**{r['prodotto']}**")
                        if r['stato'] == "NO":
                            if c2.button("OK", key=f"ok_{r['id_univoco']}"):
                                for o in ordini_attuali: 
                                    if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                                salva_ordini(ordini_attuali); st.rerun()
                        else: c2.write("✅")

    with tab_vetrina:
        stk = carica_stock()
        brioches = menu_df[menu_df['categoria'] == 'BRIOCHE&CORNETTI']['prodotto'].unique()
        cv = st.columns(4)
        for i, p in enumerate(brioches):
            q = stk.get(p, 0)
            if cv[i % 4].button(f"{p} ({q})", key=f"v_{p}"):
                stk[p] = q + 1; salva_stock(stk); st.rerun()

    with tab_stock:
        st.subheader("📦 Gestione Stock Cornetti")
        stk = carica_stock()
        brioches = menu_df[menu_df['categoria'] == 'BRIOCHE&CORNETTI']['prodotto'].unique()
        for p in brioches:
            q = stk.get(p, 0)
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write(f"**{p}**")
                if c2.button("➖", key=f"m_{p}"): stk[p]=max(0, q-1); salva_stock(stk); st.rerun()
                c3.markdown(f"<div class='quantita-display'>{q}</div>", unsafe_allow_html=True)
                if c4.button("➕", key=f"p_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()

    with tab_menu:
        sub1, sub2 = st.tabs(["📂 CATEGORIE", "🍔 PRODOTTI"])
        
        with sub1:
            cats_nel_file = menu_df['categoria'].unique().tolist() if not menu_df.empty else []
            tutte_le_cats = sorted(list(set(cats_nel_file + st.session_state.nuove_categorie)))
            for cat in tutte_le_cats:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"**{cat}**")
                    if c2.button("🗑️", key=f"del_cat_{cat}"):
                        menu_df = menu_df[menu_df['categoria'] != cat]
                        salva_menu(menu_df)
                        if cat in st.session_state.nuove_categorie: st.session_state.nuove_categorie.remove(cat)
                        st.rerun()
            new_c = st.text_input("Nome Nuova Categoria")
            if st.button("CREA CATEGORIA") and new_c:
                st.session_state.nuove_categorie.append(new_c.upper().strip())
                st.rerun()

        with sub2:
            cats_per_p = sorted(list(set(cats_nel_file + st.session_state.nuove_categorie)))
            with st.form("add_p"):
                f_cat = st.selectbox("Categoria", cats_per_p if cats_per_p else ["BRIOCHE&CORNETTI"])
                f_nome = st.text_input("Nome Prodotto")
                f_prezzo = st.number_input("Prezzo", step=0.1)
                if st.form_submit_button("AGGIUNGI PRODOTTO"):
                    nuovo = pd.DataFrame([{"categoria": f_cat, "prodotto": f_nome, "prezzo": f_prezzo}])
                    salva_menu(pd.concat([menu_df, nuovo])); st.rerun()
            st.divider()
            for i, r in menu_df.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.write(f"{r['categoria']} - **{r['prodotto']}**")
                    c2.write(f"€{r['prezzo']:.2f}")
                    if c3.button("🗑️", key=f"dp_{i}"): salva_menu(menu_df.drop(i)); st.rerun()

# ==========================================
# SEZIONE CLIENTE
# ==========================================
else:
    tavolo = st.selectbox("Seleziona Tavolo", ["---"] + [str(i) for i in range(1, 21)])
    if tavolo != "---":
        stk = carica_stock()
        if st.session_state.carrello:
            with st.container(border=True):
                st.subheader("🛒 Carrello")
                for idx, it in enumerate(st.session_state.carrello):
                    st.write(f"{it['prodotto']} - €{it['prezzo']:.2f}")
                if st.button("INVIA ORDINE", type="primary", use_container_width=True):
                    nuovi = ordini_attuali.copy()
                    for it in st.session_state.carrello:
                        nuovi.append({"id_univoco": str(time.time())+it['prodotto'], "tavolo": tavolo, "prodotto": it['prodotto'], "prezzo": it['prezzo'], "stato": "NO", "orario": datetime.now().strftime("%H:%M")})
                    salva_ordini(nuovi); st.session_state.carrello = []; st.success("Inviato!"); time.sleep(1); st.rerun()
        
        if not menu_df.empty:
            cat_sel = st.radio("Cosa vuoi ordinare?", menu_df['categoria'].unique(), horizontal=True)
            for _, r in menu_df[menu_df['categoria'] == cat_sel].iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    q = stk.get(r['prodotto'], 999) if r['categoria'] == 'BRIOCHE&CORNETTI' else 999
                    c1.write(f"**{r['prodotto']}** - €{r['prezzo']:.2f}")
                    if q > 0:
                        if c2.button("ADD", key=f"add_{r['prodotto']}"):
                            st.session_state.carrello.append({"prodotto": r['prodotto'], "prezzo": r['prezzo']})
                            if r['categoria'] == 'BRIOCHE&CORNETTI': stk[r['prodotto']] -= 1; salva_stock(stk)
                            st.rerun()
                    else: c2.error("FINITO")
