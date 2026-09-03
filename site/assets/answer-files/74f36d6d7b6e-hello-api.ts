// 由 expo-api-route-gen 依据 expo-api-routes Skill 生成
// 对应 SKILL.md: Basic API Route / HTTP Methods / JSON Body / Error Handling

export function GET(request: Request) {
  return Response.json({ message: "Hello from Expo!" });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { name } = body;

    if (!name || typeof name !== "string") {
      return Response.json({ error: "Missing or invalid 'name'" }, { status: 400 });
    }

    return Response.json({ created: { name } }, { status: 201 });
  } catch (error) {
    console.error("API error:", error);
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
