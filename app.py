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
    .stButton > button { width: 100% !important; border-radius: 8px !important; font-weight: bold !important; height: 50px; }
    /* Colore pulsante ORDINA */
    div.stButton > button { background-color: #d4af37; color: black; border: none; }
    /* Colore pulsante OK e PAGATO */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { color: white; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- INIZIALIZZAZIONE FILE ---
DB_FILE = "ordini_bar_pagano.csv"
STOCK_FILE = "stock_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def inizializza():
    if not os.path.exists(DB_FILE): pd.DataFrame(columns=["id", "tavolo", "prodotto", "prezzo", "stato", "ora"]).to_csv(DB_FILE, index=False)
    if not os.path.exists(MENU_FILE): pd.DataFrame([{"categoria": "VETRINA", "prodotto": "Cornetto", "prezzo": 1.20}]).to_csv(MENU_FILE, index=False)
    if not os.path.exists(STOCK_FILE): pd.DataFrame(columns=["prodotto", "quantita"]).to_csv(STOCK_FILE, index=False)

inizializza()

def carica_menu(): return pd.read_csv(MENU_FILE)
def carica_ordini(): return pd.read_csv(DB_FILE).to_dict('records')
def salva_ordini(lista): pd.DataFrame(lista).to_csv(DB_FILE, index=False)
def carica_stock(): 
    df = pd.read_csv(STOCK_FILE)
    return df.set_index('prodotto')['quantita'].to_dict() if not df.empty else {}
def salva_stock(d): pd.DataFrame(list(d.items()), columns=['prodotto', 'quantita']).to_csv(STOCK_FILE, index=False)

# Refresh automatico ogni 5 secondi per il Bancone
st_autorefresh(interval=5000, key="paganocafe_refresh")

# Controllo Admin via URL: ?admin=si
admin_mode = st.query_params.get("admin") == "si"

# ==========================================
# VISTA BANCONE (ADMIN)
# ==========================================
if admin_mode:
    st.title("📟 PAGANOCAFE - GESTIONE")
    ordini = carica_ordini()
    stk = carica_stock()
    
    t1, t2, t3, t4 = st.tabs(["📋 ORDINI", "💰 CASSA", "📦 STOCK", "⚙️ MENU"])
    
    with t1: # Ordini da servire
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

    with t2: # Cassa e chiusura conti
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini)))
        for t in tavoli:
            items = [o for o in ordini if str(o['tavolo']) == t]
            tot = sum(float(x['prezzo']) for x in items)
            if st.button(f"CHIUDI CONTO TAVOLO {t}: €{tot:.2f}", key=f"pay_{t}", type="primary"):
                salva_ordini([o for o in ordini if str(o['tavolo']) != t]); st.rerun()

    with t3: # Rifornimento Stock +1
        st.subheader("Carico Vetrina")
        for p, q in stk.items():
            c1, c2, c3 = st.columns([2,1,1])
            c1.write(f"**{p}**")
            c2.write(f"Qta: {q}")
            if c3.button("+1", key=f"add_{p}"):
                stk[p] += 1; salva_stock(stk); st.rerun()
        if st.button("Aggiungi prodotto da monitorare"):
            st.info("Aggiungi i prodotti nel tab MENU per vederli qui.")

    with t4: # Gestione Listino
        st.subheader("Modifica Menu")
        with st.form("add_prod"):
            cat = st.text_input("Categoria")
            nome = st.text_input("Prodotto")
            prez = st.number_input("Prezzo", step=0.1)
            monit = st.checkbox("Monitora Stock (Vetrina)")
            if st.form_submit_button("SALVA"):
                m_df = carica_menu()
                nuovo = pd.DataFrame([{"categoria": cat, "prodotto": nome, "prezzo": prez}])
                pd.concat([m_df, nuovo]).to_csv(MENU_FILE, index=False)
                if monit:
                    stk[nome] = 0; salva_stock(stk)
                st.rerun()

# ==========================================
# VISTA CLIENTE
# ==========================================
else:
    st.markdown("<h1 style='text-align:center; color:#d4af37;'>PAGANOCAFE</h1>", unsafe_allow_html=True)
    
    m_df = carica_menu()
    stk = carica_stock()
    ordini = carica_ordini()

    # Scelta Tavolo a Tendina
    tavolo_sel = st.selectbox("Seleziona il tuo tavolo:", ["---"] + [str(i) for i in range(1, 16)])

    if tavolo_sel != "---":
        categoria = st.radio("Cosa desideri?", m_df['categoria'].unique(), horizontal=True)
        st.divider()
        
        prod_filtrati = m_df[m_df['categoria'] == categoria]
        for _, row in prod_filtrati.iterrows():
            c1, c2 = st.columns([3, 1])
            nome = row['prodotto']
            prezzo = row['prezzo']
            
            # Scalo stock se monitorato
            q_disp = stk.get(nome, 999) 
            
            c1.markdown(f"**{nome}**\n€ {prezzo:.2f}")
            
            if q_disp > 0:
                if c2.button("ORDINA", key=f"ord_{nome}"):
                    # AGGIORNA STOCK
                    if nome in stk:
                        stk[nome] -= 1
                        salva_stock(stk)
                    
                    # SALVA ORDINE
                    nuovo_ordine = {
                        "id": str(time.time()), "tavolo": tavolo_sel, 
                        "prodotto": nome, "prezzo": prezzo, "stato": "NO",
                        "ora": datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                    }
                    ordini_lista = pd.read_csv(DB_FILE).to_dict('records')
                    ordini_lista.append(nuovo_ordine)
                    salva_ordini(ordini_lista)
                    
                    st.success(f"Ordinato: {nome}!")
                    time.sleep(1); st.rerun()
            else:
                c2.error("ESAURITO")
