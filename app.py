import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO", page_icon="☕", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    div[data-testid="column"] button { width: 100% !important; font-weight: bold !important; border-radius: 10px !important; }
    
    /* Stile testo ordini */
    .servito { color: #555555 !important; text-decoration: line-through; opacity: 0.6; font-style: italic; }
    .da-servire { color: #FFFFFF !important; font-weight: bold; font-size: 16px; }
    
    /* Tasto Pagato Rosso */
    .btn-paga > div[data-testid="stButton"] > button {
        background-color: #D32F2F !important; color: white !important;
        height: 60px !important; font-size: 20px !important; border: 2px solid #FF5252 !important;
    }
    
    /* Stile Tavoli Cliente */
    .stButton > button[kind="secondary"] { background-color: #1E1E1E !important; color: white !important; height: 60px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIONE DATABASE ---
DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"
STOCK_FILE = "stock_bar_pagano.csv"

def inizializza_file(file, colonne):
    if not os.path.exists(file) or os.stat(file).st_size <= 2:
        pd.DataFrame(columns=colonne).to_csv(file, index=False)

inizializza_file(DB_FILE, ["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"])
inizializza_file(MENU_FILE, ["categoria", "prodotto", "prezzo"])
inizializza_file(STOCK_FILE, ["prodotto", "quantita"])

def carica_menu(): return pd.read_csv(MENU_FILE)
def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []
def salva_ordini(lista): 
    pd.DataFrame(lista if lista else [], columns=["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]).to_csv(DB_FILE, index=False)

# --- LOGICA CORE ---
ruolo = st.query_params.get("ruolo", "cliente")
menu_df = carica_menu()
ordini_attuali = carica_ordini()

# ---------------------------------------------------------
# 👨‍🍳 INTERFACCIA BANCONE (?ruolo=banco)
# ---------------------------------------------------------
if ruolo == "banco":
    st_autorefresh(interval=5000, key="banco_refresh")
    st.title("👨‍🍳 CONSOLE BANCONE")
    
    tab_ordini, tab_vetrina, tab_stock, tab_menu = st.tabs(["📋 ORDINI", "⚡ VETRINA", "📦 STOCK", "⚙️ MENU"])
    
    with tab_ordini:
        if not ordini_attuali:
            st.info("Nessun ordine attivo.")
        else:
            tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
            cols = st.columns(3)
            for idx, t in enumerate(tavoli_attivi):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.subheader(f"🪑 Tavolo {t}")
                        items = [o for o in ordini_attuali if str(o['tavolo']) == str(t)]
                        totale = sum(float(o['prezzo']) for o in items)
                        
                        for r in items:
                            c_del, c_txt, c_ok = st.columns([0.6, 3, 1])
                            if c_del.button("❌", key=f"del_{r['id_univoco']}"):
                                salva_ordini([o for o in ordini_attuali if o['id_univoco'] != r['id_univoco']]); st.rerun()
                            stile = "servito" if r['stato'] == "SI" else "da-servire"
                            c_txt.markdown(f"<span class='{stile}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                            if r['stato'] == "NO" and c_ok.button("Ok", key=f"ok_{r['id_univoco']}"):
                                for o in ordini_attuali:
                                    if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                                salva_ordini(ordini_attuali); st.rerun()
                        
                        st.divider()
                        st.write(f"### Totale: €{totale:.2f}")
                        st.markdown('<div class="btn-paga">', unsafe_allow_html=True)
                        if st.button(f"PAGATO E CHIUDI {t}", key=f"paga_{t}", type="primary"):
                            salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != str(t)]); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# ☕ INTERFACCIA CLIENTE (Link Normale)
# ---------------------------------------------------------
else:
    st.title("☕ BENVENUTI AL BAR PAGANO")
    
    # Inizializza session state per il cliente
    if 'tavolo_selezionato' not in st.session_state: st.session_state.tavolo_selezionato = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    # 1. SCELTA TAVOLO
    if st.session_state.tavolo_selezionato is None:
        st.subheader("Per iniziare, seleziona il tuo numero di tavolo:")
        for i in range(0, 15, 5):
            c = st.columns(5)
            for j in range(5):
                n = i + j + 1
                if c[j].button(f"Tavolo {n}", key=f"t_{n}", type="secondary"):
                    st.session_state.tavolo_selezionato = str(n)
                    st.rerun()
    
    # 2. MENU E CARRELLO
    else:
        st.success(f"📍 Ordinando per il **Tavolo {st.session_state.tavolo_selezionato}**")
        if st.button("⬅️ Cambia Tavolo"): st.session_state.tavolo_selezionato = None; st.rerun()
        
        col_menu, col_cart = st.columns([2, 1])
        
        with col_menu:
            st.subheader("📖 Menu")
            if menu_df.empty:
                st.warning("Il menu è vuoto. Aggiungi prodotti dalla console banco.")
            else:
                categorie = sorted(menu_df['categoria'].unique())
                cat = st.selectbox("Scegli Categoria", categorie)
                prodotti_cat = menu_df[menu_df['categoria'] == cat]
                
                for _, row in prodotti_cat.iterrows():
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{row['prodotto']}** - €{row['prezzo']:.2f}")
                    if c2.button("Aggiungi", key=f"add_{row['prodotto']}"):
                        st.session_state.carrello.append(row.to_dict())
                        st.toast(f"Aggiunto {row['prodotto']}!")

        with col_cart:
            st.subheader("🛒 Il tuo Ordine")
            if not st.session_state.carrello:
                st.write("Il carrello è vuoto.")
            else:
                tot_carrello = 0
                for i, item in enumerate(st.session_state.carrello):
                    st.write(f"{item['prodotto']} (€{item['prezzo']:.2f})")
                    tot_carrello += item['prezzo']
                
                st.divider()
                st.write(f"**Totale: €{tot_carrello:.2f}**")
                
                if st.button("🚀 INVIA ORDINE", type="primary", use_container_width=True):
                    ora = datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                    for item in st.session_state.carrello:
                        ordini_attuali.append({
                            "id_univoco": f"{time.time()}_{item['prodotto']}",
                            "tavolo": st.session_state.tavolo_selezionato,
                            "prodotto": item['prodotto'],
                            "prezzo": item['prezzo'],
                            "stato": "NO",
                            "orario": ora
                        })
                    salva_ordini(ordini_attuali)
                    st.session_state.carrello = []
                    st.balloons()
                    st.success("Ordine inviato! Stiamo preparando...")
                    time.sleep(2); st.rerun()
