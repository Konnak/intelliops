from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import re
import os
from datetime import datetime
import json
import pandas as pd
import tabula

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Configuração da IA Externa (gratuita) - Hugging Face API
import requests

# Configuração da API Google Gemini (gratuita e estável)
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyCo0mC8kOeQdiJpvu3ToG0gL6tQf0s9pns')  # Chave do Vercel ou fallback

AI_AVAILABLE = True
print("✅ IA Google Gemini configurada com sucesso!")

# Criar pasta de uploads se não existir
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except:
    # Em produção, usar pasta temporária
    app.config['UPLOAD_FOLDER'] = '/tmp'

# Termos de relevância padrão
DEFAULT_TERMS = {
    'alta': ['Arma', 'Armamento', 'Pistola', 'Tiro', 'Disparo', 'Fogo', 'Homicídio', 'Óbito', 'Incêndio'],
    'media': ['Prisão', 'Tráfico', 'Droga'],
    'baixa': ['Ameaça', 'Agressão', 'Agrediu']
}

# Cidades do 34°BPM
CIDADES = [
    'ALMIRANTE TAMANDARÉ',
    'CAMPO MAGRO', 
    'RIO BRANCO DO SUL',
    'CERRO AZUL',
    'ITAPERUÇU',
    'DOUTOR ULYSSES'
]

def convert_pdf_to_excel(pdf_path):
    """Converte PDF para Excel para análise da estrutura"""
    try:
        # Tentar extrair tabelas com tabula
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        
        if tables:
            # Criar arquivo Excel
            excel_path = pdf_path.replace('.pdf', '_analise.xlsx')
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for i, table in enumerate(tables):
                    if not table.empty:
                        # Limpar dados
                        table = table.dropna(how='all')  # Remover linhas vazias
                        table = table.dropna(axis=1, how='all')  # Remover colunas vazias
                        
                        # Salvar cada tabela em uma aba
                        sheet_name = f'Tabela_{i+1}'
                        table.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        print(f"📋 Tabela {i+1} salva com {len(table)} linhas e {len(table.columns)} colunas")
                        print(f"📋 Colunas: {list(table.columns)}")
                        print(f"📋 Primeiras 3 linhas: {table.head(3).values.tolist()}")
            
            return excel_path, tables
        else:
            print("Nenhuma tabela encontrada com tabula")
            return None, None
            
    except Exception as e:
        print(f"Erro ao converter PDF para Excel: {e}")
        return None, None

def extract_text_from_pdf(pdf_path):
    """Extrai texto do PDF e retorna as ocorrências estruturadas"""
    ocorrencias = []
    
    # Primeiro, tentar converter para Excel para análise
    excel_path, tables = convert_pdf_to_excel(pdf_path)
    
    if tables:
        print(f"✅ PDF convertido para Excel: {excel_path}")
        # Processar tabelas extraídas usando nova lógica
        ocorrencias = process_excel_tables(tables)
        
        if ocorrencias:
            print(f"✅ Método Excel encontrou {len(ocorrencias)} ocorrências")
            return ocorrencias
        else:
            print("❌ Nenhuma ocorrência encontrada no método Excel")
    
    # Método 1: Tentar extração estruturada por blocos
    try:
        ocorrencias = extract_from_structured_pdf(pdf_path)
        if ocorrencias:
            print(f"Método estruturado encontrou {len(ocorrencias)} ocorrências")
            return ocorrencias
    except Exception as e:
        print(f"Erro no método estruturado: {e}")
    
    # Método 2: Tentar extração por tabelas
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Tentar extrair tabelas primeiro
            tables = page.find_tables()
            if tables:
                for table in tables:
                    table_data = table.extract()
                    if table_data and len(table_data) > 1:  # Tem cabeçalho e dados
                        # Processar dados da tabela
                        for row in table_data[1:]:  # Pular cabeçalho
                            if len(row) >= 6:  # Verificar se tem colunas suficientes
                                ocorrencia = {
                                    'bou': row[0] if row[0] else '',
                                    'relato': row[1] if row[1] else '',
                                    'natureza': row[3] if len(row) > 3 and row[3] else '',
                                    'endereco': row[4] if len(row) > 4 and row[4] else '',
                                    'data_geracao': row[5] if len(row) > 5 and row[5] else ''
                                }
                                
                                # Limpar e validar dados
                                if ocorrencia['bou'] and len(ocorrencia['bou'].strip()) > 3:
                                    # Limpar texto
                                    for key in ocorrencia:
                                        if ocorrencia[key]:
                                            ocorrencia[key] = str(ocorrencia[key]).strip()
                                    
                                    ocorrencias.append(ocorrencia)
        
        doc.close()
        if ocorrencias:
            print(f"Método de tabelas encontrou {len(ocorrencias)} ocorrências")
            return ocorrencias
    except Exception as e:
        print(f"Erro no método de tabelas: {e}")
    
    # Método 3: Extração por texto simples
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            ocorrencias.extend(extract_from_text(text))
        
        doc.close()
        if ocorrencias:
            print(f"Método de texto encontrou {len(ocorrencias)} ocorrências")
            return ocorrencias
    except Exception as e:
        print(f"Erro no método de texto: {e}")
    
    print("Nenhum método de extração funcionou adequadamente")
    return []

def process_excel_tables(tables):
    """Processa tabelas do Excel seguindo a lógica de agrupamento por BOU"""
    ocorrencias = []
    
    for table_idx, table in enumerate(tables):
        if table.empty:
            continue
            
        print(f"Processando Tabela_{table_idx + 1} com {len(table)} linhas")
        
        # Converter para DataFrame para facilitar processamento
        table_data = table.values.tolist()
        columns = table.columns.tolist()
        
        i = 0
        while i < len(table_data):
            row = table_data[i]
            
            # Procurar BOU na primeira coluna
            bou = None
            if row and pd.notna(row[0]):
                bou_match = re.search(r'(\d{4}/\d{4,7})', str(row[0]))
                if bou_match:
                    bou = bou_match.group(1)
            
            if bou:
                print(f"Encontrado BOU: {bou} na linha {i+1}")
                
                # Coletar todas as linhas até o próximo BOU
                ocorrencia_data = {
                    'bou': bou,
                    'relato': '',
                    'natureza': '',
                    'endereco': '',
                    'data_geracao': '',
                    'colunas': {
                        'col1': [],  # Primeira coluna (BOU)
                        'col2': [],  # Segunda coluna (Descrição/Relato)
                        'col3': [],  # Terceira coluna (Grupo)
                        'col4': [],  # Quarta coluna (Relato Policial)
                        'col5': [],  # Quinta coluna (Natureza)
                        'col6': [],  # Sexta coluna (Endereço)
                        'col7': [],  # Sétima coluna (Data Geração)
                        'col8': [],  # Oitava coluna (Encerramento)
                        'col9': []   # Nona coluna (Homologação)
                    }
                }
                
                # Coletar linhas até encontrar próximo BOU ou fim da tabela
                j = i
                while j < len(table_data):
                    current_row = table_data[j]
                    
                    # Verificar se é um novo BOU (não o primeiro)
                    if j > i and current_row and pd.notna(current_row[0]):
                        next_bou_match = re.search(r'(\d{4}/\d{4,7})', str(current_row[0]))
                        if next_bou_match and next_bou_match.group(1) != bou:
                            break
                    
                    # Coletar dados por coluna
                    for col_idx, cell in enumerate(current_row):
                        if pd.notna(cell) and str(cell).strip():
                            col_key = f'col{col_idx + 1}'
                            if col_key in ocorrencia_data['colunas']:
                                ocorrencia_data['colunas'][col_key].append(str(cell).strip())
                    
                    j += 1
                
                # Processar os dados coletados por coluna
                ocorrencia = process_collected_data_by_columns(ocorrencia_data)
                if ocorrencia:
                    ocorrencias.append(ocorrencia)
                
                # Pular para a próxima ocorrência
                i = j
            else:
                i += 1
    
    return ocorrencias

def process_collected_data_by_columns(ocorrencia_data):
    """Processa os dados coletados por colunas"""
    
    # Juntar dados de cada coluna
    col1_text = ' '.join(ocorrencia_data['colunas']['col1'])  # BOU
    col2_text = ' '.join(ocorrencia_data['colunas']['col2'])  # Descrição
    col3_text = ' '.join(ocorrencia_data['colunas']['col3'])  # Grupo
    col4_text = ' '.join(ocorrencia_data['colunas']['col4'])  # Relato Policial
    col5_text = ' '.join(ocorrencia_data['colunas']['col5'])  # Natureza
    col6_text = ' '.join(ocorrencia_data['colunas']['col6'])  # Endereço
    col7_text = ' '.join(ocorrencia_data['colunas']['col7'])  # Data Geração
    col8_text = ' '.join(ocorrencia_data['colunas']['col8'])  # Encerramento
    col9_text = ' '.join(ocorrencia_data['colunas']['col9'])  # Homologação
    
    # Extrair data/hora da coluna 7 (Data Geração)
    data_match = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})', col7_text)
    if data_match:
        ocorrencia_data['data_geracao'] = data_match.group(1)
    
    # Natureza - procurar na coluna 5 primeiro, depois em outras colunas
    natureza = ''
    if col5_text:
        # Procurar por padrões de natureza na coluna 5
        natureza_patterns = [
            r'(ABORDAGEM[^.]*)',
            r'(OCORRÊNCIA[^.]*)',
            r'(DISTÚRBIO[^.]*)',
            r'(FURTO[^.]*)',
            r'(ROUBO[^.]*)',
            r'(TRÁFICO[^.]*)',
            r'(SUICÍDIO[^.]*)',
            r'(LESÃO[^.]*)',
            r'(POLICIAM[^.]*)',
            r'(FATO NAC[^.]*)',
            r'(INFRACAC[^.]*)'
        ]
        
        for pattern in natureza_patterns:
            match = re.search(pattern, col5_text, re.IGNORECASE)
            if match:
                natureza = match.group(1).strip()
                break
        
        # Se não encontrou padrão específico, usar o texto da coluna 5
        if not natureza and len(col5_text.strip()) > 3:
            natureza = col5_text.strip()
    
    ocorrencia_data['natureza'] = natureza
    
    # Endereço - procurar na coluna 6 primeiro
    endereco = ''
    if col6_text:
        # Procurar por padrões de endereço na coluna 6
        endereco_patterns = [
            r'(RUA [^,]+,\s*\d+[^,]*,\s*[^,]+,\s*[^,]+,\s*Paraná)',
            r'(AVENIDA [^,]+,\s*\d+[^,]*,\s*[^,]+,\s*[^,]+,\s*Paraná)',
            r'(AV [^,]+,\s*\d+[^,]*,\s*[^,]+,\s*[^,]+,\s*Paraná)',
            r'(RUA [^,]+,\s*\d+[^,]*,\s*[^,]+,\s*Paraná)',
            r'(AVENIDA [^,]+,\s*\d+[^,]*,\s*[^,]+,\s*Paraná)'
        ]
        
        for pattern in endereco_patterns:
            match = re.search(pattern, col6_text, re.IGNORECASE)
            if match:
                endereco = match.group(1).strip()
                break
        
        # Se não encontrou padrão específico, usar o texto da coluna 6
        if not endereco and len(col6_text.strip()) > 3:
            endereco = col6_text.strip()
    
    ocorrencia_data['endereco'] = endereco
    
    # Relato - apenas coluna 4 (Relato Policial Ocorrido)
    relato = col4_text if col4_text else ''
    
    # Descrição - coluna 2 (para mostrar separadamente)
    descricao = col2_text if col2_text else ''
    
    # Limpar espaços extras
    relato = re.sub(r'\s+', ' ', relato).strip()
    
    ocorrencia_data['relato'] = relato
    
    # Validar se tem dados mínimos
    if ocorrencia_data['bou'] and (ocorrencia_data['relato'] or ocorrencia_data['natureza']):
        return {
            'bou': ocorrencia_data['bou'],
            'relato': ocorrencia_data['relato'],
            'descricao': descricao,
            'natureza': ocorrencia_data['natureza'],
            'endereco': ocorrencia_data['endereco'],
            'data_geracao': ocorrencia_data['data_geracao']
        }
    
    return None

def extract_from_text(text):
    """Extrai ocorrências do texto quando não há tabelas estruturadas"""
    ocorrencias = []
    lines = text.split('\n')
    
    # Padrões para identificar ocorrências
    protocolo_pattern = re.compile(r'(\d{4}/\d{7})')
    data_pattern = re.compile(r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Procurar por protocolo (formato: 2025/1135699)
        protocolo_match = protocolo_pattern.search(line)
        if protocolo_match:
            protocolo = protocolo_match.group(1)
            
            # Procurar dados relacionados nas próximas linhas
            ocorrencia = {
                'bou': protocolo,
                'relato': '',
                'natureza': '',
                'endereco': '',
                'data_geracao': ''
            }
            
            # Coletar dados das próximas linhas
            j = i + 1
            relato_lines = []
            natureza_found = False
            endereco_found = False
            data_found = False
            
            while j < len(lines) and j < i + 30:  # Aumentar limite de busca
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                
                # Verificar se é uma nova ocorrência
                if protocolo_pattern.search(next_line):
                    break
                
                # Procurar data/hora (formato: 07/09/2025 09:29:44)
                if not data_found:
                    data_match = data_pattern.search(next_line)
                    if data_match:
                        ocorrencia['data_geracao'] = data_match.group(1)
                        data_found = True
                        j += 1
                        continue
                
                # Procurar natureza (geralmente contém palavras específicas)
                if not natureza_found and any(word in next_line.upper() for word in ['ABORDAGEM', 'OCORRÊNCIA', 'DISTÚRBIO', 'FURTO', 'ROUBO', 'TRÁFICO', 'SUSPEITOS', 'ILICITUDE']):
                    ocorrencia['natureza'] = next_line
                    natureza_found = True
                    j += 1
                    continue
                
                # Procurar endereço (contém RUA, AV, etc. e geralmente tem vírgula e cidade)
                if not endereco_found and any(word in next_line.upper() for word in ['RUA', 'AVENIDA', 'AV', 'ALAMEDA', 'TRAVESSA']) and ',' in next_line:
                    ocorrencia['endereco'] = next_line
                    endereco_found = True
                    j += 1
                    continue
                
                # Resto é relato (texto longo)
                if len(next_line) > 15 and not any(word in next_line.upper() for word in ['PÁGINA', 'TOTAL', 'RELATÓRIO']):
                    relato_lines.append(next_line)
                
                j += 1
            
            # Juntar linhas do relato
            if relato_lines:
                ocorrencia['relato'] = ' '.join(relato_lines)
            
            # Só adicionar se tem dados mínimos
            if ocorrencia['bou'] and (ocorrencia['relato'] or ocorrencia['natureza']):
                ocorrencias.append(ocorrencia)
            
            i = j
        else:
            i += 1
    
    return ocorrencias

def extract_from_structured_pdf(pdf_path):
    """Método alternativo para extrair dados de PDFs com estrutura específica"""
    doc = fitz.open(pdf_path)
    ocorrencias = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Obter texto com informações de posição
        text_dict = page.get_text("dict")
        
        # Procurar por blocos de texto que contenham protocolos
        for block in text_dict["blocks"]:
            if "lines" in block:
                block_text = ""
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text += span["text"] + " "
                
                # Verificar se contém protocolo
                protocolo_match = re.search(r'(\d{4}/\d{7})', block_text)
                if protocolo_match:
                    protocolo = protocolo_match.group(1)
                    
                    # Extrair dados do bloco
                    ocorrencia = extract_ocorrencia_from_block(block_text, protocolo)
                    if ocorrencia:
                        ocorrencias.append(ocorrencia)
    
    doc.close()
    return ocorrencias

def extract_ocorrencia_from_block(block_text, protocolo):
    """Extrai dados de uma ocorrência de um bloco de texto"""
    lines = block_text.split('\n')
    
    ocorrencia = {
        'bou': protocolo,
        'relato': '',
        'natureza': '',
        'endereco': '',
        'data_geracao': ''
    }
    
    relato_parts = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Procurar data/hora
        data_match = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})', line)
        if data_match and not ocorrencia['data_geracao']:
            ocorrencia['data_geracao'] = data_match.group(1)
            continue
        
        # Procurar natureza
        if any(word in line.upper() for word in ['ABORDAGEM', 'OCORRÊNCIA', 'DISTÚRBIO', 'FURTO', 'ROUBO', 'TRÁFICO', 'SUSPEITOS', 'ILICITUDE']) and not ocorrencia['natureza']:
            ocorrencia['natureza'] = line
            continue
        
        # Procurar endereço
        if any(word in line.upper() for word in ['RUA', 'AVENIDA', 'AV', 'ALAMEDA', 'TRAVESSA']) and ',' in line and not ocorrencia['endereco']:
            ocorrencia['endereco'] = line
            continue
        
        # Resto é relato
        if len(line) > 20 and line != protocolo:
            relato_parts.append(line)
    
    # Juntar partes do relato
    if relato_parts:
        ocorrencia['relato'] = ' '.join(relato_parts)
    
    return ocorrencia if ocorrencia['relato'] or ocorrencia['natureza'] else None

def analyze_relevance(ocorrencia, terms):
    """Analisa a relevância de uma ocorrência baseada nos termos"""
    relato = ocorrencia.get('relato', '').upper()
    
    count_alto = 0
    count_medio = 0
    count_baixo = 0
    
    # Contar termos de alta relevância
    for term in terms['alta']:
        if term.upper() in relato:
            count_alto += 1
    
    # Contar termos de média relevância
    for term in terms['media']:
        if term.upper() in relato:
            count_medio += 1
    
    # Contar termos de baixa relevância
    for term in terms['baixa']:
        if term.upper() in relato:
            count_baixo += 1
    
    # Aplicar regras de classificação
    if count_alto >= 1 or count_medio >= 3:
        return 'ALTA', count_alto, count_medio, count_baixo
    elif count_medio >= 1 or count_baixo >= 3:
        return 'MÉDIA', count_alto, count_medio, count_baixo
    elif count_baixo >= 1:
        return 'BAIXA', count_alto, count_medio, count_baixo
    else:
        return 'NENHUMA', count_alto, count_medio, count_baixo

def sort_ocorrencias(ocorrencias):
    """Ordena ocorrências por relevância e quantidade de termos"""
    def sort_key(oc):
        relevancia = oc.get('relevancia', 'NENHUMA')
        total_termos = oc.get('count_alto', 0) + oc.get('count_medio', 0) + oc.get('count_baixo', 0)
        
        # Ordem de relevância: ALTA > MÉDIA > BAIXA > NENHUMA
        relevancia_order = {'ALTA': 0, 'MÉDIA': 1, 'BAIXA': 2, 'NENHUMA': 3}
        
        return (relevancia_order.get(relevancia, 3), -total_termos)
    
    return sorted(ocorrencias, key=sort_key)

def extract_city_from_address(endereco):
    """Extrai o nome da cidade do endereço"""
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

def is_valid_summary(summary):
    """Verifica se o resumo é válido (português, sem textos estranhos)"""
    if not summary or len(summary.strip()) < 10:
        return False

    # Verificar se contém textos estranhos específicos (apenas os mais problemáticos)
    strange_patterns = [
        'indivíduo.com', 'iReporter', 'photos', 'gallery', 'submit', 'visit', 'travel', 'wednesday', 'snapshots',
        'will feature', 'weekly', 'shots', 'next week', 'new gallery'
    ]

    for pattern in strange_patterns:
        if pattern.lower() in summary.lower():
            print(f"DEBUG: Resumo rejeitado por conter texto estranho: {summary[:100]}...")
            return False

    # Verificar se contém caracteres estranhos
    if '?' in summary and summary.count('?') > 1:
        print(f"DEBUG: Resumo rejeitado por conter muitos caracteres estranhos: {summary[:100]}...")
        return False

    # Verificar se contém palavras problemáticas em inglês (apenas as mais específicas)
    problematic_english = ['iReporter', 'photos', 'gallery', 'submit', 'visit', 'travel', 'wednesday', 'snapshots', 'will feature', 'weekly', 'shots', 'next week', 'new gallery']
    english_count = sum(1 for word in problematic_english if word.lower() in summary.lower())

    if english_count > 0:  # Qualquer palavra problemática
        print(f"DEBUG: Resumo rejeitado por conter palavras problemáticas em inglês: {summary[:100]}...")
        return False

    return True

def summarize_occurrence_with_ai(relato):
    """Resume o relato da ocorrência usando IA externa (Google Gemini API)"""
    if not relato or relato.strip() == '':
        return None  # Retorna None para indicar que não há relato
    
    # Primeiro, aplicar limpeza básica
    cleaned_text = clean_police_report(relato)
    
    if AI_AVAILABLE:
        try:
            # Preparar dados para a API Google Gemini
            prompt = f"""Resuma este relato policial em português brasileiro, seguindo estas regras:
1. Remova todos os nomes próprios, substituindo por termos genéricos (vítima, autor, solicitante, indivíduo)
2. Mantenha apenas os fatos criminais relevantes
3. Use linguagem técnica policial
4. Seja conciso e objetivo (máximo 2 frases)
5. Não inclua informações sobre procedimentos policiais (equipe acionada, viatura, etc.)
6. Use apenas português brasileiro, sem palavras em inglês
7. Não use palavras como "feature", "gallery", "submit", "visit", "travel", "photos"

Relato: {cleaned_text}

Resumo:"""
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "maxOutputTokens": 100,
                    "temperature": 0.3,
                    "topP": 0.8,
                    "topK": 10
                }
            }
            
            # Fazer requisição para a API
            url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"DEBUG: Resposta da API Gemini: {result}")
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        ai_summary = candidate['content']['parts'][0]['text'].strip()
                        print(f"DEBUG: Resumo bruto da IA: {ai_summary}")
                        
                        # Limpar o resumo removendo "Resumo:" se presente
                        if ai_summary.startswith('Resumo:'):
                            ai_summary = ai_summary[7:].strip()
                        
                        # Verificar se o resumo é válido
                        if not is_valid_summary(ai_summary):
                            print(f"DEBUG: Resumo da IA rejeitado por ser inválido: {ai_summary[:100]}...")
                            return None
                        
                        # Aplicar regras específicas pós-processamento
                        final_summary = apply_police_rules(ai_summary)
                        print(f"DEBUG: Resumo após aplicar regras: {final_summary}")
                        
                        # Verificar novamente após aplicar regras
                        if not is_valid_summary(final_summary):
                            print(f"DEBUG: Resumo final rejeitado por ser inválido: {final_summary[:100]}...")
                            return None
                        
                        print(f"DEBUG: Resumo final aprovado: {final_summary}")
                        return final_summary
                else:
                    print(f"Resposta inesperada da API: {result}")
                    return None  # IA falhou
            else:
                print(f"Erro na API: {response.status_code} - {response.text}")
                return None  # IA falhou
                
        except Exception as e:
            print(f"Erro ao resumir com IA externa: {str(e)}")
            return None  # IA falhou
    else:
        return None  # IA não disponível

def clean_police_report(text):
    """Limpa o relato policial removendo informações desnecessárias"""
    # Remover frases comuns desnecessárias
    patterns_to_remove = [
        r'Equipe acionada[^.]*\.',
        r'Equipe deslocou[^.]*\.',
        r'Equipe chegou ao local[^.]*\.',
        r'No local[^.]*equipe[^.]*\.',
        r'Via Sistema[^.]*\.',
        r'Através do[^.]*\.',
        r'Guarnição[^.]*\.',
        r'viatura[^.]*\.',
        r'COPOM[^.]*\.',
        r'SESP[^.]*\.',
        r'intranet[^.]*\.',
        r'sinais sonoros[^.]*\.',
        r'atualização[^.]*\.',
        r'passado[^.]*\.',
        r'Por fim[^.]*\.',
        r'Então[^.]*\.',
        r'Fiante do fato[^.]*\.',
        r'em frente[^.]*\.',
        r'vizualizou[^.]*\.',
        r'Realizado[^.]*verificação[^.]*\.',
    ]
    
    cleaned = text
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Limpar espaços extras
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def apply_police_rules(text):
    """Aplica regras específicas para relatos policiais"""
    result = text
    
    # Remover TODOS os nomes próprios (padrões mais rigorosos)
    name_patterns = [
        r'\b[A-Z][A-Z\s]+[A-Z]\b',  # Nomes em maiúsculas (HILDA PERISSUTI DE BRITTO)
        r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',  # Nome completo (3 palavras)
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',              # Nome e sobrenome
        r'\bSr\.?\s+[A-Z][a-z]+\b',                  # Sr. Nome
        r'\bSra\.?\s+[A-Z][a-z]+\b',                 # Sra. Nome
        r'\b[A-Z][a-z]+ de [A-Z][a-z]+\b',           # Nome de Sobrenome
        r'\b[A-Z][a-z]+ [A-Z][a-z]+ de [A-Z][a-z]+\b', # Nome Sobrenome de Sobrenome
        r'\b[A-Z][a-z]+ Cirino\b',                   # Nomes específicos encontrados
        r'\bAnastácia\b',                            # Nomes específicos
        r'\bAcir\b',                                 # Nomes específicos
        r'\bJosé Mailson\b',                         # Nomes específicos
        r'\bGilson\b',                               # Nomes específicos
    ]
    
    for pattern in name_patterns:
        # Substituir por termo genérico baseado no contexto
        if 'vítima' in result.lower() or 'agredida' in result.lower() or 'ferida' in result.lower():
            result = re.sub(pattern, 'vítima', result)
        elif 'solicitante' in result.lower() or 'informou' in result.lower() or 'relatando' in result.lower():
            result = re.sub(pattern, 'solicitante', result)
        elif 'autor' in result.lower() or 'agressor' in result.lower() or 'companheiro' in result.lower():
            result = re.sub(pattern, 'autor', result)
        elif 'tio' in result.lower() or 'parente' in result.lower():
            result = re.sub(pattern, 'parente', result)
        else:
            result = re.sub(pattern, 'indivíduo', result)
    
    # Remover informações desnecessárias e textos truncados
    unnecessary_patterns = [
        r'Guarnição[^.]*\.',
        r'viatura[^.]*\.',
        r'COPOM[^.]*\.',
        r'SESP[^.]*\.',
        r'intranet[^.]*\.',
        r'sinais sonoros[^.]*\.',
        r'atualização[^.]*\.',
        r'Por fim[^.]*\.',
        r'Fiante do fato[^.]*\.',
        r'Entao[^.]*\.',
        r'ao fim do fim[^.]*\.',
        r'situaça ao que existe[^.]*\.',
        r'que na data de hoje[^.]*\.',
        r'ao passar pelo quart[^.]*\.',
        r'limitou-se ao desent[^.]*\.',
        r'para tentar aborda-lo[^.]*\.',
        r'[^.]*\.\.\.$',  # Remove textos que terminam com ...
        r'34\?[^.]*\.',   # Remove textos com 34?
        r'29\?[^.]*\.',   # Remove textos com 29?
    ]
    
    for pattern in unnecessary_patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Limpar espaços extras
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result

def create_manual_summary(text):
    """Cria resumo manual técnico otimizado"""
    if not text or text.strip() == '':
        return 'Relato não disponível'
    
    # Primeiro, aplicar limpeza rigorosa
    cleaned_text = clean_police_report(text)
    
    # Aplicar regras policiais para remover nomes
    cleaned_text = apply_police_rules(cleaned_text)
    
    # Dividir em frases
    sentences = re.split(r'[.!?]+', cleaned_text)
    
    # Palavras-chave técnicas importantes (expandidas)
    technical_keywords = [
        'vítima', 'autor', 'agrediu', 'furtou', 'roubou', 'ameaçou',
        'arma', 'tiro', 'disparo', 'lesão', 'ferimento', 'conduzido',
        'delegacia', 'preso', 'identificado', 'localizou', 'encontrou',
        'suicídio', 'depressão', 'enforcamento', 'cinto', 'peso',
        'abordagem', 'verificação', 'suspeito', 'indivíduo', 'violência',
        'doméstica', 'celular', 'destruído', 'companheiro', 'pescoço',
        'solicitante', 'informou', 'relatou', 'compareceu', 'atendimento',
        'ocorrência', 'policiamento', 'patrulhamento', 'verificação'
    ]
    
    # Filtrar e priorizar frases técnicas
    relevant_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 15:  # Ignorar frases muito curtas
            # Verificar se contém palavras técnicas importantes
            if any(keyword in sentence.lower() for keyword in technical_keywords):
                # Priorizar frases com fatos criminais
                if any(crime_word in sentence.lower() for crime_word in ['agrediu', 'furtou', 'roubou', 'ameaçou', 'arma', 'tiro', 'suicídio', 'violência', 'destruído', 'lesão']):
                    relevant_sentences.insert(0, sentence)  # Prioridade alta
                else:
                    relevant_sentences.append(sentence)
    
    # Criar resumo técnico
    if relevant_sentences:
        # Pegar as 2-3 frases mais relevantes
        summary_sentences = relevant_sentences[:3]
        
        # Reorganizar para ser mais técnico
        technical_summary = []
        for sentence in summary_sentences:
            # Tornar mais técnico
            technical_sentence = make_technical(sentence)
            technical_summary.append(technical_sentence)
        
        summary = '. '.join(technical_summary)
        if not summary.endswith('.'):
            summary += '.'
        return summary
    else:
        # Fallback: usar as primeiras frases e torná-las técnicas
        fallback_sentences = sentences[:2]
        technical_fallback = []
        for sentence in fallback_sentences:
            if len(sentence.strip()) > 10:
                technical_sentence = make_technical(sentence.strip())
                technical_fallback.append(technical_sentence)
        
        if technical_fallback:
            return '. '.join(technical_fallback) + '.'
        else:
            # Último fallback: resumo muito básico
            return "Ocorrência registrada e atendida pela equipe policial."

def make_technical(sentence):
    """Converte frase em linguagem mais técnica"""
    # Substituições para linguagem técnica
    technical_replacements = {
        r'viu\b': 'visualizou',
        r'achou\b': 'localizou',
        r'pegou\b': 'apreendeu',
        r'levou\b': 'conduziu',
        r'chegou\b': 'compareceu',
        r'falou\b': 'informou',
        r'disse\b': 'declarou',
        r'pediu\b': 'solicitou',
        r'fez\b': 'realizou',
        r'deu\b': 'prestou',
        r'teria\b': 'apresentava',
        r'vem se tratando\b': 'está em tratamento',
        r'já a algum tempo\b': 'há algum tempo',
        r'porém que não\b': 'porém não',
        r'demonstrado\b': 'apresentado',
        r'sinal\b': 'indicação',
        r'falado\b': 'mencionado',
        r'tentaria\b': 'tentaria',
        r'ela\b': 'vítima',
        r'alguns dias\b': 'alguns dias',
        r'pediu para\b': 'solicitou',
        r'dormir\b': 'pernoitar',
        r'quartos separados\b': 'quartos distintos',
        r'na data de hoje\b': 'na data atual',
        r'ao passar\b': 'ao transitar',
        r'pelo quart\b': 'pelo quarto',
        r'sentiu\b': 'percebeu',
        r'peso\b': 'peso',
        r'cinto\b': 'cinto',
        r'roupão\b': 'roupão',
        r'presa\b': 'presa',
        r'porta\b': 'porta',
        r'abrir\b': 'abrir'
    }
    
    result = sentence
    for pattern, replacement in technical_replacements.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result

def generate_whatsapp_report(selected_ocorrencias):
    """Gera o relatório formatado para WhatsApp"""
    print(f"DEBUG: Gerando relatório para {len(selected_ocorrencias)} ocorrências")
    
    # Agrupar ocorrências por cidade
    ocorrencias_por_cidade = {}
    
    for oc in selected_ocorrencias:
        endereco = oc.get('endereco', '')
        cidade = extract_city_from_address(endereco)
        
        print(f"DEBUG: Endereço: '{endereco}' -> Cidade extraída: '{cidade}'")
        
        # Mapear para cidades conhecidas do 34°BPM
        cidade_mapeada = ''
        
        # Mapeamento específico para variações de nomes
        cidade_mapping = {
            'ALMIRANTE TAMANDARE': 'ALMIRANTE TAMANDARÉ',
            'ALMIRANTE TAMANDARÉ': 'ALMIRANTE TAMANDARÉ',
            'ITAPERUCU': 'ITAPERUÇU',
            'ITAPERUÇU': 'ITAPERUÇU',
            'CAMPO MAGRO': 'CAMPO MAGRO',
            'RIO BRANCO DO SUL': 'RIO BRANCO DO SUL',
            'CERRO AZUL': 'CERRO AZUL',
            'DOUTOR ULYSSES': 'DOUTOR ULYSSES'
        }
        
        # Primeiro tentar mapeamento direto
        if cidade in cidade_mapping:
            cidade_mapeada = cidade_mapping[cidade]
        else:
            # Fallback: procurar por similaridade
            for cidade_bpm in CIDADES:
                if cidade_bpm in cidade or cidade in cidade_bpm:
                    cidade_mapeada = cidade_bpm
                    break
        
        if not cidade_mapeada:
            cidade_mapeada = cidade if cidade else 'OUTRAS'
        
        print(f"DEBUG: Cidade mapeada: '{cidade_mapeada}'")
        
        if cidade_mapeada not in ocorrencias_por_cidade:
            ocorrencias_por_cidade[cidade_mapeada] = []
        
        ocorrencias_por_cidade[cidade_mapeada].append(oc)
    
    print(f"DEBUG: Ocorrências por cidade: {list(ocorrencias_por_cidade.keys())}")
    
    # Gerar template
    template = """*RELATÓRIO DIÁRIO DE SERVIÇO – 34°BPM*

🗓 Data/Hora: das 06h de 05 setembro 25 às 06h de 06 setembro 25

📛 *Ocorrências relevantes:*
🟩 - positivo
🟥 - negativo
🟨 - atenção
⬜️ - neutro

*1ª CIA*
*ALMIRANTE TAMANDARÉ*
{almirante}

*CAMPO MAGRO*
{campo_magro}

*2ª CIA*
*RIO BRANCO DO SUL*
{rio_branco}

*CERRO AZUL*
{cerro_azul}

*ITAPERUÇU*
{itaperucu}

*DOUTOR ULYSSES*
{doutor_ulysses}

Resumo de MPs

TOTAL NA ÁREA *{total:02d}*"""

    # Formatar ocorrências para cada cidade
    def format_ocorrencias_cidade(ocorrencias):
        print(f"DEBUG: Formatando {len(ocorrencias) if ocorrencias else 0} ocorrências")
        if not ocorrencias:
            return "_sem alteração_"
        
        formatted = []
        for oc in ocorrencias:
            bou = oc.get('bou', '')
            natureza = oc.get('natureza', '')
            relato = oc.get('relato', '').strip()
            
            print(f"DEBUG: Formatando ocorrência: BOU={bou}, Natureza={natureza}, Relato={relato[:50]}...")
            
            # Resumir o relato com IA
            relato_resumido = summarize_occurrence_with_ai(relato)
            print(f"DEBUG: Relato resumido: {relato_resumido[:50] if relato_resumido else 'None'}...")
            
            # Se IA falhou, não incluir o relato
            if relato_resumido is None:
                print(f"DEBUG: IA falhou para BOU {bou}, não incluindo relato")
                formatted.append(f"{bou} - {natureza}")
            else:
                formatted.append(f"{bou} - {natureza}\n- {relato_resumido}")
        
        result = '\n\n'.join(formatted)
        print(f"DEBUG: Resultado formatado: {result[:100]}...")
        return result
    
    # Verificar se houve falhas da IA
    ai_failures = []
    total_ocorrencias = sum(len(ocorrencias) for ocorrencias in ocorrencias_por_cidade.values())
    
    # Preencher template
    report = template.format(
        almirante=format_ocorrencias_cidade(ocorrencias_por_cidade.get('ALMIRANTE TAMANDARÉ', [])),
        campo_magro=format_ocorrencias_cidade(ocorrencias_por_cidade.get('CAMPO MAGRO', [])),
        rio_branco=format_ocorrencias_cidade(ocorrencias_por_cidade.get('RIO BRANCO DO SUL', [])),
        cerro_azul=format_ocorrencias_cidade(ocorrencias_por_cidade.get('CERRO AZUL', [])),
        itaperucu=format_ocorrencias_cidade(ocorrencias_por_cidade.get('ITAPERUÇU', [])),
        doutor_ulysses=format_ocorrencias_cidade(ocorrencias_por_cidade.get('DOUTOR ULYSSES', [])),
        total=0
    )
    
    return {
        'report': report,
        'ai_available': AI_AVAILABLE,
        'total_ocorrencias': total_ocorrencias
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 404  # Retorna 404 para evitar erro no log

@app.route('/api/analyze', methods=['POST'])
def analyze_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        if file and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extrair dados do PDF
            ocorrencias = extract_text_from_pdf(filepath)
            
            # Obter termos de relevância do frontend
            terms = request.form.get('terms', '{}')
            try:
                terms = json.loads(terms)
            except:
                terms = DEFAULT_TERMS
            
            # Analisar relevância de cada ocorrência
            for oc in ocorrencias:
                relevancia, count_alto, count_medio, count_baixo = analyze_relevance(oc, terms)
                oc['relevancia'] = relevancia
                oc['count_alto'] = count_alto
                oc['count_medio'] = count_medio
                oc['count_baixo'] = count_baixo
                oc['selecionada'] = False
            
            # Ordenar ocorrências
            ocorrencias_ordenadas = sort_ocorrencias(ocorrencias)
            
            # Verificar se foi gerado arquivo Excel
            excel_file = None
            excel_path = filepath.replace('.pdf', '_analise.xlsx')
            if os.path.exists(excel_path):
                excel_filename = os.path.basename(excel_path)
                # Mover para pasta de uploads
                new_excel_path = os.path.join(app.config['UPLOAD_FOLDER'], excel_filename)
                os.rename(excel_path, new_excel_path)
                excel_file = excel_filename
            
            # Limpar arquivo temporário
            os.remove(filepath)
            
            response_data = {
                'success': True,
                'ocorrencias': ocorrencias_ordenadas,
                'total': len(ocorrencias_ordenadas)
            }
            
            if excel_file:
                response_data['excel_file'] = excel_file
            
            return jsonify(response_data)
        
        else:
            return jsonify({'error': 'Arquivo deve ser um PDF'}), 400
    
    except Exception as e:
        return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500

@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        selected_ocorrencias = data.get('selected_ocorrencias', [])
        
        print(f"DEBUG: Ocorrências recebidas: {len(selected_ocorrencias)}")
        for i, oc in enumerate(selected_ocorrencias):
            print(f"DEBUG: Ocorrência {i}: BOU={oc.get('bou')}, Endereço={oc.get('endereco')}")
        
        if not selected_ocorrencias:
            return jsonify({'error': 'Nenhuma ocorrência selecionada'}), 400
        
        result = generate_whatsapp_report(selected_ocorrencias)
        
        return jsonify({
            'success': True,
            'report': result['report'],
            'ai_available': result['ai_available'],
            'total_ocorrencias': result['total_ocorrencias']
        })
    
    except Exception as e:
        print(f"DEBUG: Erro ao gerar relatório: {str(e)}")
        return jsonify({'error': f'Erro ao gerar relatório: {str(e)}'}), 500

@app.route('/api/download-excel/<filename>')
def download_excel(filename):
    """Endpoint para baixar arquivo Excel gerado"""
    try:
        excel_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(excel_path):
            from flask import send_file
            return send_file(excel_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': 'Arquivo não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': f'Erro ao baixar arquivo: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
