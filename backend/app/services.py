import os, re, io
from typing import Any
from PIL import Image, ImageOps, UnidentifiedImageError

FOOD_TERMS = {'food','snack','chips','biscuit','cookie','chocolate','noodle','cereal','beverage','drink','sauce','pasta','bread','banana','apple','milk','juice','cracker','candy','soup','rice','flour','oil','yogurt','cheese','coffee','tea','protein bar','granola'}
NONFOOD_TERMS = {'soap','hand wash','shampoo','detergent','lotion','toothpaste','cleaner','disinfectant','perfume','conditioner','body wash'}
ALLERGENS = {
 'peanuts':['peanut','groundnut'], 'tree nuts':['almond','cashew','walnut','pistachio','hazelnut','pecan','macadamia'],
 'milk/dairy':['milk','whey','casein','lactose','butter','cheese','cream'], 'egg':['egg','albumen'],
 'soy':['soy','soya','soybean','lecithin'], 'gluten':['wheat','barley','rye','gluten','malt'],
 'sesame':['sesame','tahini'], 'shellfish':['shrimp','prawn','crab','lobster','shellfish'], 'fish':['fish oil','anchovy','salmon','tuna']}
INGREDIENT_EXPLANATIONS = {
 'maltodextrin':'A starch-derived carbohydrate often used for texture or as a carrier.',
 'monosodium glutamate':'A flavour enhancer (MSG) that adds savoury/umami taste.',
 'palm oil':'A plant oil used for texture and cooking; it is high in saturated fat.',
 'sodium bicarbonate':'Baking soda, commonly used as a raising agent.',
 'lecithin':'An emulsifier that helps oil and water stay mixed; source may vary.',
 'ascorbic acid':'Vitamin C; it may also be used as an antioxidant.',
 'citric acid':'An acidulant used to add tartness and help control acidity.',
 'high fructose corn syrup':'A glucose/fructose sweetener; frequent high added-sugar intake is worth limiting.'}

def parse_ingredients(text: str) -> list[str]:
    # Deliberately conservative: only parse a clearly labelled ingredients section.
    m = re.search(r'(?:ingredients?|composition)\s*[:\-]\s*(.+)', text or '', re.I | re.S)
    if not m: return []
    section = re.split(r'\n\s*(?:nutrition facts|nutritional information|allergen information|contains|may contain|manufactured by|net weight|best before)\b', m.group(1), flags=re.I)[0]
    section = section[:2500]
    parts = re.split(r'[,;\n•]+', section)
    cleaned=[]
    for p in parts:
        p=re.sub(r'^\s*[-•*\d.)]+\s*','',p).strip(' .:-')
        if len(p)>1 and len(p)<100 and p.lower() not in {'ingredients','composition'}: cleaned.append(p)
    return list(dict.fromkeys(cleaned))[:80]

def find_allergens(text: str) -> list[str]:
    lower=(text or '').lower(); found=[]
    for allergen, terms in ALLERGENS.items():
        if any(re.search(r'\b'+re.escape(term)+r'\b', lower) for term in terms): found.append(allergen)
    return found

def nutrition_from_text(text: str) -> dict[str, Any]:
    patterns = {
      'calories': r'(?:energy|calories?)\s*[:\-]?\s*(\d{1,4}(?:\.\d+)?)\s*(kcal|cal)?',
      'protein_g': r'protein\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*g\b',
      'carbohydrates_g': r'(?:total\s+)?carbohydrates?\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*g\b',
      'sugars_g': r'(?:total\s+)?sugars?\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*g\b',
      'fat_g': r'(?:total\s+)?fat\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*g\b',
      'saturated_fat_g': r'saturated\s+fat\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*g\b',
      'trans_fat_g': r'trans\s+fat\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*g\b',
      'fibre_g': r'(?:dietary\s+)?fibre?\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*g\b',
      'sodium_mg': r'sodium\s*[:\-]?\s*(\d{1,5}(?:\.\d+)?)\s*mg\b',
    }
    out={}
    for key, pat in patterns.items():
        m=re.search(pat, text or '', re.I)
        if m:
            try: out[key]=float(m.group(1))
            except ValueError: pass
    sm=re.search(r'(?:serving size|per serving)\s*[:\-]?\s*([^\n,;]{1,50})', text or '', re.I)
    if sm: out['serving_size']=sm.group(1).strip()
    return out

def classify_image(data: bytes) -> dict[str, Any]:
    try:
        image=Image.open(io.BytesIO(data)); image=ImageOps.exif_transpose(image).convert('RGB')
        if image.width < 80 or image.height < 80: return {'status':'uncertain','label':'uncertain','confidence':0.0,'reason':'Image is too small for reliable classification.'}
        if min(image.size) < 224:
            image.thumbnail((1024,1024))
    except (UnidentifiedImageError, OSError, ValueError):
        return {'status':'error','label':'unknown','confidence':0.0,'reason':'The file is not a readable image.'}
    # If configured, prefer the project's fine-tuned two-class model. It must be trained separately.
    custom_path = os.getenv('NUTRILENS_CLASSIFIER_PATH', '').strip()
    if custom_path:
        try:
            import torch
            from torchvision.models import mobilenet_v3_small
            from torchvision import transforms
            checkpoint_path = custom_path if os.path.isabs(custom_path) else os.path.join(os.getcwd(), custom_path)
            checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
            if checkpoint.get('architecture') != 'mobilenet_v3_small' or set(checkpoint.get('classes', [])) != {'food', 'non_food'}:
                raise ValueError('Checkpoint architecture/classes are not supported')
            model = mobilenet_v3_small(weights=None)
            model.classifier[-1] = __import__('torch').nn.Linear(model.classifier[-1].in_features, len(checkpoint['classes']))
            model.load_state_dict(checkpoint['state_dict']); model.eval()
            norm = checkpoint.get('normalization', {})
            transform = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(), transforms.Normalize(norm.get('mean', [0.485,0.456,0.406]), norm.get('std', [0.229,0.224,0.225]))])
            with torch.inference_mode(): probs = model(transform(image).unsqueeze(0)).softmax(1)[0]
            score, idx = probs.max(0); label = checkpoint['classes'][int(idx)]; confidence = float(score)
            threshold = float(os.getenv('NUTRILENS_CLASSIFIER_THRESHOLD', '0.80'))
            if confidence < threshold:
                status = 'uncertain'
            else:
                status = 'food_candidate' if label == 'food' else 'non_food'
            return {'status':status,'label':label,'confidence':round(confidence,3),'model':'NutriLens fine-tuned MobileNetV3-Small','reason':'Custom food/non-food classifier prediction; confirm using package text. This is not an allergy or food-safety guarantee.','threshold':threshold}
        except Exception as exc:
            return {'status':'uncertain','label':'unknown','confidence':0.0,'model':'custom model unavailable','reason':f'Configured NutriLens model could not be loaded ({type(exc).__name__}). Check NUTRILENS_CLASSIFIER_PATH and the checkpoint; no fallback prediction was made.'}
    # ImageNet pretrained MobileNetV3 is a general object classifier, not a validated food-safety classifier.
    try:
        import torch
        from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
        weights=MobileNet_V3_Small_Weights.DEFAULT
        model=mobilenet_v3_small(weights=weights).eval()
        tensor=weights.transforms()(image).unsqueeze(0)
        with torch.inference_mode(): probs=model(tensor).softmax(1)[0]
        score, idx=probs.max(0); label=weights.meta['categories'][int(idx)].lower(); confidence=float(score)
        if any(t in label for t in NONFOOD_TERMS) and confidence >= .60:
            return {'status':'non_food','label':label,'confidence':round(confidence,3),'model':'MobileNetV3-Small ImageNet pretrained','reason':'Preliminary visual classification; confirm against package text.'}
        if any(t in label for t in FOOD_TERMS) and confidence >= .45:
            return {'status':'food_candidate','label':label,'confidence':round(confidence,3),'model':'MobileNetV3-Small ImageNet pretrained','reason':'Candidate only; package-label evidence is still required.'}
        return {'status':'uncertain','label':label,'confidence':round(confidence,3),'model':'MobileNetV3-Small ImageNet pretrained','reason':'ImageNet labels do not reliably establish food vs non-food. Review package text.'}
    except Exception as exc:
        return {'status':'uncertain','label':'unknown','confidence':0.0,'model':'unavailable','reason':f'Pretrained classifier unavailable ({type(exc).__name__}). OCR and manual review can still be used.'}

def run_ocr(data: bytes) -> dict[str, Any]:
    try:
        import easyocr
        import numpy as np
        image=ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB')
        # EasyOCR downloads recognition weights on first use if not cached.
        reader=easyocr.Reader(['en'], gpu=False, verbose=False)
        results=reader.readtext(np.array(image), detail=1, paragraph=False)
        text='\n'.join(str(row[1]) for row in results)
        confidence=sum(float(row[2]) for row in results)/len(results) if results else 0.0
        return {'text':text,'confidence':round(confidence,3),'engine':'EasyOCR','status':'ok' if text.strip() else 'uncertain','items':len(results)}
    except Exception as exc:
        return {'text':'','confidence':0.0,'engine':'unavailable','status':'unavailable','message':f'OCR engine unavailable ({type(exc).__name__}). Install EasyOCR and its PyTorch dependencies, or paste the label text manually.'}

def analyze_product(text: str, profile: dict[str, Any], classification: dict | None=None, product: dict | None=None) -> dict[str, Any]:
    lower=(text or '').lower(); ingredients=parse_ingredients(text)
    cls=classification or {'status':'uncertain','label':'unknown','confidence':0}
    if cls.get('status')=='non_food' or any(re.search(r'\b'+re.escape(t)+r'\b',lower) for t in NONFOOD_TERMS) and not any(re.search(r'\b'+re.escape(t)+r'\b',lower) for t in FOOD_TERMS):
        return {'classification':'non_food','message':'Not a consumable food product','ingredients':ingredients,'nutrition':{},'allergens':find_allergens(text),'compatibility':{'status':'insufficient_information','reasons':['The detected product appears to be non-food.']},'warnings':[],'visualization':{'mode':'qualitative','percentages_available':False,'message':'Percentage unavailable: no verified quantitative ingredient data.'},'source':product.get('source') if product else 'label OCR / user text'}
    if cls.get('status')=='uncertain' and not ingredients and not re.search(r'\b(?:nutrition|calories|protein|carbohydrates)\b',lower):
        return {'classification':'uncertain','message':'We could not confidently determine whether this is a food product. Review the image or enter the label text.','ingredients':[],'nutrition':{},'allergens':find_allergens(text),'compatibility':{'status':'insufficient_information','reasons':['Food classification and ingredient information are insufficient.']},'warnings':[],'visualization':{'mode':'qualitative','percentages_available':False,'message':'Percentage unavailable: no verified quantitative ingredient data.'},'source':'label OCR / user text'}
    allergens=find_allergens(text); nutrition=product.get('nutrition',{}) if product else {}; nutrition={**nutrition,**nutrition_from_text(text)}
    restrictions=[str(x).lower() for x in profile.get('restrictions',[])]+[str(x).lower() for x in profile.get('custom_restrictions',[])]
    diet=profile.get('diet','none').lower()
    if diet=='vegan': restrictions += ['milk/dairy','egg','meat','fish','gelatin','honey']
    if diet=='jain': restrictions += ['onion','garlic','potato','carrot','beetroot','ginger','turmeric','root vegetable']
    if diet=='vegetarian': restrictions += ['meat','fish','gelatin']
    if profile.get('no_added_sugar') or profile.get('low_sugar'): restrictions.append('added sugar' if profile.get('no_added_sugar') else 'sugar')
    if profile.get('low_sodium'): restrictions.append('sodium')
    conflicts=[]; warnings=[]
    for r in dict.fromkeys(restrictions):
        terms=ALLERGENS.get(r,[r])
        if any(term in lower for term in terms): conflicts.append(r)
    if allergens: warnings.append({'level':'red','title':'Declared / detected allergen terms','detail':'Label text contains: '+', '.join(allergens)+'. Verify the full allergen statement and manufacturing cross-contact warnings.'})
    for key,title,threshold,unit in [('sugars_g','Sugars',10,'g per 100 g/ml'),('sodium_mg','Sodium',400,'mg per 100 g/ml'),('saturated_fat_g','Saturated fat',5,'g per 100 g/ml'),('trans_fat_g','Trans fat',1,'g per 100 g/ml')]:
        val=nutrition.get(key)
        if val is not None and val>=threshold: warnings.append({'level':'orange','title':f'{title} level may be worth reviewing','detail':f'{val:g} {unit.split(" per")[0]} reported in the supplied data. Confirm whether this is per serving or per 100 g/ml; this screening cue is not a personalized medical judgement.'})
    if conflicts: status='not_compatible'
    elif not ingredients and not allergens: status='insufficient_information'
    elif restrictions: status='potential_conflict' if any(r in lower for r in restrictions) else 'compatible_based_on_available_information'
    else: status='compatible_based_on_available_information'
    details=[]
    for ing in ingredients:
        exp=next((v for k,v in INGREDIENT_EXPLANATIONS.items() if k in ing.lower()),'No verified plain-language explanation is available for this ingredient yet.')
        matched=[a for a,terms in ALLERGENS.items() if any(t in ing.lower() for t in terms)]
        details.append({'name':ing,'explanation':exp,'allergens':matched,'percentage':None,'percentage_label':'Percentage unavailable','status':'conflict' if matched else 'unknown'})
    return {'classification':'food_candidate','message':'Analysis is based on the supplied label text and any matched database data; OCR can be wrong.','ingredients':ingredients,'ingredient_details':details,'nutrition':nutrition,'allergens':allergens,'compatibility':{'status':status,'reasons':conflicts or (['No conflict detected in the available text; this is not proof of safety.'] if status.startswith('compatible') else ['Evidence is incomplete; review the label manually.'])},'warnings':warnings,'visualization':{'mode':'qualitative','percentages_available':False,'message':'Percentage unavailable unless a reliable source provides ingredient quantities. Ingredient order is not converted into percentages.'},'source':product.get('source') if product else 'label OCR / user text'}
