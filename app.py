import streamlit as st
import pandas as pd
import os, time

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="PAGANOCAFE", layout="centered")

# CSS per colori e bottoni
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #fff; }
    .stButton > button { width: 100%; border-radius: 10px; font-weight: bold; height: 60px; background-color: #d4af37 !important; color: black !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE (FILE) ---
def setup_file(name, cols):
    if not os.path.exists(name) or os.stat(name).st_size == 0:
        pd.DataFrame(columns=cols).to_csv(name, index=False)

setup_file("menu.csv", ["cat", "prod", "prezzo", "stock"])
setup_file("ordini.csv", ["tavolo", "prod", "prezzo"])

menu = pd.read_csv("menu.csv")
ordini = pd.read_csv("ordini.csv")
ruolo = st.query_params.get("ruolo", "cliente")

# ==========================================
# BANCONE (?ruolo=banco)
# ==========================================
if ruolo == "banco":
    st.title("📟 BANCONE PAGANOCAFE")
    t1, t2, t3 = st.tabs(["ORDINI & CASSA", "CARICO VETRINA", "AGGIUNGI PRODOTTI"])

    with t1:
        if ordini.empty: st.info("Nessun ordine.")
        else:
            for t in ordini['tavolo'].unique():
                with st.container(border=True):
                    items = ordini[ordini['tavolo'] == t]
                    totale = items['prezzo'].sum()
                    st.subheader(f"Tavolo {t} - Tot: €{totale:.2f}")
                    st.write(", ".join(items['prod'].tolist()))
                    if st.button(f"PAGATO / LIBERA {t}", key=f"pay_{t}"):
                        ordini[ordini['tavolo'] != t].to_csv("ordini.csv", index=False)
                        st.rerun()

    with t2:
        st.subheader("Rifornimento +1")
        for i, r in menu.iterrows():
            c1, c2, c3 = st.columns([2,1,1])
            c1.write(r['prod'])
            c2.write(f"Disp: {r['stock']}")
            if c3.button("+1", key=f"add_{i}"):
                menu.at[i, 'stock'] += 1
                menu.to_csv("menu.csv", index=False)
                st.rerun()

    with t3:
        with st.form("new"):
            c_cat = st.selectbox("Categoria", ["VETRINA", "CAFFETTERIA", "BIBITE"])
            c_prod = st.text_input("Nome")
            c_prez = st.number_input("Prezzo", step=0.1)
            if st.form_submit_button("SALVA"):
                nuovo = pd.DataFrame([{"cat": c_cat, "prod": c_prod, "prezzo": c_prez, "stock": 0}])
                pd.concat([menu, nuovo]).to_csv("menu.csv", index=False)
                st.rerun()

# ==========================================
# CLIENTE
# ==========================================
else:
    st.title("☕ PAGANOCAFE")
    
    if menu.empty:
        st.warning("Configura prima il menu dal banco!")
    else:
        # 1. Tavolo a tendina
        tavolo = st.selectbox("Scegli il tuo tavolo:", ["---"] + [str(i) for i in range(1, 16)])
        
        if tavolo != "---":
            # 2. Categorie
            cat_scelta = st.radio("Cosa desideri?", menu['cat'].unique(), horizontal=True)
            st.divider()
            
            # 3. Prodotti
            prod_filtrati = menu[menu['cat'] == cat_scelta]
            for i, r in prod_filtrati.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{r['prod']}**\n€{r['prezzo']:.2f}")
                
                if r['stock'] > 0:
                    if c2.button("ORDINA", key=f"ord_{i}"):
                        # Salva Ordine
                        nuovo_o = pd.DataFrame([{"tavolo": tavolo, "prod": r['prod'], "prezzo": r['prezzo']}])
                        pd.concat([ordini, nuovo_o]).to_csv("ordini.csv", index=False)
                        # Scala stock
                        menu.at[i, 'stock'] -= 1
                        menu.to_csv("menu.csv", index=False)
                        st.success("Inviato!")
                        time.sleep(1)
                        st.rerun()
                else:
                    c2.error("FINITO")
