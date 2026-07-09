# 서브에이전트 작성법 비교: Claude Code vs OpenCode

> 기준일: 2026-07-09 · 두 도구의 서브에이전트 정의 파일(.md) 작성 방식 차이

---

## 1. 핵심 차이 한눈에

| 항목 | **Claude Code** | **OpenCode** |
|---|---|---|
| 파일 위치 | `~/.claude/agents/` (전역)<br>`.claude/agents/` (프로젝트) | `~/.config/opencode/agents/` (전역)<br>`.opencode/agents/` (프로젝트) |
| 정의 방식 | Markdown 파일만 | Markdown 파일 **또는** `opencode.json`의 `agent` 블록 |
| 파일 형식 | YAML frontmatter + 본문(=시스템 프롬프트) | YAML frontmatter + 본문(=시스템 프롬프트) |
| `name` 필드 | **frontmatter에 필수** (`name:`) | **없음** — 파일명이 곧 에이전트 이름 (`review.md` → `review`) |
| 필수 필드 | `name`, `description` | `description` |
| 에이전트 종류 구분 | 서브에이전트 전용 (메인은 별도) | `mode` 필드로 `primary`/`subagent`/`all` 구분 |
| 도구 제어 | `tools:` (허용 목록, 쉼표구분) | `permission:` (read/edit/bash… 별 allow/ask/deny)<br>`tools:`는 deprecated |
| 모델 지정 | `model:` (`sonnet`/`opus`/`haiku` 별칭) | `model:` (`provider/model-id` 전체 경로) |
| 호출 방식 | description 매칭 자동 위임 / Task 도구 | `@이름` 멘션 / 자동 위임 / Task 도구 |
| 생성 도우미 | 대화형 `/agents` 명령 | 대화형 `opencode agent create` |

**요약:** 구조(YAML frontmatter + 프롬프트 본문)는 거의 같지만, ① OpenCode는 `name`을 파일명으로 대체하고 `mode`로 종류를 구분하며, ② 도구 제어를 Claude Code의 단순 허용목록(`tools`) 대신 **세분화된 permission 시스템**으로 한다는 점이 가장 큰 차이다.

---

## 2. Claude Code 서브에이전트 작성

`.claude/agents/code-reviewer.md`:

```markdown
---
name: code-reviewer
description: 코드 변경을 리뷰하고 가독성·성능·베스트프랙티스를 점검. 커밋 전에 사용.
tools: Read, Grep, Glob
model: sonnet
---

You are a senior code reviewer.
변경된 파일을 읽고 다음을 점검하라:
- 정확성과 엣지 케이스
- 성능 영향
- 보안 취약점
직접 수정하지 말고 구체적 피드백만 제시한다.
```

**작성 규칙**
- `name`: frontmatter에 반드시 명시(소문자·하이픈 권장).
- `description`: **메인 에이전트가 위임 여부를 판단하는 근거**. "언제 써야 하는지"를 구체적으로. "use proactively" 같은 표현을 넣으면 자동 호출이 잘 걸린다.
- `tools`: 생략하면 메인 에이전트의 모든 도구를 상속. 명시하면 그 목록으로 제한(최소 권한 원칙).
- `model`: `haiku`/`sonnet`/`opus` 별칭으로 비용·성능 조절. grep 위주 탐색은 haiku로 보내면 비용 절감.
- `---` 아래 본문 전체가 시스템 프롬프트.

---

## 3. OpenCode 서브에이전트 작성

### 방식 A — Markdown 파일 (`.opencode/agents/review.md`)

```markdown
---
description: 코드 품질과 베스트프랙티스를 리뷰
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
permission:
  edit: deny
  bash:
    "*": ask
    "git diff": allow
    "grep *": allow
  webfetch: deny
---

You are in code review mode.
가독성, 잠재적 버그, 성능, 보안을 중심으로
직접 수정 없이 건설적 피드백을 제공하라.
```

> 파일명 `review.md` 가 곧 에이전트 이름 `review`. frontmatter에 `name`을 쓰지 않는다.

### 방식 B — `opencode.json`

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "code-reviewer": {
      "description": "Reviews code for best practices and issues",
      "mode": "subagent",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "{file:./prompts/review.txt}",
      "permission": { "edit": "deny" }
    }
  }
}
```

**작성 규칙**
- `description`: 유일한 필수 필드. 자동 위임 판단 근거.
- `mode`: `subagent`(위임 전용) / `primary`(Tab으로 직접 전환) / `all`(둘 다). 미지정 시 `all`.
- `model`: 반드시 `provider/model-id` 전체 경로. (`opencode models`로 확인)
- `permission`: 도구별로 `allow`/`ask`/`deny`. `bash`·`edit` 등은 glob 패턴으로 명령 단위 제어 가능(예: `"git push": "ask"`). **Claude Code에는 없는 세밀함**.
- `temperature`/`top_p`, `steps`(반복 상한), `disable`, `hidden`(@목록에서 숨김), `color`, 프로바이더 고유 옵션(`reasoningEffort` 등) 지원.
- `prompt`는 `{file:./경로}`로 외부 파일 분리 가능(JSON 방식). Markdown 방식은 본문이 프롬프트.

---

## 4. 필드 매핑 대조표

| 목적 | Claude Code | OpenCode |
|---|---|---|
| 이름 | `name:` | 파일명 (또는 JSON 키) |
| 설명/위임 근거 | `description:` (필수) | `description:` (필수) |
| 종류 구분 | 파일 위치로 서브에이전트 | `mode: subagent` |
| 모델 | `model: sonnet` | `model: anthropic/claude-sonnet-4-...` |
| 도구 허용 | `tools: Read, Grep` | `permission: { read: allow, edit: deny }` |
| 명령 단위 제어 | ✖ (도구 단위까지만) | ✅ `bash: { "git *": ask }` |
| 창의성 조절 | ✖ (frontmatter 미지원) | `temperature`, `top_p` |
| 반복 상한 | (CLI `maxTurns`) | `steps` |
| 시스템 프롬프트 | `---` 아래 본문 | `---` 아래 본문 (또는 `prompt` 파일) |
| 자동 위임 트리거 | description + "proactively" | description 매칭 |
| 수동 호출 | Task 도구 | `@이름` 멘션 |

---

## 5. 마이그레이션 팁 (Claude Code → OpenCode)

1. `name:` 줄을 지우고 파일명을 그 이름으로 바꾼다 (`code-reviewer.md`).
2. `mode: subagent` 를 추가한다.
3. `model: sonnet` → `model: anthropic/claude-sonnet-4-...` 전체 경로로 교체.
4. `tools: Read, Grep, Glob` → `permission:` 로 재작성.
   - 허용할 것만 `allow`, 나머지는 기본 `deny`/`ask`.
   - 예: 읽기 전용 리뷰어라면 `edit: deny`, `bash: deny`.
5. 본문(시스템 프롬프트)은 그대로 재사용 가능.

---

## 출처

- [Create custom subagents — Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [Agents — OpenCode Docs](https://opencode.ai/docs/agents/)
- [Config — OpenCode Docs](https://opencode.ai/docs/config/)
- [Permissions — OpenCode Docs](https://opencode.ai/docs/permissions/)
- [How to Build Custom Sub-Agents in Claude Code — MindStudio](https://www.mindstudio.ai/blog/build-custom-sub-agents-claude-code-yaml)
- [How to Create Custom Agents in OpenCode CLI — BSWEN](https://docs.bswen.com/blog/2026-03-30-opencode-custom-agents/)
