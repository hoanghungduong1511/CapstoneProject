"""
Segmentation Inference Pipeline — Production Ready
===================================================
This module provides a self-contained inference pipeline for skin lesion
segmentation. It reads ALL settings from segmentation_config.json so
that preprocessing, model inference, and postprocessing are guaranteed
to be identical across training, backend, and frontend.

Usage:
    from ai_models.segmentation.inference import SegmentationPipeline
    
    pipeline = SegmentationPipeline("ai_models/segmentation")
    result = pipeline.predict(image_rgb)
    # result["mask"]       → binary mask (H, W) uint8
    # result["roi_crop"]   → cropped ROI for classifier (H', W', 3) uint8
    # result["bbox"]       → (x_min, y_min, x_max, y_max)
    # result["prob_map"]   → probability map (H, W) float32
    # result["fallback"]   → True if no lesion found
"""

import json
import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import efficientnet_b3, EfficientNet_B3_Weights

# Optional: only needed if loading .pth with full model definition
try:
    import segmentation_models_pytorch as smp
except ImportError:
    smp = None


class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
    def forward(self, x):
        return self.conv(x)

class CustomUNetEfficientNetB3(nn.Module):
    def __init__(self):
        super().__init__()
        # 1. Load Pretrained Encoder
        encoder = efficientnet_b3(weights=None)
        features = encoder.features
        
        # Split encoder stages based on correct feature dimensions
        self.stem = features[0:2]   # enc1: [B, 24, 128, 128]
        self.stage2 = features[2]   # enc2: [B, 32, 64, 64]
        self.stage3 = features[3]   # enc3: [B, 48, 32, 32]
        self.stage4 = features[4:6] # enc4: [B, 136, 16, 16]
        self.bottleneck = features[6:9] # btn: [B, 1536, 8, 8]
        
        # 2. Bridge (Bottleneck Compression)
        self.bridge = DoubleConv(1536, 512) # [B, 512, 8, 8]
        
        # 3. Decoder
        self.up4 = DoubleConv(512 + 136, 512) # [B, 512, 16, 16]
        self.up3 = DoubleConv(512 + 48, 256)  # [B, 256, 32, 32]
        self.up2 = DoubleConv(256 + 32, 128)  # [B, 128, 64, 64]
        self.up1 = DoubleConv(128 + 24, 64)   # [B, 64, 128, 128]
        
        # Final upsample to 256x256 (no skip from raw image)
        self.up0 = DoubleConv(64, 32)         # [B, 32, 256, 256]
        
        # 4. Output Head
        self.outc = nn.Conv2d(32, 1, kernel_size=1)

    def forward(self, x):
        # Encoder
        enc1 = self.stem(x)         # 24, 128, 128
        enc2 = self.stage2(enc1)    # 32, 64, 64
        enc3 = self.stage3(enc2)    # 48, 32, 32
        enc4 = self.stage4(enc3)    # 136, 16, 16
        btn  = self.bottleneck(enc4) # 1536, 8, 8
        
        # Bridge
        btn = self.bridge(btn)      # 512, 8, 8
        
        # Decoder with Bilinear Upsampling + Concatenation
        d4 = F.interpolate(btn, scale_factor=2, mode='bilinear', align_corners=False)
        d4 = torch.cat([d4, enc4], dim=1)
        d4 = self.up4(d4)           # 512, 16, 16
        
        d3 = F.interpolate(d4, scale_factor=2, mode='bilinear', align_corners=False)
        d3 = torch.cat([d3, enc3], dim=1)
        d3 = self.up3(d3)           # 256, 32, 32
        
        d2 = F.interpolate(d3, scale_factor=2, mode='bilinear', align_corners=False)
        d2 = torch.cat([d2, enc2], dim=1)
        d2 = self.up2(d2)           # 128, 64, 64
        
        d1 = F.interpolate(d2, scale_factor=2, mode='bilinear', align_corners=False)
        d1 = torch.cat([d1, enc1], dim=1)
        d1 = self.up1(d1)           # 64, 128, 128
        
        # Final Upsample to match input size (256x256) without skip
        d0 = F.interpolate(d1, scale_factor=2, mode='bilinear', align_corners=False)
        d0 = self.up0(d0)           # 32, 256, 256
        
        out = self.outc(d0)         # 1, 256, 256
        return out

class SegmentationPipeline:
    """
    Production inference pipeline for skin lesion segmentation.
    
    Reads all config from segmentation_config.json to ensure
    consistency between training and deployment.
    """

    def __init__(self, model_dir: str, device: str = None, use_tta: bool = None):
        """
        Args:
            model_dir: Path to directory containing model files and config.
            device: 'cuda' or 'cpu'. Auto-detects if None.
            use_tta: Override TTA setting from config. None = use config value.
        """
        self.model_dir = model_dir
        self.config = self._load_config()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.use_tta = use_tta if use_tta is not None else self.config.get("tta_enabled", True)

        # Preprocessing constants (from config — NEVER hardcode)
        self.img_size = self.config["image_size"]
        self.mean = np.array(self.config["normalize_mean"])
        self.std = np.array(self.config["normalize_std"])
        self.threshold = self.config["threshold"]

        # Postprocessing constants
        pp = self.config["postprocess"]
        self.min_area_ratio = pp["min_area_ratio"]
        self.morph_kernel_size = pp["morphology_kernel_size"]

        # ROI constants
        roi = self.config["roi_extraction"]
        self.padding_ratio = roi["padding_ratio"]
        self.min_roi_ratio = roi["min_roi_ratio"]
        self.min_mask_area_ratio = roi["min_mask_area_ratio"]

        # Load model
        self.model = self._load_model()
        self.model.eval()

        print(f"[SegmentationPipeline] Loaded successfully")
        print(f"  Device: {self.device} | TTA: {self.use_tta} | Threshold: {self.threshold}")
        print(f"  Img size: {self.img_size} | Encoder: {self.config['encoder']}")

    def _load_config(self) -> dict:
        """Load config from JSON file."""
        config_path = os.path.join(self.model_dir, "segmentation_config.json")
        if not os.path.exists(config_path):
            # Try v2 naming convention
            config_path = os.path.join(self.model_dir, "segmentation_config_v2.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config not found in: {self.model_dir}")
        with open(config_path, "r") as f:
            return json.load(f)

    def _load_model(self) -> nn.Module:
        """Build model architecture and load weights."""
        # Build architecture from config
        is_v3 = "v3" in self.config.get("weights_file", "") or "v3" in self.config.get("model_file", "")
        if is_v3:
            model = CustomUNetEfficientNetB3()
        else:
            if smp is None:
                raise ImportError(
                    "segmentation-models-pytorch is required. "
                    "Install with: pip install segmentation-models-pytorch"
                )
            model = smp.Unet(
                encoder_name=self.config.get("encoder", "efficientnet-b3"),
                encoder_weights=None,  # don't download pretrained — we load our own
                in_channels=self.config.get("in_channels", 3),
                classes=self.config.get("classes", 1),
                activation=self.config.get("activation", None),
            )

        # Load weights
        weights_path = os.path.join(self.model_dir, self.config["weights_file"])
        if not os.path.exists(weights_path):
            # Try full model file
            weights_path = os.path.join(self.model_dir, self.config["model_file"])

        if os.path.exists(weights_path):
            checkpoint = torch.load(weights_path, map_location=self.device)
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"])
            else:
                model.load_state_dict(checkpoint)
            print(f"  Weights loaded from: {os.path.basename(weights_path)}")
        else:
            raise FileNotFoundError(f"Model weights not found: {weights_path}")

        return model.to(self.device)

    # ── Preprocessing ──────────────────────────────────────────

    def preprocess(self, image_rgb: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for model input.
        
        Args:
            image_rgb: RGB image, any size, uint8 [0, 255]
            
        Returns:
            Tensor (1, 3, H, W) normalized, on device
        """
        # Resize to model input size
        img = cv2.resize(image_rgb, (self.img_size, self.img_size),
                         interpolation=cv2.INTER_LINEAR)

        # Normalize (same as training)
        img = (img / 255.0 - self.mean) / self.std

        # To tensor (H, W, C) → (1, C, H, W)
        tensor = torch.tensor(
            img.transpose(2, 0, 1), dtype=torch.float32
        ).unsqueeze(0)

        return tensor.to(self.device)

    # ── Model Inference ────────────────────────────────────────

    @torch.no_grad()
    def _predict_single(self, tensor: torch.Tensor) -> torch.Tensor:
        """Single forward pass, returns probabilities."""
        with torch.cuda.amp.autocast(enabled=self.device == "cuda"):
            logits = self.model(tensor)
        return torch.sigmoid(logits)

    @torch.no_grad()
    def _predict_tta(self, tensor: torch.Tensor) -> torch.Tensor:
        """4-flip TTA: original + hflip + vflip + hflip+vflip."""
        with torch.cuda.amp.autocast(enabled=self.device == "cuda"):
            p1 = torch.sigmoid(self.model(tensor))
            p2 = torch.flip(
                torch.sigmoid(self.model(torch.flip(tensor, [3]))), [3]
            )
            p3 = torch.flip(
                torch.sigmoid(self.model(torch.flip(tensor, [2]))), [2]
            )
            p4 = torch.flip(
                torch.sigmoid(self.model(torch.flip(tensor, [2, 3]))), [2, 3]
            )
        return (p1 + p2 + p3 + p4) / 4.0

    # ── Postprocessing ─────────────────────────────────────────

    def postprocess_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        Clean predicted binary mask.
        
        1. Remove small connected components (noise)
        2. Morphological close (fill holes)
        3. Morphological open (smooth boundaries)
        
        Args:
            mask: Binary mask (H, W) with values 0 or 1
            
        Returns:
            Cleaned binary mask (H, W) uint8
        """
        binary = mask.astype(np.uint8)
        min_area = int(self.min_area_ratio * binary.size)

        # Remove small components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
        cleaned = np.zeros_like(binary)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                cleaned[labels == i] = 1

        # Morphological operations
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.morph_kernel_size, self.morph_kernel_size)
        )
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        return cleaned

    # ── ROI Extraction ─────────────────────────────────────────

    def extract_roi(self, image_rgb: np.ndarray, mask: np.ndarray) -> dict:
        """
        Extract ROI from image using predicted mask.
        
        Returns:
            dict with 'roi_crop', 'bbox', 'fallback'
        """
        h, w = image_rgb.shape[:2]
        coords = np.where(mask > 0)

        # Check if mask is too small or empty → fallback
        if len(coords[0]) == 0 or len(coords[0]) < self.min_mask_area_ratio * h * w:
            return {
                "roi_crop": image_rgb.copy(),
                "bbox": (0, 0, w, h),
                "fallback": True,
            }

        y_min, y_max = coords[0].min(), coords[0].max()
        x_min, x_max = coords[1].min(), coords[1].max()

        # Percentage-based padding
        roi_h, roi_w = y_max - y_min, x_max - x_min
        pad_y = int(roi_h * self.padding_ratio)
        pad_x = int(roi_w * self.padding_ratio)

        y_min = max(0, y_min - pad_y)
        y_max = min(h, y_max + pad_y)
        x_min = max(0, x_min - pad_x)
        x_max = min(w, x_max + pad_x)

        # Enforce minimum ROI size
        min_dim = int(min(h, w) * self.min_roi_ratio)
        if (y_max - y_min) < min_dim:
            cy = (y_min + y_max) // 2
            y_min = max(0, cy - min_dim // 2)
            y_max = min(h, y_min + min_dim)
        if (x_max - x_min) < min_dim:
            cx = (x_min + x_max) // 2
            x_min = max(0, cx - min_dim // 2)
            x_max = min(w, x_min + min_dim)

        roi_crop = image_rgb[y_min:y_max, x_min:x_max]

        return {
            "roi_crop": roi_crop,
            "bbox": (x_min, y_min, x_max, y_max),
            "fallback": False,
        }

    # ── Main Predict ───────────────────────────────────────────

    def predict(self, image_rgb: np.ndarray) -> dict:
        """
        Complete prediction pipeline.
        
        Args:
            image_rgb: Input image in RGB format, any size, uint8 [0, 255]
            
        Returns:
            dict with:
                - "mask": binary mask at original resolution (H, W) uint8
                - "mask_256": binary mask at model resolution (256, 256) uint8
                - "prob_map": probability map at original resolution (H, W) float32
                - "roi_crop": cropped ROI for classifier (H', W', 3) uint8
                - "bbox": (x_min, y_min, x_max, y_max)
                - "fallback": True if no lesion detected
                - "lesion_ratio": percentage of image covered by lesion
        """
        orig_h, orig_w = image_rgb.shape[:2]

        # 1. Preprocess
        tensor = self.preprocess(image_rgb)

        # 2. Predict (with or without TTA)
        if self.use_tta:
            probs = self._predict_tta(tensor)
        else:
            probs = self._predict_single(tensor)

        # 3. Get probability map at model resolution
        prob_256 = probs[0, 0].cpu().float().numpy()

        # 4. Threshold → binary mask
        mask_256 = (prob_256 > self.threshold).astype(np.uint8)

        # 5. Postprocess (clean noise, fill holes)
        mask_256 = self.postprocess_mask(mask_256)

        # 6. Resize mask to original resolution
        mask_full = cv2.resize(
            mask_256, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST
        )

        # 7. Resize probability map to original resolution
        prob_full = cv2.resize(prob_256, (orig_w, orig_h))

        # 8. Extract ROI
        roi_result = self.extract_roi(image_rgb, mask_full)

        # 9. Calculate lesion ratio
        lesion_ratio = mask_full.sum() / mask_full.size

        return {
            "mask": mask_full,
            "mask_256": mask_256,
            "prob_map": prob_full,
            "roi_crop": roi_result["roi_crop"],
            "bbox": roi_result["bbox"],
            "fallback": roi_result["fallback"],
            "lesion_ratio": float(lesion_ratio),
        }

    def predict_from_file(self, image_path: str) -> dict:
        """
        Predict from image file path.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Same as predict()
        """
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        return self.predict(img_rgb)

    def predict_from_bytes(self, image_bytes: bytes) -> dict:
        """
        Predict from image bytes (e.g., from HTTP upload).
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Same as predict()
        """
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("Cannot decode image from bytes")
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        return self.predict(img_rgb)


# ── FastAPI Integration Example ────────────────────────────
#
# from fastapi import FastAPI, UploadFile
# from ai_models.segmentation.inference import SegmentationPipeline
#
# app = FastAPI()
# seg_pipeline = SegmentationPipeline("ai_models/segmentation")
#
# @app.post("/api/segment")
# async def segment(file: UploadFile):
#     image_bytes = await file.read()
#     result = seg_pipeline.predict_from_bytes(image_bytes)
#     return {
#         "lesion_ratio": result["lesion_ratio"],
#         "bbox": result["bbox"],
#         "fallback": result["fallback"],
#     }
