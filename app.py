import streamlit as st
import pandas as pd
import os, time

# --- 1. CONFIGURAZIONE & GRAFICA ---
st.set_page_config(page_title="BAR PAGANO", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    /* Griglia 5 colonne fissa per smartphone */
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; gap: 4px !important; }
    [data-testid="column"] { flex: 1 !important; min-width: 0px !important; }
    /* Bottoni Tavoli */
    .stButton > button { 
        width: 100% !important; height: 75px !important; 
        font-weight: 900 !important; font-size: 22px !important; border-radius: 5px !important;
    }
    /* Colori: Verde Libero, Rosso Occupato */
    div.stButton > button:first-child { background-color: #00FF00; color: black; border: none; }
    div.stButton > button:disabled { background-color: #FF0000 !important; color: white !important; opacity: 1 !important; border: none; }
    /* Estetica Categorie */
    .stSelectbox label { color: #00FF00 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
if not os.path.exists("menu.csv"):
    pd.DataFrame([
        {"cat": "VETRINA", "prod": "Cornetto", "prezzo": 1.2, "stock": 10},
        {"cat": "CAFFETTERIA", "prod": "Caffè", "prezzo": 1.0, "stock": 999},
        {"cat": "BIBITE", "prod": "Acqua 0.5L", "prezzo": 1.0, "stock": 20}
    ]).to_csv("menu.csv", index=False)

if not os.path.exists("ordini.csv"):
    pd.DataFrame(columns=["tavolo", "prod"]).to_csv("ordini.csv", index=False)

menu = pd.read_csv("menu.csv")
ordini = pd.read_csv("ordini.csv")
ruolo = st.query_params.get("ruolo", "cliente")

# ==========================================
# PARTE A: BANCONE (GESTIONE)
# ==========================================
if ruolo == "banco":
    st.title("📟 BANCONE")
    t1, t2 = st.tabs(["📋 ORDINI", "🥐 VETRINA & STOCK"])
    
    with t1:
        if ordini.empty: st.info("Nessun ordine presente.")
        for t in ordini['tavolo'].unique():
            with st.container(border=True):
                c_a, c_b = st.columns([3, 1])
                lista_p = ordini[ordini['tavolo'] == t]['prod'].tolist()
                c_a.write(f"### TAVOLO {t}")
                c_a.write(", ".join(lista_p))
                if c_b.button(f"LIBERA", key=f"lib_{t}"):
                    ordini[ordini['tavolo'] != t].to_csv("ordini.csv", index=False)
                    st.rerun()

    with t2:
        st.subheader("Carico Vetrina")
        for i, row in menu.iterrows():
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"**{row['prod']}** ({row['cat']})")
            c2.write(f"Qta: {row['stock']}")
            if c3.button("+1", key=f"ref_{i}"):
                menu.at[i, 'stock'] += 1
                menu.to_csv("menu.csv", index=False)
                st.rerun()

# ==========================================
# PARTE B: CLIENTE (SMARTPHONE)
# ==========================================
else:
    st.markdown("<h1 style='text-align:center; color:#00FF00;'>BAR PAGANO</h1>", unsafe_allow_html=True)
    
    if 'tavolo' not in st.session_state:
        st.session_state.tavolo = None

    # SCELTA TAVOLO
    if st.session_state.tavolo is None:
        occupati = ordini['tavolo'].astype(str).tolist()
        for r in range(3):
            cols = st.columns(5)
            for c in range(5):
                n = str((r * 5) + c + 1)
                if cols[c].button(n, key=f"t_{n}", disabled=(n in occupati)):
                    st.session_state.tavolo = n
                    st.rerun()

    # MENU CON CATEGORIE
    else:
        st.markdown(f"<h3 style='text-align:center; background:#00FF00; color:black;'>TAVOLO {st.session_state.tavolo}</h3>", unsafe_allow_html=True)
        if st.button("⬅ CAMBIA TAVOLO", use_container_width=True):
            st.session_state.tavolo = None
            st.rerun()
        
        # Selezione Categoria
        categorie = menu['cat'].unique()
        scelta_cat = st.selectbox("Scegli Categoria:", categorie)
        
        st.divider()
        
        # Filtra menu per categoria scelta
        prodotti_filtrati = menu[menu['cat'] == scelta_cat]
        
        for i, row in prodotti_filtrati.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{row['prod']}**\n€ {row['prezzo']:.2f}")
            
            if row['stock'] > 0:
                if c2.button("ORDINA", key=f"o_{i}"):
                    # Salva Ordine
                    nuovo = pd.DataFrame([{"tavolo": st.session_state.tavolo, "prod": row['prod']}])
                    pd.concat([ordini, nuovo]).to_csv("ordini.csv", index=False)
                    # Scala Stock
                    # Troviamo l'indice originale nel menu completo per scalare correttamente
                    menu.loc[menu['prod'] == row['prod'], 'stock'] -= 1
                    menu.to_csv("menu.csv", index=False)
                    st.success("Ordinato!")
                    time.sleep(0.5)
                    st.rerun()
            else:
                c2.error("ESAURITO")
