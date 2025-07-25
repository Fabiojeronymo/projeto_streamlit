import streamlit as st

pages  = {
    "Dashboards": [
        st.Page("page_1.py", title="Evolução e Performance", icon="📈"),
        st.Page("page_2.py", title="Variação mensal", icon="📊"),
    ],
}

pg = st.navigation(pages, position="sidebar")
pg.run()