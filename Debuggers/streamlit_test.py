# Last updated: 2025-04-29 14:23:14
# app.py

import streamlit as st

st.title("Hello, Streamlit!")
st.write("This is a simple test app to check if Streamlit is running properly.")

# Add a basic button
if st.button("Click me"):
    st.success("Streamlit is working!")