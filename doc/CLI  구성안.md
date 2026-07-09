https://github.com/panicdna/convert-skill-to-opencode 를 참고하여,
다음의 skill을 완성하라.
https://github.com/panicdna/agent-port

이 skill 의 용법은 다음과 같다.
해야할 기능은 claude-code-vs-opencode.md 과 subagent-authoring-compare.md 두 파일을 참고하라.

agent-port convert <파일> --to {opencode|claude} [--out <경로>]
    # 단일 파일 변환. --from 생략 시 frontmatter로 소스 포맷 자동 감지

agent-port check <파일>
    # 변환 없이 검증만: 필수 필드 누락, 매핑 불가 필드(예: temperature→Claude),
    # 모델 별칭 문제 등을 리포트. exit code로 CI 연동

agent-port batch <디렉터리> --to {opencode|claude} [--out <디렉터리>]
    # .claude/agents/ ↔ .opencode/agents/ 폴더 통째 변환