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
    /* Pulsanti grandi e leggibili */
    .stButton > button { 
        width: 100% !important; 
        border-radius: 10px !important; 
        font-weight: bold !important; 
        height: 65px; 
        font-size: 18px !important;
    }
    /* Colore Oro/Bronzo per il brand Paganocafe */
    div.stButton > button { background-color: #d4af37; color: black; border: none; }
    /* Nasconde menu Streamlit */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- INIZIALIZZAZIONE DATABASE ---
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

# Refresh automatico ogni 5 secondi per il monitoraggio ordini
st_autorefresh(interval=5000, key="paganocafe_refresh")

# Riconoscimento Ruolo tramite URL: ?ruolo=banco
ruolo = st.query_params.get("ruolo", "cliente")

# ==========================================
# PARTE 1: GESTIONE (BANCO + CASSA)
# ==========================================
if ruolo == "banco":
    st.title("📟 PAGANOCAFE - GESTIONE")
    ordini = carica_ordini()
    stk = carica_stock()
    
    t1, t2, t3, t4 = st.tabs(["📋 ORDINI", "💰 CASSA", "📦 STOCK/VETRINA", "⚙️ MENU"])
    
    with t1:
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini)))
        if not tavoli: st.info("In attesa di ordini...")
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
        tavoli = sorted(list(set(str(o['tavolo']) for o in ordini)))
        if not tavoli: st.info("Nessun conto aperto.")
        for t in tavoli:
            items = [o for o in ordini if str(o['tavolo']) == t]
            tot = sum(float(x['prezzo']) for x in items)
            if st.button(f"CHIUDI CONTO TAVOLO {t}: €{tot:.2f}", key=f"pay_{t}", type="primary"):
                salva_ordini([o for o in ordini if str(o['tavolo']) != t]); st.rerun()

    with t3:
        st.subheader("Rifornimento (+1)")
        for p, q in stk.items():
            c1, c2, c3 = st.columns([2,1,1])
            c1.write(f"**{p}**")
            c2.write(f"Disponibili: {q}")
            if c3.button("+1", key=f"rif_{p}"):
                stk[p] += 1; salva_stock(stk); st.rerun()

    with t4:
        st.subheader("⚙️ Gestione Listino")
        with st.form("add_new"):
            c_cat = st.text_input("Categoria")
            c_prod = st.text_input("Nome Prodotto")
            c_prez = st.number_input("Prezzo", step=0.10)
            c_mon = st.checkbox("Monitora Stock (Vetrina)")
            if st.form_submit_button("AGGIUNGI AL MENU"):
                m_df = carica_menu()
                nuovo = pd.DataFrame([{"categoria": c_cat, "prodotto": c_prod, "prezzo": c_prez}])
                pd.concat([m_df, nuovo]).to_csv(MENU_FILE, index=False)
                if c_mon:
                    stk[c_prod] = 0; salva_stock(stk)
                st.rerun()

# ==========================================
# PARTE 2: CLIENTE (INTERFACCIA SMARTPHONE)
# ==========================================
else:
    st.markdown("<h1 style='text-align:center; color:#d4af37;'>PAGANOCAFE</h1>", unsafe_allow_html=True)
    
    m_df = carica_menu()
    stk = carica_stock()
    ordini_lista = carica_ordini()

    # Tavoli a tendina
    tavolo_sel = st.selectbox("Seleziona il tuo tavolo:", ["---"] + [str(i) for i in range(1, 16)])

    if tavolo_sel != "---":
        st.write(f"Benvenuto! Cosa possiamo portarti al **Tavolo {tavolo_sel}**?")
        
        # Filtro Categorie
        categoria = st.radio("Scegli categoria:", m_df['categoria'].unique(), horizontal=True)
        st.divider()
        
        prodotti_cat = m_df[m_df['categoria'] == categoria]
        for _, row in prodotti_cat.iterrows():
            c1, c2 = st.columns([3, 1])
            p_nome = row['prodotto']
            p_prezzo = row['prezzo']
            
            # Controllo Stock automatico
            q_disp = stk.get(p_nome, 999) # Se non monitorato, è considerato infinito
            
            c1.markdown(f"**{p_nome}**\n€ {p_prezzo:.2f}")
            
            if q_disp > 0:
                if c2.button("ORDINA", key=f"cl_{p_nome}"):
                    # 1. SCALO AUTOMATICO STOCK
                    if p_nome in stk:
                        stk[p_nome] -= 1
                        salva_stock(stk)
                    
                    # 2. SALVATAGGIO ORDINE
                    nuovo_ordine = {
                        "id": str(time.time()), "tavolo": tavolo_sel, 
                        "prodotto": p_nome, "prezzo": p_prezzo, "stato": "NO",
                        "ora": datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                    }
                    temp_ordini = carica_ordini()
                    temp_ordini.append(nuovo_ordine)
                    salva_ordini(temp_ordini)
                    
                    st.success(f"Ordine inviato: {p_nome}")
                    time.sleep(1); st.rerun()
            else:
                c2.error("ESAURITO")
