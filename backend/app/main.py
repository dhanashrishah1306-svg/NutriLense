import os, re, httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .services import classify_image, run_ocr, analyze_product
from .schemas import AnalyzeRequest, Profile, OCRCorrection

app=FastAPI(title='NutriLens AI API', version='1.0.0', description='Label OCR and cautious product analysis. Not medical advice.')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
MAX_BYTES=int(os.getenv('MAX_UPLOAD_MB','12'))*1024*1024
async def read_image(file: UploadFile) -> bytes:
    if file.content_type not in ('image/jpeg','image/png','image/webp','image/bmp','image/tiff'):
        raise HTTPException(415,'Upload a JPG, PNG, WEBP, BMP, or TIFF image.')
    data=await file.read(MAX_BYTES+1)
    if not data: raise HTTPException(400,'The uploaded file is empty.')
    if len(data)>MAX_BYTES: raise HTTPException(413,f'Image exceeds the {MAX_BYTES//1024//1024} MB limit.')
    return data
@app.get('/api/health')
def health(): return {'status':'ok','service':'NutriLens AI API','ml_dependencies':'loaded on demand','open_food_facts':'public API, network dependent'}
@app.post('/api/classify')
async def classify(file: UploadFile=File(...)): return classify_image(await read_image(file))
@app.post('/api/ocr')
async def ocr(file: UploadFile=File(...)): return run_ocr(await read_image(file))
@app.post('/api/analyze')
def analyze(req: AnalyzeRequest):
    text=req.corrected_text if req.corrected_text is not None else req.ocr_text
    product=None
    if req.product_code:
        # Best-effort lookup; never treat a product-code match as verified without user review.
        try:
            with httpx.Client(timeout=5, headers={'User-Agent':os.getenv('OPEN_FOOD_FACTS_USER_AGENT','NutriLensAI/1.0')}) as client:
                r=client.get(f'https://world.openfoodfacts.org/api/v2/product/{re.sub(r"[^0-9]", "", req.product_code)}.json',params={'fields':'code,product_name,ingredients_text,nutriments,allergens_tags'})
                r.raise_for_status(); payload=r.json(); p=payload.get('product') if payload.get('status')==1 else None
                if p:
                    nutr=p.get('nutriments',{})
                    product={'name':p.get('product_name'),'source':'Open Food Facts (matched by barcode; verify package match)','nutrition':{k:v for k,v in {'calories':nutr.get('energy-kcal_100g'),'protein_g':nutr.get('proteins_100g'),'carbohydrates_g':nutr.get('carbohydrates_100g'),'sugars_g':nutr.get('sugars_100g'),'fat_g':nutr.get('fat_100g'),'saturated_fat_g':nutr.get('saturated-fat_100g'),'trans_fat_g':nutr.get('trans-fat_100g'),'fibre_g':nutr.get('fiber_100g'),'sodium_mg':float(nutr['sodium_100g'])*1000 if nutr.get('sodium_100g') is not None else None}.items() if v is not None}}
                    if not text.strip() and p.get('ingredients_text'): text=p['ingredients_text']
        except Exception: product=None
    return analyze_product(text,req.profile.model_dump(),req.classification,product)
@app.get('/api/ingredient/{name}')
def ingredient(name: str):
    from .services import INGREDIENT_EXPLANATIONS
    key=name.strip().lower()
    matches=[{'name':k,'explanation':v} for k,v in INGREDIENT_EXPLANATIONS.items() if key in k or k in key]
    return {'query':name,'matches':matches,'status':'found' if matches else 'unknown','message':None if matches else 'No curated explanation found. Check an authoritative label or regulator source.'}
@app.get('/api/nutrition/{barcode}')
def nutrition(barcode: str):
    code=re.sub(r'[^0-9]','',barcode)
    if len(code)<8 or len(code)>14: raise HTTPException(422,'Barcode must contain 8–14 digits.')
    try:
        with httpx.Client(timeout=6,headers={'User-Agent':os.getenv('OPEN_FOOD_FACTS_USER_AGENT','NutriLensAI/1.0')}) as c:
            r=c.get(f'https://world.openfoodfacts.org/api/v2/product/{code}.json',params={'fields':'code,product_name,brands,ingredients_text,nutriments,allergens_tags,quantity'}); r.raise_for_status(); data=r.json()
        if data.get('status')!=1: raise HTTPException(404,'No product found for this barcode.')
        p=data['product']; return {'source':'Open Food Facts','match_requires_review':True,'barcode':code,'name':p.get('product_name'),'brand':p.get('brands'),'quantity':p.get('quantity'),'ingredients_text':p.get('ingredients_text'),'allergens':p.get('allergens_tags',[]),'nutrition_per_100g':p.get('nutriments',{})}
    except HTTPException: raise
    except Exception: raise HTTPException(502,'Open Food Facts is currently unavailable; retry or use the package label.')
