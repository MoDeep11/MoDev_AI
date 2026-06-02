# MoDev_AI

## Docker

`.env` 파일에 Gemini API 키를 설정합니다.

```env
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
```

컨테이너를 실행합니다.

```bash
docker compose up --build
```

Swagger 문서는 아래 주소에서 확인할 수 있습니다.

```text
http://127.0.0.1:8000/docs
```

AI 호출 없이 API/SSE 흐름만 테스트하려면 `.env`에 아래 값을 추가합니다.

```env
MODEV_USE_AI=false
```
