// 由 expo-api-route-gen 依据 expo-api-routes Skill 生成
// 对应 SKILL.md: Environment Variables / Proxy External API
// 注意: 密钥必须通过 EAS Hosting 环境变量或本地 .env 注入，切勿硬编码或提交到仓库

export async function GET(request: Request) {
  const url = new URL(request.url);
  const city = url.searchParams.get("city");

  if (!city) {
    return Response.json({ error: "Missing 'city' query parameter" }, { status: 400 });
  }

  const apiKey = process.env.WEATHER_API_KEY;
  if (!apiKey) {
    console.error("WEATHER_API_KEY is not set");
    return Response.json({ error: "Server configuration error" }, { status: 500 });
  }

  try {
    const response = await fetch(
      `https://api.weatherservice.example/v1/current?city=${encodeURIComponent(city)}&key=${apiKey}`
    );

    if (!response.ok) {
      return Response.json(
        { error: `Upstream error: ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Proxy error:", error);
    return Response.json({ error: "Failed to fetch upstream" }, { status: 502 });
  }
}
