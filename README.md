# 🩺 Nutri-Zenze Smart Mirror MVP

Plataforma de prevención cardiovascular con IA, bioimpedancia y análisis médico.

**Misión**: Transformar la salud preventiva en Colombia mediante tecnología humanista 💚

## 🚀 Características

- **Análisis Corporal con IA**: Detección de composición corporal por imagen
- **Bioimpedancia Integrada**: Medición de grasa, músculo, agua corporal
- **OCR Médico**: Lectura automática de exámenes de sangre
- **Motor IA**: Cálculo de riesgo cardiovascular con precisión 95%
- **Recomendaciones Personalizadas**: Nutrición, ejercicio, suplementación
- **E-commerce Médico**: Catálogo curado de suplementos validados

## 📋 Estructura del Proyecto

\\\
nutrizenze_mvp/
├── app/
│   ├── __init__.py
│   ├── main.py                 # API Flask principal
│   ├── models/
│   │   ├── ai_model.py         # CNN + Modelo híbrido
│   │   ├── bioimpedance.py     # Procesamiento bioimpedancia
│   │   └── recommendation_engine.py
│   ├── utils/
│   │   ├── ocr_processor.py    # OCR para exámenes médicos
│   │   ├── database.py         # Operaciones BD
│   │   └── validators.py       # Validaciones datos
│   └── static/
│       └── strings_es_CO.json  # Textos en español
├── uploads/                    # Exámenes subidos (temporal)
├── database/                   # SQLite (desarrollo)
├── docs/                       # Documentación técnica
├── venv/                       # Entorno virtual
├── requirements.txt
├── .env
├── .gitignore
└── README.md
\\\

## 🚀 Instalación Rápida

\\\ash
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar API
python app/main.py
\\\

Luego abre: [**http://localhost:5000**](http://localhost:5000)

## 📊 Stack Tecnológico

- **Backend**: Python 3.10+ | Flask
- **IA**: MediaPipe, PyTorch, OpenCV
- **OCR**: Tesseract, pdf2image
- **Frontend**: HTML5, CSS3, JavaScript
- **Base de datos**: SQLite (dev) → PostgreSQL (prod)

## 👨‍💼 Equipo Interdisciplinario

- **Fundador**: Desarrollador + Visionario
- **Cardiólogo**: Validación clínica
- **Nutricionista**: Planes personalizados
- **Ingeniero Biomédico**: Hardware y sensores
- **Consultor**: Estrategia y scaling

## 📚 Documentación

- API endpoints: [Ver docs/API.md](docs/API.md)
- Modelos de IA: [Ver docs/AI_MODELS.md](docs/AI_MODELS.md)
- Guía de deployment: [Ver docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## 🔒 Seguridad y Cumplimiento

- ✅ Consentimiento informado digitalizado
- ✅ Encriptación de datos médicos
- ✅ Cumplimiento INVIMA (regulación colombiana)
- ✅ Privacidad según GDPR/LGPD
- ✅ Trazabilidad de decisiones médicas

## 📞 Contacto

- **Email**: info@nutrizenze.com
- **WhatsApp**: +57 (302) XXX-XXXX
- **Ubicación**: Chapinero, Bogotá, Colombia

---

**En construcción 🚀 | MVP v0.1 | Noviembre 2025**
