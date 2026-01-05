import streamlit as st
import pandas as pd
import os, time
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

# --- CSS PER SMARTPHONE (5 COLONNE FISSE) ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    /* Forza 5 colonne affiancate */
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; gap: 4px !important; }
    [data-testid="column"] { flex: 1 !important; min-width: 0px !important; }
    /* Tasti Tavoli */
    .stButton > button { 
        width: 100% !important; height: 75px !important; 
        background-color: #00FF00 !important; color: black !important;
        font-weight: 900 !important; font-size: 22px !important; border-radius: 4px !important;
        border: none !important;
    }
    .stButton > button:disabled { background-color: #FF0000 !important; color: white !important; opacity: 1 !important; }
    /* Tab e scritte */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIONE DATI ---
if not os.path.exists("menu.csv"):
    pd.DataFrame([{"prod": "Cornetto", "prezzo": 1.2, "stock": 10}, {"prod": "Caffè", "prezzo": 1.0, "stock": 999}]).to_csv("menu.csv", index=False)
if not os.path.exists("ordini.csv"):
    pd.DataFrame(columns=["tavolo", "prod", "ora"]).to_csv("ordini.csv", index=False)

menu = pd.read_csv("menu.csv")
ordini = pd.read_csv("ordini.csv")
ruolo = st.query_params.get("ruolo", "cliente")

# ==========================================
# GESTIONE BANCO (URL + ?ruolo=banco)
# ==========================================
if ruolo == "banco":
    st.title("📟 GESTIONE BANCO")
    tab_ordini, tab_vetrina = st.tabs(["📋 ORDINI ATTIVI", "🥐 VETRINA & PREZZI"])

    with tab_ordini:
        if ordini.empty:
            st.info("Nessun tavolo occupato.")
        else:
            # Raggruppa ordini per tavolo
            tavoli_occupati = ordini['tavolo'].unique()
            for t in sorted(tavoli_occupati):
                with st.container(border=True):
                    col_t, col_b = st.columns([3, 1])
                    prodotti_tavolo = ordini[ordini['tavolo'] == t]
                    col_t.write(f"### TAVOLO {t}")
                    for p in prodotti_tavolo['prod']:
                        col_t.write(f"- {p}")
                    
                    if col_b.button(f"PAGATO / LIBERA", key=f"libera_{t}"):
                        ordini = ordini[ordini['tavolo'] != t]
                        ordini.to_csv("ordini.csv", index=False)
                        st.rerun()

    with tab_vetrina:
        st.write("### Modifica Stock e Menu")
        # Form per aggiungere nuovi prodotti
        with st.expander("➕ Aggiungi Nuovo Prodotto"):
            n_p = st.text_input("Nome Prodotto")
            n_pz = st.number_input("Prezzo", min_value=0.0, step=0.5)
            n_s = st.number_input("Quantità Iniziale", min_value=0, value=10)
            if st.button("Salva nel Menu"):
                nuovo = pd.DataFrame([{"prod": n_p, "prezzo": n_pz, "stock": n_s}])
                menu = pd.concat([menu, nuovo]).to_csv("menu.csv", index=False)
                st.rerun()

        st.divider()
        # Modifica stock esistente
        for i, row in menu.iterrows():
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"**{row['prod']}** (€{row['prezzo']})")
            c2.write(f"Disp: {row['stock']}")
            if c3.button("Rifornisci +10", key=f"refill_{i}"):
                menu.at[i, 'stock'] += 10
                menu.to_csv("menu.csv", index=False)
                st.rerun()

# ==========================================
# INTERFACCIA CLIENTE
# ==========================================
else:
    st.markdown("<h1 style='text-align:center; color:#00FF00; margin-bottom:0;'>BAR PAGANO</h1>", unsafe_allow_html=True)
    
    if 'tav' not in st.session_state:
        st.session_state.tav = None

    # 1. Selezione Tavolo
    if st.session_state.tav is None:
        st.markdown("<p style='text-align:center;'>Scegli il tuo tavolo:</p>", unsafe_allow_html=True)
        occupati = ordini['tavolo'].astype(str).tolist()
        
        for r in range(3): # 3 righe
            cols = st.columns(5) # 5 colonne
            for c in range(5):
                n = str((r * 5) + c + 1)
                is_occ = n in occupati
                # Il tasto è rosso (disabilitato) se occupato, verde se libero
                if cols[c].button(n, key=f"btn_{n}", disabled=is_occ):
                    st.session_state.tav = n
                    st.rerun()
    
    # 2. Menu Ordinazione
    else:
        st.markdown(f"<h2 style='text-align:center; background:#00FF00; color:black;'>TAVOLO {st.session_state.tav}</h2>", unsafe_allow_html=True)
        if st.button("⬅ CAMBIA TAVOLO"):
            st.session_state.tav = None
            st.rerun()
            
        st.write("---")
        for i, row in menu.iterrows():
            c1, c2 = st.columns([3, 1])
            disp = row['stock'] > 0
            
            c1.write(f"**{row['prod']}**")
            c1.write(f"€ {row['prezzo']}")
            
            if disp:
                if c2.button("ORDINA", key=f"ord_{i}"):
                    # Registra ordine
                    nuovo = pd.DataFrame([{"tavolo": st.session_state.tav, "prod": row['prod'], "ora": time.strftime("%H:%M")}])
                    pd.concat([ordini, nuovo]).to_csv("ordini.csv", index=False)
                    # Scala stock
                    menu.at[i, 'stock'] -= 1
                    menu.to_csv("menu.csv", index=False)
                    st.success(f"Ordinato: {row['prod']}!")
                    time.sleep(1)
                    st.rerun()
            else:
                c2.error("FINITO")
