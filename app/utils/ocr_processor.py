# app/utils/ocr_processor.py
import re

class LabResultsOCR:
    """Extrae valores de laboratorio desde reportes"""
    
    REFERENCE_RANGES = {
        "glucose": {"low": 70, "normal": (70, 100), "high": 126},
        "cholesterol": {"low": 0, "normal": (0, 200), "high": 240},
        "triglycerides": {"low": 0, "normal": (0, 150), "high": 200},
    }
    
    PATTERNS = {
        "glucose": r"glucosa[:\s]*(\d+(?:,\d+)?)\s*mg/dL",
        "cholesterol": r"colesterol[:\s]*(\d+(?:,\d+)?)\s*mg/dL",
        "triglycerides": r"triglic?ridos[:\s]*(\d+(?:,\d+)?)\s*mg/dL",
    }
    
    def parse_lab_values(self, text):
        """Extrae valores del texto"""
        results = {}
        text_lower = text.lower()
        
        for test_name, pattern in self.PATTERNS.items():
            match = re.search(pattern, text_lower)
            if match:
                value_str = match.group(1).replace(",", ".")
                results[test_name] = float(value_str)
        
        return results
    
    def classify_values(self, values):
        """Clasifica como NORMAL, ELEVADO o CR?TICO"""
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
                status = "CR?TICO"
                risk = 10
            
            classification[test_name] = {
                "value": value,
                "status": status,
                "risk_score": risk
            }
        
        return classification
