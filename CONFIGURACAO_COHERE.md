# 🤖 Configuração da API Cohere (Gratuita)

## 🎯 **Por que Cohere?**

### ✅ **Vantagens sobre Hugging Face:**
- **Melhor para Português**: Modelos treinados em múltiplos idiomas
- **Resumos Mais Precisos**: Algoritmos otimizados para resumo
- **Menos Textos Estranhos**: Menos probabilidade de gerar conteúdo inadequado
- **API Mais Estável**: Menos falhas e timeouts
- **Gratuito**: Plano gratuito generoso

## 🔑 **Como Obter a Chave da API**

### **1. Criar Conta no Cohere**
1. Acesse: https://cohere.ai/
2. Clique em "Get Started" ou "Sign Up"
3. Crie uma conta gratuita
4. Verifique seu email

### **2. Obter a Chave da API**
1. Faça login na sua conta
2. Vá para: https://dashboard.cohere.ai/api-keys
3. Clique em "Create API Key"
4. Dê um nome para sua chave (ex: "SADE-Sistema")
5. Copie a chave gerada

### **3. Configurar no Sistema**
1. Abra o arquivo `app.py`
2. Substitua `cohere_api_key_here` pela sua chave real
3. Salve o arquivo

**Exemplo:**
```python
COHERE_API_KEY = "cohere_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## 🎯 **Configuração da API**

### **Parâmetros Otimizados:**
```python
payload = {
    "text": cleaned_text,
    "length": "medium",           # Tamanho médio do resumo
    "format": "paragraph",        # Formato em parágrafo
    "model": "summarize-xlarge",  # Modelo mais avançado
    "extractiveness": "medium",   # Extração média (não muito resumido)
    "temperature": 0.3            # Baixa criatividade (mais preciso)
}
```

### **Headers Configurados:**
```python
headers = {
    "Authorization": f"Bearer {COHERE_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
```

## 🎯 **Exemplo de Uso**

### **Texto Original:**
```
Equipe acionada para atendimento de ocorrência na Rua das Flores, 123. No local, foi constatada discussão entre casal. A vítima Maria Silva informou que foi agredida pelo companheiro João Santos. Realizada verificação e conduzido o autor para delegacia.
```

### **Resumo Esperado:**
```
Vítima informou que foi agredida pelo autor. Realizada verificação e conduzido para delegacia.
```

## 🔍 **Logs de Debug Esperados**

### **Sucesso:**
```
DEBUG: Relato original: Equipe acionada para atendimento de ocorrência na Rua das Flores...
DEBUG: Relato limpo: Ocorrência na Rua das Flores. Vítima informou que foi agredida pelo autor...
DEBUG: Relato resumido: Vítima informou que foi agredida pelo autor. Realizada verificação e conduzido para delegacia.
```

### **Falha:**
```
DEBUG: Resumo da IA rejeitado por ser inválido: Texto em inglês ou estranho...
DEBUG: IA falhou para BOU 2025/1135699, não incluindo relato
```

## 🎯 **Benefícios da Cohere**

### **Qualidade:**
- **Resumos Mais Precisos**: Algoritmos otimizados
- **Melhor Português**: Modelos treinados em múltiplos idiomas
- **Menos Textos Estranhos**: Menos probabilidade de falhas
- **Consistência**: Resultados mais previsíveis

### **Confiabilidade:**
- **API Estável**: Menos falhas e timeouts
- **Suporte Técnico**: Documentação completa
- **Uptime Alto**: Serviço confiável
- **Rate Limits Generosos**: Plano gratuito suficiente

### **Facilidade:**
- **Configuração Simples**: Apenas uma chave
- **Documentação Clara**: Fácil de implementar
- **Suporte**: Comunidade ativa
- **Gratuito**: Sem custos

## 🚀 **Próximos Passos**

1. **Criar Conta**: Acesse https://cohere.ai/
2. **Obter Chave**: Gere API key no dashboard
3. **Configurar**: Substitua a chave no código
4. **Testar**: Verifique os resumos melhorados

## 📊 **Comparação de APIs**

| Característica | Hugging Face | Cohere |
|----------------|--------------|---------|
| **Português** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Resumos** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Estabilidade** | ⭐⭐ | ⭐⭐⭐⭐ |
| **Facilidade** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Gratuito** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

**A Cohere oferece resumos muito melhores em português!** 🎯

Configure a chave e veja a diferença na qualidade dos resumos.
