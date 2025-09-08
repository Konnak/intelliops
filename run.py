#!/usr/bin/env python3
"""
Script de inicialização para o Analisador de Ocorrências Policiais
34° Batalhão de Polícia Militar
"""

import os
import sys
import subprocess
import webbrowser
from time import sleep

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 7):
        print("❌ Erro: Python 3.7 ou superior é necessário")
        print(f"   Versão atual: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} - OK")
    return True

def install_requirements():
    """Instala as dependências necessárias"""
    print("📦 Verificando dependências...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError:
        print("❌ Erro ao instalar dependências")
        return False

def create_upload_folder():
    """Cria a pasta de uploads se não existir"""
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        print(f"📁 Pasta '{upload_dir}' criada")
    else:
        print(f"📁 Pasta '{upload_dir}' já existe")

def start_application():
    """Inicia a aplicação Flask"""
    print("\n🚀 Iniciando Analisador de Ocorrências Policiais...")
    print("📍 Aplicação será executada em: http://localhost:5000")
    print("⏹️  Para parar a aplicação, pressione Ctrl+C")
    print("\n" + "="*60)
    
    # Aguarda um pouco antes de abrir o navegador
    sleep(2)
    
    try:
        # Tenta abrir o navegador automaticamente
        webbrowser.open("http://localhost:5000")
        print("🌐 Navegador aberto automaticamente")
    except:
        print("🌐 Abra manualmente: http://localhost:5000")
    
    # Inicia a aplicação Flask
    from app import app
    app.run(debug=True, host='0.0.0.0', port=5000)

def main():
    """Função principal"""
    print("="*60)
    print("📊 ANALISADOR DE OCORRÊNCIAS POLICIAIS - 34°BPM")
    print("="*60)
    
    # Verificações iniciais
    if not check_python_version():
        return
    
    # Instala dependências
    if not install_requirements():
        return
    
    # Cria pasta de uploads
    create_upload_folder()
    
    # Inicia aplicação
    try:
        start_application()
    except KeyboardInterrupt:
        print("\n\n⏹️  Aplicação encerrada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar aplicação: {e}")
        print("💡 Verifique se a porta 5000 não está sendo usada por outro processo")

if __name__ == "__main__":
    main()
