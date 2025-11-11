# app/main.py
from flask import Flask, jsonify, request
from datetime import datetime
import json
import re

app = Flask(__name__)

# Cargar strings
try:
    with open('app/static/strings_es_CO.json', 'r', encoding='utf-8') as f:
        strings = json.load(f)
except:
    strings = {}

# ===== OCR INLINE =====
class LabResultsOCR:
    REFERENCE_RANGES = {
        "glucose": {"low": 70, "normal": (70, 100), "high": 126},
        "cholesterol": {"low": 0, "normal": (0, 200), "high": 240},
        "triglycerides": {"low": 0, "normal": (0, 150), "high": 200},
    }
    
    PATTERNS = {
        "glucose": r"glucosa[:\s]*(\d+(?:,\d+)?)\s*mg/dL",
        "cholesterol": r"colesterol[:\s]*(\d+(?:,\d+)?)\s*mg/dL",
        "triglycerides": r"triglicéridos[:\s]*(\d+(?:,\d+)?)\s*mg/dL",
    }
    
    def parse_lab_values(self, text):
        results = {}
        text_lower = text.lower()
        for test_name, pattern in self.PATTERNS.items():
            match = re.search(pattern, text_lower)
            if match:
                value_str = match.group(1).replace(",", ".")
                results[test_name] = float(value_str)
        return results
    
    def classify_values(self, values):
        classification = {}
        for test_name, value in values.items():
            if test_name not in self.REFERENCE_RANGES:
                continue
            ranges = self.REFERENCE_RANGES[test_name]
            if value < ranges["low"]:
                status = "BAJO"
                risk = 2
            elif ranges["normal"][0] <= value <= ranges["normal"][1]:
                status = "NORMAL"
                risk = 0
            elif value < ranges["high"]:
                status = "ELEVADO"
                risk = 5
            else:
                status = "CRÍTICO"
                risk = 10
            classification[test_name] = {"value": value, "status": status, "risk_score": risk}
        return classification

# ===== RECOMMENDATION ENGINE INLINE =====
class RecommendationEngine:
    SUPPLEMENT_DB = {
        "glucose_high": {
            "supplements": ["Berberina 500mg", "Cromo 200mcg"],
            "foods": ["Canela", "Cebolla"],
            "priority": 9
        },
        "cholesterol_high": {
            "supplements": ["Omega-3 1000mg", "Levadura Roja"],
            "foods": ["Avocado", "Nueces"],
            "priority": 8
        }
    }
    
    def generate_recommendations(self, lab_results, composition):
        recommendations = {"supplements": [], "foods": [], "priority_issues": []}
        if lab_results.get("glucose", {}).get("value", 0) > 125:
            rec = self.SUPPLEMENT_DB["glucose_high"]
            recommendations["supplements"].extend(rec["supplements"])
            recommendations["foods"].extend(rec["foods"])
            recommendations["priority_issues"].append({"condition": "Prediabetes", "priority": 9})
        if lab_results.get("cholesterol", {}).get("value", 0) > 200:
            rec = self.SUPPLEMENT_DB["cholesterol_high"]
            recommendations["supplements"].extend(rec["supplements"])
            recommendations["priority_issues"].append({"condition": "Colesterol Alto", "priority": 8})
        return recommendations

# Instanciar
ocr = LabResultsOCR()
engine = RecommendationEngine()

# ===== ENDPOINTS =====
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Nutri-Zenze Smart Mirror API v0.1",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
        "language": "es_CO",
        "vision": "Transformando vidas, un latido a la vez 💚",
        "endpoints": [
            "GET /",
            "GET /api/health",
            "POST /api/analyze-labs",
            "POST /api/get-recommendations"
        ]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/api/analyze-labs', methods=['POST'])
def analyze_labs():
    try:
        data = request.json
        text = data.get('lab_text', '')
        values = ocr.parse_lab_values(text)
        classified = ocr.classify_values(values)
        return jsonify({
            "status": "success",
            "values": classified,
            "message": "Análisis completado"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get-recommendations', methods=['POST'])
def get_recommendations():
    try:
        data = request.json
        lab_results = data.get('lab_results', {})
        composition = data.get('composition', {})
        recommendations = engine.generate_recommendations(lab_results, composition)
        return jsonify({
            "status": "success",
            "recommendations": recommendations,
            "message": "Recomendaciones generadas"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🇨🇴 NUTRI-ZENZE API INICIANDO...")
    print("="*50)
    print("👉 http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
