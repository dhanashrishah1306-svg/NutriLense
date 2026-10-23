from app.services import analyze_product, parse_ingredients, find_allergens, nutrition_from_text

def test_parse_ingredients():
    assert parse_ingredients('Ingredients: potato, palm oil, salt\nNutrition Facts') == ['potato','palm oil','salt']
def test_allergen_flag_not_safety_claim():
    result=analyze_product('Ingredients: rice flour, peanut oil, salt. Contains peanuts.',{'restrictions':['peanuts']})
    assert 'peanuts' in result['allergens']
    assert result['compatibility']['status']=='not_compatible'
    assert 'not proof of safety' not in result['compatibility']['reasons'][0] # conflict reason is explicit

def test_unknown_percentages_never_fabricated():
    r=analyze_product('Ingredients: oats, sugar, cocoa.',{})
    assert r['visualization']['percentages_available'] is False
    assert all(x['percentage'] is None for x in r['ingredient_details'])
def test_missing_nutrition_stays_missing():
    r=analyze_product('Ingredients: oats, salt.',{})
    assert r['nutrition']=={}
    assert 'calories' not in r['nutrition']
def test_uncertain_empty_label():
    r=analyze_product('',{}, {'status':'uncertain'})
    assert r['classification']=='uncertain'
    assert r['compatibility']['status']=='insufficient_information'
def test_nonfood_no_invented_nutrition():
    r=analyze_product('Hand wash antibacterial liquid',{}, {'status':'non_food'})
    assert r['message']=='Not a consumable food product'
    assert r['nutrition']=={}
def test_nutrition_parsing():
    n=nutrition_from_text('Calories 120 kcal\nProtein 3 g\nSodium 250 mg')
    assert n['calories']==120 and n['protein_g']==3 and n['sodium_mg']==250
