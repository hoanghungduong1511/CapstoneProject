import { NextRequest, NextResponse } from 'next/server';

// This is an example API route that would connect to your FastAPI backend
// In production, this would forward the request to your actual ML model server

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const image = formData.get('image') as File;

    if (!image) {
      return NextResponse.json(
        { success: false, error: 'No image provided' },
        { status: 400 }
      );
    }

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(image.type)) {
      return NextResponse.json(
        { success: false, error: 'Invalid image type. Please upload JPEG, PNG, or WebP.' },
        { status: 400 }
      );
    }

    // In production, forward to FastAPI backend:
    // const response = await fetch(`${FASTAPI_URL}/api/analyze`, {
    //   method: 'POST',
    //   body: formData,
    // });
    // const data = await response.json();
    // return NextResponse.json(data);

    // For demonstration, return mock data
    // Simulate processing time
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Convert image to base64 for preview
    const buffer = await image.arrayBuffer();
    const base64 = Buffer.from(buffer).toString('base64');
    const imageData = `data:${image.type};base64,${base64}`;

    // Mock diagnosis results
    const diseases = [
      {
        name: 'Eczema',
        info: 'Eczema (atopic dermatitis) is a condition that causes dry, itchy, and inflamed skin. It is common in children but can occur at any age. Eczema is chronic and tends to flare periodically. It may be accompanied by asthma or hay fever.',
      },
      {
        name: 'Psoriasis',
        info: 'Psoriasis is an autoimmune condition that causes skin cells to multiply faster than normal, leading to thick, scaly patches. It commonly affects the scalp, elbows, knees, and lower back.',
      },
      {
        name: 'Acne',
        info: 'Acne is a skin condition that occurs when hair follicles become clogged with oil and dead skin cells. It causes whiteheads, blackheads, or pimples and is most common among teenagers.',
      },
      {
        name: 'Melanoma',
        info: 'Melanoma is the most serious type of skin cancer, developing from the cells that give skin its color. Early detection is crucial. ABCDE rule: Asymmetry, Border, Color, Diameter, Evolving.',
      },
      {
        name: 'Contact Dermatitis',
        info: 'Contact dermatitis is a red, itchy rash caused by direct contact with a substance or an allergic reaction to it. Common triggers include poison ivy, jewelry metals, soaps, and cosmetics.',
      },
    ];

    const randomDisease = diseases[Math.floor(Math.random() * diseases.length)];
    const confidence = 0.75 + Math.random() * 0.2; // Random confidence between 0.75 and 0.95

    return NextResponse.json({
      success: true,
      data: {
        id: crypto.randomUUID(),
        originalImage: imageData,
        segmentationMask: imageData, // In production, this would be the actual mask
        predictedDisease: randomDisease.name,
        confidence: Number(confidence.toFixed(2)),
        basicInfo: randomDisease.info,
      },
    });
  } catch (error) {
    console.error('Analysis error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to process image. Please try again.' },
      { status: 500 }
    );
  }
}
