"""OPTIONAL: train your own CNN (MobileNetV3-small) on photos you collected. UNTESTED TEMPLATE, read it first.
Folder layout:  dataset/train/<class_name>/*.jpg   and   dataset/val/<class_name>/*.jpg
Run:  pip install torch torchvision    then    python train_cnn.py dataset 8
Output: models/my_cnn/model.ts and labels.json. Then set LOCAL_CNN=models/my_cnn in .env."""
import json, os, sys
import torch
from torch import nn
from torchvision import datasets, models, transforms

root, epochs = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5
mean, std = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
tf_train = transforms.Compose([transforms.RandomResizedCrop(224, scale=(0.6, 1.0)), transforms.RandomHorizontalFlip(),
                               transforms.ColorJitter(0.3, 0.3, 0.2), transforms.ToTensor(), transforms.Normalize(mean, std)])
tf_val = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), transforms.Normalize(mean, std)])
train = datasets.ImageFolder(os.path.join(root, "train"), tf_train)
val = datasets.ImageFolder(os.path.join(root, "val"), tf_val)
tl = torch.utils.data.DataLoader(train, batch_size=32, shuffle=True)
vl = torch.utils.data.DataLoader(val, batch_size=64)

model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, len(train.classes))
opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
loss_fn = nn.CrossEntropyLoss()

for ep in range(epochs):
    model.train()
    for x, y in tl:
        opt.zero_grad(); loss_fn(model(x), y).backward(); opt.step()
    model.eval(); ok = n = 0
    with torch.no_grad():
        for x, y in vl:
            ok += (model(x).argmax(1) == y).sum().item(); n += len(y)
    print(f"epoch {ep + 1}/{epochs}  validation accuracy {ok / max(n, 1):.3f}")

os.makedirs("models/my_cnn", exist_ok=True)
torch.jit.trace(model.eval(), torch.randn(1, 3, 224, 224)).save("models/my_cnn/model.ts")
json.dump(train.classes, open("models/my_cnn/labels.json", "w", encoding="utf-8"), ensure_ascii=False)
print("saved models/my_cnn")
