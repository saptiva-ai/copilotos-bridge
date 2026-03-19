#!/usr/bin/env python3
"""
Extract expected results from happy_path_debug/ outputs
Creates a structured database of validated test responses
"""
import json
from pathlib import Path
from typing import Dict, Any, List


def extract_sql_query(metadata: Dict[str, Any]) -> str:
    """Extract SQL query from metadata"""
    return metadata.get('sql_generated', '').strip()


def extract_metric_info(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metric information from chart data"""
    metadata = chart_data.get('metadata', {})
    plotly_config = chart_data.get('plotly_config', {})

    return {
        'metric': metadata.get('metric', ''),
        'metric_type': metadata.get('metric_type', ''),
        'metric_name': chart_data.get('metric_name', ''),
        'title': chart_data.get('title', ''),
        'sql_query': extract_sql_query(metadata),
        'bank_names': chart_data.get('bank_names', []),
        'data_points': len(plotly_config.get('data', [])),
        'has_data': any(
            trace.get('y') and len([y for y in trace['y'] if y is not None]) > 0
            for trace in plotly_config.get('data', [])
        )
    }


def extract_test_result(filepath: Path) -> Dict[str, Any]:
    """Extract relevant information from a test result JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = data.get('result', {})
    sse_parsed = data.get('sse', {}).get('parsed', {})

    extracted = {
        'test_id': result.get('id'),
        'query': result.get('query'),
        'passed': result.get('passed'),
        'type_received': result.get('type_received'),
        'latency_ms': result.get('latency_ms'),
        'issues': result.get('issues', []),
    }

    # Add chart-specific data if present
    if sse_parsed.get('bank_chart'):
        extracted['chart'] = extract_metric_info(sse_parsed['bank_chart'])

    # Add content preview for RAG responses
    if sse_parsed.get('content'):
        content = sse_parsed['content']
        extracted['content_preview'] = content[:200] if len(content) > 200 else content
        extracted['content_length'] = len(content)

    # Add clarification data if present
    if sse_parsed.get('clarification'):
        extracted['clarification'] = sse_parsed['clarification']

    return extracted


def main():
    debug_dir = Path('happy_path_debug')
    output_file = Path('tests/fixtures/happy_path/expected_results.json')

    if not debug_dir.exists():
        print(f"❌ Directory {debug_dir} not found")
        return

    results = []
    json_files = sorted(debug_dir.glob('*.json'))

    print(f"📂 Processing {len(json_files)} test result files...")

    for filepath in json_files:
        try:
            extracted = extract_test_result(filepath)
            results.append(extracted)
            status = "✅" if extracted['passed'] else "❌"
            print(f"{status} [{extracted['test_id']}] {extracted['query'][:50]}...")
        except Exception as e:
            print(f"⚠️  Error processing {filepath.name}: {e}")

    # Sort by test_id
    results.sort(key=lambda x: x['test_id'])

    # Create output
    output = {
        'version': '1.0.0',
        'description': 'Expected results database for Happy Path test suite',
        'total_cases': len(results),
        'passed': sum(1 for r in results if r['passed']),
        'failed': sum(1 for r in results if not r['passed']),
        'results': results
    }

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Extracted {len(results)} test results")
    print(f"📊 Passed: {output['passed']}/{output['total_cases']}")
    print(f"💾 Saved to: {output_file}")

    # Print summary of issues
    all_issues = {}
    for r in results:
        for issue in r.get('issues', []):
            all_issues[issue] = all_issues.get(issue, 0) + 1

    if all_issues:
        print("\n🔍 Issue Summary:")
        for issue, count in sorted(all_issues.items(), key=lambda x: x[1], reverse=True):
            print(f"   ({count}x) {issue}")


if __name__ == '__main__':
    main()
