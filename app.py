import streamlit as st
import pandas as pd
import os, time
from datetime import datetime

# 1. Configurazione Base
st.set_page_config(page_title="BAR PAGANO", layout="wide")

# 2. CSS Essenziale (Solo per la griglia 5 colonne)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    /* Forza 5 colonne su smartphone */
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; gap: 2px !important; }
    [data-testid="column"] { flex: 1 !important; min-width: 0px !important; }
    /* Tasti Tavoli */
    .stButton > button { 
        width: 100% !important; height: 80px !important; 
        background-color: #00FF00 !important; color: black !important;
        font-weight: bold; font-size: 20px !important; border-radius: 5px !important;
    }
    .stButton > button:disabled { background-color: #FF0000 !important; color: white !important; opacity: 1; }
    </style>
    """, unsafe_allow_html=True)

# 3. Gestione File
if not os.path.exists("menu.csv"):
    pd.DataFrame([{"prod": "Cornetto", "prezzo": 1.2, "stock": 10}]).to_csv("menu.csv", index=False)
if not os.path.exists("ordini.csv"):
    pd.DataFrame(columns=["tavolo", "prod", "ora"]).to_csv("ordini.csv", index=False)

menu = pd.read_csv("menu.csv")
ordini = pd.read_csv("ordini.csv")

# 4. Logica Ruoli
ruolo = st.query_params.get("ruolo", "cliente")

# --- VISTA BANCO ---
if ruolo == "banco":
    st.title("BANCO - ORDINI")
    if st.button("Svuota Tutti gli Ordini"):
        pd.DataFrame(columns=["tavolo", "prod", "ora"]).to_csv("ordini.csv", index=False)
        st.rerun()
    st.table(ordini)
    
    st.divider()
    st.write("### Rifornimento Vetrina")
    for i, row in menu.iterrows():
        c1, c2 = st.columns(2)
        c1.write(f"{row['prod']} (Disp: {row['stock']})")
        if c2.button(f"Aggiungi 10 {row['prod']}", key=f"add_{i}"):
            menu.at[i, 'stock'] += 10
            menu.to_csv("menu.csv", index=False)
            st.rerun()

# --- VISTA CLIENTE ---
else:
    st.markdown("<h1 style='text-align:center; color:#00FF00;'>BAR PAGANO</h1>", unsafe_allow_html=True)
    
    if 'tav' not in st.session_state:
        st.session_state.tav = None

    if st.session_state.tav is None:
        st.write("Scegli il tavolo:")
        occupati = ordini['tavolo'].astype(str).tolist()
        
        # Griglia 3 righe x 5 colonne
        for r in range(3):
            cols = st.columns(5)
            for c in range(5):
                n = str((r * 5) + c + 1)
                is_occ = n in occupati
                if cols[c].button(n, key=f"btn_{n}", disabled=is_occ):
                    st.session_state.tav = n
                    st.rerun()
    else:
        st.write(f"### Tavolo {st.session_state.tav}")
        if st.button("Torna indietro"):
            st.session_state.tav = None
            st.rerun()
            
        st.divider()
        for i, row in menu.iterrows():
            c1, c2 = st.columns([3, 1])
            disponibile = row['stock'] > 0
            c1.write(f"**{row['prod']}** - €{row['prezzo']}")
            
            if disponibile:
                if c2.button("Ordina", key=f"buy_{i}"):
                    # Salva Ordine
                    nuovo_ordine = pd.DataFrame([{"tavolo": st.session_state.tav, "prod": row['prod'], "ora": time.strftime("%H:%M")}])
                    pd.concat([ordini, nuovo_ordine]).to_csv("ordini.csv", index=False)
                    # Scala Stock
                    menu.at[i, 'stock'] -= 1
                    menu.to_csv("menu.csv", index=False)
                    st.success("Ordinato!")
                    time.sleep(1)
                    st.rerun()
            else:
                c2.write("FINITO")
