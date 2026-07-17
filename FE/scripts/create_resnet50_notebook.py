import copy
import json
from pathlib import Path


SOURCE = Path(
    r"E:\DHBKDN\CapstoneProject\SkinDeseases-AI\models\classification"
    r"\notebooks\train_custom_efficientnet_b0_scratch.ipynb"
)
TARGET = SOURCE.with_name("train_resnet50_same_pipeline.ipynb")


def set_source(cell: dict, source: str) -> None:
    cell["source"] = source.splitlines(keepends=True)
    if source and not source.endswith("\n"):
        cell["source"][-1] += "\n"


source_notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
notebook = copy.deepcopy(source_notebook)
cells = notebook["cells"]

set_source(
    cells[0],
    """# ResNet-50 - Same Training Pipeline Baseline

Training notebook using a pretrained torchvision ResNet-50 classifier for the same 10-class skin disease dataset.

Only the model architecture and architecture-dependent parameter access are changed. Data splits, preprocessing, augmentation, sampling, loss, MixUp/CutMix, optimizer and scheduler hyperparameters, EMA, early stopping, metrics, TTA, logging, and evaluation remain aligned with the EfficientNet-B0 notebook for a fair comparison.
""",
)

set_source(
    cells[1],
    """## Controlled Baseline Strategy

This notebook is a controlled architecture comparison against Custom EfficientNet-B0.

- The train/validation/test manifests and split checks are unchanged.
- Train and validation/test transforms are unchanged.
- WeightedRandomSampler and class-balanced loss weights are unchanged.
- ClassBalancedFocalLoss, MixUp, CutMix, AMP, gradient clipping, and EMA are unchanged.
- AdamW, differential learning rates, OneCycleLR, warmup, and stage epoch counts are unchanged.
- Stage 1 freezes the ResNet-50 backbone and trains only the custom `fc` classifier.
- Stage 2 unfreezes the entire model, matching the original two-stage training intent.
- Early stopping, checkpoint selection, TTA, metrics, reports, plots, and failure analysis are unchanged.
- Outputs are isolated in `output_resnet50` and use ResNet-50-specific artifact names.
""",
)

cell_2 = "".join(cells[2]["source"])
cell_2 = cell_2.replace(
    "from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights",
    "from torchvision.models import resnet50, ResNet50_Weights",
)
set_source(cells[2], cell_2)

cell_3 = "".join(cells[3]["source"])
cell_3 = cell_3.replace(
    "@dataclass\nclass CFG:",
    'MODEL_NAME = "resnet50"\n\n@dataclass\nclass CFG:',
)
cell_3 = cell_3.replace(
    "    # Differential LR. Stage 1 trains the head and the last blocks; stage 2 fine-tunes all layers.",
    "    # Differential LR values are unchanged. Stage 1 trains only fc; stage 2 fine-tunes all layers.",
)
cell_3 = cell_3.replace(
    "    output_dir: str = '/kaggle/working/output'",
    "    output_dir: str = '/kaggle/working/output_resnet50'",
)
cell_3 = cell_3.replace(
    "    cfg.output_dir = 'models/classification/outputs/skin_effnet_b0_v3_regularized'",
    "    cfg.output_dir = 'models/classification/outputs/resnet50_same_pipeline'",
)
set_source(cells[3], cell_3)

set_source(
    cells[12],
    """import torch
import torch.nn as nn
from torchvision.models import resnet50, ResNet50_Weights


class CustomResNet50Classifier(nn.Module):
    def __init__(self, num_classes=10, pretrained=True):
        super().__init__()

        weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        self.backbone = resnet50(weights=weights)
        in_features = self.backbone.fc.in_features

        self.backbone.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(in_features, 512),
            nn.BatchNorm1d(512),
            nn.SiLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        return self.backbone(x)

    def get_backbone_params(self):
        return [
            param
            for name, param in self.backbone.named_parameters()
            if not name.startswith("fc.")
        ]

    def get_classifier_params(self):
        return self.backbone.fc.parameters()


def build_model(num_classes: int):
    return CustomResNet50Classifier(
        num_classes=num_classes,
        pretrained=True,
    )


model = build_model(cfg.num_classes).to(device)

num_params = sum(param.numel() for param in model.parameters())
num_trainable = sum(param.numel() for param in model.parameters() if param.requires_grad)
print(f"Parameters: {num_params:,} | Trainable: {num_trainable:,}")

# Required forward smoke test.
model.eval()
with torch.no_grad():
    x = torch.randn(2, 3, cfg.image_size, cfg.image_size, device=device)
    y = model(x)
print("Forward output shape:", y.shape)
assert y.shape == (2, cfg.num_classes)
del x, y
""",
)

cell_13 = "".join(cells[13]["source"])
cell_13 = cell_13.replace(
    "model_summary_df.to_csv(OUTPUT_DIR / 'model_summary.csv', index=False)",
    "model_summary_df.to_csv(OUTPUT_DIR / 'model_summary_resnet50.csv', index=False)",
)
cell_13 = cell_13.replace(
    'print(f\'Model summary saved to: {OUTPUT_DIR / "model_summary.csv"}\')',
    'print(f\'Model summary saved to: {OUTPUT_DIR / "model_summary_resnet50.csv"}\')',
)
set_source(cells[13], cell_13)

cell_14 = "".join(cells[14]["source"])
stage_start = cell_14.index("def set_trainable_for_stage")
stage_end = cell_14.index("optimizer, scheduler = get_optimizer_and_scheduler")
stage_code = """def set_trainable_for_stage(model, stage: int):
    if stage == 1:
        for param in model.get_backbone_params():
            param.requires_grad = False
        for param in model.get_classifier_params():
            param.requires_grad = True
    else:
        for param in model.parameters():
            param.requires_grad = True


def get_optimizer_and_scheduler(model, stage: int, steps_per_epoch: int, total_epochs: int):
    set_trainable_for_stage(model, stage)

    # Keep the same two differential-LR groups and unchanged LR values.
    backbone_params = list(model.get_backbone_params())
    classifier_params = list(model.get_classifier_params())
    if stage == 1:
        max_lrs = [cfg.stage1_backbone_lr, cfg.stage1_classifier_lr]
    else:
        max_lrs = [cfg.backbone_lr, cfg.classifier_lr]

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


"""
cell_14 = cell_14[:stage_start] + stage_code + cell_14[stage_end:]
set_source(cells[14], cell_14)

cell_17 = "".join(cells[17]["source"])
cell_17 = cell_17.replace(
    "best_model_path = OUTPUT_DIR / 'best_model_clf.pth'",
    "best_model_path = OUTPUT_DIR / 'best_model_resnet50.pth'",
)
cell_17 = cell_17.replace(
    "best_loss_model_path = OUTPUT_DIR / 'best_val_loss_model_clf.pth'",
    "best_loss_model_path = OUTPUT_DIR / 'best_val_loss_model_resnet50.pth'",
)
cell_17 = cell_17.replace(
    "last_model_path = OUTPUT_DIR / 'last_model_clf.pth'",
    "last_model_path = OUTPUT_DIR / 'last_model_resnet50.pth'",
)
cell_17 = cell_17.replace(
    "print(f'\\nTraining completed in {(time.time() - start_time) / 60:.1f} minutes')",
    "training_time_minutes = (time.time() - start_time) / 60\n"
    "print(f'\\nTraining completed in {training_time_minutes:.1f} minutes')",
)
set_source(cells[17], cell_17)

cell_19 = "".join(cells[19]["source"])
cell_19 = cell_19.replace(
    "OUTPUT_DIR / 'classification_report.csv'",
    "OUTPUT_DIR / 'classification_report_resnet50.csv'",
)
cell_19 = cell_19.replace(
    "OUTPUT_DIR / 'classification_report.txt'",
    "OUTPUT_DIR / 'classification_report_resnet50.txt'",
)
cell_19 = cell_19.replace(
    "OUTPUT_DIR / 'classification_report_no_tta.csv'",
    "OUTPUT_DIR / 'classification_report_no_tta_resnet50.csv'",
)
set_source(cells[19], cell_19)

cell_20 = "".join(cells[20]["source"])
cell_20 = cell_20.replace(
    "OUTPUT_DIR / 'confusion_matrix.png'",
    "OUTPUT_DIR / 'confusion_matrix_resnet50.png'",
)
cell_20 = cell_20.replace(
    "OUTPUT_DIR / 'normalized_confusion_matrix.png'",
    "OUTPUT_DIR / 'normalized_confusion_matrix_resnet50.png'",
)
set_source(cells[20], cell_20)

cell_23 = "".join(cells[23]["source"])
cell_23 = cell_23.replace(
    "hist_df = pd.DataFrame(history)\n",
    "hist_df = pd.DataFrame(history)\n"
    "hist_df.to_csv(OUTPUT_DIR / 'history_resnet50.csv', index=False)\n",
    1,
)
set_source(cells[23], cell_23)

set_source(
    cells[24],
    """required_artifacts = [
    'best_model_resnet50.pth',
    'best_val_loss_model_resnet50.pth',
    'last_model_resnet50.pth',
    'config.json',
    'model_summary_resnet50.csv',
    'history_resnet50.csv',
    'train_val_loss.png',
    'train_val_accuracy.png',
    'train_val_macro_f1.png',
    'learning_rate_curve.png',
    'confusion_matrix_resnet50.png',
    'normalized_confusion_matrix_resnet50.png',
    'classification_report_resnet50.csv',
    'classification_report_no_tta_resnet50.csv',
    'classification_report_resnet50.txt',
    'per_class_metrics_tta.csv',
    'per_class_metrics_no_tta.csv',
    'per_class_f1.png',
    'tta_comparison.csv',
    'misclassified_samples.csv',
    'test_predictions_visualization.png',
    'model_comparison_resnet50.csv',
]

print('Generated required artifacts:')
for name in required_artifacts:
    path = OUTPUT_DIR / name
    status = 'OK' if path.exists() else 'MISSING'
    size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0
    print(f'- {name}: {status} ({size_mb:.2f} MB)')
""",
)

set_source(
    cells[25],
    """train_config_summary = pd.DataFrame([
    {'item': 'model', 'value': 'ResNet-50 IMAGENET1K_V2 + custom classifier'},
    {'item': 'input_size', 'value': f'{cfg.image_size}x{cfg.image_size}'},
    {'item': 'batch_size', 'value': cfg.batch_size},
    {'item': 'epochs', 'value': cfg.epochs},
    {'item': 'stage1_epochs', 'value': cfg.stage1_epochs},
    {'item': 'optimizer', 'value': 'AdamW'},
    {'item': 'scheduler', 'value': 'OneCycleLR batch-wise'},
    {'item': 'backbone_lr_stage2', 'value': cfg.backbone_lr},
    {'item': 'classifier_lr_stage2', 'value': cfg.classifier_lr},
    {'item': 'weight_decay', 'value': cfg.weight_decay},
    {'item': 'loss', 'value': cfg.loss_name},
    {'item': 'label_smoothing', 'value': cfg.label_smoothing},
    {'item': 'mixup_prob', 'value': cfg.mixup_prob},
    {'item': 'cutmix_prob', 'value': cfg.cutmix_prob},
    {'item': 'ema_decay', 'value': cfg.ema_decay},
    {'item': 'early_stop_monitor', 'value': cfg.monitor_metric},
])
train_config_summary.to_csv(OUTPUT_DIR / 'train_config_summary_resnet50.csv', index=False)

hist_df = pd.DataFrame(history)
best_f1_row = hist_df.loc[hist_df['val_f1_macro'].idxmax()].to_dict() if not hist_df.empty else {}
best_loss_row = hist_df.loc[hist_df['val_loss'].idxmin()].to_dict() if not hist_df.empty else {}
best_accuracy_row = hist_df.loc[hist_df['val_accuracy'].idxmax()].to_dict() if not hist_df.empty else {}
final_row = hist_df.iloc[-1].to_dict() if not hist_df.empty else {}

result_summary = pd.DataFrame([
    {'metric': 'efficientnet_b0_previous_best_val_macro_f1', 'value': 0.7327},
    {'metric': 'resnet50_best_val_macro_f1', 'value': best_f1_row.get('val_f1_macro')},
    {'metric': 'resnet50_best_val_loss', 'value': best_loss_row.get('val_loss')},
    {'metric': 'resnet50_best_val_accuracy', 'value': best_accuracy_row.get('val_accuracy')},
    {'metric': 'final_train_macro_f1', 'value': final_row.get('train_f1_macro')},
    {'metric': 'final_val_macro_f1', 'value': final_row.get('val_f1_macro')},
    {'metric': 'final_generalization_gap_f1', 'value': (final_row.get('train_f1_macro') - final_row.get('val_f1_macro')) if final_row else None},
    {'metric': 'test_macro_f1_no_tta', 'value': test_metrics_no_tta['f1_macro'] if 'test_metrics_no_tta' in globals() else None},
    {'metric': 'test_macro_f1_tta', 'value': test_metrics['f1_macro'] if 'test_metrics' in globals() else None},
])
result_summary.to_csv(OUTPUT_DIR / 'training_result_summary_resnet50.csv', index=False)

model_comparison = pd.DataFrame([{
    'Model name': MODEL_NAME,
    'Total parameters': num_params,
    'Trainable parameters': num_trainable,
    'Best Val Loss': best_loss_row.get('val_loss'),
    'Best Val Accuracy': best_accuracy_row.get('val_accuracy'),
    'Best Val Macro-F1': best_f1_row.get('val_f1_macro'),
    'Test Accuracy': test_metrics['accuracy'] if 'test_metrics' in globals() else None,
    'Test Macro-F1': test_metrics['f1_macro'] if 'test_metrics' in globals() else None,
    'Test Weighted-F1': test_metrics['f1_weighted'] if 'test_metrics' in globals() else None,
    'Training time (minutes)': training_time_minutes if 'training_time_minutes' in globals() else None,
    'Best checkpoint path': str(best_model_path),
}])
model_comparison.to_csv(OUTPUT_DIR / 'model_comparison_resnet50.csv', index=False)

print('Training configuration summary')
display(train_config_summary)
print('Training/result summary')
display(result_summary)
print('EfficientNet-B0 vs ResNet-50 report row')
display(model_comparison)

if final_row:
    gap = final_row.get('train_f1_macro') - final_row.get('val_f1_macro')
    print(f"Final train/val macro-F1 gap: {gap:.4f}")
    if gap < 0.12:
        print('Overfitting gap is in a moderate range.')
    else:
        print('Overfitting is still visible; compare this result directly with the EfficientNet-B0 baseline.')
""",
)

# New architecture notebook must not carry stale EfficientNet execution results.
for cell in cells:
    if cell.get("cell_type") == "code":
        cell["execution_count"] = None
        cell["outputs"] = []

# Guard the parts that must remain identical for a fair comparison.
unchanged_cells = [4, 5, 6, 7, 8, 9, 10, 11, 15, 16, 18, 21, 22, 26]
for index in unchanged_cells:
    assert (
        notebook["cells"][index]["source"] == source_notebook["cells"][index]["source"]
    ), f"Unexpected pipeline change in cell {index}"

serialized = json.dumps(notebook, ensure_ascii=False, indent=1)
TARGET.write_text(serialized + "\n", encoding="utf-8")
print(f"Created: {TARGET}")
print(f"Source preserved: {SOURCE}")
