"""
Skin Gate — Binary Classification Inference Pipeline
Validates if an uploaded image contains human skin before passing to segmentation.

Usage:
    from ai_models.skin_gate import SkinGatePipeline

    gate = SkinGatePipeline("ai_models/skin_gate/best_model_binary.pth")
    result = gate.predict("photo.jpg")
    # result["is_skin"]     -> True/False
    # result["confidence"]  -> 0.0 - 1.0
    # result["class_name"]  -> "person_skin" or "non_person_skin"
"""

import json
import numpy as np
import torch
import torch.nn as nn
import cv2
from pathlib import Path

try:
    import timm
except ImportError:
    raise ImportError("Install timm: pip install timm")


class SkinBinaryModel(nn.Module):
    """EfficientNet-B0 binary classifier."""

    def __init__(self, model_name="efficientnet_b0", pretrained=False):
        super().__init__()
        self.backbone = timm.create_model(model_name, pretrained=pretrained, num_classes=0)
        self.num_features = self.backbone.num_features
        self.head = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(self.num_features, 1),
        )

    def forward(self, x):
        features = self.backbone(x)
        return self.head(features).squeeze(-1)


class SkinGatePipeline:
    """
    Production inference pipeline for skin validation gate.

    Args:
        model_path: Path to .pth weights file
        config_path: Path to skin_gate_config.json (auto-detected if None)
        device: 'cuda', 'cpu', or 'auto'
    """

    def __init__(self, model_path, config_path=None, device="auto"):
        self.model_path = Path(model_path)

        # Load config
        if config_path is None:
            config_path = self.model_path.parent / "skin_gate_config.json"
        with open(config_path, "r") as f:
            self.config = json.load(f)

        # Device
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Inference params
        inf = self.config["inference"]
        self.img_size = inf["img_size"]
        self.mean = np.array(inf["normalize_mean"])
        self.std = np.array(inf["normalize_std"])
        self.threshold = inf["threshold"]
        self.classes = self.config["classes"]

        # Load model
        self.model = SkinBinaryModel(
            model_name=self.config["model"]["backbone"],
            pretrained=False,
        )
        state_dict = torch.load(str(self.model_path), map_location=self.device)
        # Handle wrapped state dict (from training checkpoint)
        if "model_state_dict" in state_dict:
            state_dict = state_dict["model_state_dict"]
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

    def _preprocess(self, image):
        """Preprocess image to tensor. Accepts path, bytes, or numpy array."""
        if isinstance(image, (str, Path)):
            img = cv2.imread(str(image))
            if img is None:
                raise ValueError(f"Cannot read image: {image}")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif isinstance(image, bytes):
            arr = np.frombuffer(image, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif isinstance(image, np.ndarray):
            img = image.copy()
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            raise TypeError(f"Unsupported input type: {type(image)}")

        # Resize
        img = cv2.resize(img, (self.img_size, self.img_size), interpolation=cv2.INTER_LANCZOS4)

        # Normalize
        img = img.astype(np.float32) / 255.0
        img = (img - self.mean) / self.std

        # To tensor (H, W, C) -> (1, C, H, W)
        tensor = torch.tensor(img.transpose(2, 0, 1), dtype=torch.float32).unsqueeze(0)
        return tensor

    @torch.no_grad()
    def predict(self, image, threshold=None, use_tta=False):
        """
        Predict if image contains human skin.

        Args:
            image: file path (str), bytes, or numpy array (RGB)
            threshold: override default threshold
            use_tta: horizontal flip TTA

        Returns:
            dict: is_skin, confidence, class_name, probability, threshold
        """
        if threshold is None:
            threshold = self.threshold

        tensor = self._preprocess(image)

        # Forward
        logit = self.model(tensor.to(self.device))
        prob = torch.sigmoid(logit).item()

        # TTA: horizontal flip
        if use_tta:
            logit_flip = self.model(torch.flip(tensor, [3]).to(self.device))
            prob_flip = torch.sigmoid(logit_flip).item()
            prob = (prob + prob_flip) / 2.0

        is_skin = prob > threshold
        class_idx = 1 if is_skin else 0

        return {
            "is_skin": bool(is_skin),
            "confidence": float(prob if is_skin else 1.0 - prob),
            "class_name": self.classes[str(class_idx)],
            "probability": float(prob),
            "threshold": float(threshold),
        }

    def validate_upload(self, image, min_confidence=0.6):
        """
        Validate an uploaded image for the dermatology pipeline.

        Args:
            image: file path, bytes, or numpy array
            min_confidence: minimum confidence to accept

        Returns:
            dict: accepted (bool), reason (str), details (dict)
        """
        result = self.predict(image, use_tta=True)

        if result["is_skin"] and result["confidence"] >= min_confidence:
            return {
                "accepted": True,
                "reason": "Image contains human skin",
                "details": result,
            }
        elif result["is_skin"]:
            return {
                "accepted": False,
                "reason": f"Low confidence ({result['confidence']:.1%}). Please upload a clearer skin image.",
                "details": result,
            }
        else:
            return {
                "accepted": False,
                "reason": "Image does not appear to contain human skin. Please upload a skin photo.",
                "details": result,
            }


# ── Quick test ──
if __name__ == "__main__":
    import sys

    model_dir = Path(__file__).parent
    model_path = model_dir / "best_model_binary.pth"

    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("Download from Kaggle and place in ai_models/skin_gate/")
        sys.exit(1)

    gate = SkinGatePipeline(model_path)
    print(f"Skin Gate loaded on {gate.device}")
    print(f"Threshold: {gate.threshold}")

    if len(sys.argv) > 1:
        for img_path in sys.argv[1:]:
            result = gate.validate_upload(img_path)
            status = "✓ ACCEPTED" if result["accepted"] else "✗ REJECTED"
            print(f"  {status} | {Path(img_path).name} | {result['reason']}")
    else:
        print("Usage: python inference.py image1.jpg image2.png ...")
