import { NextRequest, NextResponse } from 'next/server';

// This is an example API route that would connect to your AI chatbot backend
// In production, this would forward the request to your actual LLM/chatbot service

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

interface ChatRequest {
  message: string;
  context: {
    predictedDisease: string;
    confidence: number;
    basicInfo: string;
  };
}

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    const { message, context } = body;

    if (!message || !message.trim()) {
      return NextResponse.json(
        { success: false, error: 'Message is required' },
        { status: 400 }
      );
    }

    // In production, forward to FastAPI backend:
    // const response = await fetch(`${FASTAPI_URL}/api/chat`, {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ message, context }),
    // });
    // const data = await response.json();
    // return NextResponse.json(data);

    // For demonstration, generate a contextual response
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const diseaseInfo = context?.predictedDisease || 'the skin condition';
    const confidence = context?.confidence || 0;

    // Generate response based on message keywords
    let response = '';

    if (message.toLowerCase().includes('cause') || message.toLowerCase().includes('why')) {
      response = `${diseaseInfo} can be caused by various factors including:

1. **Genetic factors** - Family history plays a significant role
2. **Environmental triggers** - Allergens, irritants, weather changes
3. **Immune system responses** - Inflammatory reactions in the skin
4. **Lifestyle factors** - Stress, diet, sleep patterns

Would you like more specific information about prevention or treatment?`;
    } else if (message.toLowerCase().includes('treatment') || message.toLowerCase().includes('cure')) {
      response = `Treatment options for ${diseaseInfo} typically include:

**Topical Treatments:**
- Moisturizers and emollients
- Prescription creams or ointments
- Corticosteroids for inflammation

**Lifestyle Changes:**
- Identifying and avoiding triggers
- Maintaining proper skin hygiene
- Managing stress levels

**Medical Interventions:**
- Phototherapy (light therapy)
- Oral medications for severe cases
- Biologic drugs for specific conditions

Always consult a dermatologist for personalized treatment recommendations.`;
    } else if (message.toLowerCase().includes('doctor') || message.toLowerCase().includes('specialist')) {
      const urgencyLevel = confidence >= 0.8 ? 'routine' : 'prioritized';
      response = `Based on the AI analysis (${Math.round(confidence * 100)}% confidence), here's my recommendation:

**When to See a Doctor:**
- If symptoms persist for more than 2 weeks
- If the condition is spreading or worsening
- If there are signs of infection (increased redness, warmth, pus)
- If over-the-counter treatments aren't helping

**Type of Specialist:**
A dermatologist specializes in skin conditions and would be the most appropriate specialist to consult.

**What to Prepare:**
- Photos showing progression over time
- List of products you've been using
- Your medical history and current medications

Would you like help with any other questions?`;
    } else if (message.toLowerCase().includes('contagious') || message.toLowerCase().includes('spread')) {
      response = `Regarding whether ${diseaseInfo} is contagious:

Most common skin conditions like eczema, psoriasis, and acne are **NOT contagious**. They cannot be spread through:
- Direct contact
- Sharing personal items
- Being in close proximity

However, some skin conditions caused by bacteria, viruses, or fungi CAN be contagious. Signs that might indicate a contagious condition:
- Rapid spreading to other body parts
- Similar symptoms appearing in close contacts
- Presence of blisters or open sores

For a definitive answer about your specific condition, please consult a healthcare professional.`;
    } else {
      response = `Thank you for your question about "${message}".

Based on the analysis showing ${diseaseInfo} with ${Math.round(confidence * 100)}% confidence, I can provide general guidance.

Key points to remember:
1. This AI analysis is for informational purposes only
2. Skin conditions can vary significantly in presentation
3. Professional evaluation is recommended for accurate diagnosis
4. Treatment should be personalized to your specific situation

Is there anything specific about ${diseaseInfo} you'd like to know more about? You can ask about:
- Causes and triggers
- Treatment options
- Prevention strategies
- When to see a doctor`;
    }

    return NextResponse.json({
      success: true,
      data: {
        message: response,
      },
    });
  } catch (error) {
    console.error('Chat error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to process message. Please try again.' },
      { status: 500 }
    );
  }
}
