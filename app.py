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

def extract_text_from_pdf(pdf_path):
    """Extrai texto do PDF e retorna as ocorrências estruturadas"""
    try:
        print(f"🔍 Iniciando extração de ocorrências do PDF: {pdf_path}")
        
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
                print(f"✅ Encontradas {len(ocorrencias)} ocorrências")
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
        
        # Procurar BOU
        bou_match = re.search(r'(\d{4}/\d{4,7})', line)
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
            while j < len(lines):
                next_line = lines[j].strip()
                
                # Verificar se é novo BOU
                if re.search(r'(\d{4}/\d{4,7})', next_line):
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
                    k = j + 1
                    while k < len(lines) and not re.search(r'(\d{4}/\d{4,7})', lines[k]):
                        if lines[k].strip():
                            relato_lines.append(lines[k].strip())
                        k += 1
                    ocorrencia['relato'] = ' '.join(relato_lines)
                
                j += 1
            
            ocorrencias.append(ocorrencia)
            i = j
        else:
            i += 1
    
    return ocorrencias

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
            
            # Analisar relevância
            terms = request.json.get('terms', DEFAULT_TERMS) if request.json else DEFAULT_TERMS
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
