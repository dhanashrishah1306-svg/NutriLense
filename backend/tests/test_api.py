from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def image_bytes():
    b=BytesIO(); Image.new('RGB',(256,256),'white').save(b,format='PNG'); return b.getvalue()

def test_health_endpoint():
    r=client.get('/api/health'); assert r.status_code==200 and r.json()['status']=='ok'

def test_upload_accepts_image_and_classification_returns_state():
    r=client.post('/api/classify',files={'file':('label.png',image_bytes(),'image/png')})
    assert r.status_code==200
    assert r.json()['status'] in {'uncertain','food_candidate','non_food','error'}

def test_upload_rejects_unsupported_mime():
    r=client.post('/api/ocr',files={'file':('label.txt',b'ingredients','text/plain')})
    assert r.status_code==415

def test_corrected_ocr_text_is_used_for_analysis():
    r=client.post('/api/analyze',json={'ocr_text':'Ingredients: oats, sugar.','corrected_text':'Ingredients: oats, peanut flour. Contains peanuts.','profile':{'restrictions':['peanuts']}})
    assert r.status_code==200
    assert 'peanuts' in r.json()['allergens']
    assert r.json()['compatibility']['status']=='not_compatible'
