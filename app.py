import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import pytz 
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="BAR PAGANO", 
    page_icon="☕", 
    layout="centered" # Centrato è meglio per l'elenco verticale
)

# --- CSS PERSONALIZZATO (DARK MODE & LISTA TAVOLI) ---
st.markdown("""
    <style>
    /* Dark Mode Totale */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Titoli Verde Fluo */
    h1, h2, h3 { color: #00FF00 !important; text-align: center; }

    /* ELENCO TAVOLI: Tasti larghi e vicini */
    div[data-testid="column"] { padding: 0px !important; margin: 0px !important; }
    
    .stButton > button {
        width: 100% !important;
        height: 60px !important;
        border-radius: 5px !important;
        font-weight: 900 !important;
        font-size: 22px !important;
        margin-bottom: 5px !important;
    }

    /* TAVOLO LIBERO: Verde / Testo Bianco */
    .btn-libero div[data-testid="stButton"] > button {
        background-color: #2E7D32 !important;
        color: #FFFFFF !important;
        border: 1px solid #4CAF50 !important;
    }

    /* TAVOLO OCCUPATO: Rosso / Testo Nero */
    .btn-occupato div[data-testid="stButton"] > button {
        background-color: #D32F2F !important;
        color: #000000 !important;
        border: 1px solid #FF5252 !important;
    }

    /* CARRELLO */
    .btn-del-cart div[data-testid="stButton"] > button {
        height: 40px !important;
        background-color: transparent !important;
        color: #FF5252 !important;
        border: 1px solid #FF5252 !important;
        font-size: 16px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DATI ---
def get_ora_italiana():
    return datetime.now(pytz.timezone('Europe/Rome')).strftime("%H:%M")

DB_FILE = "ordini_bar_pagano.csv"
MENU_FILE = "menu_personalizzato.csv"

def carica_ordini(): 
    try: return pd.read_csv(DB_FILE).to_dict('records')
    except: return []

def salva_ordini(lista): 
    pd.DataFrame(lista if lista else [], columns=["id_univoco", "tavolo", "prodotto", "prezzo", "stato", "orario"]).to_csv(DB_FILE, index=False)

st_autorefresh(interval=5000, key="global_refresh")
ordini_attuali = carica_ordini()
ruolo = st.query_params.get("ruolo", "cliente")

# =========================================================
# BANCONE (GESTIONE)
# =========================================================
if ruolo == "banco":
    st.title("👨‍🍳 GESTIONE BANCO")
    tavoli_attivi = sorted(list(set(str(o['tavolo']) for o in ordini_attuali)))
    
    if not tavoli_attivi:
        st.info("Nessun ordine presente.")
    else:
        for t in tavoli_attivi:
            with st.container(border=True):
                st.subheader(f"Tavolo {t}")
                items = [o for o in ordini_attuali if str(o['tavolo']) == t]
                tot = 0
                for r in items:
                    tot += float(r['prezzo'])
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"{r['prodotto']} (€{r['prezzo']})")
                    if r['stato'] == "NO" and c2.button("OK", key=f"ok_{r['id_univoco']}"):
                        for o in ordini_attuali: 
                            if o['id_univoco'] == r['id_univoco']: o['stato'] = "SI"
                        salva_ordini(ordini_attuali); st.rerun()
                st.write(f"**Totale: €{tot:.2f}**")
                if st.button(f"CHIUDI E LIBERA TAVOLO {t}", key=f"chiudi_{t}"):
                    salva_ordini([o for o in ordini_attuali if str(o['tavolo']) != t]); st.rerun()

# =========================================================
# CLIENTE (ELENCO TAVOLI & DARK)
# =========================================================
else:
    st.title("☕ BAR PAGANO")
    if 'tavolo' not in st.session_state: st.session_state.tavolo = None
    if 'carrello' not in st.session_state: st.session_state.carrello = []

    if st.session_state.tavolo is None:
        st.markdown("### 🪑 SCEGLI IL TUO TAVOLO")
        occupati = set(str(o['tavolo']) for o in ordini_attuali)
        
        # Elenco verticale dei tavoli
        for n in range(1, 16):
            t_str = str(n)
            is_occ = t_str in occupati
            classe = "btn-occupato" if is_occ else "btn-libero"
            etichetta = f"TAVOLO {n} (OCCUPATO)" if is_occ else f"TAVOLO {n} (LIBERO)"
            
            st.markdown(f'<div class="{classe}">', unsafe_allow_html=True)
            if st.button(etichetta, key=f"list_t_{n}", disabled=is_occ):
                st.session_state.tavolo = t_str
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
    else:
        # Interfaccia Menu Cliente
        st.success(f"📍 Ordinando al Tavolo {st.session_state.tavolo}")
        if st.button("⬅️ CAMBIA TAVOLO / INDIETRO"):
            st.session_state.tavolo = None; st.rerun()
        
        menu_df = pd.read_csv(MENU_FILE) if os.path.exists(MENU_FILE) else pd.DataFrame()
        if not menu_df.empty:
            cat = st.radio("Seleziona categoria:", sorted(menu_df['categoria'].unique()), horizontal=True)
            for _, row in menu_df[menu_df['categoria'] == cat].iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['prodotto']}** - €{row['prezzo']:.2f}")
                if c2.button("AGGIUNGI", key=f"add_{row['prodotto']}"):
                    item = row.to_dict()
                    item['temp_id'] = time.time()
                    st.session_state.carrello.append(item); st.rerun()

        if st.session_state.carrello:
            st.markdown("---")
            st.subheader("🛒 TUO ORDINE")
            tot = sum(i['prezzo'] for i in st.session_state.carrello)
            for i, item in enumerate(st.session_state.carrello):
                c1, c2 = st.columns([4, 1])
                c1.write(item['prodotto'])
                st.markdown('<div class="btn-del-cart">', unsafe_allow_html=True)
                if c2.button("❌", key=f"rm_{i}"):
                    st.session_state.carrello.pop(i); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.write(f"### Totale: €{tot:.2f}")
            if st.button("🚀 INVIA ORDINE AL BANCONE", type="primary", use_container_width=True):
                ora = get_ora_italiana()
                for item in st.session_state.carrello:
                    ordini_attuali.append({
                        "id_univoco": f"{time.time()}_{item['prodotto']}",
                        "tavolo": st.session_state.tavolo, "prodotto": item['prodotto'],
                        "prezzo": item['prezzo'], "stato": "NO", "orario": ora
                    })
                salva_ordini(ordini_attuali)
                st.session_state.carrello = []
                st.success("Ordine Inviato!")
                time.sleep(1); st.rerun()
