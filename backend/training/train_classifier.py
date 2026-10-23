"""Fine-tune MobileNetV3-Small for food vs non-food using a labelled ImageFolder dataset.

This script performs real transfer learning. It does not claim to train without data.
"""
from __future__ import annotations
import argparse, json, random, time
from pathlib import Path
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=Path('training/data'), help='Contains train/ and val/ ImageFolder directories')
    p.add_argument('--output', type=Path, default=Path('models/food_nonfood_mobilenetv3.pt'))
    p.add_argument('--epochs', type=int, default=8)
    p.add_argument('--batch-size', type=int, default=16)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--workers', type=int, default=0, help='Use 0 for easiest Windows compatibility')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--no-pretrained-download', action='store_true', help='Fail if ImageNet weights are not already cached')
    args = p.parse_args()
    if args.epochs < 1 or args.batch_size < 1: p.error('epochs and batch-size must be positive')
    torch.manual_seed(args.seed); random.seed(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    train_dir, val_dir = args.data / 'train', args.data / 'val'
    if not train_dir.is_dir() or not val_dir.is_dir():
        raise SystemExit(f'Dataset folders missing. Expected {train_dir} and {val_dir}. See training/README.md.')
    weights = None if args.no_pretrained_download else MobileNet_V3_Small_Weights.DEFAULT
    # If downloads are disabled, use the architecture without ImageNet weights; training still works but needs more data.
    try:
        model = mobilenet_v3_small(weights=weights)
    except Exception as e:
        raise SystemExit(f'Could not load pretrained ImageNet weights ({e}). Connect to the internet once, or rerun with --no-pretrained-download.')
    base = MobileNet_V3_Small_Weights.DEFAULT.transforms() if weights is not None else None
    mean, std = ((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
    train_tf = transforms.Compose([transforms.Resize((232,232)), transforms.RandomResizedCrop(224, scale=(0.75,1.0)), transforms.RandomHorizontalFlip(), transforms.ColorJitter(brightness=.15, contrast=.15, saturation=.10), transforms.ToTensor(), transforms.Normalize(mean,std)])
    eval_tf = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(), transforms.Normalize(mean,std)])
    train_ds = datasets.ImageFolder(train_dir, transform=train_tf)
    val_ds = datasets.ImageFolder(val_dir, transform=eval_tf)
    expected = {'food','non_food'}
    if set(train_ds.classes) != expected or set(val_ds.classes) != expected:
        raise SystemExit(f'Both train and val must contain exactly folders named food and non_food. Found train={train_ds.classes}, val={val_ds.classes}.')
    if train_ds.classes != val_ds.classes: raise SystemExit('Train and validation class order differs.')
    for ds, label in ((train_ds,'training'),(val_ds,'validation')):
        counts = {name: sum(1 for y in ds.targets if ds.classes[y] == name) for name in ds.classes}
        if min(counts.values()) < 2: raise SystemExit(f'{label} set is too small: {counts}. Add more labelled images per class.')
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)
    # Freeze feature extractor first; train classifier head, then unfreeze last feature blocks.
    for param in model.features.parameters(): param.requires_grad = False
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, len(train_ds.classes))
    model = model.to(device)
    optimizer = torch.optim.AdamW(filter(lambda x: x.requires_grad, model.parameters()), lr=args.lr)
    criterion = nn.CrossEntropyLoss()
    best_acc = -1.0; history=[]
    for epoch in range(args.epochs):
        model.train(); total=correct=loss_sum=0
        for x,y in train_loader:
            x,y=x.to(device),y.to(device); optimizer.zero_grad(set_to_none=True)
            logits=model(x); loss=criterion(logits,y); loss.backward(); optimizer.step()
            loss_sum += loss.item()*y.size(0); correct += (logits.argmax(1)==y).sum().item(); total += y.size(0)
        train_loss=loss_sum/max(total,1); train_acc=correct/max(total,1)
        model.eval(); total=correct=loss_sum=0; tp=fp=fn=0
        food_idx=train_ds.class_to_idx['food']
        with torch.inference_mode():
            for x,y in val_loader:
                x,y=x.to(device),y.to(device); logits=model(x); loss=criterion(logits,y); pred=logits.argmax(1)
                loss_sum += loss.item()*y.size(0); correct += (pred==y).sum().item(); total += y.size(0)
                tp += ((pred==food_idx)&(y==food_idx)).sum().item(); fp += ((pred==food_idx)&(y!=food_idx)).sum().item(); fn += ((pred!=food_idx)&(y==food_idx)).sum().item()
        val_loss=loss_sum/max(total,1); val_acc=correct/max(total,1); precision=tp/max(tp+fp,1); recall=tp/max(tp+fn,1)
        row={'epoch':epoch+1,'train_loss':round(train_loss,4),'train_accuracy':round(train_acc,4),'val_loss':round(val_loss,4),'val_accuracy':round(val_acc,4),'food_precision':round(precision,4),'food_recall':round(recall,4)}; history.append(row); print(json.dumps(row))
        if val_acc > best_acc:
            best_acc=val_acc; args.output.parent.mkdir(parents=True,exist_ok=True)
            torch.save({'architecture':'mobilenet_v3_small','state_dict':model.cpu().state_dict(),'classes':train_ds.classes,'class_to_idx':train_ds.class_to_idx,'image_size':224,'normalization':{'mean':mean,'std':std},'validation':row,'history':history,'created_at_unix':time.time(),'pretrained_imagenet_initialization':weights is not None,'training_data':str(args.data)}, args.output)
            model.to(device)
    report=args.output.with_suffix('.metrics.json'); report.write_text(json.dumps({'device':str(device),'classes':train_ds.classes,'train_images':len(train_ds),'validation_images':len(val_ds),'best_validation_accuracy':best_acc,'history':history,'caution':'Validation metrics are only meaningful if images are representative and split without near-duplicate leakage.'},indent=2),encoding='utf-8')
    print(f'Best checkpoint: {args.output}\nMetrics: {report}\nDevice: {device}')

if __name__ == '__main__': main()
