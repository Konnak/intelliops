# 🚀 Instruções de Deploy - IntelliOps

## 📋 Pré-requisitos

1. **Conta GitHub** (gratuita)
2. **Conta Vercel** (gratuita)
3. **Google Gemini API Key** (gratuita)

## 🔧 Passo a Passo

### **1. Preparar o Projeto**

✅ **Arquivos já criados:**
- `vercel.json` - Configuração do Vercel
- `.gitignore` - Ignora arquivos desnecessários
- `README.md` - Documentação do projeto
- `Procfile` - Para Heroku (alternativa)

### **2. Upload para GitHub**

1. **Crie um repositório no GitHub:**
   - Acesse [github.com](https://github.com)
   - Clique em "New repository"
   - Nome: `intelliops` (ou outro de sua escolha)
   - Marque como "Public" (para Vercel gratuito)

2. **Faça upload dos arquivos:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - IntelliOps"
   git branch -M main
   git remote add origin https://github.com/SEU-USUARIO/intelliops.git
   git push -u origin main
   ```

### **3. Deploy no Vercel**

1. **Acesse o Vercel:**
   - Vá para [vercel.com](https://vercel.com)
   - Clique em "Sign up" e conecte com GitHub

2. **Importe o projeto:**
   - Clique em "New Project"
   - Selecione seu repositório `intelliops`
   - Clique em "Import"

3. **Configure as variáveis:**
   - Na seção "Environment Variables"
   - Adicione: `GEMINI_API_KEY` = `sua-chave-aqui`

4. **Deploy:**
   - Clique em "Deploy"
   - Aguarde o processo (2-3 minutos)

### **4. Obter Google Gemini API Key**

1. **Acesse Google AI Studio:**
   - Vá para [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
   - Faça login com sua conta Google

2. **Crie uma API Key:**
   - Clique em "Create API Key"
   - Copie a chave gerada
   - Cole no Vercel nas variáveis de ambiente

## 🌐 URLs Finais

Após o deploy, você terá:
- **URL do Vercel**: `https://intelliops.vercel.app`
- **Domínio personalizado**: Pode configurar depois

## 🔄 Atualizações Automáticas

- **Push no GitHub** = **Deploy automático no Vercel**
- Cada commit atualiza o site automaticamente
- Sem necessidade de reconfigurar

## 📱 Teste Final

1. **Acesse sua URL do Vercel**
2. **Teste o upload de PDF**
3. **Verifique se a IA está funcionando**
4. **Teste no mobile**

## 🛠️ Solução de Problemas

### **Erro 500 - Internal Server Error**
- Verifique se a `GEMINI_API_KEY` está configurada
- Veja os logs no painel do Vercel

### **Arquivo não encontrado**
- Certifique-se que `p2.png` está na raiz do projeto
- Verifique se todos os arquivos foram commitados

### **IA não funciona**
- Confirme se a API Key do Gemini está correta
- Teste a chave localmente primeiro

## 📊 Monitoramento

- **Vercel Dashboard**: Veja estatísticas de uso
- **GitHub**: Controle de versões
- **Logs**: Acesse via painel do Vercel

## 💰 Custos

- **GitHub**: Gratuito (repositórios públicos)
- **Vercel**: Gratuito (100GB bandwidth/mês)
- **Google Gemini**: Gratuito (15 requests/minuto)

## 🔒 Segurança

- **HTTPS**: Automático no Vercel
- **API Keys**: Armazenadas de forma segura
- **Uploads**: Temporários, não persistem

## 📈 Próximos Passos

1. **Domínio personalizado** (opcional)
2. **Analytics** (Google Analytics)
3. **Backup** (GitHub já faz isso)
4. **Monitoramento** (Vercel Analytics)

---

**🎉 Parabéns! Seu sistema IntelliOps está online!**
