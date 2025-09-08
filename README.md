# IntelliOps - Sistema de Análise Inteligente

## 🚀 Sobre o Projeto

**IntelliOps** é uma plataforma avançada de processamento de ocorrências policiais que utiliza inteligência artificial para análise e classificação automática de relatórios. O sistema processa PDFs de ocorrências, extrai dados relevantes e gera relatórios formatados para WhatsApp.

## ✨ Funcionalidades

- 📄 **Upload de PDFs**: Processamento automático de relatórios policiais
- 🤖 **IA Integrada**: Resumos automáticos com Google Gemini
- 🎯 **Classificação Inteligente**: Relevância ALTA, MÉDIA e BAIXA
- 📱 **Interface Responsiva**: Otimizada para desktop e mobile
- 💬 **Relatórios WhatsApp**: Formatação automática para mensagens
- 🔍 **Análise de Termos**: Destaque de palavras-chave relevantes

## 🛠️ Tecnologias

- **Backend**: Python + Flask
- **Frontend**: HTML5, CSS3, JavaScript
- **IA**: Google Gemini API
- **PDF Processing**: PyMuPDF, tabula-py
- **Deploy**: Vercel

## 📋 Pré-requisitos

- Python 3.8+
- Conta Google (para Gemini API)
- Git

## 🚀 Instalação Local

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/intelliops.git
cd intelliops
```

2. **Instale as dependências**
```bash
pip install -r requirements.txt
```

3. **Configure a API Key**
```bash
export GEMINI_API_KEY="sua-chave-aqui"
```

4. **Execute o projeto**
```bash
python app.py
```

5. **Acesse no navegador**
```
http://localhost:5000
```

## 🌐 Deploy no Vercel

### 1. **Prepare o Repositório**
- Faça upload do projeto para GitHub
- Certifique-se que todos os arquivos estão commitados

### 2. **Configure no Vercel**
- Acesse [vercel.com](https://vercel.com)
- Conecte sua conta GitHub
- Importe o repositório

### 3. **Configure Variáveis de Ambiente**
No painel do Vercel, adicione:
```
GEMINI_API_KEY = sua-chave-do-gemini
```

### 4. **Deploy Automático**
- O Vercel fará deploy automático
- Cada push no GitHub atualiza o site

## 📁 Estrutura do Projeto

```
intelliops/
├── app.py                 # Aplicação Flask principal
├── requirements.txt       # Dependências Python
├── vercel.json           # Configuração Vercel
├── templates/
│   └── index.html        # Interface principal
├── uploads/              # Arquivos temporários
├── p2.png               # Logo do sistema
└── README.md            # Este arquivo
```

## 🔧 Configuração da IA

O sistema utiliza a **Google Gemini API** para resumos automáticos:

1. **Obtenha uma API Key**:
   - Acesse [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Crie uma nova API Key

2. **Configure no Vercel**:
   - Adicione `GEMINI_API_KEY` nas variáveis de ambiente

## 📱 Recursos Mobile

- **Modal Inteligente**: Visualização de relatórios em tela cheia
- **Layout Responsivo**: Adapta-se a qualquer dispositivo
- **Touch-Friendly**: Botões otimizados para toque
- **Performance**: Carregamento rápido em 3G/4G

## 🎨 Interface

- **Tema Escuro**: Design moderno e profissional
- **Animações**: Efeitos visuais suaves
- **Gradientes**: Cores da bandeira brasileira
- **Tipografia**: Fonte Inter para melhor legibilidade

## 📊 Funcionalidades de Análise

### **Classificação Automática**
- **ALTA**: Armas, homicídios, incêndios
- **MÉDIA**: Prisões, tráfico, drogas
- **BAIXA**: Ameaças, agressões

### **Extração de Dados**
- BOU/Protocolo
- Natureza da ocorrência
- Endereço completo
- Data e hora
- Relato policial

### **Relatórios WhatsApp**
- Formatação automática
- Agrupamento por cidade
- Resumos com IA
- Emojis e formatação

## 🔒 Segurança

- **Upload Seguro**: Validação de arquivos
- **Sanitização**: Limpeza de dados
- **Rate Limiting**: Proteção contra spam
- **HTTPS**: Conexão segura

## 📈 Performance

- **Processamento Assíncrono**: Não trava a interface
- **Cache Inteligente**: Dados temporários
- **Otimização Mobile**: Carregamento rápido
- **Compressão**: Arquivos otimizados

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

Para suporte e dúvidas:
- Abra uma [Issue](https://github.com/seu-usuario/intelliops/issues)
- Entre em contato via email

## 🎯 Roadmap

- [ ] Integração com mais APIs de IA
- [ ] Dashboard de estatísticas
- [ ] Exportação em múltiplos formatos
- [ ] API REST para integrações
- [ ] Sistema de usuários
- [ ] Backup automático

---

**Desenvolvido com ❤️ para otimizar o trabalho policial**