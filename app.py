from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import PyPDF2
import re
import os
from datetime import datetime
import json
import requests

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Configuração da API Google Gemini (gratuita e estável)
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyCo0mC8kOeQdiJpvu3ToG0gL6tQf0s9pns')  # Chave do Vercel ou fallback

AI_AVAILABLE = True
print("✅ IA Google Gemini configurada com sucesso!")

# Criar pasta de uploads se não existir
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except:
    # Em produção (Discloud), usar pasta temporária
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
    """Converte PDF para Excel usando tabula-py"""
    try:
        print(f"🔍 Iniciando conversão PDF para Excel: {pdf_path}")
        
        # Tentar extrair tabelas do PDF
        try:
            import tabula
            # Extrair todas as tabelas do PDF
            tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            
            if tables:
                print(f"✅ Encontradas {len(tables)} tabelas no PDF")
                return tables
            else:
                print("❌ Nenhuma tabela encontrada, tentando extração de texto")
                return None
                
        except ImportError:
            print("❌ tabula-py não disponível, usando extração de texto")
            return None
            
    except Exception as e:
        print(f"Erro na conversão PDF para Excel: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    """Extrai texto do PDF e retorna as ocorrências estruturadas"""
    try:
        print(f"🔍 Iniciando extração de ocorrências do PDF: {pdf_path}")
        
        # Primeiro tentar conversão para Excel
        tables = convert_pdf_to_excel(pdf_path)
        if tables:
            print("📊 Processando tabelas extraídas...")
            ocorrencias = process_excel_tables(tables)
            if ocorrencias:
                print(f"✅ Encontradas {len(ocorrencias)} ocorrências via Excel")
                return ocorrencias
        
        # Fallback: extração de texto
        print("📝 Fallback: extração de texto...")
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            print(f"✅ Texto extraído com sucesso ({len(text)} caracteres)")
            
            # Processar texto extraído
            ocorrencias = extract_from_text(text)
            if ocorrencias:
                print(f"✅ Encontradas {len(ocorrencias)} ocorrências via texto")
                return ocorrencias
            else:
                print("❌ Nenhuma ocorrência encontrada no texto")
                return []
            
    except Exception as e:
        print(f"Erro na extração: {e}")
        return []

def extract_from_text(text):
    """Extrai ocorrências do texto extraído do PDF"""
    ocorrencias = []
    
    # Dividir texto em linhas
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Procurar BOU válido (formato: 2025/1135296)
        bou_match = re.search(r'(2025/\d{4,7})', line)
        if bou_match:
            bou = bou_match.group(1)
            
            # Coletar informações da ocorrência
            ocorrencia = {
                'bou': bou,
                'relato': '',
                'natureza': '',
                'endereco': '',
                'data_geracao': ''
            }
            
            # Coletar linhas até encontrar próximo BOU
            j = i + 1
            relato_lines = []
            
            while j < len(lines):
                next_line = lines[j].strip()
                
                # Verificar se é novo BOU válido
                if re.search(r'(2025/\d{4,7})', next_line):
                    break
                
                # Procurar por padrões específicos
                if 'NATUREZA:' in next_line or 'Natureza:' in next_line:
                    ocorrencia['natureza'] = next_line.split(':', 1)[1].strip()
                elif 'ENDEREÇO:' in next_line or 'Endereço:' in next_line:
                    ocorrencia['endereco'] = next_line.split(':', 1)[1].strip()
                elif 'DATA GERAÇÃO:' in next_line or 'Data Geração:' in next_line:
                    ocorrencia['data_geracao'] = next_line.split(':', 1)[1].strip()
                elif 'RELATO:' in next_line or 'Relato:' in next_line:
                    # Coletar relato (pode ser múltiplas linhas)
                    relato_lines = [next_line.split(':', 1)[1].strip()]
                elif next_line and not any(x in next_line for x in ['NATUREZA:', 'ENDEREÇO:', 'DATA GERAÇÃO:', 'RELATO:']):
                    # Se não é um campo específico, pode ser parte do relato
                    if relato_lines and next_line:
                        relato_lines.append(next_line)
                
                j += 1
            
            # Juntar relato
            if relato_lines:
                ocorrencia['relato'] = ' '.join(relato_lines)
            
            # Se não encontrou campos específicos, tentar extrair do texto geral
            if not ocorrencia['natureza'] or not ocorrencia['endereco']:
                # Procurar por padrões mais gerais
                text_block = ' '.join(lines[i:j])
                
                # Procurar natureza
                if not ocorrencia['natureza']:
                    natureza_match = re.search(r'(?:NATUREZA|Natureza)[:\s]+([^-\n]+)', text_block)
                    if natureza_match:
                        ocorrencia['natureza'] = natureza_match.group(1).strip()
                
                # Procurar endereço
                if not ocorrencia['endereco']:
                    endereco_match = re.search(r'(?:ENDEREÇO|Endereço)[:\s]+([^-\n]+)', text_block)
                    if endereco_match:
                        ocorrencia['endereco'] = endereco_match.group(1).strip()
                
                # Procurar data
                if not ocorrencia['data_geracao']:
                    data_match = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})', text_block)
                    if data_match:
                        ocorrencia['data_geracao'] = data_match.group(1)
            
            # Se ainda não tem relato, usar o texto geral
            if not ocorrencia['relato']:
                ocorrencia['relato'] = ' '.join(lines[i:j]).strip()
            
            # Validar se é uma ocorrência válida
            if len(ocorrencia['bou']) >= 10 and ocorrencia['bou'].startswith('2025/'):
                # Debug: mostrar o que foi extraído
                print(f"🔍 BOU: {ocorrencia['bou']}")
                print(f"📋 Natureza: {ocorrencia['natureza'][:50]}..." if ocorrencia['natureza'] else "📋 Natureza: N/A")
                print(f"📍 Endereço: {ocorrencia['endereco'][:50]}..." if ocorrencia['endereco'] else "📍 Endereço: N/A")
                print(f"📅 Data: {ocorrencia['data_geracao']}" if ocorrencia['data_geracao'] else "📅 Data: N/A")
                print(f"📝 Relato: {ocorrencia['relato'][:100]}..." if ocorrencia['relato'] else "📝 Relato: N/A")
                print("---")
                
                ocorrencias.append(ocorrencia)
            else:
                print(f"❌ BOU inválido ignorado: {ocorrencia['bou']}")
            i = j
        else:
            i += 1
    
    return ocorrencias

def process_excel_tables(tables):
    """Processa tabelas extraídas do PDF e retorna ocorrências estruturadas"""
    ocorrencias = []
    
    try:
        import pandas as pd
        
        for i, table in enumerate(tables):
            print(f"📊 Processando tabela {i+1}/{len(tables)}")
            
            if table is None or table.empty:
                continue
                
            # Converter para DataFrame se necessário
            if not isinstance(table, pd.DataFrame):
                table = pd.DataFrame(table)
            
            print(f"📋 Colunas da tabela: {list(table.columns)}")
            print(f"📏 Dimensões: {table.shape}")
            
            # Procurar coluna com BOU
            bou_column = None
            for col in table.columns:
                if any('bou' in str(col).lower() or '2025/' in str(table[col].iloc[0] if len(table) > 0 else '') for _ in [1]):
                    bou_column = col
                    break
            
            if bou_column is None:
                # Procurar por padrão BOU na primeira coluna
                first_col = table.columns[0]
                for idx, row in table.iterrows():
                    if pd.notna(row[first_col]) and '2025/' in str(row[first_col]):
                        bou_column = first_col
                        break
            
            if bou_column is None:
                print(f"❌ Nenhuma coluna BOU encontrada na tabela {i+1}")
                continue
            
            print(f"✅ Coluna BOU encontrada: {bou_column}")
            
            # Processar cada linha da tabela
            for idx, row in table.iterrows():
                bou_value = row[bou_column]
                
                if pd.notna(bou_value) and '2025/' in str(bou_value):
                    # Extrair BOU
                    bou_match = re.search(r'(2025/\d{4,7})', str(bou_value))
                    if bou_match:
                        bou = bou_match.group(1)
                        
                        # Criar ocorrência
                        ocorrencia = {
                            'bou': bou,
                            'relato': '',
                            'natureza': '',
                            'endereco': '',
                            'data_geracao': ''
                        }
                        
                        # Extrair outros campos da linha
                        for col in table.columns:
                            if pd.notna(row[col]):
                                value = str(row[col]).strip()
                                
                                # Identificar tipo de campo
                                if 'natureza' in col.lower():
                                    ocorrencia['natureza'] = value
                                elif 'endereço' in col.lower() or 'endereco' in col.lower():
                                    ocorrencia['endereco'] = value
                                elif 'data' in col.lower() and 'geração' in col.lower():
                                    ocorrencia['data_geracao'] = value
                                elif 'relato' in col.lower():
                                    ocorrencia['relato'] = value
                                elif len(value) > 50 and not value.startswith('2025/'):
                                    # Provavelmente é o relato
                                    ocorrencia['relato'] = value
                        
                        # Se não encontrou relato, usar toda a linha
                        if not ocorrencia['relato']:
                            relato_parts = []
                            for col in table.columns:
                                if pd.notna(row[col]) and col != bou_column:
                                    value = str(row[col]).strip()
                                    if value and not value.startswith('2025/'):
                                        relato_parts.append(value)
                            ocorrencia['relato'] = ' '.join(relato_parts)
                        
                        print(f"🔍 BOU: {ocorrencia['bou']}")
                        print(f"📋 Natureza: {ocorrencia['natureza'][:50]}..." if ocorrencia['natureza'] else "📋 Natureza: N/A")
                        print(f"📍 Endereço: {ocorrencia['endereco'][:50]}..." if ocorrencia['endereco'] else "📍 Endereço: N/A")
                        print(f"📅 Data: {ocorrencia['data_geracao']}" if ocorrencia['data_geracao'] else "📅 Data: N/A")
                        print(f"📝 Relato: {ocorrencia['relato'][:100]}..." if ocorrencia['relato'] else "📝 Relato: N/A")
                        print("---")
                        
                        ocorrencias.append(ocorrencia)
        
        return ocorrencias
        
    except Exception as e:
        print(f"Erro ao processar tabelas: {e}")
        return []

def analyze_relevance(ocorrencias, terms):
    """Analisa a relevância das ocorrências baseada nos termos"""
    for ocorrencia in ocorrencias:
        relato = ocorrencia.get('relato', '').lower()
        natureza = ocorrencia.get('natureza', '').lower()
        texto_completo = f"{relato} {natureza}"
        
        # Contar termos por categoria
        alta_count = sum(1 for termo in terms['alta'] if termo.lower() in texto_completo)
        media_count = sum(1 for termo in terms['media'] if termo.lower() in texto_completo)
        baixa_count = sum(1 for termo in terms['baixa'] if termo.lower() in texto_completo)
        
        # Determinar relevância
        if alta_count > 0:
            ocorrencia['relevancia'] = 'alta'
            ocorrencia['relevancia_score'] = alta_count * 3 + media_count * 2 + baixa_count
        elif media_count > 0:
            ocorrencia['relevancia'] = 'media'
            ocorrencia['relevancia_score'] = media_count * 2 + baixa_count
        elif baixa_count > 0:
            ocorrencia['relevancia'] = 'baixa'
            ocorrencia['relevancia_score'] = baixa_count
        else:
            ocorrencia['relevancia'] = 'nenhuma'
            ocorrencia['relevancia_score'] = 0
        
        # Armazenar termos encontrados
        ocorrencia['termos_encontrados'] = {
            'alta': [termo for termo in terms['alta'] if termo.lower() in texto_completo],
            'media': [termo for termo in terms['media'] if termo.lower() in texto_completo],
            'baixa': [termo for termo in terms['baixa'] if termo.lower() in texto_completo]
        }
    
    return ocorrencias

def extract_city_from_address(endereco):
    """Extrai a cidade do endereço"""
    if not endereco:
        return 'N/A'
    
    # Procurar por padrão "- CIDADE"
    for cidade in CIDADES:
        if f"- {cidade}" in endereco.upper():
            return cidade
    
    return 'N/A'

def summarize_occurrence_with_ai(relato):
    """Resume o relato usando IA externa (Google Gemini)"""
    if not AI_AVAILABLE or not relato.strip():
        return None
    
    try:
        prompt = f"""
        Resuma este relato policial em português, seguindo estas regras:
        1. NÃO cite nomes próprios, use apenas "autor", "vítima", "solicitante"
        2. Foque nos fatos criminais principais
        3. Seja conciso (máximo 2 frases)
        4. Use linguagem técnica policial
        5. NÃO use frases como "equipe acionada", "equipe deslocou"
        6. NÃO use palavras em inglês como "individual", "situation", "update"
        
        Relato: {relato}
        
        Resumo:
        """
        
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': GEMINI_API_KEY
        }
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                summary = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # Limpar o resumo
                if summary.startswith('Resumo:'):
                    summary = summary[7:].strip()
                
                # Validar se é um resumo válido
                if is_valid_summary(summary):
                    print(f"✅ IA resumiu com sucesso: {summary[:50]}...")
                    return summary
                else:
                    print(f"❌ Resumo rejeitado pela validação: {summary[:50]}...")
                    return None
            else:
                print("❌ Resposta da IA sem candidatos")
                return None
        else:
            print(f"❌ Erro na API Gemini: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao resumir com IA: {e}")
        return None

def is_valid_summary(summary):
    """Valida se o resumo é adequado"""
    if not summary or len(summary.strip()) < 10:
        return False
    
    # Verificar se contém palavras problemáticas em inglês
    problematic_words = ['individual', 'situation', 'update', 'team', 'called', 'dispatched']
    if any(word in summary.lower() for word in problematic_words):
        return False
    
    # Verificar se está em português (básico)
    portuguese_words = ['autor', 'vítima', 'solicitante', 'ocorrência', 'local', 'policial']
    if not any(word in summary.lower() for word in portuguese_words):
        return False
    
    return True

def generate_report(selected_ocorrencias, terms):
    """Gera o relatório formatado para WhatsApp"""
    if not selected_ocorrencias:
        return "Nenhuma ocorrência selecionada."
    
    # Agrupar por cidade
    cidades_ocorrencias = {}
    for ocorrencia in selected_ocorrencias:
        cidade = extract_city_from_address(ocorrencia.get('endereco', ''))
        if cidade not in cidades_ocorrencias:
            cidades_ocorrencias[cidade] = []
        cidades_ocorrencias[cidade].append(ocorrencia)
    
    # Gerar relatório
    report = "*RELATÓRIO DIÁRIO DE SERVIÇO – 34°BPM*\n"
    report += "🗓 Data/Hora: das 06h de 05 setembro 25 às 06h de 06 setembro 25\n"
    report += "📛 *Ocorrências relevantes:*\n"
    report += "🟩 - positivo 🟥 - negativo 🟨 - atenção ⬜️ - neutro\n\n"
    
    # Agrupar por CIA
    cia1_cidades = ['ALMIRANTE TAMANDARÉ', 'CAMPO MAGRO']
    cia2_cidades = ['RIO BRANCO DO SUL', 'CERRO AZUL', 'ITAPERUÇU', 'DOUTOR ULYSSES']
    
    # 1ª CIA
    report += "*1ª CIA*\n"
    for cidade in cia1_cidades:
        if cidade in cidades_ocorrencias:
            report += f"*{cidade}*\n"
            for ocorrencia in cidades_ocorrencias[cidade]:
                bou = ocorrencia.get('bou', 'N/A')
                natureza = ocorrencia.get('natureza', 'N/A')
                relato = ocorrencia.get('relato', '')
                
                # Tentar resumir com IA
                summary = summarize_occurrence_with_ai(relato)
                if summary:
                    report += f"{bou} - {natureza} - {summary}\n"
                else:
                    report += f"{bou} - {natureza}\n"
        else:
            report += f"*{cidade}*\n_sem alteração_\n"
    
    # 2ª CIA
    report += "\n*2ª CIA*\n"
    for cidade in cia2_cidades:
        if cidade in cidades_ocorrencias:
            report += f"*{cidade}*\n"
            for ocorrencia in cidades_ocorrencias[cidade]:
                bou = ocorrencia.get('bou', 'N/A')
                natureza = ocorrencia.get('natureza', 'N/A')
                relato = ocorrencia.get('relato', '')
                
                # Tentar resumir com IA
                summary = summarize_occurrence_with_ai(relato)
                if summary:
                    report += f"{bou} - {natureza} - {summary}\n"
                else:
                    report += f"{bou} - {natureza}\n"
        else:
            report += f"*{cidade}*\n_sem alteração_\n"
    
    report += "\nResumo de MPs\n"
    report += "TOTAL NA ÁREA *00*"
    
    return report

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
            
            # Extrair ocorrências
            ocorrencias = extract_text_from_pdf(filepath)
            
            if not ocorrencias:
                return jsonify({'error': 'Nenhuma ocorrência encontrada no PDF'}), 400
            
            # Analisar relevância - usar termos padrão
            terms = DEFAULT_TERMS
            ocorrencias = analyze_relevance(ocorrencias, terms)
            
            # Ordenar por relevância e score
            ocorrencias.sort(key=lambda x: (x['relevancia_score'], len(x.get('relato', ''))), reverse=True)
            
            return jsonify({
                'ocorrencias': ocorrencias,
                'total': len(ocorrencias),
                'alta': len([o for o in ocorrencias if o['relevancia'] == 'alta']),
                'media': len([o for o in ocorrencias if o['relevancia'] == 'media']),
                'baixa': len([o for o in ocorrencias if o['relevancia'] == 'baixa'])
            })
        else:
            return jsonify({'error': 'Arquivo deve ser um PDF'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500

@app.route('/api/generate-report', methods=['POST'])
def generate_report_api():
    try:
        data = request.json
        selected_ocorrencias = data.get('selected_ocorrencias', [])
        terms = data.get('terms', DEFAULT_TERMS)
        
        report = generate_report(selected_ocorrencias, terms)
        
        return jsonify({
            'report': report,
            'ai_available': AI_AVAILABLE,
            'total_ocorrencias': len(selected_ocorrencias)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao gerar relatório: {str(e)}'}), 500

if __name__ == '__main__':
    # Para Discloud
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
