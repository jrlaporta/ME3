@echo off
REM =====================================================
REM 🚀 Inicializador do Painel ME3_Node (versão compatível)
REM =====================================================

cd /d "%~dp0"
echo ===========================================
echo Iniciando o Painel ME3_Node...
echo ===========================================

REM Ativa o ambiente virtual e instala dependências
echo Ativando ambiente virtual e instalando dependências...
powershell -ExecutionPolicy RemoteSigned -Command ".\.venv\Scripts\Activate.ps1; pip install --upgrade pip; pip install -r requirements.txt; pip install openpyxl; streamlit run app.py"

echo ===========================================
echo Painel iniciado. Feche esta janela para encerrar.
echo ===========================================
pause
