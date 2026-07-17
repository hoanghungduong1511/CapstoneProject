import type { MedicalContext, SkinAnalysisResponse } from '@/types';

export function buildMedicalContext(result: SkinAnalysisResponse): MedicalContext {
  const probability = result.validation.probability;
  const severity = probability > 0.8 ? 'high' : probability > 0.5 ? 'medium' : 'low';
  const confidence =
    result.classification?.top_confidence ?? result.validation.confidence * 100;

  return {
    disease: result.classification?.top_label ?? result.validation.class_name,
    confidence,
    severity,
    lesionAreaPercent: result.segmentation?.lesion_ratio
      ? Math.round(result.segmentation.lesion_ratio * 100)
      : 0,
    symptoms: [],
    characteristics: [
      'Ph\u00e1t hi\u1ec7n qua h\u1ec7 th\u1ed1ng ph\u00e2n t\u00edch h\u00ecnh \u1ea3nh da',
      'K\u1ebft qu\u1ea3 ch\u1ec9 mang t\u00ednh ch\u1ea5t h\u1ed7 tr\u1ee3 tham kh\u1ea3o',
    ],
  };
}

export function generateInitialGreeting(context: MedicalContext): string {
  return `Xin ch\u00e0o. T\u00f4i l\u00e0 Tr\u1ee3 l\u00fd Y khoa AI.

K\u1ebft qu\u1ea3 ph\u00e2n t\u00edch h\u00ecnh \u1ea3nh ghi nh\u1eadn kh\u1ea3 n\u0103ng ph\u00f9 h\u1ee3p nh\u1ea5t l\u00e0 **${context.disease}**

B\u1ea1n c\u00f3 th\u1ec3 h\u1ecfi t\u00f4i v\u1ec1 t\u00ecnh tr\u1ea1ng n\u00e0y, c\u00e1ch ch\u0103m s\u00f3c da c\u01a1 b\u1ea3n v\u00e0 th\u1eddi \u0111i\u1ec3m n\u00ean \u0111i kh\u00e1m. Th\u00f4ng tin t\u01b0 v\u1ea5n kh\u00f4ng thay th\u1ebf ch\u1ea9n \u0111o\u00e1n c\u1ee7a b\u00e1c s\u0129.`;
}
