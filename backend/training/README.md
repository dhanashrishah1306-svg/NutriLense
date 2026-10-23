# Train NutriLens AI's food/non-food image classifier

This is a real transfer-learning pipeline. It fine-tunes the final classifier layer of MobileNetV3-Small, initialized from pretrained ImageNet weights by default. It does **not** train from scratch and does not train an ingredient/OCR model.

## 1. Prepare a labelled dataset

Put real images in this layout (image files can be JPG, PNG, or other formats supported by torchvision):

```text
backend/training/data/
  train/
    food/       # photos of packaged foods; ideally show a range of packages and angles
    non_food/   # personal care, cleaning, household products, etc.
  val/
    food/
    non_food/
```

Use only images you have permission to use. Do not put the same photo, burst, or near-duplicate product photo in both train and validation. Split by product/package where possible, not just random image, or validation accuracy will be misleading. Aim for hundreds to thousands of diverse images per class; a tiny dataset is only a pipeline smoke test. Include back-of-package photos because that is the application's intended input. Keep a separate test set that is never used for training or tuning.

The folders in this repository are empty placeholders. **No dataset is bundled and no trained model is shipped.** The project does not pretend that training has already occurred.

## 2. Install ML dependencies (Windows PowerShell)

From `backend/`, activate the project's `.venv` first. Install the CPU-compatible PyTorch baseline (or follow https://pytorch.org/get-started/locally/ for a CUDA build if you have a supported NVIDIA GPU):

```powershell
python -m pip install torch torchvision
```

The first normal training run downloads the MobileNetV3 ImageNet weights if they are not cached. Internet is required for that first download. To train without downloading pretrained weights, use `--no-pretrained-download`; that is generally less effective and requires more data.

## 3. Train

From `backend/`:

```powershell
python training/train_classifier.py --data training/data --epochs 8 --batch-size 16 --workers 0
```

Checkpoint is written to `backend/models/food_nonfood_mobilenetv3.pt`; metrics are written next to it as `.metrics.json`. CPU training is supported but may be slow. Start with a small dataset to verify the pipeline, then train with a carefully labelled, representative dataset. Check validation precision/recall and test performance before using the model for decisions. Class imbalance and data leakage can make accuracy deceptive.

## 4. Use the trained checkpoint in FastAPI

Set `NUTRILENS_CLASSIFIER_PATH` in `backend/.env` to the checkpoint path, for example:

```dotenv
NUTRILENS_CLASSIFIER_PATH=models/food_nonfood_mobilenetv3.pt
```

Run FastAPI from `backend/` so that the relative path resolves. Restart the API. The backend uses the custom checkpoint when configured; otherwise it falls back to the existing ImageNet model and marks it as a preliminary signal. If custom checkpoint loading fails, classification is uncertain rather than silently claiming a successful custom inference.

## 5. Important scope and safety

- This model only predicts the broad visual classes `food` and `non_food`; it does not identify ingredients, allergens, or nutrition.
- Food/non-food classification from a photo of the back label can be difficult. Retain the uncertain state and use OCR/label evidence as a separate signal.
- Never use this classifier as proof that a product is edible, allergy-safe, or suitable for a medical diet.
- Report held-out test results, per-class precision/recall, and confusion matrix in your project report. Do not claim the model is trained until you run training on a real labelled dataset.
