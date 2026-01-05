import streamlit as st
import pandas as pd
import os, time

st.set_page_config(page_title="BAR PAGANO", layout="wide")

# CSS MINIMALE: Solo per bloccare le 5 colonne su telefono
st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; gap: 5px !important; }
    [data-testid="column"] { flex: 1 !important; min-width: 0px !important; }
    .stButton > button { width: 100% !important; height: 70px !important; font-weight: bold; }
    /* Verde se libero, Rosso se occupato */
    div.stButton > button { background-color: #28a745; color: white; }
    div.stButton > button:disabled { background-color: #dc3545 !important; color: white !important; opacity: 1 !important; }
    </style>
    """, unsafe_allow_html=True)

# DATABASE VOLANTE
if not os.path.exists("menu.csv"):
    pd.DataFrame([
        {"cat": "VETRINA", "prod": "Cornetto", "stock": 10},
        {"cat": "CAFFETERIA", "prod": "Caffè", "stock": 99}
    ]).to_csv("menu.csv", index=False)
if not os.path.exists("ordini.csv"):
    pd.DataFrame(columns=["tavolo", "prod"]).to_csv("ordini.csv", index=False)

menu = pd.read_csv("menu.csv")
ordini = pd.read_csv("ordini.csv")
ruolo = st.query_params.get("ruolo", "cliente")

# --- BANCO ---
if ruolo == "banco":
    st.title("BANCO")
    st.subheader("Ordini")
    st.write(ordini)
    if st.button("Svuota tutto"):
        pd.DataFrame(columns=["tavolo", "prod"]).to_csv("ordini.csv", index=False)
        st.rerun()
    
    st.write("---")
    st.subheader("Vetrina")
    for i, r in menu.iterrows():
        c1, c2 = st.columns([3,1])
        c1.write(f"{r['prod']} (Disp: {r['stock']})")
        if c2.button("+1", key=i):
            menu.at[i, 'stock'] += 1
            menu.to_csv("menu.csv", index=False)
            st.rerun()

# --- CLIENTE ---
else:
    st.title("BAR PAGANO")
    if 't' not in st.session_state: st.session_state.t = None

    if st.session_state.t is None:
        st.write("Scegli Tavolo:")
        occ = ordini['tavolo'].astype(str).tolist()
        for r in range(3):
            cols = st.columns(5)
            for c in range(5):
                n = str((r * 5) + c + 1)
                if cols[c].button(n, key=n, disabled=(n in occ)):
                    st.session_state.t = n
                    st.rerun()
    else:
        st.header(f"Tavolo {st.session_state.t}")
        if st.button("Indietro"):
            st.session_state.t = None
            st.rerun()
        
        cat = st.radio("Categoria:", menu['cat'].unique(), horizontal=True)
        items = menu[menu['cat'] == cat]
        
        for i, r in items.iterrows():
            c1, c2 = st.columns([3,1])
            c1.write(r['prod'])
            if r['stock'] > 0:
                if c2.button("ORDINA", key=f"o{i}"):
                    pd.concat([ordini, pd.DataFrame([{"tavolo":st.session_state.t, "prod":r['prod']}])]).to_csv("ordini.csv", index=False)
                    menu.loc[menu['prod']==r['prod'], 'stock'] -= 1
                    menu.to_csv("menu.csv", index=False)
                    st.rerun()
            else: c2.write("FINITO")
