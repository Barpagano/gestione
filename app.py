import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAGANOCAFE", page_icon="☕", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton > button { height: 40px !important; font-size: 13px !important; border-radius: 8px !important; }
    .stButton > button[kind="secondary"] { background-color: #d4af37; color: black; }
    .quantita-display { 
        font-size: 18px !important; font-weight: bold !important; color: #00FF00 !important; 
        text-align: center; background-color: #1E2127; padding: 5px; border-radius: 5px; border: 1px solid #333;
    }
    .carrello-box {
        background-color: #1E2127; padding: 15px; border-radius: 10px; border: 2px solid #d4af37; margin-bottom: 20px;
    }
    .categoria-header {
        background-color: #d4af37; color: black; padding: 5px 15px; border-radius: 5px; font-weight: bold; margin-bottom: 10px;
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

# Inizializzazione variabili di sessione
if "carrello" not in st.session_state: st.session_state.carrello = []
if "nuove_categorie" not in st.session_state: st.session_state.nuove_categorie = []

# ==========================================
# SEZIONE BANCONE (ADMIN)
# ==========================================
if admin_mode:
    st.title("☕ PAGANOCAFE - Gestione")
    tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "💰 CASSA", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])

    with tab_ordini:
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        cols = st.columns(4)
        for idx, t in enumerate(tavoli):
            with cols[idx % 4]:
                with st.container(border=True):
                    st.write(f"**Tavolo {t}**")
                    items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                    for r in items:
                        c1, c2, c3 = st.columns([0.6, 3, 1])
                        if c1.button("❌", key=f"del_o_{r['id_univoco']}"):
                            salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']]); st.rerun()
                        cl = "servito" if r['stato'] == "SI" else ""
                        c2.write(f"{r['prodotto']}")
                        if r['stato'] == "NO" and c3.button("Ok", key=f"ok_o_{r['id_univoco']}"):
                            for o in ordini_attuali: 
                                if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                            salva_ordini(ordini_attuali); st.rerun()

    with tab_cassa:
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
        for t in tavoli:
            with st.container(border=True):
                items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                totale = sum(float(x['prezzo']) for x in items)
                c1, c2 = st.columns([2, 1])
                c1.write(f"**Tavolo {t}** - €{totale:.2f}")
                if c2.button(f"CHIUDI {t}", key=f"pay_{t}"):
                    salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != t]); st.rerun()

    with tab_stock:
        st.subheader("📦 Stock BRIOCHE&CORNETTI")
        stk = carica_stock()
        brioches = menu_df[menu_df['categoria'] == 'BRIOCHE&CORNETTI']['prodotto'].unique()
        for p in brioches:
            if p not in stk: stk[p] = 0; salva_stock(stk)
            q = stk[p]
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{p}**")
            if c2.button("➖", key=f"m_stk_{p}"): stk[p]=max(0, q-1); salva_stock(stk); st.rerun()
            c3.markdown(f"<div class='quantita-display'>{q}</div>", unsafe_allow_html=True)
            if c4.button("➕", key=f"p_stk_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()

    with tab_menu:
        sub_cat, sub_prod = st.tabs(["📂 CATEGORIE", "🍔 PRODOTTI"])

        with sub_cat:
            st.subheader("Gestione Categorie")
            # Uniamo categorie salvate e categorie create in sessione
            cats_nel_file = menu_df['categoria'].unique().tolist() if not menu_df.empty else []
            tutte_le_cats = sorted(list(set(cats_nel_file + st.session_state.nuove_categorie)))
            
            for cat in tutte_le_cats:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    nuovo_nome = col1.text_input("Nome Categoria", value=cat, key=f"edit_cat_{cat}")
                    if col2.button("SALVA", key=f"save_cat_{cat}"):
                        if not menu_df.empty:
                            menu_df.loc[menu_df['categoria'] == cat, 'categoria'] = nuovo_nome.upper().strip()
                            salva_menu(menu_df)
                        # Aggiorna anche in sessione
                        if cat in st.session_state.nuove_categorie:
                            idx = st.session_state.nuove_categorie.index(cat)
                            st.session_state.nuove_categorie[idx] = nuovo_nome.upper().strip()
                        st.success("Modificato!"); time.sleep(0.5); st.rerun()
                    if col3.button("ELIMINA", key=f"del_cat_{cat}"):
                        menu_df = menu_df[menu_df['categoria'] != cat]
                        salva_menu(menu_df)
                        if cat in st.session_state.nuove_categorie: st.session_state.nuove_categorie.remove(cat)
                        st.rerun()
            
            st.divider()
            new_cat = st.text_input("Crea Nuova Categoria (es: APERITIVI)")
            if st.button("CREA CATEGORIA") and new_cat:
                nome_pulito = new_cat.upper().strip()
                if nome_pulito not in tutte_le_cats:
                    st.session_state.nuove_categorie.append(nome_pulito)
                    st.success(f"Categoria {nome_pulito} creata! Ora aggiungi un prodotto.")
                    st.rerun()

        with sub_prod:
            st.subheader("➕ Aggiungi Prodotto")
            # Lista dinamica per il selectbox
            cats_per_prodotto = sorted(list(set(cats_nel_file + st.session_state.nuove_categorie)))
            if not cats_per_prodotto: cats_per_prodotto = ["BRIOCHE&CORNETTI"]

            with st.form("new_prod_form"):
                c1, c2, c3 = st.columns(3)
                f_cat = c1.selectbox("Categoria", cats_per_prodotto)
                f_prod = c2.text_input("Nome Prodotto")
                f_prez = c3.number_input("Prezzo (€)", step=0.1)
                if st.form_submit_button("AGGIUNGI"):
                    if f_prod:
                        nuovo = pd.DataFrame([{"categoria": f_cat, "prodotto": f_prod.strip(), "prezzo": f_prez}])
                        salva_menu(pd.concat([menu_df, nuovo]))
                        st.rerun()

            st.divider()
            for i, r in menu_df.iterrows():
                with st.container(border=True):
                    mc1, mc2, mc3, mc4, mc5 = st.columns([2, 3, 1, 1, 1])
                    new_c = mc1.selectbox("Cat", cats_per_prodotto, index=cats_per_prodotto.index(r['categoria']) if r['categoria'] in cats_per_prodotto else 0, key=f"p_cat_{i}")
                    new_n = mc2.text_input("Nome", value=r['prodotto'], key=f"p_name_{i}")
                    new_p = mc3.number_input("€", value=float(r['prezzo']), step=0.1, key=f"p_prez_{i}")
                    if mc4.button("💾", key=f"upd_{i}"):
                        menu_df.at[i, 'categoria'], menu_df.at[i, 'prodotto'], menu_df.at[i, 'prezzo'] = new_c, new_n, new_p
                        salva_menu(menu_df); st.rerun()
                    if mc5.button("🗑️", key=f"del_{i}"):
                        salva_menu(menu_df.drop(i)); st.rerun()

# ==========================================
# SEZIONE CLIENTE
# ==========================================
else:
    st.markdown("<h1 style='text-align:center;'>🥐 PAGANOCAFE</h1>", unsafe_allow_html=True)
    tavolo_sel = st.selectbox("Seleziona Tavolo:", ["---"] + [str(i) for i in range(1, 21)])
    
    if tavolo_sel != "---":
        stk = carica_stock()
        if st.session_state.carrello:
            st.markdown(f"<div class='carrello-box'>", unsafe_allow_html=True)
            st.subheader(f"🛒 Carrello - Tavolo {tavolo_sel}")
            for idx, item in enumerate(st.session_state.carrello):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(item['prodotto'])
                c2.write(f"€{item['prezzo']:.2f}")
                if c3.button("Rimuovi", key=f"rc_{idx}"):
                    if item['prodotto'] in stk: stk[item['prodotto']] += 1; salva_stock(stk)
                    st.session_state.carrello.pop(idx); st.rerun()
            if st.button("✅ INVIA ORDINE", type="primary", use_container_width=True):
                nuovi = ordini_attuali.copy()
                ora = datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                for it in st.session_state.carrello:
                    nuovi.append({"id_univoco": str(time.time())+it['prodotto'], "tavolo": tavolo_sel, "prodotto": it['prodotto'], "prezzo": it['prezzo'], "stato": "NO", "orario": ora})
                salva_ordini(nuovi); st.session_state.carrello = []; st.success("Inviato!"); time.sleep(1); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        if not menu_df.empty:
            categorie_visibili = menu_df['categoria'].unique()
            scelta = st.radio("Scegli Categoria:", categorie_visibili, horizontal=True)
            st.markdown(f"<div class='categoria-header'>{scelta}</div>", unsafe_allow_html=True)
            
            for _, r in menu_df[menu_df['categoria'] == scelta].iterrows():
                c1, c2 = st.columns([3, 1])
                q = stk.get(r['prodotto'], 999) if r['categoria'] == 'BRIOCHE&CORNETTI' else 999
                c1.write(f"**{r['prodotto']}** - €{r['prezzo']:.2f}")
                if q > 0:
                    if c2.button("AGGIUNGI", key=f"a_{r['prodotto']}"):
                        st.session_state.carrello.append({"prodotto": r['prodotto'], "prezzo": r['prezzo']})
                        if r['categoria'] == 'BRIOCHE&CORNETTI': stk[r['prodotto']] -= 1; salva_stock(stk)
                        st.rerun()
                else: c2.error("ESAURITO")
