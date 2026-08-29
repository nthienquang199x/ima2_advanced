# Vertex AI vs Public Gemini API — Image Generation Config 포맷 차이 조사

> 조사일: 2026-06-10
> 컨텍스트: Vertex AI 서비스 계정으로 이미지 생성 시 400 에러 발생
> 에러: `Unknown name "responseFormat" at generation_config: Cannot find field.`

## 핵심 발견

Public Gemini API와 Vertex AI REST API에서 이미지 생성 config 구조가 **다르다**.

### Public Gemini API (`generativelanguage.googleapis.com`)

```json
{
  "generation_config": {
    "response_modalities": ["TEXT", "IMAGE"],
    "response_format": {
      "image": {
        "aspect_ratio": "16:9",
        "image_size": "2K"
      }
    }
  }
}
```

- snake_case 필드명 사용 (camelCase도 허용)
- 이미지 설정은 `response_format.image` 안에 위치
- 출처: https://ai.google.dev/gemini-api/docs/gemini-3

### Vertex AI (`aiplatform.googleapis.com`)

```json
{
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"],
    "imageConfig": {
      "aspectRatio": "16:9",
      "imageSize": "2K"
    }
  }
}
```

- camelCase 필드명 사용
- `responseFormat` 필드가 **존재하지 않음** → 400 에러 원인
- 이미지 설정은 `imageConfig`에 직접 위치 (`.image` 중첩 없음)
- 출처: https://github.com/BerriAI/litellm/issues/21070, https://github.com/googleapis/js-genai/issues/1461

## 공통 이미지 파라미터

| 파라미터 | Public API (snake) | Vertex AI (camel) | 값 |
|---------|-------------------|-------------------|-----|
| 비율 | `aspect_ratio` | `aspectRatio` | `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9` |
| 크기 | `image_size` | `imageSize` | `512`, `1K`, `2K`, `4K` |

## 현재 코드 문제점 (`lib/geminiApiImageAdapter.ts:122-132`)

```ts
// 현재 (버그)
const generationConfig = useVertex
  ? {
      responseModalities: ["TEXT", "IMAGE"],
      responseFormat: { image: imageConfig },   // ← Vertex에서 없는 필드!
    }
  : {
      response_modalities: ["TEXT", "IMAGE"],
      response_format: { image: imageConfig },  // ← 동작함
    };
```

## 수정 방향

```ts
// 수정
const generationConfig = useVertex
  ? {
      responseModalities: ["TEXT", "IMAGE"],
      imageConfig: {                            // ← responseFormat → imageConfig
        aspectRatio: imageParams.aspectRatio,    // ← camelCase
        imageSize: imageParams.imageSize,
      },
    }
  : {
      response_modalities: ["TEXT", "IMAGE"],
      response_format: {
        image: {
          aspect_ratio: imageParams.aspectRatio,
          image_size: imageParams.imageSize,
        },
      },
    };
```

## 참고 자료

- 공식 Gemini API 이미지 생성 문서: https://ai.google.dev/gemini-api/docs/image-generation
- Gemini 3 Developer Guide: https://ai.google.dev/gemini-api/docs/gemini-3
- Vertex AI GenerationConfig 레퍼런스: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/GenerationConfig
- litellm Vertex imageConfig 이슈: https://github.com/BerriAI/litellm/issues/21070
- js-genai imageSize 이슈: https://github.com/googleapis/js-genai/issues/1461
