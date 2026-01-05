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
    .stApp { background-color: #000000; color: #FFFFFF; }
    .stButton > button { 
        width: 100% !important; 
        border-radius: 10px !important; 
        font-weight: bold !important; 
        height: 65px; 
    }
    div.stButton > button { background-color: #d4af37; color: black; border: none; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- COSTANTI E FILE ---
DB_FILE = "ordini_bar_pagano.csv"
STOCK_FILE = "stock_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

# --- FUNZIONI DI GESTIONE ROBUSTE ---

def inizializza():
    """Crea i file con le intestazioni se non esistono o sono vuoti"""
    files_config = {
        DB_FILE: ["id", "tavolo", "prodotto", "prezzo", "stato", "ora"],
        MENU_FILE: ["categoria", "prodotto", "prezzo"],
        STOCK_FILE: ["prodotto", "quantita"]
    }
    for file, colonne in files_config.items():
        if not os.path.exists(file) or os.path.getsize(file) == 0:
            pd.DataFrame(columns=colonne).to_csv(file, index=False)

def carica_sicuro(file, colonne):
    """Carica un CSV e gestisce l'errore EmptyDataError"""
    try:
        if not os.path.exists(file) or os.path.getsize(file) == 0:
            return pd.DataFrame(columns=colonne)
        return pd.read_csv(file)
    except Exception:
        return pd.DataFrame(columns=colonne)

def carica_ordini():
    df = carica_sicuro(DB_FILE, ["id", "tavolo", "prodotto", "prezzo", "stato", "ora"])
    return df.to_dict('records')

def salva_ordini(lista):
    pd.DataFrame(lista).to_csv(DB_FILE, index=False)

def carica_stock():
    df = carica_sicuro(STOCK_FILE, ["prodotto", "quantita"])
    return df.set_index('prodotto')['quantita'].to_dict() if not df.empty else {}

def salva_stock(d):
    pd.DataFrame(list(d.items()), columns=['prodotto', 'quantita']).to_csv(STOCK_FILE, index=False)

# Inizializza al caricamento
inizializza()

# --- LOGICA APP ---
st_autorefresh(interval=5000, key="paganocafe_refresh")
ruolo = st.query_params.get("ruolo", "cliente")

if ruolo == "banco":
    st.title("📟 PAGANOCAFE - GESTIONE")
    ordini = carica_ordini()
    stk = carica_stock()
    menu_df = carica_sicuro(MENU_FILE, ["categoria", "prodotto", "prezzo"])
    
    t1, t2, t3, t4 = st.tabs(["📋 ORDINI", "💰 CASSA", "📦 STOCK", "⚙️ MENU"])
    
    with t1:
        if not ordini: st.info("Nessun ordine attivo.")
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini)))
        for t in tavoli:
            with st.container(border=True):
                st.write(f"### Tavolo {t}")
                items = [o for o in ordini if str(o['tavolo']) == t]
                for r in items:
                    c1, c2 = st.columns([4,1])
                    cl = "text-decoration: line-through; color:gray;" if r['stato'] == "SI" else ""
                    c1.markdown(f"<span style='{cl}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                    if r['stato'] == "NO" and c2.button("OK", key=f"ok_{r['id']}"):
                        for o in ordini: 
                            if o['id'] == r['id']: o['stato'] = "SI"
                        salva_ordini(ordini); st.rerun()

    with t2:
        if not ordini: st.info("Cassa vuota.")
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini)))
        for t in tavoli:
            items = [o for o in ordini if str(o['tavolo']) == t]
            tot = sum(float(x['prezzo']) for x in items)
            if st.button(f"CHIUDI TAVOLO {t}: €{tot:.2f}", key=f"pay_{t}", type="primary"):
                salva_ordini([o for o in ordini if str(o['tavolo']) != t]); st.rerun()

    with t3:
        for p, q in stk.items():
            c1, c2, c3 = st.columns([2,1,1])
            c1.write(f"**{p}**"); c2.write(f"Qta: {q}")
            if c3.button("+1", key=f"rif_{p}"):
                stk[p] += 1; salva_stock(stk); st.rerun()

    with t4:
        with st.form("add_new"):
            c_cat = st.text_input("Categoria")
            c_prod = st.text_input("Nome Prodotto")
            c_prez = st.number_input("Prezzo", step=0.10)
            c_mon = st.checkbox("Monitora Stock")
            if st.form_submit_button("AGGIUNGI"):
                nuovo = pd.DataFrame([{"categoria": c_cat, "prodotto": c_prod, "prezzo": c_prez}])
                pd.concat([menu_df, nuovo]).to_csv(MENU_FILE, index=False)
                if c_mon:
                    stk[c_prod] = 0; salva_stock(stk)
                st.rerun()

else:
    st.markdown("<h1 style='text-align:center; color:#d4af37;'>PAGANOCAFE</h1>", unsafe_allow_html=True)
    m_df = carica_sicuro(MENU_FILE, ["categoria", "prodotto", "prezzo"])
    stk = carica_stock()
    
    if m_df.empty:
        st.warning("Menu non configurato. Accedi come banco per aggiungere prodotti.")
    else:
        tavolo_sel = st.selectbox("Tavolo:", ["---"] + [str(i) for i in range(1, 16)])
        if tavolo_sel != "---":
            categoria = st.radio("Categoria:", m_df['categoria'].unique(), horizontal=True)
            prodotti_cat = m_df[m_df['categoria'] == categoria]
            for _, row in prodotti_cat.iterrows():
                c1, c2 = st.columns([3, 1])
                nome, prezzo = row['prodotto'], row['prezzo']
                q_disp = stk.get(nome, 999)
                c1.markdown(f"**{nome}**\n€ {prezzo:.2f}")
                if q_disp > 0:
                    if c2.button("ORDINA", key=f"cl_{nome}"):
                        if nome in stk:
                            stk[nome] -= 1
                            salva_stock(stk)
                        nuovo_ordine = {
                            "id": str(time.time()), "tavolo": tavolo_sel, 
                            "prodotto": nome, "prezzo": prezzo, "stato": "NO",
                            "ora": datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                        }
                        ordini_attuali = carica_ordini()
                        ordini_attuali.append(nuovo_ordine)
                        salva_ordini(ordini_attuali)
                        st.success(f"Inviato: {nome}!"); time.sleep(1); st.rerun()
                else:
                    c2.error("ESAURITO")
