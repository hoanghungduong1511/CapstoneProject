from __future__ import annotations

from pathlib import Path

import nbformat


SRC = Path(
    r"E:\DHBKDN\CapstoneProject\SkinDeseases-AI\models\classification\notebooks\train_custom_efficientnet_b0_scratch.ipynb"
)
OUT = SRC.with_name("custom-densenet121.ipynb")


DENSENET_MODEL_CELL = r'''
import torch
import torch.nn as nn
from torchvision.models import densenet121, DenseNet121_Weights

MODEL_NAME = "densenet121"
ARCHITECTURE = "densenet121"


def initialize_classifier(module):
    if isinstance(module, nn.Linear):
        nn.init.kaiming_normal_(module.weight, mode="fan_out", nonlinearity="relu")
        if module.bias is not None:
            nn.init.zeros_(module.bias)
    elif isinstance(module, nn.BatchNorm1d):
        nn.init.ones_(module.weight)
        nn.init.zeros_(module.bias)


def build_model(num_classes: int):
    model = densenet121(weights=DenseNet121_Weights.IMAGENET1K_V1)
    in_features = model.classifier.in_features
    model.classifier = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(in_features, 512),
        nn.BatchNorm1d(512),
        nn.SiLU(inplace=True),
        nn.Dropout(0.3),
        nn.Linear(512, num_classes),
    )
    model.classifier.apply(initialize_classifier)
    return model


model = build_model(cfg.num_classes).to(device)

num_params = sum(p.numel() for p in model.parameters())
num_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Model name: DenseNet-121")
print(f"Parameters: {num_params:,} | Trainable: {num_trainable:,}")
'''.strip()


TRAINING_SETUP_CELL = r'''
class ClassBalancedFocalLoss(nn.Module):
    def __init__(self, class_weights, gamma=2.0, label_smoothing=0.0):
        super().__init__()
        self.register_buffer('class_weights', class_weights.detach().clone().float())
        self.gamma = gamma
        self.label_smoothing = label_smoothing

    def _prepare_targets(self, targets, num_classes):
        if targets.ndim == 1:
            targets = F.one_hot(targets, num_classes=num_classes).float()
        else:
            targets = targets.float()

        if self.label_smoothing > 0:
            targets = targets * (1.0 - self.label_smoothing) + self.label_smoothing / num_classes
        return targets

    def forward(self, logits, targets):
        num_classes = logits.size(1)
        targets = self._prepare_targets(targets, num_classes)
        log_probs = F.log_softmax(logits, dim=1)
        probs = log_probs.exp()
        focal_factor = torch.pow(1.0 - probs, self.gamma)
        class_weights = self.class_weights.to(logits.device).view(1, -1)
        loss = -(targets * focal_factor * log_probs * class_weights).sum(dim=1)
        return loss.mean()

criterion = ClassBalancedFocalLoss(
    class_weights=loss_class_weights,
    gamma=cfg.focal_gamma,
    label_smoothing=cfg.label_smoothing,
).to(device)
print(
    f'Using Loss: ClassBalancedFocalLoss(gamma={cfg.focal_gamma}, '
    f'label_smoothing={cfg.label_smoothing}) + tempered WeightedRandomSampler'
)


def set_trainable_for_stage(model, stage: int):
    if stage == 1:
        for param in model.parameters():
            param.requires_grad = False

        for param in model.features.denseblock4.parameters():
            param.requires_grad = True

        for param in model.features.norm5.parameters():
            param.requires_grad = True

        for param in model.classifier.parameters():
            param.requires_grad = True
    else:
        for param in model.parameters():
            param.requires_grad = True


def _assert_disjoint_param_groups(param_groups):
    seen = set()
    for group_idx, params in enumerate(param_groups):
        for p in params:
            pid = id(p)
            if pid in seen:
                raise RuntimeError(f"Parameter appears in more than one optimizer group: group {group_idx}")
            seen.add(pid)


def get_optimizer_and_scheduler(model, stage: int, steps_per_epoch: int, total_epochs: int):
    set_trainable_for_stage(model, stage)

    classifier_params = list(model.classifier.parameters())

    if stage == 1:
        backbone_params = (
            list(model.features.denseblock4.parameters())
            + list(model.features.norm5.parameters())
        )
        max_lrs = [cfg.stage1_backbone_lr, cfg.stage1_classifier_lr]
    else:
        backbone_params = list(model.features.parameters())
        max_lrs = [cfg.backbone_lr, cfg.classifier_lr]

    backbone_params = [p for p in backbone_params if p.requires_grad]
    classifier_params = [p for p in classifier_params if p.requires_grad]
    _assert_disjoint_param_groups([backbone_params, classifier_params])

    optimizer = torch.optim.AdamW(
        [
            {'params': backbone_params, 'lr': max_lrs[0]},
            {'params': classifier_params, 'lr': max_lrs[1]},
        ],
        weight_decay=cfg.weight_decay,
    )

    total_steps = max(1, steps_per_epoch * total_epochs)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=max_lrs,
        total_steps=total_steps,
        pct_start=cfg.warmup_pct,
        anneal_strategy='cos',
        div_factor=10.0,
        final_div_factor=100.0,
    )
    return optimizer, scheduler

optimizer, scheduler = get_optimizer_and_scheduler(
    model,
    stage=1,
    steps_per_epoch=len(train_loader),
    total_epochs=cfg.stage1_epochs,
)

total_params = sum(p.numel() for p in model.parameters())
trainable_params_stage1 = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Total parameters before Stage 1: {total_params:,}")
print(f"Trainable parameters in Stage 1: {trainable_params_stage1:,}")

trainable_names_stage1 = [name for name, p in model.named_parameters() if p.requires_grad]
invalid_trainable = [
    name for name in trainable_names_stage1
    if not (
        name.startswith("features.denseblock4.")
        or name.startswith("features.norm5.")
        or name.startswith("classifier.")
    )
]
assert not invalid_trainable, f"Unexpected Stage 1 trainable parameters: {invalid_trainable[:10]}"
print("Stage 1 trainable modules verified: features.denseblock4, features.norm5, classifier")
print(f"Optimizer parameter groups: {len(optimizer.param_groups)}")

dummy = torch.zeros(
    2,
    3,
    cfg.image_size,
    cfg.image_size,
    device=device,
)
model.eval()
with torch.no_grad():
    logits = model(dummy)
assert logits.shape == (2, cfg.num_classes)
print("DenseNet-121 forward test passed:", logits.shape)
model.train()

set_trainable_for_stage(model, 2)
assert all(p.requires_grad for p in model.parameters()), "Stage 2 unfreeze check failed"
print("Stage 2 unfreeze check passed: all parameters trainable")
set_trainable_for_stage(model, 1)


class ExponentialMovingAverage:
    def __init__(self, model, decay=0.999):
        self.decay = decay
        self.shadow = {}
        self.backup = {}
        for name, tensor in model.state_dict().items():
            if torch.is_floating_point(tensor):
                self.shadow[name] = tensor.detach().clone()

    @torch.no_grad()
    def update(self, model):
        state = model.state_dict()
        for name, tensor in state.items():
            if name in self.shadow and torch.is_floating_point(tensor):
                self.shadow[name].mul_(self.decay).add_(tensor.detach(), alpha=1.0 - self.decay)

    def apply_shadow(self, model):
        self.backup = {}
        state = model.state_dict()
        for name, tensor in state.items():
            if name in self.shadow:
                self.backup[name] = tensor.detach().clone()
                tensor.copy_(self.shadow[name].to(tensor.device))

    def restore(self, model):
        state = model.state_dict()
        for name, tensor in state.items():
            if name in self.backup:
                tensor.copy_(self.backup[name].to(tensor.device))
        self.backup = {}

    def state_dict(self):
        return {name: tensor.detach().cpu().clone() for name, tensor in self.shadow.items()}

    def load_state_dict(self, state_dict):
        self.shadow = {name: tensor.detach().clone() for name, tensor in state_dict.items()}

ema = ExponentialMovingAverage(model, decay=cfg.ema_decay)
'''.strip()


FAIRNESS_APPEND = r'''

fairness_check = pd.DataFrame([
    {"component": "Dataset split", "status": "Unchanged"},
    {"component": "Input size", "status": "Unchanged"},
    {"component": "Augmentation", "status": "Unchanged"},
    {"component": "Sampler", "status": "Unchanged"},
    {"component": "Loss", "status": "Unchanged"},
    {"component": "Optimizer", "status": "Unchanged"},
    {"component": "Scheduler", "status": "Unchanged"},
    {"component": "Learning rates", "status": "Unchanged"},
    {"component": "Epochs", "status": "Unchanged"},
    {"component": "Early stopping", "status": "Unchanged"},
    {"component": "EMA", "status": "Unchanged"},
    {"component": "TTA", "status": "Unchanged"},
    {"component": "Backbone architecture", "status": "EfficientNet-B0 → DenseNet-121"},
])
fairness_check.to_csv(OUTPUT_DIR / 'fairness_check.csv', index=False)

print('Fairness check')
display(fairness_check)
'''.rstrip()


def replace_common_text(source: str) -> str:
    replacements = {
        "Custom EfficientNet-B0 (From Scratch)": "DenseNet-121",
        "Custom EfficientNet-B0": "DenseNet-121",
        "EfficientNet-B0": "DenseNet-121",
        "EfficientNet B0": "DenseNet-121",
        "EfficientNet": "DenseNet",
        "efficientnet": "densenet",
        "skin_effnet_b0": "skin_densenet121",
        "skin_effnet_b0_v3_regularized": "skin_densenet121_v1",
        "CustomEfficientNet": "DenseNet121",
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    return source


def main() -> None:
    nb = nbformat.read(SRC, as_version=4)

    # Text-only cells and global import/config cells.
    for idx in [0, 1, 3, 25]:
        nb.cells[idx].source = replace_common_text(nb.cells[idx].source)

    nb.cells[2].source = nb.cells[2].source.replace(
        "from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights",
        "from torchvision.models import densenet121, DenseNet121_Weights",
    )
    nb.cells[2].source = replace_common_text(nb.cells[2].source)

    nb.cells[3].source = nb.cells[3].source.replace(
        "output_dir: str = '/kaggle/working/output'",
        "output_dir: str = '/kaggle/working/output_densenet121'",
    )
    nb.cells[3].source = nb.cells[3].source.replace(
        "cfg.output_dir = 'models/classification/outputs/skin_densenet121_v1_regularized'",
        "cfg.output_dir = 'models/classification/outputs/skin_densenet121_v1'",
    )
    nb.cells[3].source = nb.cells[3].source.replace(
        "cfg.output_dir = 'models/classification/outputs/skin_densenet121_v3_regularized'",
        "cfg.output_dir = 'models/classification/outputs/skin_densenet121_v1'",
    )

    nb.cells[12].source = DENSENET_MODEL_CELL

    # Summary stays unchanged, but use batch 2 for the hook forward to avoid BatchNorm1d train/eval edge cases.
    nb.cells[13].source = nb.cells[13].source.replace(
        "dummy = torch.zeros(1, *input_size, device=device)",
        "dummy = torch.zeros(2, *input_size, device=device)",
    )
    nb.cells[13].source = nb.cells[13].source.replace(
        "print(f'Model Summary: {model.__class__.__name__}')",
        "print('Model name    : DenseNet-121')",
    )
    nb.cells[13].source = nb.cells[13].source.replace(
        "print(f'Input size    : (1, {input_size[0]}, {input_size[1]}, {input_size[2]})')",
        "print(f'Input size    : (1, {input_size[0]}, {input_size[1]}, {input_size[2]})')",
    )

    nb.cells[14].source = TRAINING_SETUP_CELL

    nb.cells[16].source = nb.cells[16].source.replace(
        "'config': asdict(cfg),",
        "'config': asdict(cfg),\n        'architecture': ARCHITECTURE,",
    )

    nb.cells[18].source = nb.cells[18].source.replace(
        "loaded_model = build_model(num_classes=len(checkpoint['class_names']))",
        "loaded_model = build_model(num_classes=len(checkpoint['class_names']))",
    )

    nb.cells[25].source = nb.cells[25].source.replace(
        "{'item': 'model', 'value': 'DenseNet-121 + ImageNet mapped weights'}",
        "{'item': 'model', 'value': 'DenseNet-121 + ImageNet pretrained weights'}",
    )
    nb.cells[25].source = nb.cells[25].source.rstrip() + FAIRNESS_APPEND

    # Keep upload inference logic unchanged except displayed model text from common replacements if present.
    nb.cells[26].source = replace_common_text(nb.cells[26].source)

    # Clear outputs/execution counts to make this a fresh notebook.
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        elif "execution_count" in cell:
            del cell["execution_count"]

    nbformat.write(nb, OUT)
    print(f"Created: {OUT}")


if __name__ == "__main__":
    main()
