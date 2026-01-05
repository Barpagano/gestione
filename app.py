import streamlit as st
import pandas as pd
import os, time

# --- 1. CONFIGURAZIONE & GRAFICA ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    /* Griglia 5 colonne fissa per smartphone */
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; gap: 5px !important; }
    [data-testid="column"] { flex: 1 !important; min-width: 0px !important; }
    /* Bottoni Tavoli */
    .stButton > button { 
        width: 100% !important; height: 80px !important; 
        font-weight: bold; font-size: 24px !important; border-radius: 8px !important;
    }
    /* Colore Verde per Libero, Rosso per Occupato */
    div.stButton > button:first-child { background-color: #00FF00; color: black; }
    div.stButton > button:disabled { background-color: #FF0000 !important; color: white !important; opacity: 1 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE (File CSV) ---
if not os.path.exists("menu.csv"):
    pd.DataFrame([{"prod": "Cornetto", "prezzo": 1.2, "stock": 10}]).to_csv("menu.csv", index=False)
if not os.path.exists("ordini.csv"):
    pd.DataFrame(columns=["tavolo", "prod"]).to_csv("ordini.csv", index=False)

menu = pd.read_csv("menu.csv")
ordini = pd.read_csv("ordini.csv")

# --- 3. LOGICA RUOLI (?ruolo=banco) ---
ruolo = st.query_params.get("ruolo", "cliente")

# ==========================================
# PARTE A: BANCONE (GESTIONE)
# ==========================================
if ruolo == "banco":
    st.title("📟 BANCONE")
    
    col_sx, col_dx = st.columns(2)
    
    with col_sx:
        st.subheader("📋 Ordini da servire")
        if ordini.empty: st.write("Nessun ordine.")
        for t in ordini['tavolo'].unique():
            with st.expander(f"TAVOLO {t}", expanded=True):
                st.write(ordini[ordini['tavolo'] == t]['prod'].tolist())
                if st.button(f"LIBERA TAVOLO {t}", key=f"libera_{t}"):
                    ordini[ordini['tavolo'] != t].to_csv("ordini.csv", index=False)
                    st.rerun()

    with col_dx:
        st.subheader("🥐 Vetrina (Stock)")
        for i, row in menu.iterrows():
            c1, c2 = st.columns([2,1])
            c1.write(f"{row['prod']} (Disp: {row['stock']})")
            if c2.button("+10", key=f"refill_{i}"):
                menu.at[i, 'stock'] += 10
                menu.to_csv("menu.csv", index=False)
                st.rerun()

# ==========================================
# PARTE B: CLIENTE (SMARTPHONE)
# ==========================================
else:
    st.header("BAR PAGANO")
    
    if 'tavolo_scelto' not in st.session_state:
        st.session_state.tavolo_scelto = None

    # SCELTA TAVOLO (GRIGLIA 3x5)
    if st.session_state.tavolo_scelto is None:
        st.write("Tocca il tuo tavolo:")
        occupati = ordini['tavolo'].astype(str).tolist()
        
        for r in range(3):
            cols = st.columns(5)
            for c in range(5):
                n = str((r * 5) + c + 1)
                is_occ = n in occupati
                if cols[c].button(n, key=f"t_{n}", disabled=is_occ):
                    st.session_state.tavolo_scelto = n
                    st.rerun()

    # MENU ORDINAZIONE
    else:
        st.subheader(f"Tavolo {st.session_state.tavolo_scelto}")
        if st.button("⬅ Indietro"):
            st.session_state.tavolo_scelto = None
            st.rerun()
        
        st.write("---")
        for i, row in menu.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{row['prod']}**\n€{row['prezzo']}")
            
            if row['stock'] > 0:
                if c2.button("ORDINA", key=f"ord_{i}"):
                    # Salva Ordine
                    nuovo = pd.DataFrame([{"tavolo": st.session_state.tavolo_scelto, "prod": row['prod']}])
                    pd.concat([ordini, nuovo]).to_csv("ordini.csv", index=False)
                    # Scala Stock
                    menu.at[i, 'stock'] -= 1
                    menu.to_csv("menu.csv", index=False)
                    st.success("Inviato!")
                    time.sleep(1)
                    st.rerun()
            else:
                c2.error("FINITO")
