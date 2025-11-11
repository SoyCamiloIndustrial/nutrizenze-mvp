# app/models/recommendation_engine.py

class RecommendationEngine:
    """Genera recomendaciones basadas en perfil m?dico"""
    
    SUPPLEMENT_DB = {
        "glucose_high": {
            "supplements": ["Berberina 500mg", "Cromo 200mcg"],
            "foods": ["Canela", "Cebolla", "Vinagre de manzana"],
            "priority": 9
        },
        "cholesterol_high": {
            "supplements": ["Omega-3 1000mg", "Levadura Roja"],
            "foods": ["Avocado", "Nueces", "Pescado"],
            "priority": 8
        },
        "triglycerides_high": {
            "supplements": ["Omega-3 2000mg", "Niacina"],
            "foods": ["Pescado azul", "Fibra"],
            "priority": 8
        }
    }
    
    def generate_recommendations(self, lab_results, composition):
        """Genera plan personalizado"""
        recommendations = {
            "supplements": [],
            "foods": [],
            "priority_issues": []
        }
        
        # Detectar condiciones
        if lab_results.get("glucose", {}).get("value", 0) > 125:
            rec = self.SUPPLEMENT_DB["glucose_high"]
            recommendations["supplements"].extend(rec["supplements"])
            recommendations["foods"].extend(rec["foods"])
            recommendations["priority_issues"].append({
                "condition": "Glucosa Elevada (Prediabetes)",
                "priority": rec["priority"]
            })
        
        if lab_results.get("cholesterol", {}).get("value", 0) > 200:
            rec = self.SUPPLEMENT_DB["cholesterol_high"]
            recommendations["supplements"].extend(rec["supplements"])
            recommendations["foods"].extend(rec["foods"])
            recommendations["priority_issues"].append({
                "condition": "Colesterol Elevado",
                "priority": rec["priority"]
            })
        
        return recommendations
