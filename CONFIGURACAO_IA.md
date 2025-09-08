# 🤖 Configuração da IA para Resumo de Relatos

## 📋 **Funcionalidade Implementada**

Agora o sistema usa **Inteligência Artificial** para resumir os relatos das ocorrências seguindo regras específicas:

### ✅ **Regras da IA:**
1. **NÃO cita nomes** - apenas usa: autor, vítima, solicitante, testemunha
2. **Foca nos fatos criminais** principais
3. **Remove informações desnecessárias** como "equipe acionada", "equipe deslocou", etc.
4. **Seja conciso e direto**
5. **Mantém apenas informações relevantes** para o relatório
6. **Usa linguagem formal e objetiva**

## 🔧 **Configuração Necessária**

### Passo 1: Instalar Dependência
```bash
pip install openai==1.3.0
```

### Passo 2: Configurar API Key
Crie um arquivo `.env` na raiz do projeto com:
```
OPENAI_API_KEY=sua_chave_api_aqui
```

### Passo 3: Obter Chave da API
1. Acesse: https://platform.openai.com/api-keys
2. Faça login na sua conta OpenAI
3. Clique em "Create new secret key"
4. Copie a chave e cole no arquivo `.env`

## 🎯 **Como Funciona**

### **Antes (Relato Original):**
```
Equipe acionada via Sistema Sade Mobile para atendimento de ocorrência na Rua Pedro Belino de Bonfim, 526, Itaperuçu. No local, a equipe encontrou a vítima Maria Silva que informou ter sido agredida pelo autor João Santos com socos e pontapés. A vítima apresentava lesões no rosto e braços. O autor foi identificado e conduzido à delegacia.
```

### **Depois (Resumo com IA):**
```
Vítima informou ter sido agredida pelo autor com socos e pontapés, apresentando lesões no rosto e braços. Autor foi identificado e conduzido à delegacia.
```

## 🚀 **Exemplo de Uso**

### **Relatório WhatsApp:**
```
*ALMIRANTE TAMANDARÉ*
2025/1135699 - ABORDAGEM DE SUSPEITOS
- Vítima informou que indivíduos retornaram com arma de fogo em mãos após disparos no local anterior

2025/1135702 - SUICÍDIO
- Ocorrência envolvendo mulher que teria tentado suicídio

2025/1136328 - POLICIAMENTO PRESENÇA
- Atendimento de ocorrência na localidade
```

## 🔍 **Logs de Debug**

O sistema mostra logs detalhados:
```
DEBUG: Formatando ocorrência: BOU=2025/1135699, Natureza=ABORDAGEM DE SUSPEITOS, Relato=Equipe acionada para atendimento...
DEBUG: Relato resumido: Vítima informou que indivíduos retornaram com arma de fogo...
```

## ⚠️ **Fallback de Segurança**

Se a IA falhar, o sistema:
1. Mostra erro no console
2. Usa o relato original truncado (200 caracteres)
3. Continua funcionando normalmente

## 💰 **Custos da API**

- **Modelo usado:** GPT-3.5-turbo
- **Custo aproximado:** $0.001 por resumo
- **Limite de tokens:** 150 por resumo
- **Temperatura:** 0.3 (mais determinístico)

## 🎨 **Benefícios**

### ✅ **Relatórios Mais Limpos:**
- Remove informações desnecessárias
- Foca nos fatos criminais
- Mantém anonimato das vítimas

### ✅ **Melhor Legibilidade:**
- Textos mais concisos
- Linguagem formal e objetiva
- Informações relevantes destacadas

### ✅ **Padronização:**
- Todos os relatos seguem o mesmo padrão
- Remove variações de linguagem
- Mantém consistência

---

**Configure a API key e teste a funcionalidade de resumo com IA!** 🤖

A IA tornará os relatórios muito mais profissionais e focados nos fatos relevantes.
