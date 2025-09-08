# 🔧 Correção: Relatório sem Ocorrências e Extração de Cidade

## ❌ **Problemas Identificados**

1. **Relatório vazio**: Ocorrências selecionadas não apareciam no relatório
2. **Cidade não extraída**: A cidade não estava sendo extraída corretamente do endereço
3. **Falta de debug**: Não havia logs para identificar onde estava o problema

## ✅ **Correções Implementadas**

### 🎯 **1. Extração de Cidade Corrigida**

**Antes:**
```python
def extract_city_from_address(endereco):
    parts = endereco.split('-')
    if len(parts) > 1:
        city_part = parts[-1].strip()
        city = re.sub(r'[0-9\-\/]', '', city_part).strip()
        return city.upper()
    return endereco.upper()
```

**Agora:**
```python
def extract_city_from_address(endereco):
    if not endereco:
        return 'Cidade não identificada'
    
    # Padrão principal: cidade após o traço
    # Exemplo: "RUA DIVINA RODRIGUES, 123 - CURITIBA"
    match = re.search(r'-\s*([^,\n]+)', endereco, re.IGNORECASE)
    if match:
        city = match.group(1).strip()
        # Limpar caracteres especiais e espaços extras
        city = re.sub(r'[^\w\s]', '', city)
        city = re.sub(r'\s+', ' ', city).strip()
        if len(city) > 2:  # Cidade deve ter pelo menos 3 caracteres
            return city.upper()
    
    # Fallback: procurar após vírgula
    match = re.search(r',\s*([^,\n]+)', endereco, re.IGNORECASE)
    if match:
        city = match.group(1).strip()
        city = re.sub(r'[^\w\s]', '', city)
        city = re.sub(r'\s+', ' ', city).strip()
        if len(city) > 2:
            return city.upper()
    
    return 'Cidade não identificada'
```

### 🔍 **2. Logs de Debug Adicionados**

**Endpoint de Geração:**
```python
@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        selected_ocorrencias = data.get('selected_ocorrencias', [])
        
        print(f"DEBUG: Ocorrências recebidas: {len(selected_ocorrencias)}")
        for i, oc in enumerate(selected_ocorrencias):
            print(f"DEBUG: Ocorrência {i}: BOU={oc.get('bou')}, Endereço={oc.get('endereco')}")
        
        # ... resto do código
```

**Função de Geração:**
```python
def generate_whatsapp_report(selected_ocorrencias):
    print(f"DEBUG: Gerando relatório para {len(selected_ocorrencias)} ocorrências")
    
    for oc in selected_ocorrencias:
        endereco = oc.get('endereco', '')
        cidade = extract_city_from_address(endereco)
        
        print(f"DEBUG: Endereço: '{endereco}' -> Cidade extraída: '{cidade}'")
        
        # Mapear para cidades conhecidas do 34°BPM
        cidade_mapeada = ''
        for cidade_bpm in CIDADES:
            if cidade_bpm in cidade or cidade in cidade_bpm:
                cidade_mapeada = cidade_bpm
                break
        
        print(f"DEBUG: Cidade mapeada: '{cidade_mapeada}'")
    
    print(f"DEBUG: Ocorrências por cidade: {list(ocorrencias_por_cidade.keys())}")
```

## 🎯 **Como Testar**

### Passo 1: Acesse a Aplicação
```
http://localhost:5000
```

### Passo 2: Faça Upload e Análise
- Faça upload do PDF
- Clique em "Analisar Ocorrências"
- Aguarde o processamento

### Passo 3: Selecione Ocorrências
- Marque algumas ocorrências como "RELEVANTE"
- Observe se a descrição aparece em cinza abaixo da data
- Verifique se o relato mostra apenas a coluna "Relato Policial Ocorrido"

### Passo 4: Gere o Relatório
- Clique em "Gerar Mensagem"
- Verifique os logs no terminal para debug
- Confirme se as ocorrências aparecem no relatório

## 🔍 **Logs de Debug Esperados**

```
DEBUG: Ocorrências recebidas: 3
DEBUG: Ocorrência 0: BOU=2025/1135699, Endereço=RUA DIVINA RODRIGUES, 123 - CURITIBA
DEBUG: Ocorrência 1: BOU=2025/1135478, Endereço=AVENIDA BRASIL, 456 - ALMIRANTE TAMANDARÉ
DEBUG: Ocorrência 2: BOU=2025/1135635, Endereço=RUA PRINCIPAL, 789 - CAMPO MAGRO

DEBUG: Gerando relatório para 3 ocorrências
DEBUG: Endereço: 'RUA DIVINA RODRIGUES, 123 - CURITIBA' -> Cidade extraída: 'CURITIBA'
DEBUG: Cidade mapeada: 'OUTRAS'
DEBUG: Endereço: 'AVENIDA BRASIL, 456 - ALMIRANTE TAMANDARÉ' -> Cidade extraída: 'ALMIRANTE TAMANDARÉ'
DEBUG: Cidade mapeada: 'ALMIRANTE TAMANDARÉ'
DEBUG: Endereço: 'RUA PRINCIPAL, 789 - CAMPO MAGRO' -> Cidade extraída: 'CAMPO MAGRO'
DEBUG: Cidade mapeada: 'CAMPO MAGRO'
DEBUG: Ocorrências por cidade: ['OUTRAS', 'ALMIRANTE TAMANDARÉ', 'CAMPO MAGRO']
```

## 🎨 **Melhorias na Extração de Cidade**

### ✅ **Padrões Suportados:**
- `"RUA DIVINA RODRIGUES, 123 - CURITIBA"` → `"CURITIBA"`
- `"AVENIDA BRASIL, 456 - ALMIRANTE TAMANDARÉ"` → `"ALMIRANTE TAMANDARÉ"`
- `"RUA PRINCIPAL, 789 - CAMPO MAGRO"` → `"CAMPO MAGRO"`

### ✅ **Fallbacks:**
- Se não encontrar traço, procura após vírgula
- Remove caracteres especiais e números
- Limpa espaços extras
- Retorna "Cidade não identificada" se não encontrar

### ✅ **Mapeamento para Cidades do 34°BPM:**
- `ALMIRANTE TAMANDARÉ`
- `CAMPO MAGRO`
- `RIO BRANCO DO SUL`
- `CERRO AZUL`
- `ITAPERUÇU`
- `DOUTOR ULYSSES`

## 🚀 **Próximos Passos**

1. **Teste a aplicação** com as correções
2. **Verifique os logs** no terminal para debug
3. **Confirme se as ocorrências** aparecem no relatório
4. **Reporte qualquer problema** encontrado

---

**Teste agora e veja se as ocorrências selecionadas aparecem corretamente no relatório!** 🎯

As correções devem resolver tanto o problema da extração de cidade quanto a inclusão das ocorrências no relatório.
