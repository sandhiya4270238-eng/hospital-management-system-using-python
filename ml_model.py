# Pure Python simple ML model mock (Naive Bayes style)
# This avoids needing scikit-learn and C++ build tools

class SimpleNaiveBayes:
    def __init__(self):
        self.rules = {
            'Flu': {'fever': 0.8, 'cough': 0.7, 'fatigue': 0.6, 'headache': 0.4},
            'COVID': {'fever': 0.9, 'cough': 0.8, 'fatigue': 0.9, 'headache': 0.5},
            'Cold': {'fever': 0.3, 'cough': 0.9, 'fatigue': 0.4, 'headache': 0.2},
            'Normal': {'fever': 0.05, 'cough': 0.05, 'fatigue': 0.1, 'headache': 0.1}
        }
    
    def predict(self, symptoms_dict):
        best_disease = 'Normal'
        max_score = -1.0
        
        for disease, probs in self.rules.items():
            score = 1.0
            for sym, val in symptoms_dict.items():
                if val == 1:
                    score *= probs.get(sym, 0.1)
                else:
                    score *= (1.0 - probs.get(sym, 0.1))
            
            if score > max_score:
                max_score = score
                best_disease = disease
                
        return best_disease

def predict_disease(symptoms_dict):
    """Predicts disease based on symptom dictionary {fever: 1, cough: 0, etc}"""
    model = SimpleNaiveBayes()
    prediction = model.predict(symptoms_dict)
    
    disease_dept_map = {
        'Flu': 'General Physician',
        'Cold': 'General Physician',
        'COVID': 'Infectious Diseases',
        'Normal': 'General Physician'
    }
    
    return {
        'disease': prediction,
        'specialization': disease_dept_map.get(prediction, 'General Physician')
    }
