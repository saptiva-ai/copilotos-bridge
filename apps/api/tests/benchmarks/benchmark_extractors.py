"""
Performance Benchmarking Framework for Text Extractors

Compares performance metrics between ThirdPartyExtractor and SaptivaExtractor
to inform migration decisions and validate performance improvements.

Metrics Tracked:
    - Latency (p50, p95, p99)
    - Throughput (documents/second)
    - Error rate
    - Memory usage
    - API cost per document
    - Cache hit rate

Usage:
    python benchmark_extractors.py --provider third_party --documents 10
    python benchmark_extractors.py --provider saptiva --documents 10
    python benchmark_extractors.py --compare --documents 100
"""

import os
import sys
import time
import asyncio
import argparse
import statistics
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.extractors import (
    get_text_extractor,
    clear_extractor_cache,
    ThirdPartyExtractor,
    SaptivaExtractor,
)


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    provider: str
    document_type: str  # "pdf" or "image"
    document_count: int
    total_time_seconds: float
    mean_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_docs_per_sec: float
    success_count: int
    error_count: int
    error_rate: float
    cache_hit_rate: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    memory_mb: Optional[float] = None


class ExtractionBenchmark:
    """
    Benchmark runner for text extraction performance.

    Supports:
        - Single provider benchmarking
        - Comparison benchmarking (third_party vs saptiva)
        - Custom document sets
        - Warmup runs
        - Result export (JSON, CSV)
    """

    # Cost estimates (USD per document)
    COST_THIRD_PARTY = 0.0  # Free (local)
    COST_SAPTIVA_PDF = 0.02  # Estimate
    COST_SAPTIVA_OCR = 0.05  # Estimate

    def __init__(self, warmup_runs: int = 3):
        """
        Initialize benchmark runner.

        Args:
            warmup_runs: Number of warmup iterations before benchmark
        """
        self.warmup_runs = warmup_runs
        self.results: List[BenchmarkResult] = []

    def generate_test_pdf(self, size: str = "small") -> bytes:
        """
        Generate test PDF of varying sizes.

        Args:
            size: "small" (1 page), "medium" (10 pages), "large" (50 pages)

        Returns:
            PDF bytes
        """
        if size == "small":
            page_count = 1
        elif size == "medium":
            page_count = 10
        elif size == "large":
            page_count = 50
        else:
            page_count = 1

        # Generate simple PDF with multiple pages
        pdf_header = b"%PDF-1.4\n"
        pdf_body = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_body += b"2 0 obj\n<< /Type /Pages /Kids ["

        # Add page references
        for i in range(page_count):
            pdf_body += f"{3 + i} 0 R ".encode()

        pdf_body += f"] /Count {page_count} >>\nendobj\n".encode()

        # Add page objects
        for i in range(page_count):
            page_num = 3 + i
            pdf_body += f"""{page_num} 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
/MediaBox [0 0 612 792] /Contents {page_num + page_count} 0 R >>
endobj
""".encode()

        # Add content streams
        for i in range(page_count):
            stream_num = 3 + page_count + i
            content = f"BT /F1 12 Tf 100 700 Td (Page {i + 1} - Test Content) Tj ET"
            pdf_body += f"""{stream_num} 0 obj
<< /Length {len(content)} >>
stream
{content}
endstream
endobj
""".encode()

        pdf_trailer = f"""xref
0 {3 + page_count * 2}
0000000000 65535 f
trailer
<< /Size {3 + page_count * 2} /Root 1 0 R >>
startxref
%%EOF""".encode()

        return pdf_header + pdf_body + pdf_trailer

    def generate_test_image(self, size: str = "small") -> bytes:
        """Generate test PNG image."""
        # Minimal PNG (1x1 red pixel)
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf'
            b'\xc0\x00\x00\x00\x03\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00'
            b'IEND\xaeB`\x82'
        )

    async def benchmark_provider(
        self,
        provider: str,
        document_type: str,
        document_count: int,
        document_size: str = "small",
    ) -> BenchmarkResult:
        """
        Benchmark a single provider.

        Args:
            provider: "third_party" or "saptiva"
            document_type: "pdf" or "image"
            document_count: Number of documents to extract
            document_size: "small", "medium", or "large"

        Returns:
            BenchmarkResult with performance metrics
        """
        print(f"\n{'='*60}")
        print(f"Benchmarking {provider} - {document_type} ({document_size})")
        print(f"Documents: {document_count}")
        print(f"{'='*60}\n")

        # Set provider via environment
        os.environ["EXTRACTOR_PROVIDER"] = provider
        clear_extractor_cache()
        extractor = get_text_extractor()

        # Generate test documents
        if document_type == "pdf":
            test_data = self.generate_test_pdf(document_size)
            mime = "application/pdf"
        else:
            test_data = self.generate_test_image(document_size)
            mime = "image/png"

        # Warmup runs
        if self.warmup_runs > 0:
            print(f"Warmup: {self.warmup_runs} runs...")
            for _ in range(self.warmup_runs):
                try:
                    await extractor.extract_text(
                        media_type=document_type,
                        data=test_data,
                        mime=mime,
                    )
                except Exception:
                    pass  # Ignore warmup errors

        # Benchmark runs
        latencies_ms = []
        success_count = 0
        error_count = 0

        print(f"Running benchmark: {document_count} documents...")
        start_time = time.time()

        for i in range(document_count):
            doc_start = time.time()

            try:
                await extractor.extract_text(
                    media_type=document_type,
                    data=test_data,
                    mime=mime,
                    filename=f"bench_{i}.{document_type}",
                )

                doc_end = time.time()
                latency_ms = (doc_end - doc_start) * 1000
                latencies_ms.append(latency_ms)
                success_count += 1

                # Progress indicator
                if (i + 1) % 10 == 0:
                    print(f"  Processed: {i + 1}/{document_count} ({latency_ms:.0f}ms)")

            except Exception as exc:
                error_count += 1
                print(f"  Error on document {i}: {exc}")

        total_time = time.time() - start_time

        # Calculate metrics
        if latencies_ms:
            sorted_latencies = sorted(latencies_ms)
            mean_latency = statistics.mean(latencies_ms)
            median_latency = statistics.median(latencies_ms)
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]
            min_latency = min(latencies_ms)
            max_latency = max(latencies_ms)
        else:
            mean_latency = median_latency = p95_latency = p99_latency = 0
            min_latency = max_latency = 0

        throughput = success_count / total_time if total_time > 0 else 0
        error_rate = error_count / document_count if document_count > 0 else 0

        # Estimate cost
        if provider == "saptiva":
            cost_per_doc = (
                self.COST_SAPTIVA_PDF if document_type == "pdf" else self.COST_SAPTIVA_OCR
            )
            estimated_cost = success_count * cost_per_doc
        else:
            estimated_cost = 0.0

        # Cache metrics (if available)
        cache_hit_rate = None
        if hasattr(extractor, "_cache"):
            cache_hit_rate = extractor._cache.get_hit_rate()

        result = BenchmarkResult(
            provider=provider,
            document_type=document_type,
            document_count=document_count,
            total_time_seconds=total_time,
            mean_latency_ms=mean_latency,
            median_latency_ms=median_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            throughput_docs_per_sec=throughput,
            success_count=success_count,
            error_count=error_count,
            error_rate=error_rate,
            cache_hit_rate=cache_hit_rate,
            estimated_cost_usd=estimated_cost,
        )

        self.results.append(result)
        self._print_result(result)

        return result

    def _print_result(self, result: BenchmarkResult):
        """Print formatted benchmark results."""
        print(f"\n{'-'*60}")
        print(f"RESULTS: {result.provider} - {result.document_type}")
        print(f"{'-'*60}")
        print(f"Documents:        {result.document_count}")
        print(f"Success:          {result.success_count}")
        print(f"Errors:           {result.error_count} ({result.error_rate:.1%})")
        print(f"Total Time:       {result.total_time_seconds:.2f}s")
        print(f"Throughput:       {result.throughput_docs_per_sec:.2f} docs/sec")
        print(f"\nLatency:")
        print(f"  Mean:           {result.mean_latency_ms:.0f}ms")
        print(f"  Median (p50):   {result.median_latency_ms:.0f}ms")
        print(f"  p95:            {result.p95_latency_ms:.0f}ms")
        print(f"  p99:            {result.p99_latency_ms:.0f}ms")
        print(f"  Min:            {result.min_latency_ms:.0f}ms")
        print(f"  Max:            {result.max_latency_ms:.0f}ms")

        if result.cache_hit_rate is not None:
            print(f"\nCache Hit Rate:   {result.cache_hit_rate:.1%}")

        if result.estimated_cost_usd is not None:
            print(f"Estimated Cost:   ${result.estimated_cost_usd:.2f}")

        print(f"{'-'*60}\n")

    async def compare_providers(
        self,
        document_type: str,
        document_count: int,
        document_size: str = "small",
    ):
        """
        Compare ThirdPartyExtractor vs SaptivaExtractor.

        Args:
            document_type: "pdf" or "image"
            document_count: Number of documents to test
            document_size: Document size variant
        """
        print(f"\n{'='*60}")
        print(f"COMPARISON BENCHMARK: third_party vs saptiva")
        print(f"Document Type: {document_type}")
        print(f"Document Count: {document_count}")
        print(f"Document Size: {document_size}")
        print(f"{'='*60}\n")

        # Benchmark third_party
        result_third_party = await self.benchmark_provider(
            "third_party", document_type, document_count, document_size
        )

        # Benchmark saptiva
        result_saptiva = await self.benchmark_provider(
            "saptiva", document_type, document_count, document_size
        )

        # Print comparison
        self._print_comparison(result_third_party, result_saptiva)

    def _print_comparison(self, result1: BenchmarkResult, result2: BenchmarkResult):
        """Print side-by-side comparison of results."""
        print(f"\n{'='*60}")
        print(f"COMPARISON SUMMARY")
        print(f"{'='*60}\n")

        metrics = [
            ("Mean Latency", "mean_latency_ms", "ms", "lower"),
            ("Median Latency", "median_latency_ms", "ms", "lower"),
            ("p95 Latency", "p95_latency_ms", "ms", "lower"),
            ("Throughput", "throughput_docs_per_sec", "docs/sec", "higher"),
            ("Error Rate", "error_rate", "%", "lower"),
            ("Estimated Cost", "estimated_cost_usd", "USD", "lower"),
        ]

        print(f"{'Metric':<20} {'Third Party':>15} {'Saptiva':>15} {'Winner':>15}")
        print(f"{'-'*70}")

        for name, attr, unit, better in metrics:
            val1 = getattr(result1, attr)
            val2 = getattr(result2, attr)

            if val1 is None or val2 is None:
                continue

            # Format values
            if unit == "%":
                val1_str = f"{val1*100:.1f}%"
                val2_str = f"{val2*100:.1f}%"
            elif unit == "USD":
                val1_str = f"${val1:.2f}"
                val2_str = f"${val2:.2f}"
            else:
                val1_str = f"{val1:.1f} {unit}"
                val2_str = f"{val2:.1f} {unit}"

            # Determine winner
            if better == "lower":
                winner = result1.provider if val1 < val2 else result2.provider
            else:
                winner = result1.provider if val1 > val2 else result2.provider

            print(f"{name:<20} {val1_str:>15} {val2_str:>15} {winner:>15}")

        print(f"{'-'*70}\n")

    def export_results(self, output_path: str, format: str = "json"):
        """
        Export benchmark results to file.

        Args:
            output_path: Path to output file
            format: "json" or "csv"
        """
        if format == "json":
            with open(output_path, "w") as f:
                json.dump([asdict(r) for r in self.results], f, indent=2)
            print(f"✓ Results exported to {output_path}")

        elif format == "csv":
            import csv

            with open(output_path, "w", newline="") as f:
                if self.results:
                    writer = csv.DictWriter(f, fieldnames=asdict(self.results[0]).keys())
                    writer.writeheader()
                    for result in self.results:
                        writer.writerow(asdict(result))
                print(f"✓ Results exported to {output_path}")


async def main():
    """CLI entry point for benchmark runner."""
    parser = argparse.ArgumentParser(description="Benchmark text extraction performance")

    parser.add_argument(
        "--provider",
        choices=["third_party", "saptiva"],
        help="Provider to benchmark",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare third_party vs saptiva",
    )
    parser.add_argument(
        "--document-type",
        choices=["pdf", "image"],
        default="pdf",
        help="Document type to test",
    )
    parser.add_argument(
        "--document-size",
        choices=["small", "medium", "large"],
        default="small",
        help="Document size variant",
    )
    parser.add_argument(
        "--documents",
        type=int,
        default=10,
        help="Number of documents to process",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=3,
        help="Number of warmup runs",
    )
    parser.add_argument(
        "--output",
        help="Output file for results (JSON or CSV)",
    )

    args = parser.parse_args()

    # Create benchmark runner
    benchmark = ExtractionBenchmark(warmup_runs=args.warmup)

    # Run benchmarks
    if args.compare:
        await benchmark.compare_providers(
            args.document_type,
            args.documents,
            args.document_size,
        )
    elif args.provider:
        await benchmark.benchmark_provider(
            args.provider,
            args.document_type,
            args.documents,
            args.document_size,
        )
    else:
        parser.error("Must specify --provider or --compare")

    # Export results
    if args.output:
        format = "json" if args.output.endswith(".json") else "csv"
        benchmark.export_results(args.output, format)


if __name__ == "__main__":
    asyncio.run(main())
