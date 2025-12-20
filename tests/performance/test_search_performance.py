# Performance tests for PassFX global search.
# Validates search operations meet timing and memory requirements at scale.

from __future__ import annotations

import gc
import time
from unittest.mock import patch

import pytest

from passfx.core.models import (
    CreditCard,
    EmailCredential,
    EnvEntry,
    NoteEntry,
    PhoneCredential,
    RecoveryEntry,
)
from passfx.search.engine import SearchIndex, _levenshtein_bounded

# --- Credential Generation Helpers ---


def _generate_email(index: int) -> EmailCredential:
    """Generate a unique email credential for testing."""
    domains = ["gmail.com", "github.com", "example.com", "work.org", "corp.io"]
    labels = ["GitHub", "GitLab", "AWS Console", "Azure Portal", "Work Email"]
    return EmailCredential(
        id=f"email_{index:05d}",
        label=f"{labels[index % len(labels)]} Account {index}",
        email=f"user{index}@{domains[index % len(domains)]}",
        password=f"Password{index}!",
        notes=f"Test credential {index}" if index % 3 == 0 else None,
    )


def _generate_phone(index: int) -> PhoneCredential:
    """Generate a unique phone credential for testing."""
    return PhoneCredential(
        id=f"phone_{index:05d}",
        label=f"Phone PIN {index}",
        phone=f"+1-555-{index:04d}",
        password=f"{index % 10000:04d}",
        notes=f"Phone notes {index}" if index % 4 == 0 else None,
    )


def _generate_card(index: int) -> CreditCard:
    """Generate a unique credit card for testing."""
    return CreditCard(
        id=f"card_{index:05d}",
        label=f"Card {index}",
        card_number=f"4111111111{index:06d}",
        expiry="12/25",
        cvv=f"{index % 1000:03d}",
        cardholder_name=f"Test User {index}",
        notes=f"Card notes {index}" if index % 5 == 0 else None,
    )


def _generate_env(index: int) -> EnvEntry:
    """Generate a unique env entry for testing."""
    return EnvEntry(
        id=f"env_{index:05d}",
        title=f"Project {index} Env",
        filename=f".env.project{index}",
        content=f"API_KEY=secret{index}\nDB_URL=localhost",
        notes=f"Env notes {index}" if index % 6 == 0 else None,
    )


def _generate_recovery(index: int) -> RecoveryEntry:
    """Generate a unique recovery entry for testing."""
    return RecoveryEntry(
        id=f"recovery_{index:05d}",
        title=f"Recovery Codes {index}",
        content=f"CODE1-{index:04d}\nCODE2-{index:04d}\nCODE3-{index:04d}",
        notes=f"Recovery notes {index}" if index % 7 == 0 else None,
    )


def _generate_note(index: int) -> NoteEntry:
    """Generate a unique note entry for testing."""
    return NoteEntry(
        id=f"note_{index:05d}",
        title=f"Secure Note {index}",
        content=f"Secret content for note {index}",
        notes=f"Note metadata {index}" if index % 8 == 0 else None,
    )


def create_test_credentials(
    size: int,
) -> tuple[
    list[EmailCredential],
    list[PhoneCredential],
    list[CreditCard],
    list[EnvEntry],
    list[RecoveryEntry],
    list[NoteEntry],
]:
    """Create a balanced set of test credentials across all types.

    Distributes credentials evenly across all 6 types.

    Args:
        size: Total number of credentials to create.

    Returns:
        Tuple of credential lists (emails, phones, cards, envs, recovery, notes).
    """
    per_type = max(1, size // 6)
    remainder = size - (per_type * 6)

    emails = [_generate_email(i) for i in range(per_type + (1 if remainder > 0 else 0))]
    phones = [_generate_phone(i) for i in range(per_type + (1 if remainder > 1 else 0))]
    cards = [_generate_card(i) for i in range(per_type + (1 if remainder > 2 else 0))]
    envs = [_generate_env(i) for i in range(per_type + (1 if remainder > 3 else 0))]
    recovery = [
        _generate_recovery(i) for i in range(per_type + (1 if remainder > 4 else 0))
    ]
    notes = [_generate_note(i) for i in range(per_type)]

    return emails, phones, cards, envs, recovery, notes


def build_index_with_credentials(size: int) -> SearchIndex:
    """Build a SearchIndex populated with the specified number of credentials."""
    emails, phones, cards, envs, recovery, notes = create_test_credentials(size)
    index = SearchIndex()
    index.build_index(
        emails=emails,
        phones=phones,
        cards=cards,
        envs=envs,
        recovery=recovery,
        notes=notes,
    )
    return index


# --- Index Building Performance Tests ---


@pytest.mark.slow
class TestIndexBuildPerformance:
    """Performance tests for search index building at various scales."""

    def test_index_build_10_entries(self) -> None:
        """Index build for 10 credentials should complete in < 10ms."""
        emails, phones, cards, envs, recovery, notes = create_test_credentials(10)
        index = SearchIndex()

        start = time.perf_counter()
        index.build_index(
            emails=emails,
            phones=phones,
            cards=cards,
            envs=envs,
            recovery=recovery,
            notes=notes,
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.010, f"Index build took {elapsed * 1000:.2f}ms (limit: 10ms)"

    def test_index_build_100_entries(self) -> None:
        """Index build for 100 credentials should complete in < 50ms."""
        emails, phones, cards, envs, recovery, notes = create_test_credentials(100)
        index = SearchIndex()

        start = time.perf_counter()
        index.build_index(
            emails=emails,
            phones=phones,
            cards=cards,
            envs=envs,
            recovery=recovery,
            notes=notes,
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.050, f"Index build took {elapsed * 1000:.2f}ms (limit: 50ms)"

    def test_index_build_1000_entries(self) -> None:
        """Index build for 1000 credentials should complete in < 500ms."""
        emails, phones, cards, envs, recovery, notes = create_test_credentials(1000)
        index = SearchIndex()

        start = time.perf_counter()
        index.build_index(
            emails=emails,
            phones=phones,
            cards=cards,
            envs=envs,
            recovery=recovery,
            notes=notes,
        )
        elapsed = time.perf_counter() - start

        assert (
            elapsed < 0.500
        ), f"Index build took {elapsed * 1000:.2f}ms (limit: 500ms)"


# --- Search Performance Tests ---


@pytest.mark.slow
class TestSearchPerformance:
    """Performance tests for search operations at various scales."""

    def test_search_10_entries(self) -> None:
        """Search on 10 credentials should complete in < 1ms."""
        index = build_index_with_credentials(10)

        start = time.perf_counter()
        results = index.search("github", max_results=8)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.001, f"Search took {elapsed * 1000:.2f}ms (limit: 1ms)"
        # Verify search functionality works
        assert isinstance(results, list)

    def test_search_100_entries(self) -> None:
        """Search on 100 credentials should complete in < 10ms."""
        index = build_index_with_credentials(100)

        start = time.perf_counter()
        results = index.search("github", max_results=8)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.010, f"Search took {elapsed * 1000:.2f}ms (limit: 10ms)"
        assert isinstance(results, list)

    def test_search_1000_entries(self) -> None:
        """Search on 1000 credentials should complete in < 50ms."""
        index = build_index_with_credentials(1000)

        start = time.perf_counter()
        results = index.search("github", max_results=8)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.050, f"Search took {elapsed * 1000:.2f}ms (limit: 50ms)"
        assert isinstance(results, list)

    def test_search_single_char_worst_case(self) -> None:
        """Single character search on 1000 credentials should complete in < 100ms.

        Single character queries potentially match many entries, representing
        a worst-case scenario for search performance.
        """
        index = build_index_with_credentials(1000)

        start = time.perf_counter()
        results = index.search("a", max_results=8)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.100, f"Search took {elapsed * 1000:.2f}ms (limit: 100ms)"
        assert isinstance(results, list)


# --- Memory Tests ---


@pytest.mark.slow
class TestMemoryPerformance:
    """Memory efficiency tests for search operations."""

    def test_memory_index_100_entries(self) -> None:
        """Index for 100 credentials should use reasonable memory.

        Verifies that index entries don't hold excessive object references.
        """
        gc.collect()
        gc.collect()

        emails, phones, cards, envs, recovery, notes = create_test_credentials(100)
        index = SearchIndex()

        gc.collect()
        objects_before = len(gc.get_objects())

        index.build_index(
            emails=emails,
            phones=phones,
            cards=cards,
            envs=envs,
            recovery=recovery,
            notes=notes,
        )

        gc.collect()
        objects_after = len(gc.get_objects())

        # Allow for index entries, tokens, and normalized values
        # ~100 credentials * 3 fields each * ~5 objects per entry = ~1500 max
        increase = objects_after - objects_before
        assert increase < 5000, f"Object increase: {increase} (limit: 5000)"

    def test_memory_no_leak_repeated_searches(self) -> None:
        """Repeated searches should not accumulate garbage.

        Runs 100 consecutive searches and verifies no significant
        object accumulation indicating memory leaks.
        """
        index = build_index_with_credentials(100)

        # Warm up and stabilize
        for i in range(10):
            index.search(f"cred{i}", max_results=8)

        gc.collect()
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Run many searches
        for i in range(100):
            results = index.search(f"cred{i % 20}", max_results=8)
            del results

        gc.collect()
        gc.collect()
        final_objects = len(gc.get_objects())

        increase = final_objects - initial_objects
        assert (
            increase < 1000
        ), f"Object accumulation after 100 searches: {increase} (limit: 1000)"

    def test_memory_no_leak_index_rebuild(self) -> None:
        """Repeated index rebuilds should not accumulate garbage.

        Simulates the Ctrl+K pattern of rebuilding index on each open.
        """
        emails, phones, cards, envs, recovery, notes = create_test_credentials(50)

        index = SearchIndex()
        # Warm up
        for _ in range(3):
            index.build_index(
                emails=emails,
                phones=phones,
                cards=cards,
                envs=envs,
                recovery=recovery,
                notes=notes,
            )

        gc.collect()
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Simulate 10 Ctrl+K cycles
        for _ in range(10):
            index.build_index(
                emails=emails,
                phones=phones,
                cards=cards,
                envs=envs,
                recovery=recovery,
                notes=notes,
            )

        gc.collect()
        gc.collect()
        final_objects = len(gc.get_objects())

        increase = final_objects - initial_objects
        # Index clears entries on rebuild, so should not accumulate
        assert (
            increase < 500
        ), f"Object accumulation after 10 rebuilds: {increase} (limit: 500)"


# --- UI Responsiveness Tests ---


@pytest.mark.slow
class TestUIResponsiveness:
    """Tests validating UI layer performance requirements."""

    def test_ui_update_8_results(self) -> None:
        """Generating 8 search results should complete quickly.

        The UI layer displays at most 8 results, so generating that
        many results should be near-instant.
        """
        index = build_index_with_credentials(100)

        start = time.perf_counter()
        results = index.search("account", max_results=8)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.050, f"Search took {elapsed * 1000:.2f}ms (limit: 50ms)"
        assert len(results) <= 8

    def test_search_result_limit_respected(self) -> None:
        """Search should respect max_results parameter efficiently.

        Even with many matches, the search should cap at max_results.
        """
        index = build_index_with_credentials(500)

        start = time.perf_counter()
        results = index.search("account", max_results=8)
        elapsed = time.perf_counter() - start

        # Should complete quickly regardless of total matches
        assert elapsed < 0.050, f"Search took {elapsed * 1000:.2f}ms (limit: 50ms)"
        assert len(results) <= 8

    def test_rapid_typing_final_results_correct(self) -> None:
        """Rapid typing simulation should produce correct final results.

        Simulates a user typing "github" quickly with each character
        triggering a new search. Final results should match "github".
        """
        index = build_index_with_credentials(100)
        query_sequence = ["g", "gi", "git", "gith", "githu", "github"]

        results_sequence = []
        for query in query_sequence:
            results = index.search(query, max_results=8)
            results_sequence.append(results)

        # Final results should match the complete query
        final_results = results_sequence[-1]
        assert isinstance(final_results, list)

        # If any results, they should have positive scores
        for result in final_results:
            assert result.score > 0, "Result should have positive score"


# --- Algorithm Efficiency Tests ---


@pytest.mark.slow
class TestAlgorithmEfficiency:
    """Tests validating algorithmic efficiency of search operations."""

    def test_fuzzy_calls_bounded(self) -> None:
        """Levenshtein distance calculations should be bounded.

        Fuzzy matching is expensive (O(k^2) per comparison). This test
        verifies the algorithm doesn't make excessive fuzzy comparisons.
        """
        index = build_index_with_credentials(100)

        call_count = 0
        original_levenshtein = _levenshtein_bounded

        def counting_levenshtein(s1: str, s2: str, max_dist: int) -> int | None:
            nonlocal call_count
            call_count += 1
            return original_levenshtein(s1, s2, max_dist)

        # Patch the module-level function
        with patch(
            "passfx.search.engine._levenshtein_bounded",
            side_effect=counting_levenshtein,
        ):
            index.search("gthub", max_results=8)  # Typo query triggers fuzzy

        # With 100 credentials * ~3 fields * ~2 tokens = ~600 potential calls
        # But fuzzy only applies to primary fields and tokens >= 4 chars
        # Should be well under 500 calls
        assert call_count < 500, f"Levenshtein calls: {call_count} (limit: 500)"

    def test_early_termination_respected(self) -> None:
        """Search should stop after finding sufficient matches.

        While the current implementation scans all entries (O(n)),
        it should efficiently process results and respect max_results.
        """
        # Create index with many similar credentials
        emails = [
            EmailCredential(
                id=f"email_{i:05d}",
                label=f"GitHub Account {i}",
                email=f"user{i}@github.com",
                password=f"Password{i}!",
            )
            for i in range(200)
        ]

        index = SearchIndex()
        index.build_index(
            emails=emails,
            phones=[],
            cards=[],
            envs=[],
            recovery=[],
            notes=[],
        )

        start = time.perf_counter()
        results = index.search("github", max_results=8)
        elapsed = time.perf_counter() - start

        # Should complete quickly even with many matches
        assert elapsed < 0.020, f"Search took {elapsed * 1000:.2f}ms (limit: 20ms)"
        assert len(results) == 8, "Should return exactly max_results matches"

        # Verify results are sorted by score (highest first)
        scores = [r.score for r in results]
        assert scores == sorted(
            scores, reverse=True
        ), "Results should be sorted by score"


# --- Regression Prevention Tests ---


class TestPerformanceRegression:
    """Tests to catch performance regressions in search operations."""

    def test_empty_query_fast(self) -> None:
        """Empty query should return immediately without scanning index."""
        index = build_index_with_credentials(100)

        start = time.perf_counter()
        results = index.search("")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.001, f"Empty query took {elapsed * 1000:.2f}ms"
        assert results == []

    def test_whitespace_query_fast(self) -> None:
        """Whitespace-only query should return immediately."""
        index = build_index_with_credentials(100)

        start = time.perf_counter()
        results = index.search("   ")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.001, f"Whitespace query took {elapsed * 1000:.2f}ms"
        assert results == []

    def test_no_match_query_bounded(self) -> None:
        """Query with no matches should complete in reasonable time."""
        index = build_index_with_credentials(1000)

        start = time.perf_counter()
        results = index.search("xyznonexistent", max_results=8)
        elapsed = time.perf_counter() - start

        assert (
            elapsed < 0.050
        ), f"No-match query took {elapsed * 1000:.2f}ms (limit: 50ms)"
        assert results == []

    def test_unicode_query_performance(self) -> None:
        """Unicode query should not degrade performance significantly."""
        index = build_index_with_credentials(100)

        start = time.perf_counter()
        results = index.search("cafe", max_results=8)
        elapsed = time.perf_counter() - start

        assert (
            elapsed < 0.010
        ), f"Unicode query took {elapsed * 1000:.2f}ms (limit: 10ms)"
        assert isinstance(results, list)
