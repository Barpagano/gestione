import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton > button { width: 100% !important; border-radius: 10px !important; font-weight: bold !important; }
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; }
    .prezzo-cassa { color: #4CAF50; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIONE DATABASE ---
DB_FILE = "ordini_bar_pagano.csv"
STOCK_FILE = "stock_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def inizializza_file():
    if not os.path.exists(DB_FILE): pd.DataFrame(columns=["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]).to_csv(DB_FILE, index=False)
    if not os.path.exists(MENU_FILE): pd.DataFrame(columns=["categoria", "prodotto", "prezzo"]).to_csv(MENU_FILE, index=False)
    if not os.path.exists(STOCK_FILE): pd.DataFrame(columns=["prodotto", "quantita"]).to_csv(STOCK_FILE, index=False)

inizializza_file()

def carica_menu(): return pd.read_csv(MENU_FILE)
def carica_ordini(): return pd.read_csv(DB_FILE).to_dict('records')
def salva_ordini(lista): pd.DataFrame(lista).to_csv(DB_FILE, index=False)
def carica_stock(): 
    df = pd.read_csv(STOCK_FILE)
    return df.set_index('prodotto')['quantita'].to_dict() if not df.empty else {}
def salva_stock(d): pd.DataFrame(list(d.items()), columns=['prodotto', 'quantita']).to_csv(STOCK_FILE, index=False)

# Refresh automatico ogni 5 secondi
st_autorefresh(interval=5000, key="global_refresh")

# --- LOGICA RUOLI ---
# Se l'URL finisce con ?admin=si mostra il bancone, altrimenti mostra l'app cliente
admin_mode = st.query_params.get("admin") == "si"

if admin_mode:
    st.title("☕ CONSOLE UNIFICATA - BANCONE")
    ordini = carica_ordini()
    tab_ordini, tab_cassa, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "💰 CASSA", "⚡ VETRINA RAPIDA", "📦 STOCK", "⚙️ MENU"])

    with tab_ordini:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini)))
        cols = st.columns(3)
        for idx, t in enumerate(tavoli_attivi):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(f"🪑 Tavolo {t}")
                    items = [o for o in ordini if str(o['tavolo']) == t]
                    for r in items:
                        c1, c2, c3 = st.columns([1, 4, 2])
                        if c1.button("❌", key=f"del_{r['id_univoco']}"):
                            salva_ordini([o for o in ordini if o['id_univoco'] != r['id_univoco']]); st.rerun()
                        cl = "servito" if r['stato'] == "SI" else "da-servire"
                        c2.markdown(f"<span class='{cl}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                        if r['stato'] == "NO" and c3.button("Ok", key=f"ok_{r['id_univoco']}"):
                            for o in ordini: 
                                if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                            salva_ordini(ordini); st.rerun()

    with tab_cassa:
        tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini)))
        for t in tavoli_attivi:
            with st.container(border=True):
                items = [o for o in ordini if str(o['tavolo']) == t]
                totale = sum(float(x['prezzo']) for x in items)
                st.write(f"### Conto Tavolo {t}: €{totale:.2f}")
                if st.button(f"CHIUDI CONTO {t}", key=f"pay_{t}"):
                    salva_ordini([o for o in ordini if str(o['tavolo']) != t]); st.rerun()

    with tab_vetrina:
        stk = carica_stock()
        cv = st.columns(4)
        for i, (p, q) in enumerate(stk.items()):
            if cv[i % 4].button(f"{p} ({q})", key=f"v_{p}"):
                stk[p] = max(0, q - 1); salva_stock(stk); st.rerun()

    with tab_stock:
        stk = carica_stock()
        for p, q in stk.items():
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{p}**")
            if c2.button("➖", key=f"m_{p}"): stk[p]=max(0, q-1); salva_stock(stk); st.rerun()
            c3.write(f"**{q}**")
            if c4.button("➕", key=f"p_{p}"): stk[p]=q+1; salva_stock(stk); st.rerun()

    with tab_menu:
        st.subheader("Aggiungi al listino")
        with st.form("new_prod"):
            cat = st.text_input("Categoria")
            nome = st.text_input("Nome Prodotto")
            prezzo = st.number_input("Prezzo (€)", step=0.1)
            if st.form_submit_button("AGGIUNGI"):
                m_df = carica_menu()
                nuovo = pd.DataFrame([{"categoria": cat, "prodotto": nome, "prezzo": prezzo}])
                pd.concat([m_df, nuovo]).to_csv(MENU_FILE, index=False); st.rerun()

# --- INTERFACCIA CLIENTE ---
else:
    st.title("🥐 BAR PAGANO")
    menu_df = carica_menu()
    ordini = carica_ordini()
    stk = carica_stock()
    
    # 1. Scelta Tavolo
    tavolo_scelto = st.selectbox("Seleziona il tuo tavolo:", ["---"] + [str(i) for i in range(1, 21)])
    
    if tavolo_scelto != "---":
        cat_selezionata = st.radio("Cosa desideri?", menu_df['categoria'].unique(), horizontal=True)
        st.divider()
        
        prodotti = menu_df[menu_df['categoria'] == cat_selezionata]
        for _, row in prodotti.iterrows():
            c1, c2 = st.columns([3, 1])
            nome_p = row['prodotto']
            prezzo_p = row['prezzo']
            
            # Controllo Stock
            q_disp = stk.get(nome_p, 999) # Se non è monitorato, è infinito
            
            c1.markdown(f"**{nome_p}** \n€{prezzo_p:.2f}")
            
            if q_disp > 0:
                if c2.button("ORDINA", key=f"btn_{nome_p}"):
                    # SCALO AUTOMATICO STOCK
                    if nome_p in stk:
                        stk[nome_p] -= 1
                        salva_stock(stk)
                    
                    # SALVATAGGIO ORDINE
                    nuovo_o = {
                        "id_univoco": str(time.time()),
                        "tavolo": tavolo_scelto,
                        "prodotto": nome_p,
                        "prezzo": prezzo_p,
                        "stato": "NO",
                        "orario": datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                    }
                    ordini.append(nuovo_o)
                    salva_ordini(ordini)
                    st.success(f"Ordinato: {nome_p}!")
                    time.sleep(1)
                    st.rerun()
            else:
                c2.error("FINITO")
