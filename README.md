# NutriLens AI

A complete local-first full-stack starter for packaged-food label understanding. It includes a React + TypeScript + Vite frontend, FastAPI backend, optional pretrained PyTorch MobileNetV3 image classifier, optional EasyOCR, cautious label parsing, personal dietary checks, Open Food Facts barcode lookup, interactive SVG ingredient visualization, automated tests, and Windows PowerShell setup instructions.

> **Important limitations:** This is an assistive label-reading tool, not a medical device or allergy-safety system. OCR can miss or misread text. The pretrained MobileNetV3 model uses ImageNet weights and is **not trained or validated specifically to determine whether packaged products are food**. Its output is treated as a preliminary signal and often remains uncertain. No model is trained by this project. Nutrition and ingredient percentages are never fabricated. A missing allergen mention is not evidence that a product is allergy-safe.

## Project structure

```text
nutrilens-ai/
├── README.md
├── .gitignore
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py          # FastAPI routes
│   │   ├── schemas.py       # request schemas
│   │   └── services.py      # OCR, classification, parsing, analysis
│   └── tests/test_analysis.py
└── frontend/
    ├── package.json
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tailwind.config.js
    ├── postcss.config.js
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── styles.css
        ├── lib/api.ts
        ├── components/PackageViz.tsx
        └── testSetup.ts
```

## Requirements

- Windows 11, PowerShell 7 or Windows PowerShell
- Python 3.10 or 3.11 recommended
- Node.js 20 LTS or later and npm
- Internet connection for installing dependencies and optional first-time model-weight downloads

CPU-only inference is the baseline. PyTorch wheels are platform/version-sensitive; install the CPU build using the official PyTorch selector if needed. The app remains usable for manual label text even if ML dependencies are not installed.

## Install and run (Windows 11 PowerShell)

Open **two PowerShell terminals** in the project root.

### 1. Backend

```powershell
cd .\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Install CPU PyTorch and torchvision (recommended if not already installed):

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Install EasyOCR after PyTorch:

```powershell
pip install easyocr
```

EasyOCR downloads its recognition weights on first use. MobileNetV3's ImageNet weights are downloaded/cached by torchvision when classification is first invoked. If you do not want runtime downloads, omit these optional dependencies; the API reports an unavailable/uncertain model state and you can paste label text manually. The environment variable `ALLOW_MODEL_DOWNLOADS` is reserved/documentary in this baseline; torchvision/EasyOCR cache behaviour is controlled by those libraries.

Start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check health at <http://127.0.0.1:8000/api/health> and interactive API docs at <http://127.0.0.1:8000/docs>.

Run backend tests from the `backend` folder:

```powershell
python -m pip install pytest
pytest -q
```

### 2. Frontend

In the second terminal, from the project root:

```powershell
cd .\frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal (normally <http://127.0.0.1:5173>). The frontend expects the API at `http://127.0.0.1:8000/api` by default. To change it, create `frontend/.env.local`:

```dotenv
VITE_API_URL=http://127.0.0.1:8000/api
```

Build and run frontend tests:

```powershell
npm run build
npm test
```

## API reference

- `GET /api/health` — backend health status.
- `POST /api/classify` — multipart image upload; returns a preliminary food/non-food/uncertain signal.
- `POST /api/ocr` — multipart image upload; EasyOCR output when the optional engine is installed.
- `POST /api/analyze` — JSON containing `ocr_text`, optional `corrected_text`, `profile`, optional `classification`, and optional `product_code`.
- `GET /api/ingredient/{name}` — small curated explanation lookup; unknown terms remain unknown.
- `GET /api/nutrition/{barcode}` — best-effort Open Food Facts barcode lookup. Requires network access and a valid match; returned data must be checked against the package.

Example analysis body:

```json
{
  "ocr_text": "Ingredients: oats, sugar, cocoa powder. Contains soy.",
  "profile": {
    "diet": "vegetarian",
    "restrictions": ["soy"],
    "custom_restrictions": [],
    "low_sugar": false,
    "low_sodium": false,
    "no_added_sugar": false
  }
}
```

## Product database and data provenance

The barcode route calls the public Open Food Facts API. Its data is community-contributed, network-dependent, and may be stale or mismatched. The API marks matches as requiring review. Label OCR/user corrections are analysed separately from database values; the UI reports the response source. For robust production deployment, preserve provenance per individual field and add explicit product-match confirmation before merging sources.

## Safety and interpretation

- A detected allergen term is surfaced prominently; “not detected” never means “safe”. Always inspect the full “contains” and “may contain” label statements.
- Preference checks are string-based screening, not certification. Vegan, vegetarian, and especially Jain suitability can require ingredient-source and preparation details not present in the label.
- General nutrient thresholds are simple screening cues, not medical advice or jurisdiction-specific compliance judgements. Check serving size and the applicable local nutrition-label rules.
- Percentages are only shown if a future trusted source explicitly supplies ingredient quantities. This implementation deliberately returns `percentage: null` and “Percentage unavailable”. Ingredient order is not converted into percentages.
- Uploads are limited by file type and size. For deployment beyond localhost, add authentication, rate limiting, malware scanning, secure storage policy, logging redaction, and stricter CORS configuration.
- API keys are not needed for basic Open Food Facts lookup. Do not commit `.env` files or secrets.

## Troubleshooting

- **OCR unavailable:** confirm `torch` and `easyocr` installed in the same active venv. The first run may download model files and can take time. Enter label text manually if needed.
- **Classification uncertain:** expected for packaging photos because ImageNet isn't a packaging-specific food classifier. Use the ingredient/nutrition panel and manually verify.
- **Open Food Facts error:** check network connectivity, barcode digits, and whether a record exists. Manual text analysis still works.
- **CORS or connection error:** start the backend on port 8000 and frontend on port 5173; confirm `VITE_API_URL` if changed.
- **PyTorch installation error:** use the official PyTorch install selector for the installed Python version and CPU platform, then install EasyOCR.

## Development notes

The frontend profile and history are held in component state only and reset on page refresh. The current parsing/ingredient explanation dictionary is intentionally small and conservative. The project is modular so an appropriately validated food-vs-nonfood classifier, richer ingredient knowledge base, label-region detection, and field-level database provenance can be added without presenting fabricated inference as fact.

## Train your own food/non-food model (optional, real transfer learning)

The repository now includes a training pipeline at `backend/training/train_classifier.py`. The dataset directories are empty placeholders: no training dataset or custom trained checkpoint is bundled, so the model is **not yet trained** when you download this project.

1. Label a permitted dataset into `backend/training/data/train/food`, `train/non_food`, `val/food`, and `val/non_food`. Keep near-duplicate photos of the same product out of both train and validation sets.
2. In PowerShell, change directory to `backend`, activate `.venv`, then install PyTorch: `python -m pip install torch torchvision`.
3. Run `python training/train_classifier.py --data training/data --epochs 8 --batch-size 16 --workers 0`.
4. Review `models/food_nonfood_mobilenetv3.metrics.json` and evaluate on a separate held-out test set.
5. Set `NUTRILENS_CLASSIFIER_PATH=models/food_nonfood_mobilenetv3.pt` in `backend/.env` and restart FastAPI. A configured custom model is used for classification; if it fails to load, the API returns an uncertain result instead of claiming inference succeeded.

See `backend/training/README.md` for dataset layout, training details, safety limitations, and troubleshooting. The model fine-tunes MobileNetV3-Small from ImageNet initialization; it classifies only broad food/non-food image categories and is not an ingredient, allergen, or nutrition model. First training may download ImageNet weights. CPU is supported, but training time depends on dataset size and hardware.
