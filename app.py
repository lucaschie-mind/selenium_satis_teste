import os
from pathlib import Path

import streamlit as st

from runner import run_login_test

st.set_page_config(page_title="Selenium no Railway", page_icon="🤖", layout="centered")
st.title("Teste manual do Selenium no Railway")
st.caption("Versão 1 segura: execução manual com credenciais apenas nas Variables do Railway.")

with st.expander("Variáveis esperadas no Railway"):
    st.code(
        "\n".join(
            [
                "TENANT=seu-tenant",
                "MINDSIGHT_EMAIL=seu_email@mindsight.com.br",
                "MINDSIGHT_PASSWORD=sua_senha",
                "GMAIL_EMAIL=seu_email@gmail.com",
                "GMAIL_APP_PASSWORD=sua_app_password",
                "HEADLESS=true",
            ]
        )
    )
    st.caption("Esses valores devem ser cadastrados em Railway > Service > Variables. Não salve credenciais no repositório.")

col1, col2 = st.columns(2)
with col1:
    tenant = st.text_input("Tenant", value=os.getenv("TENANT", ""), placeholder="ex.: brio")
with col2:
    headless = st.toggle("Headless", value=os.getenv("HEADLESS", "true").lower() == "true")

st.info(
    "Esta versão executa o login no auth e a captura do OTP no Gmail para validar o ambiente do Railway. "
    "Depois disso, a mesma base pode ser usada para a rotina automática."
)

if st.button("Rodar script", type="primary", use_container_width=True):
    with st.spinner("Executando Selenium no container do Railway..."):
        result = run_login_test(tenant=tenant, headless=headless)

    if result.success:
        st.success("Execução concluída com sucesso.")
    else:
        st.error(result.error or "Falha na execução.")

    st.subheader("Logs")
    st.code("\n".join(result.logs) if result.logs else "Sem logs.")

    meta = {
        "success": result.success,
        "current_url": result.current_url,
        "otp_code_captured": bool(result.otp_code),
        "screenshot_path": result.screenshot_path,
    }
    st.subheader("Resumo")
    st.json(meta)

    if result.screenshot_path and Path(result.screenshot_path).exists():
        st.subheader("Screenshot final")
        st.image(result.screenshot_path)
