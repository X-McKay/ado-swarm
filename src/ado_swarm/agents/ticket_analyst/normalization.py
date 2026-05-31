from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from ado_swarm.contracts.casefile import NormalizedFinding, RepositoryEvidence, SecurityCasefile
from ado_swarm.contracts.source_provider import SourceIssue

CWE_RE = re.compile(r"\bCWE[-_ ]?(\d{1,5})\b", re.IGNORECASE)
FILE_RE = re.compile(
    r"(?P<path>(?:[\w.-]+/)*[\w.-]+\.(?:py|js|ts|tsx|java|cs|go|rs|rb|php|yml|yaml|tf|json|xml|csproj|pom|gradle|lock))"
)
LINE_RE = re.compile(r"(?:line|ln|:)(?:\s*)(?P<line>\d{1,7})", re.IGNORECASE)
PACKAGE_PATTERNS = [
    re.compile(r"package\s+['`\"]?(?P<package>[A-Za-z0-9_.@/:-]+)", re.IGNORECASE),
    re.compile(r"dependency\s+['`\"]?(?P<package>[A-Za-z0-9_.@/:-]+)", re.IGNORECASE),
    re.compile(r"module\s+['`\"]?(?P<package>[A-Za-z0-9_.@/:-]+)", re.IGNORECASE),
    re.compile(r"library\s+['`\"]?(?P<package>[A-Za-z0-9_.@/:-]+)", re.IGNORECASE),
]
SEVERITIES = ("critical", "high", "medium", "moderate", "low", "informational", "info")
SCANNERS = {
    "dependabot": "dependabot",
    "github advanced security": "github-advanced-security",
    "codeql": "codeql",
    "secret scanning": "secret-scanning",
    "trivy": "trivy",
    "snyk": "snyk",
    "mend": "mend",
    "whiteSource": "mend",
    "semgrep": "semgrep",
    "checkov": "checkov",
    "tfsec": "tfsec",
    "ado": "azure-devops",
}
CATEGORY_KEYWORDS = (
    ("secret", "secret"),
    ("credential", "secret"),
    ("dependency", "dependency"),
    ("package", "dependency"),
    ("container", "container"),
    ("docker", "container"),
    ("terraform", "iac"),
    ("bicep", "iac"),
    ("cloudformation", "iac"),
    ("sast", "sast"),
    ("codeql", "sast"),
    ("injection", "sast"),
    ("xss", "sast"),
)


@dataclass(frozen=True)
class NormalizationEvidence:
    source_fields: list[str]
    derived_fields: list[str]
    missing_fields: list[str]


def _text(issue: SourceIssue) -> str:
    labels = " ".join(issue.labels)
    payload = " ".join(
        str(value) for value in issue.provider_payload.values() if isinstance(value, str)
    )
    return f"{issue.title}\n{issue.body or ''}\n{labels}\n{payload}"


def _first_payload_value(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    lowered = {key.lower(): value for key, value in payload.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def infer_severity(issue: SourceIssue) -> str | None:
    payload_value = _first_payload_value(
        issue.provider_payload, ("severity", "risk", "alert.severity")
    )
    if payload_value:
        return payload_value.lower()
    haystack = _text(issue).lower()
    for severity in SEVERITIES:
        if severity in haystack:
            return (
                "medium"
                if severity == "moderate"
                else "informational"
                if severity == "info"
                else severity
            )
    return None


def infer_scanner(issue: SourceIssue) -> str | None:
    payload_value = _first_payload_value(
        issue.provider_payload, ("scanner", "tool", "tool_name", "analysisTool")
    )
    if payload_value:
        return payload_value
    haystack = _text(issue).lower()
    for marker, scanner in SCANNERS.items():
        if marker.lower() in haystack:
            return scanner
    return None


def infer_category(issue: SourceIssue) -> str | None:
    payload_value = _first_payload_value(
        issue.provider_payload, ("category", "finding_type", "rule_category")
    )
    if payload_value:
        return payload_value.lower()
    haystack = _text(issue).lower()
    for marker, category in CATEGORY_KEYWORDS:
        if marker in haystack:
            return category
    return "security" if "security" in haystack else None


def infer_cwe(issue: SourceIssue) -> str | None:
    payload_value = _first_payload_value(issue.provider_payload, ("cwe", "cwe_id", "weakness"))
    if payload_value:
        match = CWE_RE.search(payload_value)
        return f"CWE-{match.group(1)}" if match else payload_value
    match = CWE_RE.search(_text(issue))
    return f"CWE-{match.group(1)}" if match else None


def infer_package(issue: SourceIssue) -> str | None:
    payload_value = _first_payload_value(
        issue.provider_payload, ("package", "package_name", "dependency")
    )
    if payload_value:
        return payload_value
    text = _text(issue)
    for pattern in PACKAGE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group("package").strip("'`\".,;:()[]{}")
    return None


def infer_file_path(issue: SourceIssue) -> str | None:
    payload_value = _first_payload_value(
        issue.provider_payload, ("file", "file_path", "path", "location.path")
    )
    if payload_value:
        return payload_value
    match = FILE_RE.search(_text(issue))
    return match.group("path") if match else None


def infer_line(issue: SourceIssue) -> int | None:
    payload_value = _first_payload_value(
        issue.provider_payload, ("line", "line_number", "location.line")
    )
    if payload_value and payload_value.isdigit():
        return int(payload_value)
    match = LINE_RE.search(_text(issue))
    return int(match.group("line")) if match else None


def build_finding_id(
    issue: SourceIssue, scanner: str | None, file_path: str | None, package_name: str | None
) -> str:
    raw = "|".join(
        [
            issue.provider.value,
            issue.external_id,
            issue.title,
            scanner or "",
            file_path or "",
            package_name or "",
        ]
    )
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"finding-{digest}"


def confidence_for(finding: NormalizedFinding, issue: SourceIssue) -> float:
    score = 0.35
    if issue.body:
        score += 0.1
    if issue.labels:
        score += 0.1
    if finding.severity:
        score += 0.1
    if finding.scanner:
        score += 0.1
    if finding.category:
        score += 0.1
    if finding.file_path or finding.package_name:
        score += 0.1
    if finding.cwe:
        score += 0.05
    return min(score, 0.95)


def normalize_source_issue(issue: SourceIssue) -> NormalizedFinding:
    scanner = infer_scanner(issue)
    category = infer_category(issue)
    severity = infer_severity(issue)
    cwe = infer_cwe(issue)
    package_name = infer_package(issue)
    file_path = infer_file_path(issue)
    line = infer_line(issue)
    finding = NormalizedFinding(
        finding_id=build_finding_id(issue, scanner, file_path, package_name),
        title=issue.title.strip(),
        description=issue.body,
        scanner=scanner,
        category=category,
        severity=severity,
        cwe=cwe,
        package_name=package_name,
        file_path=file_path,
        line=line,
        confidence=0.0,
    )
    return finding.model_copy(update={"confidence": confidence_for(finding, issue)})


def evidence_for(issue: SourceIssue, finding: NormalizedFinding) -> NormalizationEvidence:
    source_fields = [
        "provider",
        "external_id",
        "url",
        "title",
        "state",
        "labels",
        "provider_payload",
    ]
    if issue.body:
        source_fields.append("body")
    if issue.repository:
        source_fields.append("repository")
    derived_fields = [
        field
        for field in ("scanner", "category", "severity", "cwe", "package_name", "file_path", "line")
        if getattr(finding, field) is not None
    ]
    missing_fields = [
        field
        for field in ("scanner", "category", "severity", "package_name", "file_path")
        if getattr(finding, field) is None
    ]
    return NormalizationEvidence(source_fields, derived_fields, missing_fields)


def build_casefile(
    run_id: str, issue: SourceIssue, *, casefile_id: str | None = None
) -> SecurityCasefile:
    finding = normalize_source_issue(issue)
    evidence = evidence_for(issue, finding)
    repository_evidence = None
    if issue.repository:
        repository_evidence = RepositoryEvidence(
            repository=issue.repository,
            evidence=["repository supplied by source provider issue context"],
        )
    return SecurityCasefile(
        casefile_id=casefile_id
        or f"casefile-{issue.provider.value}-{issue.external_id}".replace("#", "-"),
        run_id=run_id,
        source_issue=issue,
        normalized_finding=finding,
        repository_evidence=repository_evidence,
        audit={
            "ticket_analyst": {
                "source_fields": evidence.source_fields,
                "derived_fields": evidence.derived_fields,
                "missing_fields": evidence.missing_fields,
                "normalizer_version": "0.1.0",
            }
        },
    )
