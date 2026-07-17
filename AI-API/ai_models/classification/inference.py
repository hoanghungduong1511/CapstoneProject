import io
import math
from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms


def drop_connect(x, drop_ratio):
    if drop_ratio == 0 or not x.requires_grad:
        return x
    keep_ratio = 1.0 - drop_ratio
    batch_size = x.size(0)
    random_tensor = keep_ratio + torch.rand(
        [batch_size, 1, 1, 1],
        dtype=x.dtype,
        device=x.device,
    )
    binary_tensor = torch.floor(random_tensor)
    return x.div(keep_ratio) * binary_tensor


class SqueezeExcitation(nn.Module):
    def __init__(self, in_channels, reduced_dim):
        super().__init__()
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, reduced_dim, 1),
            nn.SiLU(inplace=True),
            nn.Conv2d(reduced_dim, in_channels, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return x * self.se(x)


class MBConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels, expand_ratio, stride, kernel_size, drop_ratio):
        super().__init__()
        self.drop_ratio = drop_ratio
        self.use_residual = in_channels == out_channels and stride == 1
        hidden_dim = in_channels * expand_ratio

        layers = []
        if expand_ratio != 1:
            layers.extend([
                nn.Conv2d(in_channels, hidden_dim, 1, bias=False),
                nn.BatchNorm2d(hidden_dim),
                nn.SiLU(inplace=True),
            ])

        layers.extend([
            nn.Conv2d(
                hidden_dim,
                hidden_dim,
                kernel_size,
                stride,
                kernel_size // 2,
                groups=hidden_dim,
                bias=False,
            ),
            nn.BatchNorm2d(hidden_dim),
            nn.SiLU(inplace=True),
            SqueezeExcitation(hidden_dim, max(1, int(in_channels * 0.25))),
            nn.Conv2d(hidden_dim, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
        ])
        self.conv = nn.Sequential(*layers)

    def forward(self, x):
        if self.use_residual:
            return x + drop_connect(self.conv(x), self.drop_ratio)
        return self.conv(x)


class CustomEfficientNet(nn.Module):
    def __init__(
        self,
        num_classes=10,
        width_mult=1.0,
        depth_mult=1.0,
        dropout_rate=0.2,
        drop_connect_rate=0.2,
    ):
        super().__init__()

        def scale_width(w):
            w *= width_mult
            new_w = max(8, int(w + 4) // 8 * 8)
            if new_w < 0.9 * w:
                new_w += 8
            return int(new_w)

        def scale_depth(d):
            return int(math.ceil(d * depth_mult))

        base_config = [
            [1, 16, 1, 1, 3],
            [6, 24, 2, 2, 3],
            [6, 40, 2, 2, 5],
            [6, 80, 3, 2, 3],
            [6, 112, 3, 1, 5],
            [6, 192, 4, 2, 5],
            [6, 320, 1, 1, 3],
        ]

        out_channels = scale_width(32)
        self.stem = nn.Sequential(
            nn.Conv2d(3, out_channels, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.SiLU(inplace=True),
        )

        in_channels = out_channels
        total_blocks = sum(scale_depth(c[2]) for c in base_config)
        block_idx = 0

        self.blocks = nn.ModuleList([])
        for expand_ratio, channels, repeats, stride, kernel_size in base_config:
            out_channels = scale_width(channels)
            repeats = scale_depth(repeats)
            for i in range(repeats):
                s = stride if i == 0 else 1
                drop_ratio = drop_connect_rate * float(block_idx) / total_blocks
                self.blocks.append(
                    MBConvBlock(in_channels, out_channels, expand_ratio, s, kernel_size, drop_ratio)
                )
                in_channels = out_channels
                block_idx += 1

        last_channels = scale_width(1280)
        self.head = nn.Sequential(
            nn.Conv2d(in_channels, last_channels, 1, bias=False),
            nn.BatchNorm2d(last_channels),
            nn.SiLU(inplace=True),
        )

        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.flatten = nn.Flatten()

        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(last_channels, 512),
            nn.BatchNorm1d(512),
            nn.SiLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, (nn.BatchNorm2d, nn.BatchNorm1d)):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.stem(x)
        for block in self.blocks:
            x = block(x)
        x = self.head(x)
        x = self.avgpool(x)
        x = self.flatten(x)
        x = self.classifier(x)
        return x


class ClassificationPipeline:
    def __init__(self, model_dir: str, device: str = "cpu"):
        self.model_dir = Path(model_dir)
        self.device = torch.device(device)

        checkpoint_path = self.model_dir / "best_model_clf_v2.pth"
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Classification checkpoint not found: {checkpoint_path}")

        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.class_names = checkpoint.get("class_names") or [
            "ACNE", "AK", "BCC", "BKL", "ECZEMA",
            "MELANOMA", "NEVUS", "PSORIASIS", "SCC", "TINEA",
        ]
        config = checkpoint.get("config", {})
        self.image_size = int(config.get("image_size", 256))
        self.resize_size = int(config.get("resize_size", self.image_size))

        self.model = CustomEfficientNet(num_classes=len(self.class_names))

        state_dict = checkpoint.get("ema_state_dict") or checkpoint["model_state_dict"]
        self.model.load_state_dict(state_dict, strict=True)
        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize(self.resize_size),
            transforms.CenterCrop(self.image_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def _to_pil(self, image: Union[bytes, np.ndarray, Image.Image]) -> Image.Image:
        if isinstance(image, bytes):
            return Image.open(io.BytesIO(image)).convert("RGB")
        if isinstance(image, np.ndarray):
            array = image
            if array.dtype != np.uint8:
                array = np.clip(array, 0, 255).astype(np.uint8)
            return Image.fromarray(array).convert("RGB")
        return image.convert("RGB")

    def predict(self, image: Union[bytes, np.ndarray, Image.Image], top_k: int = 5) -> dict:
        tensor = self.transform(self._to_pil(image)).unsqueeze(0).to(self.device)

        with torch.inference_mode():
            logits = self.model(tensor)
            flipped_logits = self.model(torch.flip(tensor, dims=[3]))
            probabilities = F.softmax((logits + flipped_logits) / 2, dim=1)[0]

        top_k = min(top_k, len(self.class_names))
        scores, indices = torch.topk(probabilities, k=top_k)
        candidates = [
            {
                "label": self.class_names[index],
                "confidence": round(float(score), 6),
            }
            for score, index in zip(scores.cpu().tolist(), indices.cpu().tolist())
        ]

        return {
            "top_label": candidates[0]["label"],
            "top_confidence": candidates[0]["confidence"],
            "candidates": candidates,
        }
