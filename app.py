import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

# --- CSS PER GRIGLIA 3x5 RISTRETTA E LOGO ---
st.markdown("""
    <style>
    /* Sfondo nero assoluto */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Contenitore per restringere la griglia tavoli (centrata) */
    .tavoli-wrapper {
        max-width: 400px;
        margin: 0 auto;
        padding: 10px;
    }

    /* RIMUOVE SPAZI TRA COLONNE E RIGHE */
    [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        margin-bottom: 0px !important;
    }
    
    [data-testid="column"] {
        padding: 0px !important;
        margin: 0px !important;
    }

    /* STILE TASTI TAVOLI */
    .stButton > button {
        width: 100% !important;
        height: 80px !important; 
        border-radius: 0px !important;
        font-weight: 900 !important;
        font-size: 28px !important;
        margin: 0px !important;
        border: 1px solid #111111 !important;
    }

    /* COLORI TAVOLI */
    .btn-libero div[data-testid="stButton"] > button {
        background-color: #00FF00 !important;
        color: #000000 !important;
    }

    .btn-occupato div[data-testid="stButton"] > button {
        background-color: #FF0000 !important;
        color: #FFFFFF !important;
    }

    /* Logo centrato */
    .logo-container {
        display: flex;
        justify-content: center;
        padding: 20px 0;
    }

    /* Nasconde interfacce standard */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA DATI ---
DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []

def salva_ordini(lista): 
    pd.DataFrame(lista if lista else [], columns=["id", "tavolo", "prodotto", "prezzo", "stato", "ora"]).to_csv(DB_FILE, index=False)

st_autorefresh(interval=5000, key="refresh_global")
ordini = carica_ordini()
ruolo = st.query_params.get("ruolo", "cliente")

# =========================================================
# VISUALIZZAZIONE LOGO O TITOLO
# =========================================================
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
if os.path.exists("logo.png"):
    st.image("logo.png", width=200)
else:
    # Se il logo non c'è, mettiamo una scritta bellissima
    st.markdown("<h1 style='color:#00FF00; font-size:45px; font-family:sans-serif; letter-spacing:-2px; margin:0;'>BAR PAGANO</h1>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BANCONE (GESTIONE)
# =========================================================
if ruolo == "banco":
    st.markdown("<h2 style='text-align:center;'> Pannello Banco</h2>", unsafe_allow_html=True)
    tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini)))
    
    if not tavoli_attivi:
        st.info("Nessun ordine in attesa")
    else:
        for t in tavoli_attivi:
            with st.container(border=True):
                st.write(f"### Tavolo {t}")
                items = [o for o in ordini if str(o['tavolo']) == t]
                totale = sum(float(o['prezzo']) for o in items)
                for r in items:
                    c1, c2 = st.columns([4, 1])
                    cl = "text-decoration: line-through; color: #555;" if r['stato'] == "SI" else "color: white;"
                    c1.markdown(f"<span style='{cl}'>{r['prodotto']}</span>", unsafe_allow_html=True)
                    if r['stato'] == "NO" and c2.button("OK", key=f"ok_{r['id']}"):
                        for o in ordini: 
                            if o['id'] == r['id']: o['stato'] = "SI"
                        salva_ordini(ordini); st.rerun()
                if st.button(f"CHIUDI CONTO {t}", key=f"pay_{t}", type="primary", use_container_width=True):
                    salva_ordini([o for o in ordini if str(o['tavolo']) != t]); st.rerun()

# =========================================================
# CLIENTE (GRIGLIA TAVOLI 3x5 RISTRETTA)
# =========================================================
else:
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.markdown("<p style='text-align:center; color:#888;'>SELEZIONA IL TAVOLO</p>", unsafe_allow_html=True)
        
        occupati = set(str(o['tavolo']) for o in ordini)
        
        # GRIGLIA COMPATTA AL CENTRO
        st.markdown('<div class="tavoli-wrapper">', unsafe_allow_html=True)
        for riga in range(3):
            cols = st.columns(5)
            for colonna in range(5):
                n = str((riga * 5) + colonna + 1)
                is_occ = n in occupati
                classe = "btn-occupato" if is_occ else "btn-libero"
                
                with cols[colonna]:
                    st.markdown(f'<div class="{classe}">', unsafe_allow_html=True)
                    if st.button(n, key=f"t_{n}", disabled=is_occ):
                        st.session_state.tavolo = n
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # INTERFACCIA MENU
        st.markdown(f"<div style='background-color:#00FF00; color:black; text-align:center; padding:12px; font-weight:bold; font-size:22px;'>TAVOLO {st.session_state.tavolo}</div>", unsafe_allow_html=True)
        if st.button("⬅️ CAMBIA TAVOLO", use_container_width=True):
            st.session_state.tavolo = None; st.rerun()
        
        if os.path.exists(MENU_FILE):
            menu_df = pd.read_csv(MENU_FILE)
            cat = st.radio("Categoria:", sorted(menu_df['categoria'].unique()), horizontal=True)
            for _, r in menu_df[menu_df['categoria'] == cat].iterrows():
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{r['prodotto']}**\n€{r['prezzo']:.2f}")
                if c2.button("➕", key=f"add_{r['prodotto']}"):
                    st.session_state.carrello.append(r.to_dict()); st.rerun()

        if st.session_state.carrello:
            st.divider()
            tot = sum(i['prezzo'] for i in st.session_state.carrello)
            st.write(f"### TOTALE: €{tot:.2f}")
            if st.button("🚀 INVIA ORDINE ORA", type="primary", use_container_width=True):
                ora = datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")
                for item in st.session_state.carrello:
                    ordini.append({
                        "id": f"{time.time()}_{item['prodotto']}",
                        "tavolo": st.session_state.tavolo, "prodotto": item['prodotto'],
                        "prezzo": item['prezzo'], "stato": "NO", "ora": ora
                    })
                salva_ordini(ordini)
                st.session_state.carrello = []
                st.success("Ordine Inviato!"); time.sleep(1); st.rerun()
